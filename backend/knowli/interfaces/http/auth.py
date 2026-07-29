"""Local account and cookie-session endpoints for a self-hosted install."""
import base64
import hashlib
import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from ...infrastructure.postgres.pool import pool

router = APIRouter(prefix="/api/auth", tags=["auth"])
COOKIE = "knowli_session"


def _hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.b64encode(salt + digest).decode()


def _valid(password: str, saved: str) -> bool:
    raw = base64.b64decode(saved)
    return secrets.compare_digest(_hash(password, raw[:16]), saved)


def _token() -> tuple[str, str]:
    value = secrets.token_urlsafe(32)
    return value, hashlib.sha256(value.encode()).hexdigest()


class Credentials(BaseModel):
    email: str
    password: str
    display_name: str = ""
    organisation_name: str = ""


def _set(response: Response, token: str) -> None:
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 14)


def member(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "sign in required")
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT u.id, u.display_name, u.email, t.id, t.name, kb.slug
               FROM app_session s JOIN app_user u ON u.id=s.user_id
               JOIN team_member m ON m.user_id=u.id JOIN team t ON t.id=m.team_id
               JOIN knowledge_base kb ON kb.id=t.knowledge_base_id
               WHERE s.token_hash=%s AND s.expires_at > now() LIMIT 1""",
            (hashlib.sha256(token.encode()).hexdigest(),),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(401, "sign in required")
    return {"id": str(row[0]), "name": row[1], "email": row[2], "team": {"id": str(row[3]), "name": row[4], "knowledge_base": row[5]}}


@router.post("/register")
def register(body: Credentials, response: Response) -> dict:
    if not body.email.strip() or len(body.password) < 8 or not body.display_name.strip():
        raise HTTPException(400, "email, name and an 8-character password are required")
    token, token_hash = _token()
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO app_user (email, display_name, password_hash) VALUES (%s,%s,%s) RETURNING id", (body.email.strip().lower(), body.display_name.strip(), _hash(body.password)))
        user_id = cur.fetchone()[0]
        cur.execute("INSERT INTO organisation (name) VALUES (%s) RETURNING id", (body.organisation_name.strip() or body.display_name.strip(),))
        org = cur.fetchone()[0]
        slug = hashlib.sha256(str(org).encode()).hexdigest()[:12]
        cur.execute("SELECT id FROM workspace ORDER BY created_at LIMIT 1")
        workspace = cur.fetchone()[0]
        cur.execute("INSERT INTO knowledge_base (workspace_id,slug,name) VALUES (%s,%s,%s) RETURNING id", (workspace, slug, "Equipo principal"))
        kb = cur.fetchone()[0]
        cur.execute("INSERT INTO team (organisation_id, name, knowledge_base_id) VALUES (%s,%s,%s) RETURNING id", (org, "Equipo principal", kb))
        team = cur.fetchone()[0]
        cur.execute("INSERT INTO team_member (team_id, user_id) VALUES (%s,%s)", (team, user_id))
        cur.execute("INSERT INTO app_session (token_hash,user_id,expires_at) VALUES (%s,%s,now()+interval '14 days')", (token_hash, user_id))
    _set(response, token)
    return {"user": {"id": str(user_id), "name": body.display_name.strip(), "email": body.email.strip().lower()}}


@router.post("/login")
def login(body: Credentials, response: Response) -> dict:
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, display_name, password_hash FROM app_user WHERE email=%s", (body.email.strip().lower(),))
        row = cur.fetchone()
        if not row or not _valid(body.password, row[2]):
            raise HTTPException(401, "invalid email or password")
        token, token_hash = _token()
        cur.execute("INSERT INTO app_session (token_hash,user_id,expires_at) VALUES (%s,%s,now()+interval '14 days')", (token_hash, row[0]))
    _set(response, token)
    return {"user": {"id": str(row[0]), "name": row[1], "email": body.email.strip().lower()}}


@router.get("/me")
def me(request: Request) -> dict:
    return {"user": member(request)}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    if token := request.cookies.get(COOKIE):
        with pool().connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM app_session WHERE token_hash=%s", (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie(COOKIE)
    return {"ok": True}
