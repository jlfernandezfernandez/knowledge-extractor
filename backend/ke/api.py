"""HTTP API.

Sync endpoints on purpose: FastAPI runs `def` handlers in a threadpool, and
every dependency here (LangGraph's sync checkpointer, psycopg, fastembed) is
sync. Async handlers would need an async checkpointer and pool for no gain at
this scale.
"""

import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command

from . import ask as ask_module
from . import config, graph, store
from .schemas import (
    AskRequest,
    AskResponse,
    CaptureRequest,
    ConfirmRequest,
    ResolveRequest,
    SessionState,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init()
    graph.graph()  # builds the graph and runs the checkpointer migrations
    yield


app = FastAPI(
    title="Knowledge Extractor",
    version="0.2.0",
    description="Human-in-the-loop knowledge capture over a pgvector hybrid RAG.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _pending(session_id: str):
    """The interrupt this session is currently parked on, if any."""
    snapshot = graph.graph().get_state(_config(session_id))
    if not snapshot.created_at:
        raise HTTPException(404, "no such session")
    interrupt = next(
        (i for task in snapshot.tasks for i in task.interrupts), None
    )
    return snapshot, interrupt


def _resume(session_id: str, value: dict) -> None:
    """Resume the paused node.

    The resume value is keyed by interrupt id on purpose. With a bare
    `Command(resume=value)` LangGraph hands the same value to *every* interrupt
    reached in that run — so the resolve gate would swallow the confirm gate's
    payload instead of pausing. Keying by id resumes exactly one interrupt and
    lets the next one stop the run properly.
    """
    _, interrupt = _pending(session_id)
    if interrupt is None:
        raise HTTPException(409, "session is not waiting for input")
    graph.graph().invoke(Command(resume={interrupt.id: value}), _config(session_id))


def _state(session_id: str) -> SessionState:
    """Read the current state of a review straight out of the checkpointer."""
    snapshot, interrupt = _pending(session_id)
    values = snapshot.values
    stage = interrupt.value.get("stage") if interrupt else (
        "done" if values.get("committed") is not None else "extracting"
    )
    return SessionState(
        session_id=session_id,
        stage=stage,
        summary=values.get("summary", ""),
        open_questions=values.get("open_questions", []),
        claims=values.get("claims", []),
        conflicts=values.get("conflicts", []),
        committed=values.get("committed", []),
    )


# --- the review workflow ------------------------------------------------


@app.post("/api/sessions", response_model=SessionState, tags=["review"])
def capture(body: CaptureRequest) -> SessionState:
    """Step 1 -> 2. Extract claims and pause for confirmation."""
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    session_id = str(uuid.uuid4())
    graph.graph().invoke(
        {"raw_text": body.text, "author": body.author, "source": body.source},
        _config(session_id),
    )
    return _state(session_id)


@app.post("/api/sessions/{session_id}/confirm", response_model=SessionState, tags=["review"])
def confirm(session_id: str, body: ConfirmRequest) -> SessionState:
    """Step 2 -> 3. Accept the claims (or send a clarification to re-extract)."""
    _resume(
        session_id,
        {"clarification": body.clarification}
        if body.clarification
        else {"claims": [c.model_dump() for c in body.claims]},
    )
    return _state(session_id)


@app.post("/api/sessions/{session_id}/resolve", response_model=SessionState, tags=["review"])
def resolve(session_id: str, body: ResolveRequest) -> SessionState:
    """Step 3 -> 4. Apply the conflict decisions and index the result."""
    state = _state(session_id)
    if state.stage != "resolve":
        raise HTTPException(409, f"session is at stage '{state.stage}', not 'resolve'")
    try:
        _resume(
            session_id,
            {"resolutions": {k: v.model_dump() for k, v in body.resolutions.items()}},
        )
    except ValueError as error:
        raise HTTPException(400, str(error))
    return _state(session_id)


@app.get("/api/sessions/{session_id}", response_model=SessionState, tags=["review"])
def session(session_id: str) -> SessionState:
    return _state(session_id)


# --- using the knowledge ------------------------------------------------


@app.post("/api/ask", response_model=AskResponse, tags=["knowledge"])
def ask(body: AskRequest) -> AskResponse:
    """Ask the knowledge base a question. Hybrid retrieval + a cited answer."""
    if not body.question.strip():
        raise HTTPException(400, "question is empty")
    return ask_module.ask(body.question, body.top_k)


@app.get("/api/knowledge", tags=["knowledge"])
def knowledge(q: str | None = None, limit: int = 200) -> dict:
    """Browse everything live, or hybrid-search it."""
    items = ask_module.search(q, limit) if q else store.live(limit)
    return {"items": items}


@app.get("/api/knowledge/{claim_id}/history", tags=["knowledge"])
def history(claim_id: str) -> dict:
    """The chain of claims this one replaced. Nothing is ever deleted."""
    return {"chain": store.history(claim_id)}


# --- capture helpers ----------------------------------------------------


@app.post("/api/transcribe", tags=["capture"])
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
        segments, _ = _whisper(WhisperModel).transcribe(path, vad_filter=True)
        return {"text": " ".join(s.text.strip() for s in segments).strip()}
    finally:
        Path(path).unlink(missing_ok=True)


_whisper_model = None


def _whisper(cls):
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = cls(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _whisper_model


@app.get("/api/health", tags=["ops"])
def health() -> dict:
    return {
        "ok": True,
        "llm": {"model": config.LLM_MODEL, "base_url": config.LLM_BASE_URL},
        "embeddings": {
            "provider": config.EMBED_PROVIDER,
            "model": config.EMBED_MODEL,
            "dim": config.EMBED_DIM,
        },
    }


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
