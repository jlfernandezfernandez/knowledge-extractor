"""MCP server — how a coding agent or company chat assistant reads this knowledge base.

MCP (Model Context Protocol, Anthropic, Nov 2024) is the vertical link: it
connects *one* model to tools and data. A2A is the horizontal link: it connects
*peer agents* to each other. They compose rather than compete, and this project
speaks both, so it is a useful place to see the difference concretely.

Run it over stdio and point any MCP client at it:

    {"mcpServers": {"knowledge": {"command": "ke-mcp"}}}

Optional: `uv pip install -e '.[mcp]'`.
"""

from . import ask as ask_module
from . import config, store


def build():
    # MCP Python SDK 2.x: the decorator-style server is `MCPServer`
    # (it was `FastMCP` in the 1.x line).
    from mcp.server.mcpserver import MCPServer

    mcp = MCPServer(
        name="knowledge-extractor",
        instructions="Curated, human-approved team knowledge. Prefer asking this "
        "server over guessing about internal processes, conventions or decisions.",
    )

    @mcp.tool()
    def search_knowledge(query: str, limit: int = 10) -> list[dict]:
        """Search the team's curated knowledge base. Hybrid semantic + keyword
        retrieval. Returns the matching claims with their ids."""
        return [c.model_dump() for c in ask_module.search(query, limit)]

    @mcp.tool()
    def ask_knowledge(question: str) -> dict:
        """Ask the knowledge base a question and get an answer grounded in, and
        citing, the stored claims. Use this instead of guessing about internal
        processes, conventions or decisions."""
        return ask_module.ask(question).model_dump()

    @mcp.tool()
    def claim_history(claim_id: str) -> list[dict]:
        """Show what a claim replaced. Knowledge here is versioned: a claim that
        lost a conflict is superseded, never deleted."""
        return store.history(claim_id)

    @mcp.tool()
    def submit_knowledge(text: str, author: str | None = None) -> dict:
        """Propose new knowledge. This does NOT write to the knowledge base: it
        opens a review session and returns a URL where a human confirms what was
        understood and resolves any conflicts first."""
        from .api import capture
        from .schemas import CaptureRequest

        state = capture(CaptureRequest(text=text, author=author, source="mcp"))
        return {
            "status": "pending_human_review",
            "session_id": state.session_id,
            "review_url": f"{config.REVIEW_BASE_URL}/review/{state.session_id}",
            "summary": state.summary,
            "claims": [c.model_dump() for c in state.claims],
        }

    return mcp


def main() -> None:
    store.init()
    build().run()
