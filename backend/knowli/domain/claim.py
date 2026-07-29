"""Claims, at each point in their life.

A claim starts as something the model proposed (`Claim`), gets an id inside a
review session (`ClaimDraft`), lands in the store (`StoredClaim`) and comes back
out of a finished review as a receipt (`CommittedClaim`).

`Claim` carries `Field(description=...)` on every attribute because the same
model is handed to the LLM through `with_structured_output`: those descriptions
are part of the prompt, not documentation. They live with the type they
describe, so the shape and the instructions can never drift apart.
"""

from pydantic import BaseModel, Field


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


class CommittedClaim(BaseModel):
    id: str
    title: str
    statement: str
    superseded: list[str] = []
