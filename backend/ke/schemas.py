"""Typed contracts.

The `Extraction` and `Comparison` models are handed to the LLM through
LangChain's `with_structured_output`, so the model is constrained to this shape
instead of us parsing prose. Everything the API returns is also declared here,
which is what gives the frontend a generated, always-correct client.
"""

from typing import Literal

from pydantic import BaseModel, Field

Verdict = Literal["conflict", "duplicate", "refines", "unrelated"]
Decision = Literal["keep_new", "keep_old", "keep_both", "merge"]


# --- what the LLM must return -------------------------------------------


class Claim(BaseModel):
    """One discrete, self-contained piece of knowledge."""

    title: str = Field(description="Short label, at most a few words.")
    statement: str = Field(
        description="The full claim in 1-3 sentences. Must stand alone with no "
        "pronouns or references to other claims."
    )
    tags: list[str] = Field(default_factory=list, description="Lowercase topic tags.")


class Extraction(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    summary: str = Field(
        default="",
        description="Two or three sentences telling the person what you understood, "
        "in their own language.",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Anything genuinely ambiguous that the person should clarify. "
        "Leave empty when nothing is unclear.",
    )


class Comparison(BaseModel):
    existing_id: str
    verdict: Verdict
    reason: str = Field(description="One sentence, in the language of the claims.")


class Comparisons(BaseModel):
    comparisons: list[Comparison] = Field(default_factory=list)


class Answer(BaseModel):
    answer: str = Field(
        description="The answer, grounded only in the supplied claims. Say you do "
        "not know when the claims do not cover it."
    )
    cited_ids: list[str] = Field(
        default_factory=list, description="ids of the claims actually used."
    )


# --- what the API exchanges ---------------------------------------------


class ClaimDraft(Claim):
    id: str  # stable within a session: "c0", "c1", ...


class StoredClaim(BaseModel):
    id: str
    title: str
    statement: str
    tags: list[str] = []
    author: str | None = None
    source: str | None = None
    score: float | None = None
    distance: float | None = None


class Conflict(BaseModel):
    key: str  # "<draft_id>::<stored_id>"
    draft_id: str
    stored: StoredClaim
    verdict: Verdict
    reason: str


class Resolution(BaseModel):
    action: Decision
    statement: str | None = None  # required when action == "merge"


class CommittedClaim(BaseModel):
    id: str
    title: str
    statement: str
    superseded: list[str] = []


class CaptureRequest(BaseModel):
    text: str
    author: str | None = None
    source: str | None = "web"


class ConfirmRequest(BaseModel):
    claims: list[ClaimDraft]
    clarification: str | None = Field(
        default=None,
        description="Free-text answer to the model's open questions. When present "
        "the claims are re-extracted with this extra context instead of moving on.",
    )


class ResolveRequest(BaseModel):
    resolutions: dict[str, Resolution]


class AskRequest(BaseModel):
    question: str
    top_k: int | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[StoredClaim]


class SessionState(BaseModel):
    session_id: str
    stage: Literal["extracting", "confirm", "detecting", "resolve", "done"]
    summary: str = ""
    open_questions: list[str] = []
    claims: list[ClaimDraft] = []
    conflicts: list[Conflict] = []
    committed: list[CommittedClaim] = []
