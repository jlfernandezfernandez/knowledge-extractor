"""A reviewer decision for one claim conflict."""

from typing import Literal

from pydantic import BaseModel, model_validator

Decision = Literal["keep_new", "keep_old", "keep_both", "merge"]
Verdict = Literal["conflict", "duplicate", "refines", "unrelated"]


class ConflictResolution(BaseModel):
    claim_draft_key: str
    action: Decision
    replacement_statement: str | None = None

    @model_validator(mode="after")
    def validate_replacement_statement(self) -> "ConflictResolution":
        if self.action == "merge" and not (self.replacement_statement or "").strip():
            raise ValueError("replacement_statement is required when action is 'merge'")
        return self
