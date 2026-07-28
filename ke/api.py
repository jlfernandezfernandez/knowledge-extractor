"""HTTP API + the review UI. Sync endpoints on purpose: FastAPI runs them in a
threadpool, and every dependency here (httpx, psycopg, fastembed) is sync."""

import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config, db, embed, pipeline

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="Knowledge Extractor", lifespan=lifespan)


class Capture(BaseModel):
    text: str
    author: str | None = None
    source: str | None = None


class Atoms(BaseModel):
    atoms: list[dict]


class Decisions(BaseModel):
    # key "<atom_id>::<existing_id>" -> {"action": ..., "statement": ...}
    decisions: dict[str, dict]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.post("/api/transcribe")
def transcribe(file: UploadFile) -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise HTTPException(
            501, "Transcription needs the audio extra: uv pip install -e '.[audio]'"
        )
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
        path = tmp.name
    try:
        model = _whisper(WhisperModel)
        segments, _ = model.transcribe(path, vad_filter=True)
        return {"text": " ".join(s.text.strip() for s in segments).strip()}
    finally:
        Path(path).unlink(missing_ok=True)


_whisper_model = None


def _whisper(cls):
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = cls(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _whisper_model


@app.post("/api/capture")
def capture(body: Capture) -> dict:
    """Phase 1: what did the AI understand?"""
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    session_id = pipeline.understand(body.text, body.author, body.source)
    return {"session_id": session_id, "atoms": _session(session_id)["payload"]["atoms"]}


@app.post("/api/sessions/{session_id}/atoms")
def confirm_atoms(session_id: str, body: Atoms) -> dict:
    """Phase 2: the user accepted (possibly edited) the claims — now check the RAG."""
    session = _session(session_id)
    payload = session["payload"]
    payload["atoms"] = body.atoms
    payload["conflicts"] = pipeline.find_conflicts(body.atoms)
    db.update_session(session_id, "reviewed", payload)
    return {"session_id": session_id, "conflicts": payload["conflicts"]}


@app.post("/api/sessions/{session_id}/resolve")
def resolve(session_id: str, body: Decisions) -> dict:
    """Phase 3: apply the user's conflict decisions and write to the RAG."""
    session = _session(session_id)
    payload = session["payload"]
    if payload.get("committed"):
        raise HTTPException(409, "this session was already committed")
    try:
        actions = pipeline.plan(payload["atoms"], payload["conflicts"], body.decisions)
    except ValueError as error:
        raise HTTPException(400, str(error))
    committed = pipeline.commit(actions, payload.get("author"), payload.get("source"))
    payload["committed"] = committed
    db.update_session(session_id, "committed", payload)
    return {"session_id": session_id, "committed": committed}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    return _session(session_id)


@app.get("/api/knowledge")
def knowledge(limit: int = 200) -> dict:
    return {"items": db.live(limit)}


@app.get("/api/search")
def search(q: str, k: int = 10) -> dict:
    vector = embed.embed([q])[0]
    # Search is a plain nearest-neighbour lookup: no distance cutoff.
    return {"items": db.neighbours(vector, k, max_distance=2.0)}


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "llm_model": config.LLM_MODEL,
        "embed_model": config.EMBED_MODEL,
        "embed_dim": config.EMBED_DIM,
    }


def _session(session_id: str) -> dict:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(404, "no such session")
    return session


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
