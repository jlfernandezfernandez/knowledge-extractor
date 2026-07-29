"""The two things about knowledge bases that can be silently wrong.

One: a slug is what decides whether two names are the same knowledge base, so
the derivation has to collapse everything that is only a spelling difference.

Two: the scope has to actually reach the store. Getting it wrong does not raise
anything — it produces a review that says "no conflicts" while a contradiction
sits in the next knowledge base over, or one that flags a contradiction between
two departments that have never heard of each other. Both look like success.
The database is not needed to test either: the stubs record which knowledge base
was asked for, which is the whole claim being made.
"""

from types import SimpleNamespace

import pytest

from knowli.application import review
from knowli.domain.claim import StoredClaim
from knowli.domain.knowledge_base import KnowledgeBase, slugify

# --- slugs --------------------------------------------------------------


def test_a_name_becomes_a_slug_a_url_can_carry():
    assert slugify("Kitchen Returns") == "kitchen-returns"
    assert slugify("  Support / Tier 2!  ") == "support-tier-2"


def test_names_that_differ_only_in_spelling_are_one_knowledge_base():
    # This is the dedup: nobody should end up with two knowledge bases they
    # cannot tell apart in a sidebar.
    same = ["Kitchen Returns", "kitchen returns", "Kitchen  Returns!", "KITCHEN-returns"]
    assert {slugify(name) for name in same} == {"kitchen-returns"}


def test_accents_are_folded_rather_than_dropped():
    # Dropping them would give "devoluciones-cocina" and "devoluciones-cocina"
    # different lengths of luck; folding makes the collision deliberate.
    assert slugify("Devoluciones Cocina") == slugify("devoluciones cocina")
    assert slugify("Atención al Cliente") == "atencion-al-cliente"


def test_a_name_with_nothing_usable_in_it_is_not_a_slug():
    # The caller decides what to do about it; it is simply not a name we can
    # address by URL.
    assert slugify("!!!") == ""
    assert slugify("   ") == ""


def test_a_long_name_is_cut_without_leaving_a_trailing_separator():
    # The cut lands exactly on the hyphen this name's space became.
    assert slugify("a" * 64 + " tail") == "a" * 64
    assert slugify("b" * 70) == "b" * 64


# --- scoping ------------------------------------------------------------

KITCHEN = KnowledgeBase(id="kb-kitchen", slug="kitchen", name="Kitchen")
SOFAS = KnowledgeBase(id="kb-sofas", slug="sofas", name="Sofas")

STORED = StoredClaim(id="x1", title="Returns", statement="Returns take 14 days.")
CLAIM = {"id": "c0", "title": "Returns", "statement": "Returns take 30 days.", "tags": []}


class StubRepository:
    """Claims per knowledge base, plus a record of which one was asked for."""

    def __init__(self, claims: dict[str, list[StoredClaim]]):
        self.claims = claims
        self.asked: list[str] = []
        self.written: list[tuple[str, str]] = []

    def neighbours(self, kb, embedding, k, max_distance):
        self.asked.append(kb.slug)
        return self.claims.get(kb.slug, [])

    def insert(self, kb, title, statement, tags, embedding, author, source):
        self.written.append((kb.slug, statement))
        return f"new-{len(self.written)}"

    def supersede(self, old_id, new_id):
        pass


class StubExtractor:
    """Says everything contradicts everything. Makes the point sharper: if a
    conflict does not appear, it is because the candidate never arrived."""

    def compare(self, claim, candidates):
        return [
            SimpleNamespace(existing_id=c.id, verdict="conflict", reason="cannot both hold")
            for c in candidates
        ]


class StubEmbedder:
    def embed(self, texts):
        return [[0.0] for _ in texts]


@pytest.fixture
def store(monkeypatch):
    def install(claims):
        repository = StubRepository(claims)
        monkeypatch.setattr(review, "repository", repository)
        monkeypatch.setattr(review, "embedder", StubEmbedder())
        monkeypatch.setattr(review, "extractor", StubExtractor())
        monkeypatch.setattr(
            review.knowledge_bases,
            "resolve",
            lambda slug: {"kitchen": KITCHEN, "sofas": SOFAS}[slug],
        )
        return repository

    return install


def test_a_contradiction_in_another_knowledge_base_is_not_a_conflict(store):
    # The whole point of the change. The stored claim contradicts the new one
    # word for word, and the extractor would say so if it ever saw it — but it
    # lives in a different knowledge base, so it is never retrieved.
    repository = store({"kitchen": [STORED]})
    result = review.detect({"claims": [CLAIM], "knowledge_base": "sofas"})
    assert result["conflicts"] == []
    assert repository.asked == ["sofas"]


def test_the_same_contradiction_inside_its_own_knowledge_base_does_conflict(store):
    repository = store({"kitchen": [STORED]})
    result = review.detect({"claims": [CLAIM], "knowledge_base": "kitchen"})
    assert [c["stored"]["id"] for c in result["conflicts"]] == ["x1"]
    assert repository.asked == ["kitchen"]


def test_a_commit_writes_into_the_sessions_knowledge_base(store):
    repository = store({})
    review.commit({"claims": [CLAIM], "knowledge_base": "sofas", "conflicts": []})
    assert repository.written == [("sofas", "Returns take 30 days.")]
