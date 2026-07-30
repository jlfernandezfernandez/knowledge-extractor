"""The use cases: reviewing a capture, asking a knowledge base a question, and
saying which knowledge bases there are to ask.

This layer owns the workflow and nothing else. It depends on `domain` for what a
claim is and on `wiring` for the ports; it knows nothing about HTTP. Resolving
which knowledge base a request means lives here so every web route has the same
answer.
"""
