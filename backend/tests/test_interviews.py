"""Interview requests are global, assignee-owned contribution prompts."""

from datetime import UTC, datetime

import pytest

from knowli.domain.contribution import StoredContribution
from knowli.domain.user import User


class MemoryInterviewStore:
    def __init__(self) -> None:
        self.users = {
            "requester": User("requester", "requester@example.test", "Requester"),
            "assignee": User("assignee", "assignee@example.test", "Assignee"),
        }
        self.interviews = {}
        self.contribution_ids = {}

    def get_user_by_id(self, user_id):
        return self.users.get(user_id)

    def create_interview(self, requester_id, assignee_id, title, brief):
        from knowli.domain.interview import Interview

        interview = Interview(
            id=f"interview-{len(self.interviews) + 1}",
            requester_id=requester_id,
            assignee_id=assignee_id,
            title=title,
            brief=brief,
            status="pending",
            created_at=datetime(2026, 7, 30, tzinfo=UTC),
            started_at=None,
            completed_at=None,
        )
        self.interviews[interview.id] = interview
        return interview

    def list_interviews(self, user_id, view):
        from dataclasses import replace

        interviews = list(self.interviews.values())
        if view == "pending":
            return [item for item in interviews if item.assignee_id == user_id and item.status == "pending"]
        if view == "sent":
            return [item for item in interviews if item.requester_id == user_id and item.status != "completed"]
        return [
            item
            for item in interviews
            if item.status == "completed" and user_id in {item.requester_id, item.assignee_id}
        ]

    def get_interview(self, interview_id):
        return self.interviews.get(interview_id)

    def start_interview(self, interview_id, assignee_id):
        from dataclasses import replace
        from knowli.domain.interview import InterviewStart

        interview = self.interviews.get(interview_id)
        if interview is None or interview.assignee_id != assignee_id:
            return None
        started = replace(
            interview,
            status="started" if interview.status == "pending" else interview.status,
            started_at=interview.started_at or datetime(2026, 7, 30, 12, tzinfo=UTC),
        )
        self.interviews[interview_id] = started
        contribution_id = self.contribution_ids.setdefault(interview_id, f"contribution-{interview_id}")
        return InterviewStart(interview=started, contribution_id=contribution_id)


class FakeContributionService:
    def __init__(self) -> None:
        self.calls = []

    def capture(self, user_id, raw_text, source, interview_id=None):
        self.calls.append((user_id, raw_text, source, interview_id))
        return {"id": "contribution-interview-1", "raw_text": raw_text}


def test_create_rejects_self_assignment_and_unknown_assignee():
    """Removing user validation would allow impossible self or missing-user requests."""
    from knowli.application.interviews import InterviewService, InvalidInterview

    service = InterviewService(MemoryInterviewStore())

    with pytest.raises(InvalidInterview, match="yourself"):
        service.create("requester", "requester", "Deployment", "")
    with pytest.raises(InvalidInterview, match="assignee"):
        service.create("requester", "missing", "Deployment", "")


def test_assignee_starts_once_and_only_submitted_answer_reaches_extraction():
    """A second start must reuse its contribution and a brief must never be captured as text."""
    from knowli.application.interviews import InterviewService, InterviewUnavailable

    store = MemoryInterviewStore()
    service = InterviewService(store)
    interview = service.create("requester", "assignee", "Deployment", "Secret requester context")

    with pytest.raises(InterviewUnavailable):
        service.start("requester", interview.id)
    first = service.start("assignee", interview.id)
    second = service.start("assignee", interview.id)
    captured_by = FakeContributionService()
    answer = service.answer("assignee", interview.id, "Deploy on Tuesdays.", captured_by)

    assert (first.contribution_id, second.contribution_id) == (
        "contribution-interview-1",
        "contribution-interview-1",
    )
    assert answer == {"id": "contribution-interview-1", "raw_text": "Deploy on Tuesdays."}
    assert captured_by.calls == [
        ("assignee", "Deploy on Tuesdays.", "text", interview.id)
    ]
    assert "Secret requester context" not in captured_by.calls[0][1]


def test_answer_requires_the_assignee_to_start_the_interview_first():
    """Capturing before start would bypass the interview's explicit assignee action."""
    from knowli.application.interviews import InterviewService, InvalidInterview

    service = InterviewService(MemoryInterviewStore())
    interview = service.create("requester", "assignee", "Deployment", "")

    with pytest.raises(InvalidInterview, match="started"):
        service.answer("assignee", interview.id, "Deploy on Tuesdays.", FakeContributionService())


def test_list_views_separate_received_sent_and_completed_interviews():
    """Mixing requester and assignee views would expose the wrong interview inbox."""
    from dataclasses import replace
    from knowli.application.interviews import InterviewService

    store = MemoryInterviewStore()
    service = InterviewService(store)
    active = service.create("requester", "assignee", "Active", "")
    completed = service.create("requester", "assignee", "Completed", "")
    store.interviews[completed.id] = replace(store.interviews[completed.id], status="completed")

    assert [item.id for item in service.list("assignee", "pending")] == [active.id]
    assert [item.id for item in service.list("requester", "sent")] == [active.id]
    assert [item.id for item in service.list("assignee", "completed")] == [completed.id]
