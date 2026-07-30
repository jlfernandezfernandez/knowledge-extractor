# Knowli Foundation Redesign

## Purpose

Knowli is a self-hosted web application for turning what people know into
reviewed, queryable claims in one shared vector-backed knowledge base.

The repository is also a portfolio and learning project. Its architecture must
show current AI techniques without hiding the product behind speculative
abstractions. A reader should be able to follow one request from React to
FastAPI, through LangGraph and the model adapters, into Postgres.

This design replaces the earlier team-oriented foundation. Knowli has users and
authorship, but no organisations, teams, memberships, roles, tenants, or
multiple knowledge bases in v1.

## Success criteria

- A fresh checkout starts the web app, API, and Postgres/pgvector with
  `docker compose up --build`.
- A person can register, sign in, contribute knowledge, review extracted
  claims, resolve conflicts, and commit them.
- A signed-in person can request an interview from another user; the assignee's
  answer enters the same review flow.
- Any signed-in person can ask a question over the one shared knowledge base
  and inspect the exact claims used as sources.
- Every committed claim is traceable to its author, contribution, source, and
  supersession history.
- Backend rules are testable without a database or model. Integration tests
  exercise the real database. One end-to-end test covers the primary journey.
- UI uses current shadcn `base-nova` components and theme tokens rather than a
  parallel custom design system.
- English and Spanish ship together. Browser language is detected and
  remembered automatically.
- Documentation describes the code that exists, including rejected choices
  and local model setup.

## Product scope

### Included in v1

- Local email/password accounts and opaque server-side sessions.
- One global vector-backed knowledge base shared by all registered users.
- Voluntary text contributions.
- Optional live dictation.
- Interviews requested from one user to another.
- Four-stage human review:
  capture, confirm claims, resolve conflicts, commit.
- Hybrid semantic and lexical retrieval.
- RAG answers with claim citations and provenance.
- Contribution history and immutable claim lineage.
- English and Spanish UI.
- Local or remote OpenAI-compatible model configuration.
- Docker Compose development/demo stack.

### Excluded from v1

- Organisations, teams, memberships, roles, and invitations.
- Per-user, per-team, or multiple knowledge bases.
- OAuth, OIDC, SAML, and enterprise tenancy.
- Files, images, object storage, and MinIO.
- MCP and A2A servers.
- Persistent chat history or long conversational memory.
- Agents, tool calling, autonomous writes, and scheduled interviews.
- External vector-store drivers.
- Database row-level security.

## Information architecture

The signed-in shell follows ChatGPT's interaction structure: a quiet sidebar,
one centered working surface, recent activity, and a compact user menu. Its
visual system remains stock shadcn `base-nova / neutral`.

### Primary routes

| Route | Purpose |
| --- | --- |
| `/` | Contribution composer plus a compact pending-interview summary. This is already the “new contribution” surface, so no duplicate add button exists. |
| `/ask` | RAG question and answer experience with citations and source details. |
| `/interviews` | Pending, sent, and completed interviews. Creating an interview opens a dialog. |
| `/history` | Contributions, authors, dates, status, and claim supersession history. |

### Auxiliary routes

| Route | Purpose |
| --- | --- |
| `/login` | Sign in, outside the application shell. |
| `/register` | Create an account, outside the application shell. |
| `/review/:id` | Resume or inspect a contribution. The same route shows the final committed state. |

Settings and logout live in the user dropdown instead of separate pages.
Desktop uses the shadcn Sidebar. Mobile uses the corresponding Sheet and a
menu button in the top bar.

### Brand

The Knowli mark remains the owl in a rounded neutral tile. The favicon and
in-app brand use the same mark and accessible product name.

## Core journeys

### Voluntary contribution

1. The signed-in user writes or dictates text on `/`.
2. The client creates a contribution with the authenticated user as author.
3. LangGraph extracts discrete claims and pauses.
4. `/review/:id` shows editable claims. The user can edit or remove each claim,
   answer clarification questions, or return to the source text.
