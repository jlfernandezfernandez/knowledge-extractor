# Task 5 report: contribution review

## Status

Implemented the contribution review as a dependency-injected LangGraph and
replaced the old session/knowledge-base HTTP surface with authenticated
`/api/contributions` routes and reconnectable native FastAPI SSE.

## RED

- Added service tests using a complete in-memory contribution store,
  deterministic model/embedder fakes, and LangGraph `InMemorySaver`.
- The first focal run failed during collection because the old review module
  still imported the removed knowledge-base policy (`RESOLUTION_POLICY`).
- Added HTTP/SSE contract tests; their first run failed because the old router
  still imported `application.knowledge_bases`.

## GREEN

- Focal gate:
  `pytest tests/test_rewind.py tests/test_contribution_review.py tests/integration/test_contribution_http.py -q`
  passed with 13 tests.
- Wider non-database regression gate covering auth, policy, review, and both
  HTTP suites passed with 24 tests.
- Python bytecode compilation completed without errors.

## Decisions

- The graph has exactly four application nodes: `extract_claims`,
  `find_conflicts`, `prepare_commit`, and `commit_claims`.
- Static LangGraph interrupts occur only after extraction and conflict
  discovery. Resolving runs `prepare_commit` to a terminal checkpoint; an
  explicit commit request resumes through `commit_claims`.
- Draft identity is UUID5 of a fixed namespace plus contribution ID and model
  output position. Model-provided keys and mutable statement text never define
  identity.
- Graph state contains only IDs and serializable review values. Store, model,
  embedder, and checkpointer are constructor dependencies.
- `commit_claims` makes one call to the store transaction, which remains the
  sole writer of claims and supersession links.
- Author checks live in `ContributionService`; inaccessible contributions map
  to 404, including mutation attempts.
- SSE uses FastAPI 0.141 `EventSourceResponse` and `ServerSentEvent`, revision
  IDs, the `review` event type, JSON data, `Last-Event-ID`, and a 15-second
  comment heartbeat. It polls only at heartbeat boundaries and adds no
  process-local bus or pub/sub layer.
- The OpenAI adapter uses `langchain_openai.ChatOpenAI` directly with
  transitively installed `langchain_core`; the general `langchain` package was
  not reintroduced.

## Concerns

- The legacy interview and Ask/knowledge modules still reference removed team
  and knowledge-base APIs. They are outside Task 5 and are intentionally not
  mounted or repaired here; Task 6 owns that migration.
- Database-backed integration suites were not part of the focal gate. The
  review service tests exercise the real graph and transaction port contract,
  while the already-approved PostgreSQL transaction implementation remains
  unchanged.
