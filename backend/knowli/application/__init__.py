"""The use cases: reviewing a capture, asking a knowledge base a question, and
saying which knowledge bases there are to ask.

This layer owns the workflow and nothing else. It depends on `domain` for what a
claim is and on `wiring` for the ports; it knows nothing about HTTP, and the
same functions serve the web app, the A2A peer and the MCP client. Resolving
which knowledge base a request means lives here for exactly that reason: three
surfaces ask the question and all three have to get the same answer.
"""
