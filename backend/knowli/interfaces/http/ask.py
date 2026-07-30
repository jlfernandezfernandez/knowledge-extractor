"""Authenticated global claim-answer route."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

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
