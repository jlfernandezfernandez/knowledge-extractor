# Knowli Foundation Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current prototype into a small, understandable, portfolio-quality Knowli application with login, one shared knowledge space, traceable contributions, interviews, RAG, a current shadcn interface, and a one-command local environment.

**Architecture:** Keep one React web application, one FastAPI application, and one PostgreSQL/pgvector database. FastAPI is a modular monolith: thin HTTP routes call small application services, services use explicit domain values and one PostgreSQL store, and LangGraph is limited to the resumable four-stage contribution review. The browser reaches only the web container; Vite proxies `/api` and `/ws` to the internal API.

**Tech Stack:** Python 3.12, FastAPI, LangGraph, `langchain-openai`, psycopg 3, PostgreSQL 17 + pgvector, fastembed, React 19, TypeScript, Vite 8, Tailwind CSS 4, shadcn `base-nova` with Base UI, i18next, Vitest, Testing Library, Playwright, Docker Compose, GitHub Actions.

## Global Constraints

- Do not add workspaces, organisations, teams, memberships, roles, tenants, or knowledge-base selectors.
- Every authenticated user reads and writes the same global knowledge space.
- Preserve existing users, sessions, interviews, review sessions, and knowledge during migration. Destructive legacy-table cleanup happens only after transactional count checks pass.
- Keep SQL out of HTTP handlers. Do not create a generic repository framework, command bus, event bus, dependency-injection container, or speculative provider abstraction.
- Keep LangGraph only where pause/resume is useful: capture, claims, conflicts, commit.
- Keep `langgraph`, `langgraph-checkpoint-postgres`, and `langchain-openai`; remove the general `langchain`, A2A, and MCP packages and surfaces.
- Use browser language detection for English and Spanish. Remember the detected language; do not add a language selector yet.
- Use only the official shadcn theme and Tailwind utilities. Do not recreate ChatGPT colours, custom shadows, composer CSS, or global animation rules.
- Use the owl mark consistently. Interview question lists contain text and status only: no avatar, initials, or person icon.
- All new behaviour starts with a failing test. Run the narrow test first, then the relevant suite, then commit.
- Run all shell commands from the repository root unless a step explicitly changes directory.

## Public Contracts

These contracts are frozen for this implementation. Backend Pydantic models and frontend TypeScript types use the same field names.

```text
POST /api/auth/register
  in:  { email, password, display_name }
  out: { user: { id, email, display_name } }

POST /api/auth/login
  in:  { email, password }
  out: { user: { id, email, display_name } }

POST /api/auth/logout
  out: 204

GET /api/auth/me
  out: { user: { id, email, display_name } }

GET /api/users
  out: { items: User[] }

POST /api/contributions
  in:  { raw_text, source: "text" | "speech", interview_id? }
  out: { id, stage: "claims", revision }

GET /api/contributions/{id}
  out: ContributionReview

PUT /api/contributions/{id}/claims
  in:  { revision, claims: ClaimDraft[] }
  out: ContributionReview

PUT /api/contributions/{id}/conflicts
  in:  { revision, resolutions: ConflictResolution[] }
  out: ContributionReview

POST /api/contributions/{id}/commit
  in:  { revision }
  out: { id, stage: "committed", committed_at, claim_count }

GET /api/contributions/{id}/events
  out: SSE events with monotonically increasing `revision`

GET /api/interviews?view=pending|sent|completed
  out: { items: Interview[] }

POST /api/interviews
  in:  { assignee_id, title, brief? }
  out: Interview

POST /api/interviews/{id}/start
  out: { interview: Interview, contribution_id }

POST /api/ask
  in:  { question }
  out: { answer, citations: Citation[], sufficient_evidence }

GET /api/history?cursor=&limit=20
  out: { items: HistoryItem[], next_cursor }
```

`ContributionReview` contains `id`, `author`, `kind`, `source`, `raw_text`,
`stage`, `revision`, `summary`, `claims`, `conflicts`, `created_at`, and
`committed_at`. `ClaimDraft` contains a stable `draft_key`, `title`,
`statement`, and `tags`. A citation contains claim ID, title, statement, author,
contribution ID, and contribution date.

---

## Task 1: Freeze the final schema and add safe migrations

**Files:**

- Create: `backend/knowli/infrastructure/postgres/migrations.py`
- Create: `backend/knowli/infrastructure/postgres/migrations/001_global_schema.sql`
- Create: `backend/knowli/infrastructure/postgres/migrations/002_import_legacy.sql`
- Create: `backend/knowli/infrastructure/postgres/migrations/003_remove_legacy.sql`
- Modify: `backend/knowli/infrastructure/postgres/pool.py`
- Delete: `backend/knowli/infrastructure/postgres/schema.sql`
- Create: `backend/tests/integration/test_migrations.py`

**Interfaces:**

