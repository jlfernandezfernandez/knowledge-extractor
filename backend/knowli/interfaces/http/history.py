"""Authenticated, cursor-paginated contribution history."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ... import wiring
from ...application.ask import AskService
from .auth import CurrentUserDep
from .schemas import HistoryResponse

router = APIRouter(prefix="/api", tags=["history"])


def get_ask_service() -> AskService:
    return wiring.ask_service()


AskServiceDep = Annotated[AskService, Depends(get_ask_service)]


@router.get("/history", response_model=HistoryResponse)
def history(
    _: CurrentUserDep,
    service: AskServiceDep,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    return service.history(cursor, limit)