5. The graph retrieves active neighbouring claims from the global knowledge
   base and classifies genuine conflicts.
6. The user resolves each conflict.
7. One transaction writes the new claims, supersedes losing claims, and marks
   the contribution committed.
8. The final review state links to history and offers another contribution.

Nothing enters the knowledge base before the final commit.

### Interview

1. A signed-in user opens the interview dialog, selects another user, and
   supplies a title and optional brief.
2. The assignee sees the interview under pending interviews.
3. Starting it creates an empty contribution linked to the interview.
4. Title and brief appear as visual context above the composer. They are not
   sent through extraction as if they were the assignee's answer.
5. The assignee writes or dictates the answer and follows the standard review
   flow.
6. Successful commit marks the interview completed.

Only the assignee can start or complete an interview. The requester and
assignee can inspect it; all committed claims still join the one shared base.

### Ask

1. The user asks a question on `/ask`.
2. The backend embeds the question and performs global hybrid retrieval over
   active claims.
3. The LLM receives only retrieved claims and instructions to cite claim IDs.
4. The response shows cited claims first, with author, contribution date, and a
   link to `/review/:id`.
5. If retrieval provides no adequate evidence, Knowli says so instead of
   synthesizing an unsupported answer.

Chat history is frontend state only in v1 and is not stored in Postgres.

## UX rules

- Home's primary action is the composer itself.
- Interviews are text rows using shadcn Item; no avatars or initials appear in
  question lists.
- The review has four visible stages: capture, claims, conflicts, saved.
- Back navigation works until commit. Committed history is never rewritten.
- Progress shows real LangGraph node updates over SSE.
- Success uses Sonner sparingly. Recoverable failures render inline beside the
  failed action.
- Empty, loading, and unavailable states use shadcn Empty, Skeleton, and Alert.
- Controls meet 44-pixel touch targets on mobile and retain visible focus.
- Reduced-motion preferences are respected by shadcn defaults and short
  utility transitions.

## Visual system

`components.json` remains:

- style: `base-nova`;
- base: Base UI;
- base color: neutral;
- icon library: Lucide;
- Tailwind CSS v4;
- CSS variables enabled.

The project installs current components through the shadcn CLI. Expected
building blocks include Sidebar, Sheet, Button, Textarea, InputGroup, Item,
Field, DropdownMenu, Dialog, Badge, Empty, Skeleton, Progress, Alert, and
Sonner.

`src/index.css` contains Tailwind/shadcn imports, official theme variables, and
base styles required by the generated preset. It does not define a separate
ChatGPT palette, composer tokens, custom shadows, global animation system, or
bespoke component classes. Layout and small state transitions use Tailwind
utilities in feature components.

ChatGPT influences information hierarchy and interaction structure, not copied
brand colors or private assets.

## Internationalisation

- `react-i18next`, `i18next`, and the browser language detector remain.
- English is the fallback locale; English and Spanish catalogs are
  type-aligned.
- Language is detected from the browser and remembered.
- v1 has no visible language selector.
- User-generated content, claims, and answers are never translated
  automatically.

## Architecture

Knowli is a modular monolith plus a React SPA and one Postgres database.

```text
React web
    |
FastAPI routers and DTOs
    |
Application use cases
    |-- auth
    |-- contributions and review
    |-- interviews
    |-- ask
    `-- history
    |
Domain rules
    |-- claims
    |-- conflicts
    `-- resolution policy
    |
Concrete adapters
    |-- Postgres repositories
    |-- LangGraph checkpointer
    |-- LLM
    |-- embeddings
    `-- optional speech
