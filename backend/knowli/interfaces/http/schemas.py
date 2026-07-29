"""What the HTTP API exchanges.

Declared as pydantic models so the OpenAPI schema is generated from the code,
which is what gives the frontend an always-correct client. These are wire
shapes, not domain types: they wrap the domain models from `knowli.domain`
rather than redefining them, so a field can never mean two different things on
the two sides of the socket.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from ...application.review import Stage
from ...domain.claim import ClaimDraft, CommittedClaim, StoredClaim
from ...domain.conflict import Conflict, Resolution

# The knowledge base is always the slug and always optional, on every request
# that has one. Optional because a solo user has exactly one and should never be
# made to name it; the slug rather than the id because it is what a URL, an
# agent and a person can all type.
_KNOWLEDGE_BASE = Field(
    default=None,
    description="Slug of the knowledge base. The configured default when absent; "
    "a slug that does not exist is a 404, never a fallback.",
)


class CaptureRequest(BaseModel):
    text: str
    author: str | None = None
    source: str | None = "web"
    knowledge_base: str | None = _KNOWLEDGE_BASE


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
    knowledge_base: str | None = _KNOWLEDGE_BASE


class AskResponse(BaseModel):
    answer: str
    sources: list[StoredClaim]


class NewKnowledgeBase(BaseModel):
    """The only thing a person supplies. The slug is derived from the name, so
    the two can never disagree."""

    name: str


class SessionSummary(BaseModel):
    """One row of the recent-captures list. Deliberately not `SessionState`: a
    list needs a stage and a sentence, and shipping every claim and conflict of
    twenty sessions to render twenty lines would be the same mistake as reading
    them out of the checkpointer in the first place."""

    session_id: str
    stage: Stage
    summary: str = ""
    author: str | None = None
    knowledge_base: str
    created_at: datetime
    updated_at: datetime


class SessionState(BaseModel):
    session_id: str
    stage: Stage
    knowledge_base: str
    # What the person originally said. The composer is repopulated from this
    # when a review is stepped out of, so nobody has to dictate it twice.
    raw_text: str = ""
    summary: str = ""
    open_questions: list[str] = []
    claims: list[ClaimDraft] = []
    conflicts: list[Conflict] = []
    committed: list[CommittedClaim] = []
