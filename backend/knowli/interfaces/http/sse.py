"""Reconnectable native FastAPI Server-Sent Events."""

import asyncio
from collections.abc import AsyncIterable

from fastapi.sse import ServerSentEvent

from ...application.review import ContributionService


def _revision(value: str | None) -> int:
    try:
        return int(value) if value is not None else -1
    except ValueError:
        return -1


async def review_events(
    service: ContributionService,
    user_id: str,
    contribution_id: str,
    *,
    last_event_id: str | None,
    heartbeat_seconds: float = 15,
) -> AsyncIterable[ServerSentEvent]:
    """Poll only on the heartbeat boundary; no process-local event bus is needed."""
    seen = _revision(last_event_id)
    while True:
        state = service.get(user_id, contribution_id)
        if state["revision"] > seen:
            seen = state["revision"]
            yield ServerSentEvent(data=state, event="review", id=str(seen))
        await asyncio.sleep(heartbeat_seconds)
        yield ServerSentEvent(comment="heartbeat")
