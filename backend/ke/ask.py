"""Question answering over the curated knowledge base.

This is the payoff of everything else: because ingestion produced short,
self-contained, human-approved claims, retrieval needs no chunking strategy and
answers can cite an exact claim id. The usual RAG failure mode — a chunk that
lost its context somewhere in a 40-page PDF — cannot happen here, because the
context was resolved by a person at write time rather than guessed at read time.
"""

from . import config, embed, store
from .llm import structured
from .schemas import Answer, AskResponse

SYSTEM = """Answer the question using only the knowledge claims provided below. \
Cite the ids of the claims you actually used. If the claims do not answer the \
question, say so plainly instead of guessing. Answer in the question's language."""


def search(query: str, k: int | None = None):
    k = k or config.RETRIEVE_TOP_K
    return store.hybrid_search(query, embed.embed([query])[0], k)


def ask(question: str, k: int | None = None) -> AskResponse:
    claims = search(question, k)
    if not claims:
        return AskResponse(answer="There is nothing in the knowledge base about that yet.",
                           sources=[])

    context = "\n".join(
        f"[{c.id}] {c.title}: {c.statement}" for c in claims
    )
    result: Answer = structured(Answer).invoke(
        [("system", SYSTEM), ("human", f"Claims:\n{context}\n\nQuestion: {question}")]
    )
    cited = {i for i in result.cited_ids}
    # Return the cited claims first so the UI can show what was actually used.
    sources = sorted(claims, key=lambda c: c.id not in cited)
    return AskResponse(answer=result.answer, sources=sources)
