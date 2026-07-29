"""The review workflow over HTTP: one endpoint per step a person takes."""

import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ...application import knowledge_bases as kb_service
from ...application import review
from .schemas import (
    CaptureRequest,
    ConfirmRequest,
    ResolveRequest,
    SessionState,
    SessionSummary,
)
from .sse import progress, sse, wants_stream

router = APIRouter(tags=["review"])


@router.get("/api/sessions")
def sessions(knowledge_base: str | None = None, limit: int = 20) -> dict:
    """The recent captures in a knowledge base, newest first.

    Served from `review_session`, which is an index over LangGraph's
    checkpointer rather than a second copy of it: rendering twenty rows should
    not cost twenty deserialised graph states. Anything past the stage and the
    summary comes from `GET /api/sessions/{id}`, which reads the real thing.
    """
    return {
        "items": [SessionSummary(**s) for s in kb_service.sessions(knowledge_base, limit)]
    }


@router.post("/api/sessions", response_model=None)
def capture(body: CaptureRequest, request: Request) -> SessionState | StreamingResponse:
    """Step 1 -> 2. Extract claims and pause for confirmation."""
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    session_id = str(uuid.uuid4())  # LangGraph's thread id
    runner = review.start(
        session_id, body.text, body.author, body.source, body.knowledge_base
    )
    if wants_stream(request):
        return sse(progress(session_id, runner, body.knowledge_base))
    review.drain(runner)
    return SessionState(**review.state(session_id))


@router.post("/api/sessions/{session_id}/confirm", response_model=None)
def confirm(
    session_id: str, body: ConfirmRequest, request: Request
) -> SessionState | StreamingResponse:
    """Step 2 -> 3. Accept the claims (or send a clarification to re-extract)."""
    # The knowledge base is the session's, not the request's: it was fixed when
    # the capture started and a confirm has no business moving it. Read before
    # resuming, because after a clarification loops back through extraction the
    # progress events need it to say what the claims are being compared against.
    knowledge_base = review.state(session_id)["knowledge_base"]
    runner = review.confirm_claims(
        session_id, [c.model_dump() for c in body.claims], body.clarification
    )
    if wants_stream(request):
        return sse(progress(session_id, runner, knowledge_base))
    review.drain(runner)
    return SessionState(**review.state(session_id))


@router.post("/api/sessions/{session_id}/resolve", response_model=SessionState)
def resolve(session_id: str, body: ResolveRequest) -> SessionState:
    """Step 3 -> 4. Apply the conflict decisions and index the result."""
    try:
        review.resolve(
            session_id, {k: v.model_dump() for k, v in body.resolutions.items()}
        )
    except ValueError as error:
        raise HTTPException(400, str(error))
    return SessionState(**review.state(session_id))


@router.post("/api/sessions/{session_id}/back", response_model=SessionState)
def back(session_id: str) -> SessionState:
    """One gate backwards.

    Restarting was the only way out of the conflict gate, and re-dictating three
    paragraphs to fix one claim is not a review, it is a punishment. So: from
    the resolve gate this rewinds the graph to the confirm gate with the claims
    as they were (see `application.review.back` for how the checkpointer makes
    that free).

    From the confirm gate the graph has nowhere left to go — the step before it
    is the text box, not a node — so this returns the state unchanged and the
    frontend puts `raw_text` back in the composer. Answering with 200 and a
    truthful state is kinder here than a 409 the caller would have to special-
    case; the stage in the response already says nothing moved.

    A committed review is a different matter and does get a 409: those claims
    are in the store, superseding real rows that other people may already have
    read. Rewinding that would be rewriting history rather than navigating it.
    """
    return SessionState(**review.back(session_id))


@router.get("/api/sessions/{session_id}", response_model=SessionState)
def session(session_id: str) -> SessionState:
    return SessionState(**review.state(session_id))
