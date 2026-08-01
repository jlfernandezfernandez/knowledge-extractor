"""Authenticated agent answer stream."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from openai import OpenAIError

from ... import wiring
from ...application.ask import AskService
from .auth import CurrentUserDep

router = APIRouter(prefix="/api", tags=["ask"])
logger = logging.getLogger(__name__)


def get_ask_service(request: Request, _: CurrentUserDep) -> AskService:
    return wiring.services(request.app).ask


AskServiceDep = Annotated[AskService, Depends(get_ask_service)]


@router.get("/ask/stream")
def stream_ask(
    question: Annotated[str, Query(max_length=2000)],
    thread_id: Annotated[str, Query(max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")],
    user: CurrentUserDep,
    service: AskServiceDep,
) -> StreamingResponse:
    def event(payload: dict) -> str:
        # `default=str` because a claim carries its `contribution_created_at` datetime:
        # without it the first event raises and the whole answer becomes one error.
        return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"

    def event_generator():
        # The response has already started, so failures travel as an event, not a status.
        # Only the stable code crosses the wire: provider messages are not for the reader,
        # but the cause is logged -- an error event with no trace is undiagnosable.
        try:
            for message in service.stream_ask(question, user_id=user.id, thread_id=thread_id):
                yield event(message)
        except OpenAIError:
            logger.exception("ask stream: model unavailable")
            yield event({"type": "error", "code": "model_unavailable"})
        except Exception:
            logger.exception("ask stream: request failed")
            yield event({"type": "error", "code": "request_failed"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
