# Learning guide

This guide follows the main requests from browser to database. Start with
`frontend/src/app/router.tsx`: protected routes send anonymous visitors to the
login screen and signed-in visitors into `frontend/src/app/shell.tsx`.

## 1. Login

1. `frontend/src/features/auth/auth-screen.tsx` collects an email, password,
   and display name for registration, or credentials for login.
2. `frontend/src/features/auth/api.ts` calls the matching `/api/auth` route.
3. `backend/knowli/interfaces/http/auth.py` validates the request, calls
   `backend/knowli/application/auth.py`, and sets an HTTP-only cookie.
4. `AuthService` hashes a password, verifies it at login, and stores only a
   hash of the random session token through the session store.
5. `backend/knowli/infrastructure/postgres/repository.py` persists users and
   sessions in PostgreSQL. Later routes use `require_user()` in the HTTP module
   to turn that cookie back into a signed-in user.

FastAPI is the thin web boundary here. Its route functions declare input and
output types, dependency injection supplies the current user and service, and
the application service contains the rules that are worth testing without HTTP.

## 2. Contribution to commit

1. `frontend/src/features/home/home-page.tsx` creates a contribution through
   `frontend/src/features/contributions/api.ts`.
2. `backend/knowli/interfaces/http/review.py` sends the request to
   `ContributionService.capture()` in `backend/knowli/application/review.py`.
3. The service creates the durable contribution, then runs the LangGraph
   `extract_claims` node. The graph pauses after extraction so the author can
   review the drafts.
4. Confirming drafts resumes `find_conflicts`. The service embeds drafts,
   retrieves candidates, and asks the model to classify the relevant pairs.
5. Resolving overlap moves the graph through `prepare_commit`; `commit` runs
   `commit_claims`, which writes approved claims and replacement links through
   `backend/knowli/infrastructure/postgres/repository.py`.

LangGraph is a small state-machine library. In Knowli it is not an autonomous
agent: it records the four named review stages, pauses after the first two, and
stores checkpoints in PostgreSQL. That is why a review can resume after a
server restart.

## 3. An interview answer

1. `frontend/src/features/interviews/interviews-page.tsx` creates or starts an
   interview using `frontend/src/features/interviews/api.ts`.
2. `backend/knowli/interfaces/http/interviews.py` calls `InterviewService` in
   `backend/knowli/application/interviews.py`.
3. Only the assignee can start or answer; the service creates a linked,
   initially empty contribution for that answer.
4. The answer calls `ContributionService.capture_interview_answer()`, so it
   enters exactly the same LangGraph review and commit path as typed capture.

This is a useful boundary: interviews change who may supply the text, not the
quality bar for publishing it.

## 4. Ask and citations

1. `frontend/src/features/ask/ask-page.tsx` sends a question through
   `frontend/src/features/ask/api.ts`.
2. `backend/knowli/interfaces/http/ask.py` authenticates the request and calls
   `AskService.ask()` in `backend/knowli/application/ask.py`.
3. The service embeds the question and asks `PostgresStore.search_claims()` for
   committed, current evidence.
4. In `backend/knowli/infrastructure/postgres/repository.py`, PostgreSQL runs
   vector and full-text queries, then combines their rankings with reciprocal
   rank fusion (RRF). RRF gives useful weight to a claim that ranks highly in
   either list, helping with both paraphrases and exact tokens.
5. The model receives only those claims. Its selected IDs are intersected with
   the retrieved IDs before the API returns citations.

pgvector is the PostgreSQL extension that stores and compares embeddings. RRF
is the compact ranking formula used to join that semantic search with ordinary
full-text search.

## Frontend conventions

The frontend is a React/Vite application. Feature directories own their page,
API wrapper, and tests; `frontend/src/app/router.tsx` owns navigation; shared
visual primitives live in `frontend/src/components/ui/`.

The primitives are shadcn components: source files owned by this repository,
composed over accessible Base UI behavior rather than a large black-box design
system. `frontend/src/i18n/en.ts` is the canonical catalog and
`frontend/src/i18n/es.ts` is typed against it. `frontend/src/i18n/index.ts`
detects the browser language and keeps the document language attribute in sync.

## Tests and a good place to add a feature

Backend unit tests in `backend/tests/` exercise services and policies. The
integration tests in `backend/tests/integration/` prove the HTTP boundary and
PostgreSQL behavior. Frontend tests sit next to the page they describe, such as
`frontend/src/features/ask/ask-page.test.tsx`; browser coverage lives in
`frontend/e2e/knowli.spec.ts`.

For a new product action, start with the domain value or port if the action
needs a new rule or dependency. Add the use case in `application/`, implement
any storage or provider detail in `infrastructure/`, expose it in
`interfaces/http/`, then add a feature API wrapper and page in `frontend/src/`.
This order keeps UI details out of business rules and makes the smallest useful
test easy to identify.
