"""Global user-to-user interview requests and answer capture."""

from typing import Protocol

from ..domain.interview import Interview, InterviewStart, InterviewView
from ..domain.ports import InterviewStore


class InvalidInterview(ValueError):
    pass


class InterviewUnavailable(LookupError):
    pass


class CaptureService(Protocol):
    def capture_interview_answer(
        self, user_id: str, raw_text: str, interview_id: str
    ) -> dict: ...


class InterviewService:
    def __init__(self, store: InterviewStore):
        self._store = store

    def create(self, requester_id: str, assignee_id: str, title: str, brief: str) -> Interview:
        if requester_id == assignee_id:
            raise InvalidInterview("you cannot assign an interview to yourself")
        if self._store.get_user_by_id(assignee_id) is None:
            raise InvalidInterview("assignee does not exist")
        cleaned_title = title.strip()
        if not cleaned_title:
            raise InvalidInterview("a title is required")
        return self._store.create_interview(
            requester_id, assignee_id, cleaned_title, brief.strip()
        )

    def list(self, user_id: str, view: InterviewView) -> list[Interview]:
        return self._store.list_interviews(user_id, view)

    def start(self, user_id: str, interview_id: str) -> InterviewStart:
        interview = self._store.get_interview(interview_id)
        if interview is None or interview.assignee_id != user_id:
            raise InterviewUnavailable(interview_id)
        started = self._store.start_interview(interview_id, user_id)
        if started is None:
            raise InterviewUnavailable(interview_id)
        return started

    def answer(
        self,
        user_id: str,
        interview_id: str,
        raw_text: str,
        contributions: CaptureService,
    ) -> dict:
        interview = self._store.get_interview(interview_id)
        if interview is None or interview.assignee_id != user_id:
            raise InterviewUnavailable(interview_id)
        if interview.status != "started":
            raise InvalidInterview("the interview must be started before answering")
        if not raw_text.strip():
            raise InvalidInterview("an answer is required")
        return contributions.capture_interview_answer(user_id, raw_text, interview_id)
