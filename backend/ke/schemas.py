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

    title: str = Field(description="A label of two to five words. Not a sentence.")
    statement: str = Field(
        description="The claim in one or two sentences. Must stand alone: no "
        "pronouns, no reference to other claims."
    )
    topic: str = Field(
        default="",
        description="The subject this belongs under, one or two words. Reuse the "
        "same wording across claims about the same subject so they group.",
    )
    tags: list[str] = Field(default_factory=list, description="Lowercase tags.")


class Extraction(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    summary: str = Field(
        default="",
        description="One or two sentences telling the person what you understood, "
        "in their own language. Plain and specific. No preamble.",
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
    allowed: list[Decision] = []
    recommended: Decision = "keep_new"


# Which resolutions make sense depends on how the two claims relate. Offering
# every action for every verdict is what the first version did, and it is wrong:
# keeping both sides of a genuine contradiction leaves retrieval to surface two
# incompatible statements and lets the generator pick one arbitrarily — the
# exact failure this project exists to prevent. Conversely, superseding one side
# of a complementary pair throws away information that was worth keeping.
#
# The taxonomy follows the conflict-type split in the 2026 RAG literature
# (temporal / complementary / duplicate), and each verdict carries a recommended
# default so the common case needs no clicking. For a contradiction the default
# is the incoming claim, on the recency prior that the person telling you now is
# describing the current state.
RESOLUTION_POLICY: dict[str, dict] = {
    "conflict": {"allowed": ["keep_new", "keep_old", "merge"], "default": "keep_new"},
    "duplicate": {"allowed": ["keep_old", "keep_new", "merge"], "default": "keep_old"},
    "refines": {"allowed": ["keep_both", "merge", "keep_new"], "default": "keep_both"},
}


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
