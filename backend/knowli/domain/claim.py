"""Values used while a contribution is reviewed."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ContributionStage = Literal["claims", "conflicts", "commit", "committed"]


class ClaimDraft(BaseModel):
    """An extracted claim, identified inside its contribution by ``draft_key``."""

    draft_key: str
    title: str
    statement: str
    tags: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class ClaimToCommit:
    """A reviewed claim with the embedding and lineage ready to persist."""

    draft_key: str
    title: str
    statement: str
    tags: tuple[str, ...]
    embedding: tuple[float, ...]
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimSearchResult:
    """A global retrieval result with enough provenance to cite it."""

    id: str
    title: str
    statement: str
    tags: tuple[str, ...]
    author: str
    contribution_id: str
    contribution_created_at: datetime
    score: float