- `run_migrations(pool: ConnectionPool) -> None`
- `schema_migration(version integer primary key, applied_at timestamptz)`
- Final tables: `app_user`, `login_session`, `interview`, `contribution`,
  `claim`, plus LangGraph checkpoint tables owned by its saver.

- [ ] Write `test_fresh_database_reaches_version_3` and
  `test_legacy_database_preserves_every_row`. The legacy test loads the current
  `schema.sql`, inserts one user, session, interview, review session, and
  knowledge row, runs migrations, then asserts the final row values and foreign
  keys.

- [ ] Run the integration test in PostgreSQL and confirm it fails because the
  migration runner does not exist:

```bash
docker compose up -d db
uv run --directory backend pytest tests/integration/test_migrations.py -q
```

Expected: `ModuleNotFoundError` for `migrations`.

- [ ] Implement a 25–40 line migration runner. It creates
  `schema_migration`, obtains `pg_advisory_xact_lock(hashtext('knowli-migrations'))`,
  reads embedded `.sql` resources in numeric order, executes each migration in
  one transaction, and records the version only after success.

- [ ] In `001_global_schema.sql`, create the final constraints directly:
  case-insensitive unique email, SHA-256 session token primary key, interview
  status check, contribution kind/stage checks, unique nullable
  `contribution.interview_id`, unique `(contribution_id, draft_key)`, pgvector
  embedding, generated `search_vector`, HNSW vector index, and GIN lexical
  index.

- [ ] In `002_import_legacy.sql`, copy rather than overwrite:
  `app_session → login_session`, `review_session → contribution`, and
  `knowledge → claim`. Create a synthetic committed contribution for each
  legacy claim without a review-session relationship. Resolve a legacy author
  by exact display name only when that match is unique. Otherwise create one
  deterministic synthetic user per distinct legacy author, so names are not
  merged or assigned arbitrarily. Convert interview `done` to `completed` and
  map its old `session_id` to `contribution.interview_id`.

- [ ] Add transactional guards before cleanup:

```sql
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'knowledge')
     AND (SELECT count(*) FROM claim) < (SELECT count(*) FROM knowledge) THEN
    RAISE EXCEPTION 'legacy claim import lost rows';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'review_session')
     AND (SELECT count(*) FROM contribution) < (SELECT count(*) FROM review_session) THEN
    RAISE EXCEPTION 'legacy contribution import lost rows';
  END IF;
END $$;
```

- [ ] In `003_remove_legacy.sql`, drop only the now-unreferenced legacy tables:
  `audit_event`, `team_member`, `team`, `organisation`, `knowledge`,
  `review_session`, `knowledge_base`, `workspace`, and `app_session`. Use
  guarded `DROP TABLE IF EXISTS` statements without `CASCADE`; an unexpected
  dependency must stop the migration.

- [ ] Call `run_migrations()` once during API startup, before constructing the
  LangGraph checkpointer.

- [ ] Run the migration tests twice against the same database. Expected: both
  runs pass and version rows remain exactly `1, 2, 3`.

```bash
uv run --directory backend pytest tests/integration/test_migrations.py -q
uv run --directory backend pytest tests/integration/test_migrations.py -q
```

- [ ] Commit:

```bash
git add backend/knowli/infrastructure/postgres backend/tests/integration
git commit -m "feat(db): add safe global schema migrations"
```

## Task 2: Simplify dependencies, configuration, and the domain

**Files:**

- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `backend/knowli/config.py`
- Modify: `backend/knowli/domain/claim.py`
- Modify: `backend/knowli/domain/conflict.py`
- Modify: `backend/knowli/domain/policy.py`
- Modify: `backend/knowli/domain/ports.py`
- Delete: `backend/knowli/domain/knowledge_base.py`
- Delete: `backend/knowli/application/knowledge_bases.py`
- Delete: `backend/tests/test_knowledge_base.py`
- Modify: `backend/tests/test_policy.py`

**Interfaces:**

- `ContributionStage = Literal["claims", "conflicts", "commit", "committed"]`
- `ClaimDraft(draft_key, title, statement, tags)`
- `ConflictResolution(claim_draft_key, action, replacement_statement=None)`
- Minimal protocols: `Model`, `Embedder`, `ContributionStore`,
  `SessionStore`. No knowledge-base arguments remain.

- [ ] Replace the knowledge-base tests with domain tests proving stable draft
  keys, allowed stage transitions, and conflict-resolution validation.

- [ ] Run the domain tests and confirm failures reference the old
  knowledge-base types:

```bash
uv run --directory backend pytest tests/test_policy.py -q
```

- [ ] Remove `langchain`, A2A, and MCP dependencies and scripts. Add
  `pwdlib[argon2]` to runtime dependencies and move `sherpa-onnx` into a
  `speech` optional extra. Keep `fastembed` in the default installation.

- [ ] Reduce configuration to explicit environment values:
  `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`,
  `EMBEDDING_MODEL`, `SESSION_DAYS`, `COOKIE_SECURE`, and optional
  `SPEECH_PROVIDER`. Delete workspace and knowledge-base settings.

