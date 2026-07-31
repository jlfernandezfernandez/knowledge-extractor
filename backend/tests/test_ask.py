"""Global ask and history projections only expose retrieved claim provenance."""

from dataclasses import asdict
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
                    source="text",
                    summary="A written rule.",
                    claim_count=1,
                    created_at=datetime(2026, 7, 30, tzinfo=UTC),
                )
            ],
            "opaque-next-page",
        )


class FakeInterviewStore:
    def __init__(self, interviews=()):
        self.interviews = list(interviews)
        self.calls = []

    def list_interviews(self, user_id, view):
        self.calls.append((user_id, view))
        return self.interviews


class FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def stream_answer(self, question, claims, *, tools=(), thread_id=None):
        self.calls.append({"question": question, "claims": claims, "tools": tools,
                           "thread_id": thread_id})
        yield {"type": "token", "content": "Deploy on Tuesdays."}


def _interview(title="Deployment retrospective"):
    from knowli.domain.interview import Interview

    return Interview(
        id="interview-1",
        requester_id="user-2",
        assignee_id="user-1",
        title=title,
        brief="Explain the release process.",
        status="pending",
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
        started_at=None,
        completed_at=None,
    )


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


def test_ask_streams_the_answer_from_the_retrieved_claims():
    """The agent must never be asked without the retrieved claims as its evidence."""
    from knowli.application.ask import AskService

    store = FakeStore([_claim(), _claim("claim-2")])
    model = FakeModel()
    service = AskService(store, model, FakeEmbedder(), FakeInterviewStore())

    events = list(service.stream_ask("When do we deploy?", "user-1", "thread-1"))

    assert events == [
        {
            "type": "claims",
            "items": [asdict(_claim()), asdict(_claim("claim-2"))],
        },
        {"type": "token", "content": "Deploy on Tuesdays."},
        {"type": "done"},
    ]
    assert [claim["id"] for claim in model.calls[0]["claims"]] == ["claim-1", "claim-2"]


def test_ask_namespaces_the_conversation_thread_by_user():
    """A guessed thread id must not replay another person's conversation."""
    from knowli.application.ask import AskService

    model = FakeModel()
    service = AskService(FakeStore([]), model, FakeEmbedder(), FakeInterviewStore())

    list(service.stream_ask("What is pending?", "user-1", "shared-thread"))

    assert model.calls[0]["thread_id"] == "user-1:shared-thread"


def test_ask_tool_only_reads_the_asking_users_interviews():
    """A tool that ignored the caller would leak someone else's interview list."""
    from knowli.application.ask import AskService

    interviews = FakeInterviewStore([_interview()])
    model = FakeModel()
    service = AskService(FakeStore([]), model, FakeEmbedder(), interviews)

    list(service.stream_ask("What interviews do I have?", "user-1", "thread-1"))
    (tool,) = model.calls[0]["tools"]
    answer = tool()

    assert interviews.calls == [("user-1", "pending")]
    assert "Deployment retrospective" in answer
    assert tool.__doc__, "the agent builds the tool schema from the docstring"


def test_ask_tool_says_so_when_no_interview_is_assigned():
    """An empty string would let the model invent interviews to fill the silence."""
    from knowli.application.ask import AskService

    model = FakeModel()
    service = AskService(FakeStore([]), model, FakeEmbedder(), FakeInterviewStore())

    list(service.stream_ask("What interviews do I have?", "user-1", "thread-1"))
    (tool,) = model.calls[0]["tools"]

    assert "No open interviews" in tool()


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
                "source": "text",
                "summary": "A written rule.",
                "claim_count": 1,
                "created_at": datetime(2026, 7, 30, tzinfo=UTC),
            }
        ],
        "next_cursor": "opaque-next-page",
    }
    assert store.history_calls == [("opaque-current-page", 20)]


def test_history_translates_a_malformed_store_cursor_to_an_application_error():
    """Leaking a cursor parse ValueError would turn a bad client page into a 500."""
    import pytest

    from knowli.application.ask import HistoryService, InvalidHistoryCursor

    class InvalidCursorStore(FakeStore):
        def list_history(self, cursor, limit):
            raise ValueError("invalid history cursor")

    with pytest.raises(InvalidHistoryCursor, match="invalid history cursor"):
        HistoryService(InvalidCursorStore([])).history("bad", 20)
