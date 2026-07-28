"""A2A server — how *peer agents* talk to this knowledge base.

Agent2Agent (Google, April 2025; v1.0 and Linux Foundation governance since
April 2026) is the horizontal protocol: agents publish an Agent Card describing
their skills, then exchange Tasks and Messages over JSON-RPC/HTTP. Where MCP
gives one model a tool, A2A lets another team's autonomous agent treat this
knowledge base as a peer it can consult — or contribute to.

Note what `submit_knowledge` does NOT do: write. An agent can propose knowledge,
and gets back a review URL. The human gate is the product, so it holds for
machine callers too.

Optional: `uv pip install -e '.[a2a]'`, then `ke-a2a`.
"""

import json
import os
import uuid

from . import ask as ask_module
from . import config, store

A2A_HOST = os.environ.get("A2A_HOST", "127.0.0.1")
A2A_PORT = int(os.environ.get("A2A_PORT", "9999"))


def _handle(text: str, skill: str | None) -> dict:
    if skill == "submit_knowledge":
        from .api import capture
        from .schemas import CaptureRequest

        state = capture(CaptureRequest(text=text, author=None, source="a2a"))
        return {
            "status": "pending_human_review",
            "session_id": state.session_id,
            "review_url": f"{config.REVIEW_BASE_URL}/review/{state.session_id}",
            "summary": state.summary,
            "claims": [c.model_dump() for c in state.claims],
        }
    if skill == "ask_knowledge":
        return ask_module.ask(text).model_dump()
    return {"results": [c.model_dump() for c in ask_module.search(text)]}


def build_app():
    from a2a.server.agent_execution import AgentExecutor, RequestContext
    from a2a.server.events import EventQueue
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
    from a2a.server.tasks import InMemoryTaskStore
    from a2a.types import (
        AgentCapabilities,
        AgentCard,
        AgentInterface,
        AgentSkill,
        Message,
        Part,
        Role,
    )
    from starlette.applications import Starlette

    class Executor(AgentExecutor):
        async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
            result = _handle(context.get_user_input(), (context.metadata or {}).get("skill"))
            # A single Message is the "immediate response" shape the SDK expects.
            await event_queue.enqueue_event(
                Message(
                    message_id=uuid.uuid4().hex,
                    context_id=context.context_id or "",
                    task_id=context.task_id or "",
                    role=Role.ROLE_AGENT,
                    parts=[Part(text=json.dumps(result, ensure_ascii=False, default=str))],
                )
            )

        async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
            raise NotImplementedError("cancel is not supported")

    def skill(skill_id: str, name: str, description: str, tags: list[str], examples: list[str]):
        return AgentSkill(
            id=skill_id, name=name, description=description, tags=tags, examples=examples,
            input_modes=["text/plain"], output_modes=["application/json"],
        )

    card = AgentCard(
        name="Knowledge Extractor",
        description=(
            "A team's curated knowledge base. Search or ask questions against "
            "accumulated internal knowledge, or propose new knowledge for human "
            "review before it is stored."
        ),
        version="0.2.0",
        default_input_modes=["text/plain"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(streaming=False),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=f"http://{A2A_HOST}:{A2A_PORT}",
                protocol_version="1.0",
            )
        ],
        skills=[
            skill("search_knowledge", "Search knowledge",
                  "Hybrid semantic + keyword search over the curated knowledge base. "
                  "Returns matching claims with their ids.",
                  ["rag", "search"],
                  ["what is our release process?", "cual es la politica de vacaciones"]),
            skill("ask_knowledge", "Ask knowledge",
                  "Ask a question and get an answer grounded in, and citing, the "
                  "stored claims.",
                  ["rag", "qa"],
                  ["how do we handle a failed production deploy?"]),
            skill("submit_knowledge", "Submit knowledge",
                  "Propose new knowledge. Returns a review URL; a human confirms the "
                  "extracted claims and resolves conflicts before anything is stored.",
                  ["rag", "write", "human-in-the-loop"],
                  ["The staging deploy now runs on Tuesdays, not Mondays."]),
        ],
    )

    handler = DefaultRequestHandler(
        agent_executor=Executor(), task_store=InMemoryTaskStore(), agent_card=card,
    )
    return Starlette(routes=[*create_agent_card_routes(card),
                            *create_jsonrpc_routes(handler, "/")])


def main() -> None:
    import uvicorn

    store.init()
    print(f"Agent card: http://{A2A_HOST}:{A2A_PORT}/.well-known/agent-card.json")
    uvicorn.run(build_app(), host=A2A_HOST, port=A2A_PORT)
