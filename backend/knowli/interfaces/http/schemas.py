"""Public HTTP request and response values."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

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


class AuthResponse(BaseModel):
    user: UserResponse


class ContributionCaptureRequest(BaseModel):
    raw_text: str
    source: str = "text"
    interview_id: str | None = None


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
    kind: str
    source: str
    raw_text: str
    stage: ContributionStage
    revision: int
    summary: str
    created_at: datetime
    committed_at: datetime | None
    claim_count: int
    claims: list[ClaimDraft]
    conflicts: list[dict[str, Any]]
