"""Global ask and history projections only expose retrieved claim provenance."""

from datetime import UTC, datetime

from knowli.domain.claim import ClaimSearchResult
from knowli.domain.contribution import HistoryItem


class FakeEmbedder:
    def embed(self, texts):
        return [[0.25, 0.75] for _ in texts]


class FakeStore:
    def __init__(self, claims):
        self.claims = claims
        self.history_calls = []

    def search_claims(self, query_text, query_embedding, limit):
        return self.claims[:limit]

    def list_history(self, cursor, limit):
        self.history_calls.append((cursor, limit))
        return (
            [
                HistoryItem(
                    contribution_id="contribution-1",
                    author="Ada",
                    summary="A written rule.",
                    claim_count=1,
                    created_at=datetime(2026, 7, 30, tzinfo=UTC),
                )
            ],
            "opaque-next-page",
        )


class FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def answer(self, question, claims):
        from knowli.domain.claim import AnswerResult

        self.calls.append((question, claims))
        return AnswerResult("Deploy on Tuesdays.", ("claim-1", "made-up-id"))


def _claim(claim_id="claim-1"):
    return ClaimSearchResult(
        id=claim_id,
        title="Deployment day",
        statement="Deploy on Tuesdays.",
        tags=("release",),
        author="Ada",
        contribution_id="contribution-1",
        contribution_created_at=datetime(2026, 7, 29, tzinfo=UTC),
    )


def test_ask_returns_only_retrieved_citations_with_exact_provenance():
    """Trusting model-invented ids would return a citation for an unstored claim."""
    from knowli.application.ask import AskService

    store = FakeStore([_claim(), _claim("claim-2")])
    model = FakeModel()
    result = AskService(store, model, FakeEmbedder()).ask("When do we deploy?")

    assert result == {
        "answer": "Deploy on Tuesdays.",
        "citations": [
            {
                "id": "claim-1",
                "title": "Deployment day",
                "statement": "Deploy on Tuesdays.",
                "author": "Ada",
                "contribution_id": "contribution-1",
                "contribution_created_at": datetime(2026, 7, 29, tzinfo=UTC),
            }
        ],
    }
    assert model.calls[0][1][0]["id"] == "claim-1"


def test_ask_returns_deterministic_insufficient_evidence_without_claims():
    """Calling the model without evidence would let it answer from outside the store."""
    from knowli.application.ask import AskService

    model = FakeModel()
    result = AskService(FakeStore([]), model, FakeEmbedder()).ask("What is the policy?")

    assert result == {
        "answer": "",
        "citations": [],
    }
    assert model.calls == []


def test_history_preserves_store_cursor_and_provenance():
    """Replacing the cursor or dropping author would break stable history pages."""
    from knowli.application.ask import HistoryService

    store = FakeStore([])
    result = HistoryService(store).history("opaque-current-page", 20)

    assert result == {
        "items": [
            {
                "contribution_id": "contribution-1",
                "author": "Ada",
                "summary": "A written rule.",
                "claim_count": 1,
                "created_at": datetime(2026, 7, 30, tzinfo=UTC),
            }
        ],
        "next_cursor": "opaque-next-page",
    }
    assert store.history_calls == [("opaque-current-page", 20)]


def test_history_service_does_not_require_an_llm():
    """Reading history must work locally without an OpenAI key."""
    from knowli.application.ask import HistoryService

    store = FakeStore([])

    result = HistoryService(store).history(None, 20)

    assert result["items"][0]["contribution_id"] == "contribution-1"
    assert result["next_cursor"] == "opaque-next-page"


def test_history_translates_a_malformed_store_cursor_to_an_application_error():
    """Leaking a cursor parse ValueError would turn a bad client page into a 500."""
    import pytest

    from knowli.application.ask import HistoryService, InvalidHistoryCursor

    class InvalidCursorStore(FakeStore):
        def list_history(self, cursor, limit):
            raise ValueError("invalid history cursor")

    with pytest.raises(InvalidHistoryCursor, match="invalid history cursor"):
        HistoryService(InvalidCursorStore([])).history("bad", 20)
