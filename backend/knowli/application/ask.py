"""Reading a knowledge base: search, ask, history.

This is the payoff of everything else: because ingestion produced short,
self-contained, human-approved claims, retrieval needs no chunking strategy and
answers can cite an exact claim id. The usual RAG failure mode — a chunk that
lost its context somewhere in a 40-page PDF — cannot happen here, because the
context was resolved by a person at write time rather than guessed at read time.

Every read takes a knowledge base slug and every one of them defaults to the
configured one, so a solo local user calls these exactly as before. The slug is
resolved here rather than at each surface, so the web API, MCP and A2A all get
the same answer for a name that does not exist.
"""

from .. import config
from ..domain.claim import StoredClaim
from ..wiring import embedder, extractor, repository
from . import knowledge_bases


def search(
    query: str, k: int | None = None, knowledge_base: str | None = None
) -> list[StoredClaim]:
    k = k or config.RETRIEVE_TOP_K
    kb = knowledge_bases.resolve(knowledge_base)
    return repository.hybrid_search(kb, query, embedder.embed([query])[0], k)


def ask(question: str, k: int | None = None, knowledge_base: str | None = None) -> dict:
    """Answer a question from the store. Returns `{"answer", "sources"}` as plain
    data: three different surfaces serialise this, and only one of them is HTTP."""
    claims = search(question, k, knowledge_base)
    if not claims:
        return {
            "answer": "There is nothing in the knowledge base about that yet.",
            "sources": [],
        }

    result = extractor.answer(question, claims)
    cited = set(result.cited_ids)
    # Return the cited claims first so the UI can show what was actually used.
    sources = sorted(claims, key=lambda c: c.id not in cited)
    return {"answer": result.answer, "sources": [c.model_dump() for c in sources]}


def history(claim_id: str) -> list[dict]:
    """What this claim replaced. Nothing is ever deleted, so this always resolves.

    The one read with no knowledge base. A claim id is a uuid, so it already
    names its scope; the chain hangs off ids the caller got from a scoped read,
    and a superseding claim is always in the same knowledge base as the claim it
    superseded, because it could only have been compared against neighbours from
    there. A slug argument here could only ever agree with the id or contradict
    it, and there is no useful answer to the second case.
    """
    return repository.history(claim_id)
