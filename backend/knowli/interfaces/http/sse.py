"""Progress streaming.

The graph does two slow things: one LLM call to extract, then one per claim
that has neighbours. A spinner would hide all of that. Instead we forward
LangGraph's own node updates as Server-Sent Events, so the UI can say what is
actually happening and how much of it there is.

The capture and confirm endpoints serve JSON by default and SSE only when the
caller asks for it, so agent callers over MCP/A2A are unaffected.
"""

import json
from collections.abc import Iterator

from fastapi import Request
from fastapi.responses import StreamingResponse

from ...application import review
from .schemas import SessionState


def wants_stream(request: Request) -> bool:
    return "text/event-stream" in request.headers.get("accept", "")


def progress(
    session_id: str, runner: Iterator[dict], knowledge_base: str | None = None
) -> Iterator[dict]:
    """Translate LangGraph node updates into UI progress events.

    The knowledge base is passed in rather than read off the session, because
    the first event is yielded before the graph has run and there is no session
    to read yet. `against` counts only that knowledge base — a capture into an
    empty one is compared against nothing, however full the database is.
    """
    yield {"type": "progress", "step": "reading"}
    for chunk in runner:
        for node, update in (chunk or {}).items():
            if node == "extract":
                yield {
                    "type": "progress",
                    "step": "extracted",
                    "count": len(update.get("claims") or []),
                    "against": review.live_claim_count(knowledge_base),
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
    yield {"type": "state", "state": SessionState(**review.state(session_id)).model_dump()}


def sse(events: Iterator[dict]) -> StreamingResponse:
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