- [ ] Replace broad ports with the exact methods consumed by services:
  `create_contribution`, `get_contribution`, `save_review`,
  `commit_claims`, `search_claims`, `list_history`, `create_interview`,
  `list_interviews`, `start_interview`, `get_user_by_session`, and session
  lifecycle methods. Use standard `Protocol`; do not add base classes.

- [ ] Regenerate and commit the lockfile:

```bash
uv lock --directory backend
uv run --directory backend pytest tests/test_policy.py -q
git add backend
git commit -m "refactor(core): model one shared knowledge space"
```

Expected: domain tests pass; the lock contains no `langchain`, `a2a-sdk`, or
`mcp` distribution.

## Task 3: Implement the one PostgreSQL store

**Files:**

- Create: `backend/knowli/infrastructure/postgres/migrations/004_contribution_revision.sql`
- Modify: `backend/knowli/infrastructure/postgres/repository.py`
- Modify: `backend/knowli/infrastructure/postgres/pool.py`
- Modify: `backend/knowli/domain/claim.py`
- Create: `backend/knowli/domain/contribution.py`
- Modify: `backend/knowli/domain/ports.py`
- Modify: `backend/tests/integration/test_migrations.py`
- Create: `backend/tests/integration/test_store.py`

**Interfaces:**

- `PostgresStore` implements the minimal protocols from Task 2.
- `contribution.revision` is an integer starting at zero and incremented by
  every successful review-state mutation.
- `ClaimToCommit`, `StoredContribution`, `ClaimSearchResult`, and `HistoryItem`
  are small frozen dataclasses used at the store boundary; do not introduce a
  generic result/model hierarchy.
- `commit_claims(contribution_id, expected_revision, claims)` is one
  transaction and returns the stored contribution.
- `search_claims(query_text, query_embedding, limit)` performs reciprocal-rank
  fusion over lexical and vector ranks.

- [ ] Write integration tests for global search across two authors, contribution
  history with provenance, optimistic revision rejection, and idempotent commit
  retry.

- [ ] Add migration `004_contribution_revision.sql` with
  `ALTER TABLE contribution ADD COLUMN revision integer NOT NULL DEFAULT 0`
  and a non-negative check. Update migration tests to expect versions
  `1, 2, 3, 4`, including repeat execution.

- [ ] Run and confirm failure because repository methods still require a
  knowledge-base ID:

```bash
uv run --directory backend pytest tests/integration/test_store.py -q
```

- [ ] Replace the repository with one concrete `PostgresStore`. Keep SQL beside
  the method that uses it. Use Pydantic/domain constructors only at the
  boundary; return typed values, not anonymous dictionaries.

- [ ] Align `ContributionStore` with the concrete task contract. Remove
  speculative methods that neither this task nor the next application service
  consumes; add methods later at their first real consumer.

- [ ] Implement hybrid retrieval as two CTEs with `row_number()`, then combine
  ranks with `1.0 / (60 + rank)`. Filter superseded claims and return at most
  the requested limit.

- [ ] Implement commit with:
  `SELECT ... FOR UPDATE`, expected-revision comparison,
  `INSERT ... ON CONFLICT (contribution_id, draft_key) DO UPDATE`, one
  contribution stage update, and interview completion in the same transaction.

- [ ] Run:

```bash
uv run --directory backend pytest tests/integration/test_store.py -q
uv run --directory backend pytest -q
```

Expected: all store and domain tests pass.

- [ ] Commit:

```bash
git add backend/knowli/infrastructure/postgres backend/tests
git commit -m "feat(db): implement global knowledge store"
```

## Task 4: Move authentication into an application service

**Files:**

- Create: `backend/knowli/application/auth.py`
- Modify: `backend/knowli/interfaces/http/auth.py`
- Modify: `backend/knowli/interfaces/http/schemas.py`
- Modify: `backend/knowli/wiring.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/tests/integration/test_auth_http.py`

**Interfaces:**

- `AuthService.register(email, password, display_name) -> AuthResult`
- `AuthService.login(email, password) -> AuthResult`
- `AuthService.authenticate(raw_token) -> User`
- `AuthService.logout(raw_token) -> None`
- Cookie name: `knowli_session`; HTTP-only; SameSite=Lax; Secure follows
  `COOKIE_SECURE`.

- [ ] Write unit tests using an in-memory fake session store for password
  hashing, wrong-password rejection, expired-session rejection, login token
  rotation, and logout.

- [ ] Write HTTP tests for register/login/me/logout and duplicate email. Assert
  only status, response body, and cookie properties; do not test implementation
  details.

- [ ] Run and confirm failure:

```bash
uv run --directory backend pytest tests/test_auth.py tests/integration/test_auth_http.py -q
```

