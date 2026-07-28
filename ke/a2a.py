"""Expose the knowledge base to other agents over Google's Agent2Agent protocol.

Two skills, matching how the humans use it:
  - search_knowledge: read the RAG.
  - submit_knowledge: propose knowledge. It does NOT land in the RAG — it opens
    a review session for a human, and the agent gets the review URL back. The
    whole point of this project is that a person approves what goes in.

Optional: `uv pip install -e '.[a2a]'`, then `ke-a2a`.
"""

import json
import os
import uuid

from . import config, db, embed, pipeline

REVIEW_BASE_URL = os.environ.get("REVIEW_BASE_URL", "http://127.0.0.1:8000")
A2A_HOST = os.environ.get("A2A_HOST", "127.0.0.1")
A2A_PORT = int(os.environ.get("A2A_PORT", "9999"))


def search_knowledge(query: str, k: int = 10) -> dict:
    vector = embed.embed([query])[0]
    items = db.neighbours(vector, k, max_distance=2.0)
    return {
        "results": [
            {
                "id": item["id"],
                "title": item["title"],
                "statement": item["statement"],
                "tags": item["tags"],
                "distance": round(float(item["distance"]), 4),
            }
            for item in items
        ]
    }


def submit_knowledge(text: str, author: str | None = None) -> dict:
    session_id = pipeline.understand(text, author, source="a2a")
    session = db.get_session(session_id)
    return {
        "status": "pending_human_review",
        "session_id": session_id,
        "review_url": f"{REVIEW_BASE_URL}/?session={session_id}",
        "atoms": session["payload"]["atoms"],
    }


def _handle(text: str, skill: str | None) -> dict:
    if skill == "submit_knowledge":
        return submit_knowledge(text)
    return search_knowledge(text)


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

    card = AgentCard(
        name="Knowledge Extractor",
        description=(
            "Team knowledge base. Search accumulated knowledge, or propose new "
            "knowledge for human review before it is stored."
        ),
        version="0.1.0",
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
            AgentSkill(
                id="search_knowledge",
                name="Search knowledge",
                description="Semantic search over the team's curated knowledge base.",
                tags=["rag", "search"],
                examples=["what is our release process?", "cual es la politica de vacaciones"],
                input_modes=["text/plain"],
                output_modes=["application/json"],
            ),
            AgentSkill(
                id="submit_knowledge",
                name="Submit knowledge",
                description=(
                    "Propose new knowledge. Returns a review URL; a human confirms "
                    "the extracted claims and resolves conflicts before anything is stored."
                ),
                tags=["rag", "write", "human-in-the-loop"],
                examples=["The staging deploy now runs on Tuesdays, not Mondays."],
                input_modes=["text/plain"],
                output_modes=["application/json"],
            ),
        ],
    )

    handler = DefaultRequestHandler(
        agent_executor=Executor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    routes = [*create_agent_card_routes(card), *create_jsonrpc_routes(handler, "/")]
    return Starlette(routes=routes)


def main() -> None:
    import uvicorn

    db.init()
    print(f"Agent card: http://{A2A_HOST}:{A2A_PORT}/.well-known/agent-card.json")
    print(f"LLM: {config.LLM_MODEL} | embeddings: {config.EMBED_MODEL}")
    uvicorn.run(build_app(), host=A2A_HOST, port=A2A_PORT)
