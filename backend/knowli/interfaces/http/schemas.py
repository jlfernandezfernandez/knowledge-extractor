"""Public HTTP request and response values."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ...domain.claim import ClaimDraft, ContributionStage
from ...domain.conflict import ConflictResolution


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str


class UsersResponse(BaseModel):
    items: list[UserResponse]


class AuthResponse(BaseModel):
    user: UserResponse


class TranscriptionResponse(BaseModel):
    text: str


class ContributionCaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_text: str


class InterviewCreateRequest(BaseModel):
    assignee_id: str
    title: str
    brief: str = ""


class InterviewAnswerRequest(BaseModel):
    raw_text: str


class InterviewResponse(BaseModel):
    id: str
    requester_id: str
    assignee_id: str
    title: str
    brief: str
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class InterviewStartResponse(BaseModel):
    interview: InterviewResponse
    contribution_id: str


class AskRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    id: str
    title: str
    statement: str
    author: str
    contribution_id: str
    contribution_created_at: datetime


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]


class HistoryItemResponse(BaseModel):
    contribution_id: str
    author: str
    summary: str
    claim_count: int
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[HistoryItemResponse]
    next_cursor: str | None


class ConfirmClaimsRequest(BaseModel):
    revision: int = Field(ge=0)
    claims: list[ClaimDraft]


class ResolveConflictsRequest(BaseModel):
    revision: int = Field(ge=0)
    resolutions: list[ConflictResolution]


class RevisionRequest(BaseModel):
    revision: int = Field(ge=0)


class ContributionResponse(BaseModel):
    id: str
    author_id: str
    author: str
    raw_text: str
    stage: ContributionStage
    revision: int
    summary: str
    created_at: datetime
    committed_at: datetime | None
    claim_count: int
    claims: list[ClaimDraft]
    conflicts: list[dict[str, Any]]
