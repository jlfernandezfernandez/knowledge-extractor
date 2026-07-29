"""Using the knowledge: which knowledge bases there are, asking one a question,
seeing what a claim replaced.

There is no route that lists a knowledge base. There was, and nothing called it:
the rail stopped listing the store when the store stopped being small enough to
list, and agents search over MCP and A2A rather than over HTTP. Retrieval is
`/api/ask` and search is a skill; a paginated dump of an organisation's
knowledge is a feature someone should ask for before it exists."""

from fastapi import APIRouter, HTTPException

from ...application import ask as ask_service
from ...application import knowledge_bases as kb_service
from ...domain.knowledge_base import KnowledgeBase, slugify
from .schemas import AskRequest, AskResponse, NewKnowledgeBase

router = APIRouter(tags=["knowledge"])


@router.get("/api/knowledge-bases")
def knowledge_bases() -> dict:
    """Every knowledge base, with how many live claims it holds."""
    return {"items": kb_service.listing()}


@router.post("/api/knowledge-bases", response_model=KnowledgeBase)
def create_knowledge_base(body: NewKnowledgeBase) -> KnowledgeBase:
    """Create one. The slug comes from the name; a name that already has a
    knowledge base is a 409 rather than a second one with a number on the end."""
    # Checked here rather than in the application layer because it is the same
    # kind of check as "question is empty" two routes down: a request that
    # cannot be acted on, not a rule about what a knowledge base is.
    if not slugify(body.name):
        raise HTTPException(400, "a name needs at least one letter or digit")
    return kb_service.create(body.name)


@router.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    """Ask a knowledge base a question. Hybrid retrieval + a cited answer."""
    if not body.question.strip():
        raise HTTPException(400, "question is empty")
    return AskResponse(**ask_service.ask(body.question, body.top_k, body.knowledge_base))


@router.get("/api/knowledge/{claim_id}/history")
def history(claim_id: str) -> dict:
    """The chain of claims this one replaced. Nothing is ever deleted.

    No knowledge base parameter, and not by oversight: a claim id already names
    its scope, so the only thing this route could do with a slug is disagree
    with the id it was handed. See `application.ask.history`.
    """
    return {"chain": ask_service.history(claim_id)}
