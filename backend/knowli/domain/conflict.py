"""How a new claim can collide with a stored one, and what a human can do about it."""

from typing import Literal

from pydantic import BaseModel

from .claim import StoredClaim

Verdict = Literal["conflict", "duplicate", "refines", "unrelated"]
Decision = Literal["keep_new", "keep_old", "keep_both", "merge"]


class Conflict(BaseModel):
    key: str  # "<draft_id>::<stored_id>"
    draft_id: str
    stored: StoredClaim
    verdict: Verdict
    reason: str
    allowed: list[Decision] = []
    recommended: Decision = "keep_new"


class Resolution(BaseModel):
    action: Decision
    statement: str | None = None  # required when action == "merge"