```

### Dependency boundaries

- HTTP authenticates, validates DTOs, calls one use case, and maps typed errors
  to status codes. It contains no SQL or business decisions.
- Application code coordinates domain rules and explicit ports. It contains no
  FastAPI response types or SQL.
- Domain code contains pure types and policies. It imports no framework,
  database, or model package.
- Infrastructure contains concrete Postgres and model implementations.
- `wiring.py` is the only composition root.

Ports exist only at boundaries used by tests or multiple implementations.
There are no factories, provider registries, or wrappers for hypothetical
storage and vector backends.

## AI framework boundaries

- LangGraph owns only the contribution review state machine and its human
  interrupts.
- `langgraph-checkpoint-postgres` persists resumable state.
- `langchain-openai` owns the OpenAI-compatible chat adapter and structured
  output.
- The general `langchain` package is removed. Knowli does not use chains,
  agents, retrievers, or tool calling.
- `fastembed` provides local embeddings.
- Speech support and `sherpa-onnx` move to an optional dependency extra.

Model packages never appear in HTTP, domain, or React code.

## Data model

### `app_user`

- `id` UUID primary key;
- normalized unique `email`;
- `display_name`;
- Argon2id `password_hash`;
- `created_at`.

### `login_session`

- SHA-256 `token_hash` primary key;
- `user_id` foreign key;
- `expires_at`;
- `created_at`.

The raw token exists only in an HTTP-only, SameSite=Lax cookie. Secure cookies
are enabled outside local HTTP mode. Login rotates the session; logout deletes
it.

### `interview`

- `id` UUID primary key;
- `requester_id` and `assignee_id` foreign keys;
- `title` and optional `brief`;
- status `pending`, `started`, or `completed`;
- created, started, and completed timestamps.

### `contribution`

- `id` UUID primary key and LangGraph thread ID;
- `author_id` foreign key;
- kind `voluntary` or `interview`;
- nullable unique `interview_id`;
- `source`;
- original `raw_text`;
- current stage and summary;
- created, updated, and committed timestamps.

This is a first-class product entity, not a denormalized index over LangGraph.

### `claim`

- `id` UUID primary key;
- `contribution_id` foreign key;
- stable `draft_key` within the contribution;
- title, statement, and tags;
- embedding vector and generated lexical search vector;
- nullable `superseded_by` self-reference;
- `created_at`.

Authorship is resolved through `claim → contribution → app_user`; it is not
duplicated on each claim. A unique `(contribution_id, draft_key)` constraint
makes graph commit retries idempotent.

No workspace, organisation, team, membership, knowledge-base, or generic audit
event table exists. History is a projection of users, interviews,
contributions, claims, and supersession links.

## API shape

### Auth

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/users` for interview assignee selection

### Contributions

- `POST /api/contributions`
- `GET /api/contributions`
- `GET /api/contributions/{id}`
- `POST /api/contributions/{id}/confirm`
- `POST /api/contributions/{id}/resolve`
- `POST /api/contributions/{id}/back`

### Interviews

- `POST /api/interviews`
- `GET /api/interviews?view=pending|sent|completed`
- `POST /api/interviews/{id}/start`

### Knowledge

- `POST /api/ask`
- `GET /api/claims/{id}/history`

### Optional speech

- `WS /api/transcribe/live`

All routes except register, login, and health require a valid session. A
resource the caller may not access returns 404. Retrieval and conflict checks
are global by design and take no workspace or knowledge-base parameter.

## Failure handling

- Application errors are typed and mapped centrally to 400, 401, 404, 409, or
  503 responses.
- Validation errors retain FastAPI's 422 contract.
- LLM, embedding, and speech failures never partially commit claims.
- Raw contribution text and the latest checkpoint remain available for retry.
- SSE disconnects cause the client to refetch `/api/contributions/{id}`.
- Claim commit and supersession run in one transaction.
- Commit is idempotent through stable draft keys and database constraints.
- Ask returns an explicit insufficient-evidence response when retrieval is
  empty or below the configured relevance threshold.
- Frontend does not swallow errors; it renders a concise message and a retry
  action when recovery is possible.

