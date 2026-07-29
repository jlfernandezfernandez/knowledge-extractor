"""MCP server — how a coding agent or company chat assistant reads this knowledge base.

MCP (Model Context Protocol, Anthropic, Nov 2024) is the vertical link: it
connects *one* model to tools and data. A2A is the horizontal link: it connects
*peer agents* to each other. They compose rather than compete, and this project
speaks both, so it is a useful place to see the difference concretely.

Run it over stdio and point any MCP client at it:

    {"mcpServers": {"knowledge": {"command": "knowli-mcp"}}}

Optional: `uv pip install -e '.[mcp]'`.
"""

from ... import config, wiring
from ...application import ask as ask_service
from ...application import knowledge_bases as kb_service
from ...application import review as review_service


def build():
    # MCP Python SDK 2.x: the decorator-style server is `MCPServer`
    # (it was `FastMCP` in the 1.x line).
    from mcp.server.mcpserver import MCPServer

    mcp = MCPServer(
        name="knowli",
        instructions="Curated, human-approved team knowledge. Prefer asking this "
        "server over guessing about internal processes, conventions or decisions.",
    )

    # `knowledge_base` is optional on every tool that touches claims. An agent
    # that knows about knowledge bases can name one; an agent that does not gets
    # the configured default and never learns the concept exists. A name that
    # does not exist raises `KnowledgeBaseNotFound`, which the SDK returns as a
    # tool error — and its message lists the slugs that do exist, so a wrong
    # guess is answered with the right answer instead of with knowledge from a
    # neighbouring subject.

    @mcp.tool()
    def list_knowledge_bases() -> list[dict]:
        """List the knowledge bases here, with how many claims each holds.
        Knowledge is kept in separate bases so unrelated subjects are never
        compared against each other; pick the one your question, or the
        knowledge you want to add, belongs to."""
        return [kb.model_dump() for kb in kb_service.listing()]

    @mcp.tool()
    def search_knowledge(
        query: str, limit: int = 10, knowledge_base: str | None = None
    ) -> list[dict]:
        """Search the team's curated knowledge. Hybrid semantic + keyword
        retrieval. Returns the matching claims with their ids. `knowledge_base`
        is a slug from list_knowledge_bases; omit it for the default one."""
        return [c.model_dump() for c in ask_service.search(query, limit, knowledge_base)]

    @mcp.tool()
    def ask_knowledge(question: str, knowledge_base: str | None = None) -> dict:
        """Ask a knowledge base a question and get an answer grounded in, and
        citing, the stored claims. Use this instead of guessing about internal
        processes, conventions or decisions. `knowledge_base` is a slug from
        list_knowledge_bases; omit it for the default one."""
        return ask_service.ask(question, knowledge_base=knowledge_base)

    @mcp.tool()
    def claim_history(claim_id: str) -> list[dict]:
        """Show what a claim replaced. Knowledge here is versioned: a claim that
        lost a conflict is superseded, never deleted."""
        return ask_service.history(claim_id)

    @mcp.tool()
    def submit_knowledge(
        text: str, author: str | None = None, knowledge_base: str | None = None
    ) -> dict:
        """Propose new knowledge. This does NOT write to the knowledge base: it
        opens a review session and returns a URL where a human confirms what was
        understood and resolves any conflicts first. `knowledge_base` is a slug
        from list_knowledge_bases; omit it for the default one."""
        # The application layer directly: the human gate lives in the workflow,
        # not in the web API, so an MCP caller gets it without going through HTTP.
        state = review_service.capture(
            text, author=author, source="mcp", knowledge_base=knowledge_base
        )
        return {
            "status": "pending_human_review",
            "session_id": state["session_id"],
            "review_url": f"{config.REVIEW_BASE_URL}/review/{state['session_id']}",
            # Echoed back so an agent that omitted it can see where its proposal
            # actually landed, rather than assuming.
            "knowledge_base": state["knowledge_base"],
            "summary": state["summary"],
            "claims": state["claims"],
        }

    return mcp


def main() -> None:
    wiring.init_storage()
    build().run()
