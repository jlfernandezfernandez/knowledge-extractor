"""Authenticated global claim-answer route."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ... import wiring
from ...application.ask import AskService
from .auth import CurrentUserDep
from .schemas import AskRequest, AskResponse

router = APIRouter(prefix="/api", tags=["ask"])


def get_ask_service(request: Request, _: CurrentUserDep) -> AskService:
    return wiring.services(request.app).ask


AskServiceDep = Annotated[AskService, Depends(get_ask_service)]


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, _: CurrentUserDep, service: AskServiceDep) -> dict:
    return service.ask(body.question)


@router.get("/ask/stream")
def stream_ask_get(question: str, _: CurrentUserDep, service: AskServiceDep):
    def event_generator():
        try:
            for event in service.stream_ask(question):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as err:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(err)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