## Database evolution

Schema changes use numbered SQL migrations and a small tested runner built on
psycopg. A `schema_migration` table records each applied file. This avoids an
ORM dependency while preserving deterministic upgrades.

The redesign migration removes the incomplete team schema only after copying
valid users, sessions, interviews, contributions, and claims into the new
tables. If the current development database contains no valuable data, the
documented local reset remains available but is never performed implicitly.

## Local infrastructure

Default Compose services:

- `web`: builds React, serves static assets, and proxies `/api` and `/ws`;
- `api`: runs FastAPI on the internal network;
- `db`: Postgres 17 with pgvector and a named volume.

Only web publishes `${KNOWLI_PORT:-3000}`. API and Postgres remain internal, so
the stack cannot collide with another local Postgres on port 5432.

`docker compose up --build` is the primary quick start. Health checks order
startup and report database/API readiness. The frontend and backend also retain
direct development commands with Vite proxying to FastAPI.

Ollama is optional and runs on the host. Compose reaches it through
`host.docker.internal`, including the Linux host-gateway mapping. Hosted
OpenAI-compatible providers use environment variables. Missing model access
does not prevent the shell from starting; model-backed actions show an
actionable unavailable state.

`uv.lock` and `package-lock.json` are committed. `.env.example` documents every
supported setting and contains local-only defaults, never secrets.

## Verification

### Backend

- Pure pytest coverage for claim resolution and graph navigation policies.
- Integration tests with real Postgres for registration, login/session expiry,
  interview authorization, author provenance, global retrieval, claim lineage,
  migrations, and idempotent commit.
- Deterministic fake LLM and embedder adapters for graph tests.

### Frontend

- Vitest and Testing Library for auth routing, home actions, review stages,
  interview views, ask citations, and error/retry states.
- One Playwright journey:
  register → contribute → confirm → commit → ask → open cited provenance.
- Oxlint, TypeScript build, and production bundle checks.

### CI

- Ruff format/lint and pytest.
- Oxlint, TypeScript, Vitest, and Vite build.
- Compose configuration validation and container build.
- No live LLM, model download, or external API key required.

## Documentation

- `README.md`: product value, screenshot, architecture summary, one-command
  quick start, and verification commands.
- `docs/architecture.md`: boundaries and one complete request trace.
- `docs/concepts.md`: claims, embeddings, hybrid retrieval, RRF, LangGraph
  interrupts, checkpoints, and lineage.
- `docs/local-models.md`: local/remote model options and memory expectations.
- `docs/decisions.md`: accepted and rejected choices, including no teams,
  single global base, web-only v1, and no A2A/MCP.
- `CONTRIBUTING.md`: environment setup, checks, migration rules, and code style.

Stale documentation, specs, and plans describing team tenancy or implemented
A2A/MCP surfaces are removed or replaced. Comments explain non-obvious reasons,
not syntax.

## Repository identity

- GitHub repository becomes `jlfernandezfernandez/knowli`.
- Local origin changes to the renamed URL.
- Clone commands, badges, package metadata, Compose project name, and
  documentation use `knowli`.
- Product spelling is `Knowli`; repository/package/slug spelling is `knowli`.

## Deletion and simplification targets

- Delete unreachable sidebar, knowledge-base picker, old ask dialog, and their
  unused hooks/API modules.
- Delete team, organisation, membership, workspace, and knowledge-base code.
- Delete MCP and A2A interfaces and optional dependencies.
- Delete the general LangChain package and speculative provider abstractions.
- Delete unused generated shadcn components after the new UI settles.
- Replace hand-written auth SQL in routers with application use cases and
  Postgres repositories.
- Replace the monolithic `App` component with route-level features.
- Replace custom theme/motion CSS with stock shadcn theme and Tailwind
  composition.

The expected result is fewer concepts and less code even after adding complete
tests, routes, and documentation.
