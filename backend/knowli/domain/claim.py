"""Values used while a contribution is reviewed."""

from typing import Literal

from pydantic import BaseModel, Field

ContributionStage = Literal["claims", "conflicts", "commit", "committed"]


class ClaimDraft(BaseModel):
    """An extracted claim, identified inside its contribution by ``draft_key``."""

    draft_key: str
    title: str
    statement: str
    tags: list[str] = Field(default_factory=list)
