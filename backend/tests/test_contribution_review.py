"""Contribution review behavior with real LangGraph state and deterministic fakes."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from knowli.application.review import (
    ContributionService,
    ContributionUnavailable,
    InvalidReview,
)
from knowli.domain.claim import ClaimDraft, ClaimSearchResult, ClaimToCommit
from knowli.domain.contribution import (
    ContributionNotFound,
    HistoryItem,
    StaleRevision,
    StoredContribution,
)


class MemoryContributionStore:
    def __init__(self):
        self.rows: dict[str, StoredContribution] = {}
        self.committed: dict[str, list[ClaimToCommit]] = {}
        self.candidates: list[ClaimSearchResult] = []
        self.interviews: dict[str, dict[str, str]] = {}
        self.contribution_interviews: dict[str, str] = {}
        self._next_id = 0

    def create_contribution(self, author_id, raw_text, source, interview_id=None):
        if interview_id is not None and interview_id not in self.interviews:
            raise ContributionNotFound(interview_id)
        self._next_id += 1
        contribution_id = f"00000000-0000-0000-0000-{self._next_id:012d}"
        row = StoredContribution(
            id=contribution_id,
            author_id=author_id,
            author=f"User {author_id}",
            kind="interview" if interview_id else "voluntary",
            source=source,
            raw_text=raw_text,
            stage="claims",
            revision=0,
            summary="",
            created_at=datetime(2026, 7, 30, tzinfo=UTC),
            committed_at=None,
            claim_count=0,
        )
        self.rows[row.id] = row
        if interview_id is not None:
            self.contribution_interviews[row.id] = interview_id
        return row

    def get_contribution(self, contribution_id):
        return self.rows.get(contribution_id)

    def save_review(self, contribution_id, expected_revision, stage, summary):
        row = self.rows.get(contribution_id)
        if row is None:
            raise ContributionNotFound(contribution_id)
        if row.revision != expected_revision or row.stage == "committed":
            raise StaleRevision(contribution_id)
        updated = replace(row, stage=stage, revision=row.revision + 1, summary=summary)
        self.rows[contribution_id] = updated
        return updated

    def commit_claims(self, contribution_id, expected_revision, claims):
        row = self.rows.get(contribution_id)
        if row is None:
            raise ContributionNotFound(contribution_id)
        if row.stage == "committed":
            if row.revision != expected_revision + 1 or self.committed[contribution_id] != claims:
                raise StaleRevision(contribution_id)
            return row
        if row.revision != expected_revision:
            raise StaleRevision(contribution_id)
        self.committed[contribution_id] = claims
        updated = replace(
            row,
            stage="committed",
            revision=row.revision + 1,
            committed_at=datetime(2026, 7, 30, 12, tzinfo=UTC),
            claim_count=len(claims),
        )
        self.rows[contribution_id] = updated
        return updated

    def search_claims(self, query_text, query_embedding, limit):
        return self.candidates[:limit]

    def list_history(self, cursor, limit):
        return ([], None)


class FixedModel:
    def __init__(self):
        self.extracted_texts: list[str] = []

    def extract_claims(self, raw_text):
        self.extracted_texts.append(raw_text)
        return [
            ClaimDraft(
                draft_key="model-key-must-be-ignored",
                title="Deployments",
                statement="Deploy on Tuesdays.",
                tags=["release"],
            )
        ]

    def find_conflicts(self, claims, candidates):
        if not candidates:
            return []
        return [
            {
                "claim_draft_key": claims[0].draft_key,
                "existing_id": candidates[0]["id"],
                "verdict": "conflict",
                "reason": "The deployment day changed.",
            }
        ]

    def answer(self, question, claims):
        return "unused"


class FixedEmbedder:
    def embed(self, texts):
        return [[float(len(text)), 1.0] for text in texts]


@pytest.fixture
def service():
    store = MemoryContributionStore()
    model = FixedModel()
    return (
        ContributionService(store, model, FixedEmbedder(), InMemorySaver()),
        store,
        model,
    )


def test_capture_review_conflicts_and_commit_are_resumable(service):
    review, store, _ = service
    store.candidates = [
        ClaimSearchResult(
            id="11111111-1111-1111-1111-111111111111",
            title="Old deployments",
            statement="Deploy on Fridays.",
            tags=("release",),
            author="Ada",
            contribution_id="22222222-2222-2222-2222-222222222222",
            contribution_created_at=datetime(2026, 7, 1, tzinfo=UTC),
            score=0.9,
        )
    ]

    captured = review.capture("author-1", "Deploy on Tuesdays.", "text")
    draft_key = captured["claims"][0]["draft_key"]
    confirmed = review.confirm_claims(
        "author-1", captured["id"], captured["revision"], captured["claims"]
    )
    ready = review.resolve_conflicts(
        "author-1",
        captured["id"],
        confirmed["revision"],
        [
            {
                "claim_draft_key": draft_key,
                "action": "keep_new",
            }
        ],
    )
    committed = review.commit("author-1", captured["id"], ready["revision"])

    assert captured["stage"] == "claims"
    assert confirmed["stage"] == "conflicts"
    assert confirmed["conflicts"][0]["existing_id"] == store.candidates[0].id
    assert ready["stage"] == "commit"
    assert (committed["stage"], committed["claim_count"]) == ("committed", 1)
    assert store.committed[captured["id"]][0].supersedes == (store.candidates[0].id,)


def test_edit_and_rewind_preserve_uuid_key_derived_from_position(service):
    review, _, _ = service
    captured = review.capture("author-1", "Deploy on Tuesdays.", "text")
    original_key = captured["claims"][0]["draft_key"]
    edited = [{**captured["claims"][0], "statement": "Deploy on Wednesdays."}]

    conflicts = review.confirm_claims(
        "author-1", captured["id"], captured["revision"], edited
    )
    rewound = review.back("author-1", captured["id"], conflicts["revision"])

    assert rewound["stage"] == "claims"
    assert rewound["claims"][0]["draft_key"] == original_key
    assert rewound["claims"][0]["statement"] == "Deploy on Wednesdays."
    assert original_key != "model-key-must-be-ignored"


def test_stale_revision_and_non_author_are_rejected(service):
    review, _, _ = service
    captured = review.capture("author-1", "Deploy on Tuesdays.", "text")

    with pytest.raises(StaleRevision):
        review.confirm_claims("author-1", captured["id"], 0, captured["claims"])
    with pytest.raises(ContributionUnavailable):
        review.get("author-2", captured["id"])


def test_commit_retry_returns_the_same_result_without_duplicate_claims(service):
    review, store, _ = service
    captured = review.capture("author-1", "Deploy on Tuesdays.", "text")
    conflicts = review.confirm_claims(
        "author-1", captured["id"], captured["revision"], captured["claims"]
    )
    ready = review.resolve_conflicts(
        "author-1", captured["id"], conflicts["revision"], []
    )

    first = review.commit("author-1", captured["id"], ready["revision"])
    retried = review.commit("author-1", captured["id"], ready["revision"])

    assert retried == first
    assert len(store.committed[captured["id"]]) == 1


def test_interview_brief_is_not_added_to_extractable_text(service):
    review, store, model = service
    interview_id = "33333333-3333-3333-3333-333333333333"
    brief = "Extract the quarterly target from this requester brief."
    store.interviews[interview_id] = {"id": interview_id, "brief": brief}

    captured = review.capture_interview_answer(
        "author-1", "My answer only.", interview_id
    )

    assert captured["raw_text"] == "My answer only."
    assert captured["kind"] == "interview"
    assert store.contribution_interviews[captured["id"]] == interview_id
    assert model.extracted_texts == ["My answer only."]
    assert brief not in model.extracted_texts[0]


def test_public_review_methods_accept_the_documented_id_keyword(service):
    review, _, _ = service
    captured = review.capture("author-1", "Deploy on Tuesdays.", "text")

    confirmed = review.confirm_claims(
        user_id="author-1",
        id=captured["id"],
        revision=captured["revision"],
        claims=captured["claims"],
    )
    ready = review.resolve_conflicts(
        user_id="author-1",
        id=captured["id"],
        revision=confirmed["revision"],
        resolutions=[],
    )
    committed = review.commit(
        user_id="author-1",
        id=captured["id"],
        revision=ready["revision"],
    )

    assert committed["stage"] == "committed"


def _review_waiting_on_a_conflict(service):
    review, store, _ = service
    store.candidates = [
        ClaimSearchResult(
            id="11111111-1111-1111-1111-111111111111",
            title="Old deployments",
            statement="Deploy on Fridays.",
            tags=("release",),
            author="Ada",
            contribution_id="22222222-2222-2222-2222-222222222222",
            contribution_created_at=datetime(2026, 7, 1, tzinfo=UTC),
            score=0.9,
        )
    ]
    captured = review.capture("author-1", "Deploy on Tuesdays.", "text")
    return review, review.confirm_claims(
        "author-1", captured["id"], captured["revision"], captured["claims"]
    )


def test_conflict_resolutions_reject_unknown_draft_keys(service):
    review, conflicted = _review_waiting_on_a_conflict(service)
    draft_key = conflicted["claims"][0]["draft_key"]

    with pytest.raises(InvalidReview, match="conflicted draft"):
        review.resolve_conflicts(
            "author-1",
            conflicted["id"],
            conflicted["revision"],
            [
                {"claim_draft_key": draft_key, "action": "keep_both"},
                {"claim_draft_key": "not-a-conflicted-draft", "action": "keep_old"},
            ],
        )


def test_conflict_resolutions_reject_duplicate_draft_keys(service):
    review, conflicted = _review_waiting_on_a_conflict(service)
    draft_key = conflicted["claims"][0]["draft_key"]

    with pytest.raises(InvalidReview, match="duplicate resolution"):
        review.resolve_conflicts(
            "author-1",
            conflicted["id"],
            conflicted["revision"],
            [
                {"claim_draft_key": draft_key, "action": "keep_new"},
                {"claim_draft_key": draft_key, "action": "keep_old"},
            ],
        )


def test_keep_old_cannot_remove_a_conflict_free_draft(service):
    review, _, _ = service
    captured = review.capture("author-1", "Deploy on Tuesdays.", "text")
    confirmed = review.confirm_claims(
        "author-1", captured["id"], captured["revision"], captured["claims"]
    )

    with pytest.raises(InvalidReview, match="conflicted draft"):
        review.resolve_conflicts(
            "author-1",
            confirmed["id"],
            confirmed["revision"],
            [
                {
                    "claim_draft_key": confirmed["claims"][0]["draft_key"],
                    "action": "keep_old",
                }
            ],
        )
