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

## Review round 1/5

### RED

- SSE ownership test returned HTTP 200 because `service.get()` first ran inside
  the async generator, after response headers had started.
- Calling the documented service methods with `id=` raised `TypeError`.
- Unknown and duplicate resolution keys were silently accepted; `keep_old`
  could consequently remove a draft that had no conflict.
- The interview test checked stored `raw_text` but did not observe the fake
  model's actual extraction input.

### GREEN

- Added a FastAPI dependency preflight for the SSE route, so inaccessible and
  missing contributions resolve to 404 before `EventSourceResponse` starts.
- Renamed the public `confirm_claims`, `resolve_conflicts`, and `commit`
  identifier parameter to `id` and covered keyword calls.
- Resolution validation now rejects duplicate keys and any key outside the set
  of actually conflicted drafts, both before graph resumption and defensively
  in `prepare_commit`.
- The fake model records extraction inputs; the interview test proves it
  receives only the assignee's raw answer and never requester brief text.
