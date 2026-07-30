"""Authenticated, author-only contribution review routes."""

from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from ... import wiring
from ...application.review import ContributionService
from .auth import CurrentUserDep
from .schemas import (
    ConfirmClaimsRequest,
    ContributionCaptureRequest,
    ContributionResponse,
    ResolveConflictsRequest,
    RevisionRequest,
)
from .sse import review_events

router = APIRouter(prefix="/api/contributions", tags=["contributions"])


def get_contribution_service() -> ContributionService:
    return wiring.contribution_service()


ContributionServiceDep = Annotated[ContributionService, Depends(get_contribution_service)]


def require_owned_contribution(
    id: str,
    user: CurrentUserDep,
    service: ContributionServiceDep,
) -> dict:
    return service.get(user.id, id)


OwnedContributionDep = Annotated[dict, Depends(require_owned_contribution)]


@router.post("", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def capture(
    body: ContributionCaptureRequest,
    user: CurrentUserDep,
    service: ContributionServiceDep,
) -> dict:
    if not body.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text is empty")
    return service.capture(user.id, body.raw_text, body.source)


@router.get("/{contribution_id}", response_model=ContributionResponse)
def get(
    contribution_id: str,
    user: CurrentUserDep,
    service: ContributionServiceDep,
) -> dict:
    return service.get(user.id, contribution_id)


@router.post("/{contribution_id}/confirm", response_model=ContributionResponse)
def confirm(
    contribution_id: str,
    body: ConfirmClaimsRequest,
    user: CurrentUserDep,
    service: ContributionServiceDep,
) -> dict:
    return service.confirm_claims(
        user.id,
        contribution_id,
        body.revision,
        [claim.model_dump() for claim in body.claims],
    )


@router.post("/{contribution_id}/resolve", response_model=ContributionResponse)
def resolve(
    contribution_id: str,
    body: ResolveConflictsRequest,
    user: CurrentUserDep,
    service: ContributionServiceDep,
) -> dict:
    return service.resolve_conflicts(
        user.id,
        contribution_id,
        body.revision,
        [resolution.model_dump() for resolution in body.resolutions],
    )


@router.post("/{contribution_id}/commit", response_model=ContributionResponse)
def commit(
    contribution_id: str,
    body: RevisionRequest,
    user: CurrentUserDep,
    service: ContributionServiceDep,
) -> dict:
    return service.commit(user.id, contribution_id, body.revision)


@router.post("/{contribution_id}/back", response_model=ContributionResponse)
def back(
    contribution_id: str,
    body: RevisionRequest,
    user: CurrentUserDep,
    service: ContributionServiceDep,
) -> dict:
    return service.back(user.id, contribution_id, body.revision)


@router.get("/{id}/events", response_class=EventSourceResponse)
async def events(
    id: str,
    user: CurrentUserDep,
    service: ContributionServiceDep,
    owned: OwnedContributionDep,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> AsyncIterable[ServerSentEvent]:
    async for event in review_events(
        service, user.id, id, last_event_id=last_event_id
    ):
        yield event
