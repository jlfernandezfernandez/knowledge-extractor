"""Typed values returned by the contribution store."""

from dataclasses import dataclass
from datetime import datetime

from .claim import ContributionStage


class ContributionNotFound(LookupError):
    pass


class StaleRevision(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredContribution:
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
    source: str


@dataclass(frozen=True)
class HistoryItem:
    contribution_id: str
    author: str
    source: str
    summary: str
    claim_count: int
    created_at: datetime
