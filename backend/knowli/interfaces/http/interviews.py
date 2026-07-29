"""Team interview inbox; every member can request or complete one."""
import uuid
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from .auth import member
from ...infrastructure.postgres.pool import pool
from ...application import review

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

@router.post("/{interview_id}/start")
def start(interview_id: str, request: Request) -> dict:
    user = member(request)
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id,title,brief,status FROM interview WHERE id=%s AND assignee_id=%s AND team_id=%s", (interview_id, user["id"], user["team"]["id"]))
        row = cur.fetchone()
        if not row: raise HTTPException(404, "interview not found")
        if row[3] == "done": raise HTTPException(409, "interview is complete")
        session_id = str(uuid.uuid4())
        cur.execute("UPDATE interview SET status='started', started_at=coalesce(started_at,now()), session_id=%s WHERE id=%s", (session_id, interview_id))
        cur.execute("INSERT INTO audit_event (team_id,actor_id,kind,subject_id) VALUES (%s,%s,'interview_started',%s)", (user["team"]["id"], user["id"], interview_id))
    # The brief is context, not a claim: the assignee still writes the answer.
    review.drain(review.start(session_id, f"Interview topic: {row[1]}\n\nBrief: {row[2]}\n\n", user["name"], "interview", user["team"]["knowledge_base"]))
    return {"session_id": session_id}
