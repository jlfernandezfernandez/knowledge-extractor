"""Interview request values at the global-store boundary."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


InterviewStatus = Literal["pending", "started", "completed"]
InterviewView = Literal["pending", "sent", "completed"]


@dataclass(frozen=True)
class Interview:
    id: str
    requester_id: str
    assignee_id: str
    title: str
    brief: str
    status: InterviewStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


@dataclass(frozen=True)
class InterviewStart:
    interview: Interview
    contribution_id: str
