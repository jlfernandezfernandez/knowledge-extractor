"""The agent's message chunks become the events the chat renders."""

from langchain_core.messages import AIMessageChunk, ToolMessage

from knowli.infrastructure.llm.openai import agent_events


def _chunk(content="", tool_call_chunks=()):
    return AIMessageChunk(content=content, tool_call_chunks=list(tool_call_chunks))


def test_a_tool_call_is_announced_once_and_closed_when_it_returns():
    """Announcing every argument chunk would flood the chat with duplicate markers."""
    stream = [
        (_chunk(tool_call_chunks=[
            {"name": "list_my_interviews", "args": "", "id": "call-1", "index": 0},
        ]), {}),
        (_chunk(tool_call_chunks=[
            {"name": None, "args": "{}", "id": None, "index": 0},
        ]), {}),
        (ToolMessage(content="- A retro", name="list_my_interviews", tool_call_id="call-1"), {}),
        (_chunk(content="You have one interview."), {}),
    ]

    assert list(agent_events(iter(stream))) == [
        {"type": "tool", "name": "list_my_interviews", "done": False},
        {"type": "tool", "name": "list_my_interviews", "done": True},
        {"type": "token", "content": "You have one interview."},
    ]


def test_empty_chunks_do_not_reach_the_client():
    """Reasoning models emit empty content chunks; each one would be a wasted event."""
    stream = [(_chunk(), {}), (_chunk(content="Friday."), {})]

    assert list(agent_events(iter(stream))) == [{"type": "token", "content": "Friday."}]
