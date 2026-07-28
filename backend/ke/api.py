"""HTTP API.

Sync endpoints on purpose: FastAPI runs `def` handlers in a threadpool, and
every dependency here (LangGraph's sync checkpointer, psycopg, fastembed) is
sync. Async handlers would need an async checkpointer and pool for no gain at
this scale.
"""

import json
import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from . import ask as ask_module
from . import config, graph, speech, store
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


# --- progress streaming -------------------------------------------------
#
# The graph does two slow things: one LLM call to extract, then one per claim
# that has neighbours. A spinner would hide all of that. Instead we forward
# LangGraph's own node updates as Server-Sent Events, so the UI can say what is
# actually happening and how much of it there is.
#
# Both endpoints below serve JSON by default and SSE when the caller asks for
# it, so agent callers over MCP/A2A are unaffected.


def _wants_stream(request: Request) -> bool:
    return "text/event-stream" in request.headers.get("accept", "")


def _progress(session_id: str, runner) -> Iterator[dict]:
    """Translate LangGraph node updates into UI progress events."""
    yield {"type": "progress", "step": "reading"}
    for chunk in runner:
        for node, update in (chunk or {}).items():
            if node == "extract":
                yield {
                    "type": "progress",
                    "step": "extracted",
                    "count": len(update.get("claims") or []),
                    "against": store.count(),
                }
            elif node == "detect":
                yield {
                    "type": "progress",
                    "step": "compared",
                    "count": len(update.get("conflicts") or []),
                }
            elif node == "commit":
                yield {
                    "type": "progress",
                    "step": "committed",
                    "count": len(update.get("committed") or []),
                }
    yield {"type": "state", "state": _state(session_id).model_dump()}


def _sse(events: Iterator[dict]) -> StreamingResponse:
    def encode():
        try:
            for event in events:
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as error:  # surface failures on the stream, not as a hang
            yield f"data: {json.dumps({'type': 'error', 'detail': str(error)})}\n\n"

    return StreamingResponse(
        encode(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- the review workflow ------------------------------------------------


@app.post("/api/sessions", response_model=None, tags=["review"])
def capture(body: CaptureRequest, request: Request) -> SessionState | StreamingResponse:
    """Step 1 -> 2. Extract claims and pause for confirmation."""
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    session_id = str(uuid.uuid4())
    start = {"raw_text": body.text, "author": body.author, "source": body.source}
    if _wants_stream(request):
        runner = graph.graph().stream(start, _config(session_id), stream_mode="updates")
        return _sse(_progress(session_id, runner))
    graph.graph().invoke(start, _config(session_id))
    return _state(session_id)


@app.post("/api/sessions/{session_id}/confirm", response_model=None, tags=["review"])
def confirm(
    session_id: str, body: ConfirmRequest, request: Request
) -> SessionState | StreamingResponse:
    """Step 2 -> 3. Accept the claims (or send a clarification to re-extract)."""
    resume = (
        {"clarification": body.clarification}
        if body.clarification
        else {"claims": [c.model_dump() for c in body.claims]}
    )
    _, interrupt = _pending(session_id)
    if interrupt is None:
        raise HTTPException(409, "session is not waiting for input")
    command = Command(resume={interrupt.id: resume})
    if _wants_stream(request):
        runner = graph.graph().stream(command, _config(session_id), stream_mode="updates")
        return _sse(_progress(session_id, runner))
    graph.graph().invoke(command, _config(session_id))
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


@app.websocket("/api/transcribe/live")
async def transcribe_live(websocket: WebSocket) -> None:
    """Dictation, transcribed while you speak.

    The client streams raw 16 kHz mono PCM16; the server pushes back each
    segment as a voice-activity detector closes it, so the text arrives roughly
    a phrase at a time instead of all at once when you stop.

    Decoding blocks, so it runs in a worker thread — otherwise a long segment
    would stall the event loop and stop the socket draining.
    """
    import asyncio

    import numpy as np

    await websocket.accept()
    try:
        transcriber = await asyncio.to_thread(speech.create)
    except Exception as error:
        await websocket.send_json({"type": "error", "detail": str(error)})
        await websocket.close()
        return

    await websocket.send_json({"type": "ready"})
    try:
        while True:
            message = await websocket.receive()
            if chunk := message.get("bytes"):
                samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                for text in await asyncio.to_thread(lambda: list(transcriber.feed(samples))):
                    await websocket.send_json({"type": "segment", "text": text})
            elif message.get("text") == "stop":
                for text in await asyncio.to_thread(lambda: list(transcriber.flush())):
                    await websocket.send_json({"type": "segment", "text": text})
                await websocket.send_json({"type": "done"})
                break
            elif message.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        with suppress(RuntimeError):
            await websocket.close()


@app.get("/api/health", tags=["ops"])
def health() -> dict:
    return {
        "ok": True,
        "speech": {"provider": config.SPEECH_PROVIDER, "available": speech.available()},
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
