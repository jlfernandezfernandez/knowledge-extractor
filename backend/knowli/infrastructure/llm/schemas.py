"""The shapes the model is constrained to.

These are handed to the LLM through LangChain's `with_structured_output`, so the
model is forced into this shape instead of us parsing prose. They live here, in
the adapter, rather than in the domain: every `description=` below is prompt
text, and the wrapper objects (`Comparisons`) exist only because a model needs a
single top-level object to fill in.

Each of them satisfies one of the little result protocols in
`domain/ports.py` structurally, which is how the application layer reads
`result.claims` or `result.cited_ids` without importing this module.
"""

from pydantic import BaseModel, Field

from ...domain.claim import Claim
from ...domain.conflict import Verdict


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
