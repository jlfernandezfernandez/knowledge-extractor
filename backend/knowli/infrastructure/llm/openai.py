"""Direct ``langchain_openai`` adapter plus the LangGraph answer agent."""

import json
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI

from ... import config
from ...domain.claim import ClaimDraft
from .prompts import ANSWER_SYSTEM, COMPARE_SYSTEM, EXTRACT_SYSTEM
from .schemas import Comparisons, Extraction


class OpenAICompatibleModel:
    def __init__(self, chat_model: BaseChatModel | None = None, checkpointer: Any = None):
        self._chat = chat_model or ChatOpenAI(
            model=config.MODEL_NAME,
            api_key=config.MODEL_API_KEY,
            base_url=config.MODEL_BASE_URL or None,
            temperature=0,
            reasoning_effort=config.MODEL_REASONING_EFFORT or None,
        )
        self._checkpointer = checkpointer

    def close(self) -> None:
        """Release the OpenAI HTTP client when the application stops."""
        close = getattr(getattr(self._chat, "root_client", None), "close", None)
        if callable(close):
            close()

    def extract_claims(self, raw_text: str) -> list[ClaimDraft]:
        result = self._chat.with_structured_output(Extraction).invoke(
            [("system", EXTRACT_SYSTEM), ("human", raw_text)]
        )
        extraction = (
            result if isinstance(result, Extraction) else Extraction.model_validate(result)
        )
        return [
            ClaimDraft(
                draft_key="",
                title=claim.title,
                statement=claim.statement,
                tags=claim.tags,
            )
            for claim in extraction.claims
        ]

    def find_conflicts(
        self, claims: list[ClaimDraft], candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        payload = {
            "new": [claim.model_dump() for claim in claims],
            "existing": candidates,
        }
        result = self._chat.with_structured_output(Comparisons).invoke(
            [
                ("system", COMPARE_SYSTEM),
                ("human", json.dumps(payload, ensure_ascii=False, default=str)),
            ]
        )
        comparisons = (
            result if isinstance(result, Comparisons) else Comparisons.model_validate(result)
        )
        return [comparison.model_dump() for comparison in comparisons.comparisons]

    def stream_answer(
        self,
        question: str,
        claims: list[dict[str, Any]],
        *,
        tools: Sequence[Callable[..., Any]] = (),
        thread_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Stream one agent turn: answer tokens, plus an event per tool call so the
        client can show what the agent is doing rather than a silent pause."""
        # This turn's evidence rides in the system prompt, which is not stored in the
        # thread: the saved conversation keeps only what the person and the agent said,
        # and the question reaches the model as a question -- wrapped in a JSON payload
        # it reads as data and the tools never fire.
        evidence = json.dumps(claims, ensure_ascii=False, default=str)
        # ponytail: compiled per turn because the tools close over the asking user and
        # the evidence changes. Cache per user if graph builds ever show in a profile.
        agent = create_agent(
            self._chat,
            list(tools),
            system_prompt=f"{ANSWER_SYSTEM}\n\nKnowledge claims for this question:\n{evidence}",
            checkpointer=self._checkpointer,
        )
        yield from agent_events(
            agent.stream(
                {"messages": [("human", question)]},
                config={"configurable": {"thread_id": thread_id}},
                stream_mode="messages",
            )
        )


def agent_events(stream: Iterator[tuple[Any, Any]]) -> Iterator[dict[str, Any]]:
    """Turn LangGraph message chunks into the events the client renders: answer
    tokens, and a running/finished pair per tool the agent decides to call."""
    announced: set[str] = set()
    for chunk, _ in stream:
        if isinstance(chunk, ToolMessage):
            yield {"type": "tool", "name": chunk.name, "done": True}
            continue
        for call in getattr(chunk, "tool_call_chunks", None) or []:
            # Chunks arrive split: the name lands once, the arguments trickle after.
            name = call.get("name")
            if name and name not in announced:
                announced.add(name)
                yield {"type": "tool", "name": name, "done": False}
        content = getattr(chunk, "content", None)
        if content and isinstance(content, str):
            yield {"type": "token", "content": content}