- [ ] Implement Argon2id password hashing through `pwdlib`. Generate 32 random
  token bytes with `secrets.token_urlsafe`, persist only
  `sha256(raw_token).hexdigest()`, and use UTC expiry.

- [ ] Make handlers parse/serialize only. Inject `AuthService`; remove all SQL
  and pool access from `interfaces/http/auth.py`.

- [ ] Add `require_user` as one FastAPI dependency shared by every protected
  route. Return stable error bodies:
  `{"code":"unauthenticated","message":"..."}` and
  `{"code":"validation_error","message":"...","fields":{...}}`.

- [ ] Run:

```bash
uv run --directory backend pytest tests/test_auth.py tests/integration/test_auth_http.py -q
```

Expected: all authentication tests pass.

- [ ] Commit:

```bash
git add backend/knowli/application/auth.py backend/knowli/interfaces/http backend/knowli/wiring.py backend/tests
git commit -m "feat(auth): add simple cookie sessions"
```

## Task 5: Refactor contribution review around LangGraph

**Files:**

- Modify: `backend/knowli/application/review.py`
- Modify: `backend/knowli/infrastructure/llm/openai.py`
- Modify: `backend/knowli/interfaces/http/review.py`
- Modify: `backend/knowli/interfaces/http/sse.py`
- Modify: `backend/tests/test_rewind.py`
- Create: `backend/tests/test_contribution_review.py`
- Create: `backend/tests/integration/test_contribution_http.py`

**Interfaces:**

- `ContributionService.capture(user_id, raw_text, source, interview_id=None)`
- `ContributionService.get(user_id, contribution_id)`
- `ContributionService.confirm_claims(user_id, id, revision, claims)`
- `ContributionService.resolve_conflicts(user_id, id, revision, resolutions)`
- `ContributionService.commit(user_id, id, revision)`
- LangGraph state contains only serializable IDs and review data; connections,
  stores, models, and embedders are injected dependencies.

- [ ] Write a fake model returning fixed structured claims and a fake embedder
  returning deterministic vectors. Test capture → claims → conflicts → commit,
  editing and rewinding claims, stale revision rejection, unauthorized author
  rejection, retry-safe commit, and interview brief remaining visual context
  rather than extractable text.

- [ ] Run and confirm failure on old knowledge-base parameters:

```bash
uv run --directory backend pytest tests/test_rewind.py tests/test_contribution_review.py -q
```

- [ ] Give every extracted draft a stable `draft_key` derived once from its
  graph position and UUID namespace; preserve the key through edits and
  rewinds. Never use mutable statement text as identity.

- [ ] Keep four explicit nodes:
  `extract_claims`, `find_conflicts`, `prepare_commit`, `commit_claims`.
  Human interrupts occur after extraction and after conflict discovery.
  `commit_claims` delegates its whole database write to the store transaction.

- [ ] Replace knowledge endpoints with the public `/api/contributions`
  contracts. Require the authenticated author on create/read/edit/commit.
  Requester access to an interview is read-only through interview history, not
  through contribution mutation.

- [ ] Make SSE reconnectable: emit `id: <revision>`, `event: review`, and one
  JSON `data:` line; on `Last-Event-ID`, immediately send the current state only
  when its revision is newer. Send a comment heartbeat every 15 seconds.

- [ ] Run:

```bash
uv run --directory backend pytest tests/test_rewind.py tests/test_contribution_review.py tests/integration/test_contribution_http.py -q
```

Expected: review, rewind, authorization, and retry tests pass.

- [ ] Commit:

```bash
git add backend/knowli/application backend/knowli/interfaces/http backend/knowli/infrastructure/llm backend/tests
git commit -m "feat(review): make contributions traceable and resumable"
```

## Task 6: Finish interviews, asking, and history

**Files:**

- Create: `backend/knowli/application/interviews.py`
- Modify: `backend/knowli/application/ask.py`
- Modify: `backend/knowli/interfaces/http/interviews.py`
- Modify: `backend/knowli/interfaces/http/knowledge.py`
- Create: `backend/knowli/interfaces/http/history.py`
- Create: `backend/tests/test_interviews.py`
- Create: `backend/tests/test_ask.py`
- Create: `backend/tests/integration/test_interview_http.py`

**Interfaces:**

- An assignee starts one interview once; the same call retried returns the same
  contribution ID.
- Ask answers cite stored claims; when retrieval is empty, answer is a localized
  insufficient-evidence response and `sufficient_evidence=false`.
- History is cursor-paginated by `(created_at, id)` and includes author/source.

- [ ] Write tests for create/list views, only-assignee start, duplicate start,
  no self-interview, automatic completion on commit, global retrieval across
  authors, exact citation provenance, empty evidence, and stable history cursor.

- [ ] Run and confirm current interview foreign-key/order behaviour fails:

```bash
uv run --directory backend pytest tests/test_interviews.py tests/test_ask.py tests/integration/test_interview_http.py -q
```

