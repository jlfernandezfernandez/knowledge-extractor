"""The ports: everything the pipeline needs from the outside world, stated as
protocols instead of imports.

There is exactly one implementation of each of these today (Postgres,
fastembed, LangChain, sherpa-onnx), and that is fine — the point is not that
they will be swapped, it is that the direction of dependency is readable. The
graph in `application/review.py` says `repository.neighbours(...)`, and nothing
above `infrastructure/` mentions psycopg or a chat model. `knowli/wiring.py` is
the single place where a port meets its implementation.

These are `typing.Protocol`, so nothing has to inherit from them: a class that
has the methods satisfies the port structurally. That also lets the LLM-facing
pydantic models in `infrastructure/llm/schemas.py` satisfy the little result
protocols below without the domain ever importing them.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Protocol

from .claim import Claim, StoredClaim
from .conflict import Verdict
from .knowledge_base import KnowledgeBase

if TYPE_CHECKING:  # only for the Transcriber signature; the domain stays import-light
    import numpy as np


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one vector per input, in order."""


class KnowledgeRepository(Protocol):
    """The store of accepted knowledge.

    Nothing here deletes: `supersede` points an old claim at the one that
    replaced it, and every read filters on that pointer being NULL.

    Every method that reads or writes claims names the knowledge base it works
    in, and names it *first*. That is not decoration: it is the parameter that
    makes a second implementation possible at all. Every vector store has this
    argument — Qdrant and Chroma call it a collection, Pinecone a namespace — and
    each of them takes it as the first argument of every call, because for them
    it is the handle rather than a filter. Shaping the port that way keeps the
    pgvector implementation honest about the fact that it is a WHERE clause here
    and would be a handle elsewhere.

    It is a `KnowledgeBase` and not an id for the same reason: this
    implementation needs `id`, a Qdrant one would need `slug`, and the port
    should not pick a winner.

    Two methods deliberately do not take it. `history` and `supersede` work on
    claim ids, which are uuids and globally unique, so the scope could only be
    redundant or wrong — and the chain either walks is inside one knowledge base
    by construction, because a claim can only supersede one it was compared
    against and comparison is already scoped. Adding the argument would let a
    caller ask for a history that contradicts the id it passed, which is a
    question with no good answer. Note what this is not: with no users and no
    auth, it is not an authorisation boundary, and it never was one.
    """

    def hybrid_search(
        self, kb: KnowledgeBase, query: str, embedding, k: int
    ) -> list[StoredClaim]:
        """Semantic + lexical, fused. What `ask` and search use."""

    def neighbours(
        self, kb: KnowledgeBase, embedding, k: int, max_distance: float
    ) -> list[StoredClaim]:
        """Pure semantic nearest neighbours. What conflict detection uses."""

    def count(self, kb: KnowledgeBase) -> int:
        """How many live claims exist in this knowledge base."""

    def history(self, claim_id: str) -> list[dict]:
        """The chain of claims this one replaced, newest first."""

    def insert(
        self, kb: KnowledgeBase, title: str, statement: str, tags, embedding, author, source
    ) -> str:
        """Store a claim and return its new id."""

    def supersede(self, old_id: str, new_id: str) -> None:
        """Mark `old_id` as replaced by `new_id`. The row stays."""


class Catalog(Protocol):
    """What knowledge bases exist, and what reviews have run in them.

    A second port rather than five more methods on `KnowledgeRepository`,
    because the two are not swapped together. Move the claims to Qdrant and the
    catalog stays in Postgres: a vector store has no opinion about which
    collections a product offers, and it certainly has no table of half-finished
    human reviews. Keeping them apart is what makes "ship pgvector, shape the
    port so Qdrant could be added" a true statement rather than a hopeful one.

    No workspace argument anywhere. The table exists so that a second workspace
    later is a WHERE clause instead of a migration, but there is no way to
    select one yet, and threading a constant through five signatures is
    flexibility nobody can exercise. The implementation resolves
    `config.DEFAULT_WORKSPACE`; that is the one line to change.
    """

    def knowledge_bases(self) -> list[KnowledgeBase]:
        """All of them, with their live claim counts, oldest first."""

    def knowledge_base(self, slug: str) -> KnowledgeBase | None:
        """One by slug, or None. No counting — this is on every request path."""

    def create_knowledge_base(self, slug: str, name: str) -> KnowledgeBase | None:
        """Create one, or None if the slug is taken.

        None rather than an exception so the adapter never has to translate a
        driver error into a domain one: the collision is a normal outcome the
        unique index already knows how to report, and the caller turns it into
        a 409 without either layer importing the other's error types.
        """

    def record_session(
        self, session_id: str, kb: KnowledgeBase, author: str | None, stage: str, summary: str
    ) -> None:
        """Upsert the listing row for a review. Idempotent, and a no-op when
        neither the stage nor the summary actually moved."""

    def sessions(self, kb: KnowledgeBase, limit: int) -> list[dict]:
        """Recent reviews in this knowledge base, newest first."""


# --- what the language model gives back ---------------------------------
#
# Declared as attribute protocols rather than concrete models: the shapes the
# LLM is constrained to belong next to the prompts that ask for them, in
# `infrastructure/llm/schemas.py`, and they satisfy these structurally.


class ExtractionResult(Protocol):
    claims: list[Claim]
    summary: str
    open_questions: list[str]


class ComparisonResult(Protocol):
    existing_id: str
    verdict: Verdict
    reason: str


class AnswerResult(Protocol):
    answer: str
    cited_ids: list[str]


class ClaimExtractor(Protocol):
    """Everything the pipeline asks a language model to do."""

    def extract(self, text: str) -> ExtractionResult:
        """Turn what a person said into separate, self-contained claims."""

    def compare(
        self, claim: Mapping[str, str], candidates: Sequence[StoredClaim]
    ) -> Sequence[ComparisonResult]:
        """Decide how a new claim (needs `title` and `statement`) relates to each
        stored candidate. Candidates the model says nothing about are unrelated."""

    def answer(self, question: str, claims: Sequence[StoredClaim]) -> AnswerResult:
        """Answer a question using only these claims, citing the ones used."""


class Transcriber(Protocol):
    def feed(self, samples: np.ndarray) -> Iterator[str]:
        """Accept mono float32 audio at 16 kHz; yield finalised segments."""

    def flush(self) -> Iterator[str]:
        """Yield whatever is left when the speaker stops."""
