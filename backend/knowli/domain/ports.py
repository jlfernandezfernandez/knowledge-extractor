"""The small external contracts used by Knowli services."""

from typing import Protocol

from .claim import ClaimDraft, ClaimSearchResult, ClaimToCommit, ContributionStage
from .contribution import HistoryItem, StoredContribution


class Model(Protocol):
    def extract_claims(self, raw_text: str) -> list[ClaimDraft]: ...

    def find_conflicts(self, claims: list[ClaimDraft], candidates: list[dict]) -> list[dict]: ...

    def answer(self, question: str, claims: list[dict]) -> str: ...


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class ContributionStore(Protocol):
    def create_contribution(
        self, author_id: str, raw_text: str, source: str, interview_id: str | None = None
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
    def create_user(self, email: str, display_name: str, password_hash: str) -> dict: ...

    def get_user_by_email(self, email: str) -> dict | None: ...

    def create_session(self, user_id: str, token_hash: str, expires_at: str) -> None: ...

    def get_user_by_session(self, token_hash: str) -> dict | None: ...

    def delete_session(self, token_hash: str) -> None: ...
