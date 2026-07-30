"""Authenticated user-to-user interview routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from ... import wiring
from ...application.interviews import CaptureService, InterviewService
from ...application.review import ContributionService
from ...domain.interview import InterviewView
from .auth import CurrentUserDep
from .schemas import (
    InterviewAnswerRequest,
    InterviewCreateRequest,
    InterviewResponse,
    InterviewStartResponse,
)

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def get_interview_service(request: Request, _: CurrentUserDep) -> InterviewService:
    return wiring.services(request.app).interviews


def get_contribution_service(
    request: Request, _: CurrentUserDep
) -> ContributionService:
    return wiring.services(request.app).contributions


InterviewServiceDep = Annotated[InterviewService, Depends(get_interview_service)]
ContributionServiceDep = Annotated[CaptureService, Depends(get_contribution_service)]


@router.get("", response_model=dict[str, list[InterviewResponse]])
def listing(
    user: CurrentUserDep,
    service: InterviewServiceDep,
    view: InterviewView = Query("pending"),
) -> dict:
    return {"items": service.list(user.id, view)}


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def create(
    body: InterviewCreateRequest,
    user: CurrentUserDep,
    service: InterviewServiceDep,
) -> object:
    return service.create(user.id, body.assignee_id, body.title, body.brief)


@router.post("/{interview_id}/start", response_model=InterviewStartResponse)
def start(
    interview_id: str,
    user: CurrentUserDep,
    service: InterviewServiceDep,
) -> dict:
    started = service.start(user.id, interview_id)
    return {"interview": started.interview, "contribution_id": started.contribution_id}


@router.post("/{interview_id}/answer")
def answer(
    interview_id: str,
    body: InterviewAnswerRequest,
    user: CurrentUserDep,
    service: InterviewServiceDep,
    contributions: ContributionServiceDep,
) -> dict:
    return service.answer(user.id, interview_id, body.raw_text, contributions)
