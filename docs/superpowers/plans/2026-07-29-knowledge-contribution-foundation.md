# Knowledge Contribution Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local accounts, equal team membership, interview assignments, provenance, and a sidebar-free home while retaining the existing review engine.

**Architecture:** Postgres owns identity, tenant, interview, target, and audit records alongside pgvector. HTTP derives the current user from a secure session and supplies the team-owned knowledge base to the existing review service. React renders authenticated home or an isolated review route.

**Tech Stack:** FastAPI, psycopg/Postgres 17 + pgvector, Argon2id via `pwdlib`, React 19, TypeScript, Vite.

## Global Constraints

- All team members have equal capabilities in this release.
- One team has one `postgres_pgvector` target; no remote vector driver yet.
- Review input supports existing text and live dictation only.
- No sidebar or global header inside a review.
- Preserve claims and supersession history; never delete an audit record.

---

### Task 1: Establish authenticated team scope

**Files:**
- Modify: `backend/pyproject.toml`, `backend/knowli/config.py`, `backend/knowli/infrastructure/postgres/schema.sql`, `backend/knowli/interfaces/http/__init__.py`
- Create: `backend/knowli/application/auth.py`, `backend/knowli/interfaces/http/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] Add `users`, `organisation`, `team`, `team_membership`, and opaque `login_session` tables, then create the request dependency that returns an authenticated membership.

```python
def current_member(request: Request) -> Membership:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise NotAuthenticated()
    return sessions.member_for(token)
```

- [ ] Register an account by creating organisation, team, membership, target knowledge base and session atomically; login always verifies a password hash and creates a fresh opaque token.

- [ ] Test that unauthenticated calls return 401, sessions identify their member, and a second user cannot read a different team's data.

### Task 2: Add interviews, target configuration, and claim provenance

**Files:**
- Modify: `backend/knowli/application/review.py`, `backend/knowli/infrastructure/postgres/repository.py`, `backend/knowli/interfaces/http/review.py`, `backend/knowli/interfaces/http/schemas.py`
- Create: `backend/knowli/application/interviews.py`, `backend/knowli/interfaces/http/interviews.py`
- Test: `backend/tests/test_interviews.py`, `backend/tests/test_provenance.py`

- [ ] Add team-scoped interview and append-only audit tables; introduce a `ContributionContext` that fixes the author, team target and optional interview before a review starts.

```python
@dataclass(frozen=True)
class ContributionContext:
    member_id: str
    knowledge_base: str
    interview_id: str | None = None
```

- [ ] Make `POST /api/interviews` create an assigned pending interview and `POST /api/interviews/{id}/start` start only for its assignee. Existing voluntary creation starts a context with no interview.

- [ ] Store `author_id`, `review_session_id`, and contribution kind with every new claim. Append audit records for interview creation/start and commit/supersession.

- [ ] Test assignment isolation, status transitions, claim provenance, and audit events.

### Task 3: Replace the shell with home and focused review

**Files:**
- Modify: `frontend/src/app.tsx`, `frontend/src/hooks/use-review.ts`, `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/review.ts`, `frontend/src/types/review.ts`, `frontend/src/i18n/en.ts`, `frontend/src/i18n/es.ts`
- Create: `frontend/src/hooks/use-auth.ts`, `frontend/src/components/auth/auth-screen.tsx`, `frontend/src/components/home/home.tsx`, `frontend/src/components/home/interview-list.tsx`, `frontend/src/components/home/history-list.tsx`, `frontend/src/components/settings/settings-dialog.tsx`, `frontend/src/lib/api/auth.ts`, `frontend/src/lib/api/interviews.ts`, `frontend/src/types/auth.ts`, `frontend/src/types/interview.ts`

- [ ] Make the root route resolve the current session and render login/registration, home, or `/review/:id`; fetch requests must include cookies.

```ts
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { credentials: "include", ...init });
  if (!response.ok) throw await failure(response);
  return response.json();
}
```

- [ ] Render pending assigned interviews, recent team history, a voluntary contribution entry point, and compact user/settings controls. Remove the sidebar and ask palette from this release.

- [ ] Keep `ReviewFlow` as the only content under `/review/:id` and voluntary new-review route; return to home after completion.

### Task 4: Verify the local product and ship one implementation commit

**Files:**
- Modify: `README.md`, `docker-compose.yml`

- [ ] Update the local quick start for registration and the new home flow; preserve one-command Compose infrastructure.
- [ ] Run backend tests, frontend lint/build, and manually verify registration, assignment, review isolation, and a fresh Compose startup.
- [ ] Commit only this implementation after the checks pass.
