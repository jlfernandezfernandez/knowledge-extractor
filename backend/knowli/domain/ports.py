"""The small external contracts used by Knowli services."""

from collections.abc import Callable, Iterator, Sequence
from datetime import datetime
from typing import Any, BinaryIO, Protocol

from .claim import ClaimDraft, ClaimSearchResult, ClaimToCommit, ContributionStage
from .contribution import HistoryItem, StoredContribution
from .interview import Interview, InterviewStart, InterviewView
from .user import User, UserCredentials


class Model(Protocol):
    def extract_claims(self, raw_text: str) -> list[ClaimDraft]: ...

    def find_conflicts(
        self, claims: list[ClaimDraft], candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]: ...

    def stream_answer(
        self,
        question: str,
        claims: list[dict[str, Any]],
        *,
        tools: Sequence[Callable[..., Any]] = (),
        thread_id: str | None = None,
    ) -> Iterator[dict[str, Any]]: ...


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class Transcriber(Protocol):
    def transcribe(self, audio: BinaryIO, filename: str) -> str: ...


class ContributionStore(Protocol):
    def create_contribution(
        self, author_id: str, raw_text: str, interview_id: str | None = None
    ) -> StoredContribution: ...

    def get_contribution(self, contribution_id: str) -> StoredContribution | None: ...

    def save_review(
        self, contribution_id: str, expected_revision: int, stage: ContributionStage, summary: str
    ) -> StoredContribution: ...

    def commit_claims(
        self, contribution_id: str, expected_revision: int, claims: list[ClaimToCommit]
    ) -> StoredContribution: ...

    def search_claims(
        self, query_text: str, query_embedding: list[float], limit: int
    ) -> list[ClaimSearchResult]: ...

    def list_history(self, cursor: str | None, limit: int) -> tuple[list[HistoryItem], str | None]: ...


class SessionStore(Protocol):
    def create_user(self, email: str, display_name: str, password_hash: str) -> User: ...

    def get_user_credentials(self, email: str) -> UserCredentials | None: ...

    def list_users(self, exclude_user_id: str) -> list[User]: ...

    def create_session(self, user_id: str, token_hash: str, expires_at: datetime) -> None: ...

    def get_user_by_session(self, token_hash: str, now: datetime) -> User | None: ...

    def delete_session(self, token_hash: str) -> None: ...

    def delete_user_sessions(self, user_id: str) -> None: ...


class InterviewStore(Protocol):
    def get_user_by_id(self, user_id: str) -> User | None: ...

    def create_interview(
        self, requester_id: str, assignee_id: str, title: str, brief: str
    ) -> Interview: ...

    def get_interview(self, interview_id: str) -> Interview | None: ...

    def get_interview_by_contribution(self, contribution_id: str) -> Interview | None: ...

    def list_interviews(self, user_id: str, view: InterviewView) -> list[Interview]: ...

    def start_interview(self, interview_id: str, assignee_id: str) -> InterviewStart | None: ...
