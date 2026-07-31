"""Authenticated, cursor-paginated contribution history."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from ... import wiring
from ...application.ask import HistoryService
from .auth import CurrentUserDep
from .schemas import HistoryResponse

router = APIRouter(prefix="/api", tags=["history"])


def get_history_service(request: Request) -> HistoryService:
    return wiring.services(request.app).history


HistoryServiceDep = Annotated[HistoryService, Depends(get_history_service)]


@router.get("/history", response_model=HistoryResponse)
def history(
    _: CurrentUserDep,
    service: HistoryServiceDep,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    return service.history(cursor, limit)
