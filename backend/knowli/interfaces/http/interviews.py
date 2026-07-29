"""Team interview inbox; every member can request or complete one."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from .auth import member
from ...infrastructure.postgres.pool import pool

router = APIRouter(prefix="/api/interviews", tags=["interviews"])

class NewInterview(BaseModel):
    assignee_id: str
    title: str
    brief: str = ""

@router.get("")
def listing(request: Request) -> dict:
    user = member(request)
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT i.id::text,i.title,i.brief,i.status,i.created_at,u.display_name FROM interview i JOIN app_user u ON u.id=i.requester_id WHERE i.assignee_id=%s ORDER BY i.created_at DESC", (user["id"],))
        return {"items": [{"id": r[0], "title": r[1], "brief": r[2], "status": r[3], "created_at": r[4], "requester": r[5]} for r in cur.fetchall()]}

@router.post("")
def create(body: NewInterview, request: Request) -> dict:
    user = member(request)
    if not body.title.strip(): raise HTTPException(400, "a topic is required")
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM team_member WHERE team_id=%s AND user_id=%s", (user["team"]["id"], body.assignee_id))
        if not cur.fetchone(): raise HTTPException(404, "person is not in this team")
        cur.execute("INSERT INTO interview (team_id,requester_id,assignee_id,title,brief) VALUES (%s,%s,%s,%s,%s) RETURNING id", (user["team"]["id"], user["id"], body.assignee_id, body.title.strip(), body.brief.strip()))
        return {"id": str(cur.fetchone()[0])}