- [ ] Implement `InterviewService` with direct rules and store calls. Starting
  an interview creates an empty `source="text"` contribution in one store
  transaction; the brief is returned as UI context but never passed to claim
  extraction. Extraction begins only after the assignee submits an answer.

- [ ] Update `AskService` to use global hybrid retrieval. The model prompt must
  state that only supplied claims may support the answer and must return cited
  claim IDs. Intersect model IDs with retrieved IDs before serializing.

- [ ] Implement `/api/history` as a read projection; do not add an audit-event
  write path.

- [ ] Run:

```bash
uv run --directory backend pytest tests/test_interviews.py tests/test_ask.py tests/integration/test_interview_http.py -q
uv run --directory backend pytest -q
```

Expected: the full backend suite passes.

- [ ] Commit:

```bash
git add backend
git commit -m "feat(api): finish interviews ask and history"
```

## Task 7: Remove unused surfaces and assemble the API

**Files:**

- Modify: `backend/knowli/interfaces/http/main.py`
- Modify: `backend/knowli/interfaces/http/health.py`
- Modify: `backend/knowli/wiring.py`
- Delete: `backend/knowli/interfaces/a2a/`
- Delete: `backend/knowli/interfaces/mcp/`
- Modify: `backend/knowli/interfaces/http/speech.py`
- Create: `backend/tests/test_app.py`

**Interfaces:**

- `/api/health/live` checks the process only.
- `/api/health/ready` checks PostgreSQL and returns 503 when unavailable.
- Speech endpoint exists only when the `speech` extra and provider are enabled;
  otherwise it returns stable `501 speech_unavailable`.

- [ ] Write an app smoke test that enumerates routes, proves every non-auth
  product endpoint returns 401 without a cookie, and proves A2A/MCP routes are
  absent.

- [ ] Run and confirm failure:

```bash
uv run --directory backend pytest tests/test_app.py -q
```

- [ ] Build dependencies once in a typed `AppServices` dataclass during
  lifespan. Mount routers explicitly. Close model, checkpointer, and pool in
  reverse construction order.

- [ ] Delete A2A and MCP source packages. Keep no compatibility stubs, protocol
  configuration, scripts, or documentation links.

- [ ] Make speech import lazy so a default install starts without
  `sherpa-onnx`.

- [ ] Run:

```bash
uv run --directory backend pytest -q
uv run --directory backend python -c "from knowli.interfaces.http.main import app; print(app.title)"
```

Expected: tests pass and command prints `Knowli`.

- [ ] Commit:

```bash
git add -A backend
git commit -m "refactor(api): keep one focused web application"
```

## Task 8: Establish the frontend foundation with stock shadcn

**Files:**

- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/main.tsx`
- Replace: `frontend/src/app.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/shell.tsx`
- Create: `frontend/src/components/brand.tsx`
- Create: `frontend/src/components/page-state.tsx`
- Modify/Create: `frontend/src/components/ui/*`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/app/router.test.tsx`

**Interfaces:**

- Routes: `/`, `/ask`, `/interviews`, `/history`, `/login`, `/register`,
  `/review/:id`.
- Desktop shell: compact left navigation and main content.
- Mobile shell: header plus shadcn Sheet navigation.
- Owl brand rendered as a small SVG React component using `currentColor`.

- [ ] Add a router test for the seven paths, authenticated redirects, active
  navigation, and the mobile navigation labels.

- [ ] Install only the needed dependencies and official components:

```bash
npm --prefix frontend install react-router
npm --prefix frontend install --save-dev vitest @testing-library/react @testing-library/jest-dom jsdom
npm exec --prefix frontend --yes --package=shadcn@latest -- shadcn add avatar card input label sheet skeleton tabs tooltip
```

- [ ] Add `"test": "vitest run"` to package scripts and run the new test.
  Expected: fail because the router and shell do not exist.

```bash
npm --prefix frontend test -- src/app/router.test.tsx
```

- [ ] Implement the router and shell with normal React composition. Navigation
  data is one local array; do not create a menu framework. Settings and logout
  live in the shadcn DropdownMenu at the bottom of the desktop rail.

- [ ] Reduce `index.css` to Tailwind import, `tw-animate-css`, official shadcn
  neutral theme variables, and shadcn base border/background rules. Layout,
  sizing, responsive behaviour, empty states, and composer appearance belong in
  Tailwind class names.

- [ ] Use the current shadcn `base-nova` components without wrapper copies.
  `Brand` is the only custom primitive because the product needs its owl mark.

- [ ] Run:

```bash
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

Expected: tests, lint, and production build pass with no export warnings.

- [ ] Commit:

```bash
git add frontend
git commit -m "feat(web): add shadcn application shell"
```

## Task 9: Add typed frontend auth and internationalization

**Files:**

- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/features/auth/types.ts`
- Create: `frontend/src/features/auth/api.ts`
- Create: `frontend/src/features/auth/auth-provider.tsx`
- Create: `frontend/src/features/auth/auth-screen.tsx`
- Modify: `frontend/src/i18n/index.ts`
- Modify: `frontend/src/i18n/en.ts`
- Modify: `frontend/src/i18n/es.ts`
- Create: `frontend/src/features/auth/auth-screen.test.tsx`

**Interfaces:**

- `api<T>(path, init) -> Promise<T>` includes cookies and converts the stable
  backend error body into `ApiError`.
- `useAuth()` returns `{ user, status, login, register, logout }`.
- Language detector order: localStorage, navigator; fallback English; supported
  languages English and Spanish.

- [ ] Write tests for login, registration, server field errors, session restore,
  logout, Spanish navigator selection, and English fallback.

- [ ] Run and confirm failure:

```bash
npm --prefix frontend test -- src/features/auth/auth-screen.test.tsx
```

- [ ] Implement one fetch helper and one auth context. Avoid a data-fetching
  library: these screens need no cache graph. Abort the `/me` request on
  provider unmount.

- [ ] Build login/register from shadcn Card, Input, Label, Button, and Sonner.
  Keep the owl mark, one clear heading, inline field errors, password
  autocomplete attributes, disabled submit state, and keyboard submit.

- [ ] Move every visible string introduced by Tasks 8–9 into both locale files.
  Use namespace-shaped plain objects; do not add runtime translation fetching.

- [ ] Run:

```bash
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

- [ ] Commit:

```bash
git add frontend
git commit -m "feat(web): add login and browser language"
```

## Task 10: Build the contribution and interview journeys

**Files:**

- Create: `frontend/src/features/home/home-page.tsx`
- Create: `frontend/src/features/contributions/api.ts`
- Create: `frontend/src/features/contributions/types.ts`
- Create: `frontend/src/features/interviews/api.ts`
- Create: `frontend/src/features/interviews/interviews-page.tsx`
- Create: `frontend/src/features/interviews/interview-dialog.tsx`
- Refactor: `frontend/src/features/review/*`
- Delete: `frontend/src/hooks/use-knowledge-bases.ts`
- Delete: `frontend/src/lib/api/knowledge-bases.ts`
- Create: `frontend/src/features/home/home-page.test.tsx`
- Create: `frontend/src/features/interviews/interviews-page.test.tsx`
- Create: `frontend/src/features/review/review-page.test.tsx`

**Interfaces:**

- Home is the contribution composer; there is no separate “add knowledge”
  button.
- Composer submit creates a contribution and navigates to `/review/:id`.
- Pending interview start navigates to the linked review route.
- Review requests always carry the last server revision.

- [ ] Write tests for empty/filled composer, pending interview summary,
  successful navigation, create interview, the three interview tabs,
  no avatars/initials in question rows, all four review stages, revision
  conflict refresh, and successful commit.

- [ ] Run and confirm failure:

```bash
npm --prefix frontend test -- src/features/home src/features/interviews src/features/review
```

- [ ] Implement the centered home composer with shadcn Textarea and Button.
  Below it, show at most three pending interviews and one link to the full list.
  No duplicated CTA exists in navigation or the page header.

- [ ] Implement interview rows with title, requester/assignee name as plain
  secondary text, status badge, date, and action. Do not render Avatar,
  initials, User icon, or per-person colour.

- [ ] Refactor existing review components rather than stacking a second review
  implementation. Delete knowledge-base selectors, old route hacks, and dead
  hooks. Use a small local reducer for editable drafts and EventSource for
  server progress.

- [ ] Ensure starting an interview shows title and brief above an empty answer
  composer. Only the submitted answer becomes `raw_text`.

- [ ] Add all new strings to English and Spanish locale files, then run:

```bash
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

- [ ] Commit:

```bash
git add -A frontend
git commit -m "feat(web): add contributions and interviews"
```

## Task 11: Build Ask and History, then remove dead frontend code

**Files:**

- Create: `frontend/src/features/ask/api.ts`
- Refactor: `frontend/src/features/ask/ask-page.tsx`
- Create: `frontend/src/features/history/api.ts`
- Create: `frontend/src/features/history/history-page.tsx`
- Create: `frontend/src/features/ask/ask-page.test.tsx`
- Create: `frontend/src/features/history/history-page.test.tsx`
- Delete: unused files under `frontend/src/components/`, `frontend/src/hooks/`,
  and `frontend/src/lib/api/` identified by `knip`
- Modify: `frontend/src/i18n/en.ts`
- Modify: `frontend/src/i18n/es.ts`

**Interfaces:**

- Ask is a single conversational page; citations are expandable shadcn Cards
  showing author and date.
- History is a chronological list with source, author, summary, claim count,
  and a link to the contribution review.

- [ ] Write Ask tests for question submit, loading, cited answer,
  insufficient-evidence state, and request error. Write History tests for
  pagination, author/source rendering, empty state, and review link.

- [ ] Run and confirm failure:

```bash
npm --prefix frontend test -- src/features/ask src/features/history
```

- [ ] Reuse the existing Ask screen only where its code remains simpler than
  replacement. Use shadcn ScrollArea/Card/Skeleton patterns and neutral theme
  tokens. Do not copy ChatGPT colour values or message bubble CSS.

- [ ] Implement history with a normal “Load more” button; do not add infinite
  scroll, virtualization, filters, or search in v1.

- [ ] Run a dead-code report, inspect every result, and delete only files with
  no runtime/test/config import:

```bash
npm exec --prefix frontend --yes --package=knip@latest -- knip
```

- [ ] Add translations and verify:

```bash
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

- [ ] Commit:

```bash
git add -A frontend
git commit -m "feat(web): add cited answers and history"
```

## Task 12: Make local development one command

**Files:**

- Modify: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `frontend/docker-entrypoint.sh`
- Modify: `frontend/vite.config.ts`
- Create: `.env.example`
- Modify: `.gitignore`
- Create: `scripts/smoke-local.sh`

**Interfaces:**

- `docker compose up --build` starts `db`, `api`, and `web`.
- Only `web` publishes `${KNOWLI_PORT:-3000}:3000`.
- Vite proxies `/api` and `/ws` to `http://api:8000`.
- PostgreSQL data lives in named volume `knowli_pgdata`.

- [ ] Write `scripts/smoke-local.sh` to poll the public web URL, request
  `/api/health/ready` through the web proxy, register a unique user, read `/me`,
  and log out. It exits non-zero on any unexpected status.

- [ ] Run it before Compose changes and confirm failure because no web/API
  services exist:

```bash
docker compose up --build -d
./scripts/smoke-local.sh
```

- [ ] Add API and web multi-stage Dockerfiles with non-root runtime users.
  Development source mounts are allowed in Compose; dependency volumes must be
  named so host `node_modules` and `.venv` are not overwritten.

- [ ] Add health checks and `depends_on: condition: service_healthy`. Do not
  publish ports 8000 or 5432. The web service binds Vite to `0.0.0.0:3000`.

- [ ] Keep environment setup small. `.env.example` contains
  `KNOWLI_PORT=3000`, `OPENAI_API_KEY=`, `OPENAI_MODEL=`, and optional speech
  values with comments. Local DB credentials remain Compose-local defaults.

- [ ] Run:

```bash
docker compose down
docker compose up --build -d
./scripts/smoke-local.sh
docker compose logs --no-color api web db
```

Expected: smoke passes; logs contain no traceback; host ports show only 3000.

- [ ] Commit:

```bash
git add docker-compose.yml backend/Dockerfile frontend/Dockerfile frontend/docker-entrypoint.sh frontend/vite.config.ts .env.example .gitignore scripts
git commit -m "feat(local): run Knowli with one command"
```

## Task 13: Add one real user journey and CI

**Files:**

- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/knowli.spec.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `.github/workflows/ci.yml`

**Interfaces:**

- E2E journey: register → contribute text → confirm claims → resolve conflicts
  → commit → ask a question → open citation/history.
- CI jobs: backend unit, backend PostgreSQL integration, frontend checks, E2E.
- AI is always fake in automated tests; CI never requires an OpenAI secret.

- [ ] Install Playwright, add `test:e2e`, and write the journey against
  `http://127.0.0.1:3000`:

```bash
npm --prefix frontend install --save-dev @playwright/test
npm --prefix frontend exec -- playwright install chromium
```

- [ ] Run the E2E test against the current app and confirm it fails at the first
  missing accessible label or route:

```bash
npm --prefix frontend run test:e2e
```

- [ ] Provide deterministic fake model/embedder configuration in Compose only
  for E2E. Do not add a production fake-provider switch reachable from HTTP.

- [ ] Add GitHub Actions with PostgreSQL/pgvector service, dependency caches,
  locked installs (`uv sync --frozen`, `npm ci`), backend tests, frontend test/
  lint/build, and Playwright artifact upload only on failure.

- [ ] Run the same commands locally:

```bash
uv sync --directory backend --frozen --extra dev
uv run --directory backend pytest -q
npm --prefix frontend ci
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Expected: every check passes without external AI/network calls during tests.

- [ ] Commit:

```bash
git add .github frontend
git commit -m "ci: verify the complete Knowli journey"
```

## Task 14: Rewrite documentation and perform the deletion audit

**Files:**

- Modify: `README.md`
- Replace: `docs/architecture.md`
- Replace: `docs/concepts.md`
- Replace: `docs/decisions.md`
- Replace: `docs/local-models.md`
- Delete: `docs/protocols.md`
- Delete: stale superseded files under `docs/superpowers/specs/` and
  `docs/superpowers/plans/`
- Create: `docs/learning-guide.md`

**Interfaces:**

- README quick start is exactly: copy `.env.example`, set an API key when using
  OpenAI, run `docker compose up --build`, open `http://localhost:3000`.
- Architecture documents one shared knowledge space and the four-stage graph.
- Learning guide explains request flow, where to add a feature, and why each
  chosen dependency exists.

- [ ] Write a documentation assertion test or shell check for forbidden product
  concepts and old names:

```bash
rtk rg -n -i "knowledge[-_ ]base|organisation|organization|\\bteam\\b|a2a|mcp|knowledge-extractor" README.md docs backend frontend docker-compose.yml
```

Expected before cleanup: matches in stale docs and code.

- [ ] Rewrite README for a portfolio reader first: what Knowli demonstrates,
  a screenshot placeholder only if a real screenshot is added in Task 15,
  features, one-command setup, test commands, and project map.

- [ ] Replace architecture docs with one Mermaid diagram:
  browser → web proxy → FastAPI services → LangGraph/store → PostgreSQL, plus
  external model/embedding edges. Document why this is a modular monolith and
  why MCP/A2A are deferred.

- [ ] Add a learning guide that traces login, contribution commit, interview,
  and ask requests using exact file paths. Explain FastAPI, LangGraph,
  pgvector/RRF, shadcn, i18n, and tests in plain language.

- [ ] Delete superseded docs rather than preserving contradictory archaeology
  in the main branch. Git history remains the archive.

- [ ] Run Ponytail’s whole-repo audit and remove dead abstractions, duplicate
  adapters, unused dependencies, abandoned feature flags, and copied UI
  primitives. Each removal must be followed by the relevant test suite.

- [ ] Verify the forbidden-concept search. Allowed matches are only the
  historical migration SQL and an explicit “deferred protocols” decision; all
  product/UI/runtime matches must be gone.

- [ ] Run full verification:

```bash
uv run --directory backend pytest -q
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
docker compose config
./scripts/smoke-local.sh
```

- [ ] Commit:

```bash
git add -A
git commit -m "docs: explain the final Knowli foundation"
```

## Task 15: Browser QA, accessibility, and repository rename

**Files:**

- Modify: only files implicated by observed QA defects
- Create: `docs/assets/knowli-home.png`
- Modify: `README.md`

**Interfaces:**

- Supported viewport checks: 390×844 mobile and 1440×900 desktop.
- Keyboard path covers login, navigation, composer, review, interviews, Ask,
  and History.
- GitHub repository final name: `knowli`.

- [ ] Start the production-like local stack and use the in-app browser to walk
  every E2E step in English and Spanish at both viewport sizes.

- [ ] Check visible focus, tab order, labels, heading hierarchy, error
  announcements, 44px mobile targets, empty/loading/error states, text
  contrast, long names, long claims, and reduced-motion behaviour.

- [ ] Confirm visual rules: official neutral shadcn palette, no custom ChatGPT
  colours, owl mark present, no duplicate add-knowledge button, no person icon
  or initials in interview lists, and no team/space selector.

- [ ] Fix every reproducible defect with a focused regression test, then rerun
  the frontend suite and Playwright journey.

- [ ] Capture a real 1440×900 home screenshot after QA and add it to README.
  Do not ship a mockup as a product screenshot.

- [ ] Run the final repository gate:

```bash
git status --short
uv run --directory backend pytest -q
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test:e2e
docker compose config
```

Expected: clean checks, no warnings, no untracked generated files.

- [ ] Rename the GitHub repository only after all local checks pass, then update
  the local remote and verify both:

```bash
gh repo rename knowli --repo jlfernandezfernandez/knowledge-extractor --yes
git remote set-url origin git@github.com:jlfernandezfernandez/knowli.git
gh repo view jlfernandezfernandez/knowli --json name,url,defaultBranchRef
git remote -v
```

- [ ] Push the current branch and open a focused pull request if work was done
  off `main`; otherwise push `main` only with the user’s explicit approval.

## Final Plan Review

- [ ] Compare every section of
  `docs/superpowers/specs/2026-07-30-knowli-foundation-redesign.md` against a
  task above: product scope, routes, auth, shared database, contribution graph,
  interviews, Ask, history, i18n, shadcn, speech, local infra, tests, docs, and
  rename each have an implementation and verification step.

- [ ] Scan the plan for unresolved placeholders:

```bash
rtk rg -n "[T]ODO|[T]BD|[F]IXME|appro[p]riate|as need[e]d|et[c]\\." docs/superpowers/plans/2026-07-30-knowli-foundation-redesign.md
```

Expected: no matches.

- [ ] Confirm type consistency across the public contracts, SQL fields, Python
  values, and TypeScript values: interview uses `completed`; contribution uses
  `committed`; `interview_id` exists only on contribution; authorship is
  `claim → contribution → app_user`; revision is an integer.

- [ ] Confirm every task ends in an observable test and a small commit, no task
  silently deletes user data, and no new abstraction exists without two current
  consumers.
