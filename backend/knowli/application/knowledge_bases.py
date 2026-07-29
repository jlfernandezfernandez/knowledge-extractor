"""Which knowledge bases exist, which one a request means, and what has been
captured into them.

Thin, and still not the router's job. Three surfaces resolve a knowledge base —
the web API, MCP and A2A — and an unknown slug has to mean the same thing on all
three. It means an error. It never means the default: silently falling back
would file a claim about kitchen returns into sofa deliveries and then compare
it against them, which is the exact failure this whole change exists to prevent.
A 404 costs a caller one retry; a silent fallback costs someone a wrong answer
months later, with no way to see where it came from.
"""

from .. import config
from ..domain.knowledge_base import KnowledgeBase, slugify
from ..wiring import catalog


class KnowledgeBaseNotFound(LookupError):
    """Raised for a slug nobody has. The HTTP layer turns it into a 404, MCP and
    A2A hand the message straight to the agent — which is why the message lists
    what does exist rather than only what does not."""


class SlugTaken(ValueError):
    pass


def resolve(slug: str | None) -> KnowledgeBase:
    """The knowledge base a request names, or the configured default when it
    names none."""
    found = catalog.knowledge_base(slug or config.DEFAULT_KNOWLEDGE_BASE)
    if found is None:
        available = ", ".join(kb.slug for kb in catalog.knowledge_bases())
        raise KnowledgeBaseNotFound(
            f"there is no knowledge base '{slug}'. Available: {available}"
        )
    return found


def listing() -> list[KnowledgeBase]:
    """All of them, with claim counts. What the sidebar is."""
    return catalog.knowledge_bases()


def create(name: str) -> KnowledgeBase:
    """Create one from a display name.

    The slug is derived, never supplied, so the name a person types and the
    string a URL carries can never disagree. Two names that derive to the same
    slug are the same knowledge base — "Kitchen Returns" and "kitchen returns"
    are one thing spelled twice — and the second attempt is refused rather than
    quietly renamed to `kitchen-returns-2`. Somebody who thinks they are opening
    the knowledge base they made yesterday should not be handed an empty new one
    with a number on the end.
    """
    created = catalog.create_knowledge_base(slugify(name), name.strip())
    if created is None:
        raise SlugTaken(f"a knowledge base called '{slugify(name)}' already exists")
    return created


def sessions(slug: str | None, limit: int = 20) -> list[dict]:
    """Recent reviews in one knowledge base, newest first. Plain dicts, like
    `ask.history`: this is a listing, not a domain concept, and giving it a
    model would only mean writing the same six fields down a third time."""
    return catalog.sessions(resolve(slug), limit)
