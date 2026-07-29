# Knowledge contribution foundation

## Goal

Turn Knowli from a single-user capture review into the first usable team
product: people can sign in, request interviews from one another, contribute
voluntarily, and trace every approved knowledge change to its people and
evidence. It remains runnable locally with Docker Compose.

## Product model

An organisation contains teams. A team owns one configured knowledge target
(the current Postgres/pgvector knowledge base is the first target). Every team
member has the same capabilities: contribute voluntarily, request an interview
from any team member, complete an assigned interview, inspect its own team
history, and configure the target.

An interview is a contribution request with an assignee, title, optional brief,
and status. Its answer enters the existing four-stage review flow. A voluntary
contribution starts the exact same flow without an assignment. The review must
show whether it came from an interview or a voluntary contribution.

## First release navigation

The signed-in home screen has no sidebar. It contains:

- pending interviews assigned to the signed-in person;
- recent contribution and interview history for their current team;
- a primary voluntary-contribution action;
- user menu and settings in the top-right.

Starting an interview or contribution opens a focused full-screen review: no
home header, sidebar, command palette, or global navigation. The existing
review steps, text input, and live dictation are reused. The question-answering
surface is removed from the primary UI for this release; the RAG remains
available through its API and agent interfaces.

## Identity and tenancy

Use application-managed accounts for local open-source startup: email,
display name, an Argon2id password hash, and opaque expiring server-side
sessions in secure HTTP-only cookies. Registration creates an organisation,
its first team, and membership. There are deliberately no role distinctions in
this release.

All application queries resolve the authenticated membership before reading or
writing a team resource. The initial implementation uses application-level
scope checks, designed around organisation and team foreign keys; it does not
claim database row-level security yet. OAuth/OIDC/SAML is explicitly deferred
behind the authentication boundary rather than added as a local dependency.

## Knowledge target configuration

Each team owns exactly one `knowledge_target` configuration. The initial and
only supported driver is `postgres_pgvector`, referencing a knowledge-base
record scoped to the team. Settings exposes its display name and the target
selection/creation. Provider credentials are never stored in the browser or
in a vector metadata field.

The driver boundary is a small backend port, not a UI abstraction: later
drivers may map a team to a Qdrant collection, Pinecone namespace, or another
retrieval service without changing interview, review, or audit behaviour.

## Audit and provenance

Keep approved claims immutable. A claim records the contributing user, review
session, contribution type, and timestamp. Any later replacement preserves
the existing `superseded_by` lineage and adds the approving/contributing user
to the new claim. An append-only audit-event row records interview creation,
completion, review decisions, claim creation, and supersession. The history
view displays the actor, action, time, source, and predecessor claim; it never
rewrites an old event.

## Infrastructure

Postgres remains the sole relational database and pgvector store. The app API,
frontend, and database run via Docker Compose. No object store is introduced
in this first block because documents and images are not accepted yet. The
schema leaves room for evidence objects and claim-to-evidence links; the next
block adds MinIO (S3-compatible) and stores originals separately from extracted
text and embeddings.

## Error handling and safety

Unauthenticated requests return 401; a valid user outside the resource's team
gets 404, avoiding cross-team resource discovery. Login and registration show
actionable validation errors without identifying whether an existing account
uses a particular email. Passwords are never logged or returned. A user cannot
open or submit an interview assigned to another user.

## Verification

Backend tests cover registration/login/session handling, team isolation,
interview assignment/completion, review provenance, and audit lineage.
Frontend checks cover the signed-in home routes, focused review route, and the
absence of global chrome during a contribution. Docker Compose starts a fresh
local stack and seeds no shared production-like credentials.

## Deferred work

File and image upload, MinIO object storage, document extraction, image-aware
retrieval and answer rendering; external RAG drivers; organisation invitations;
OAuth/OIDC/SAML; permissions beyond equal team membership; scheduled/reminder
interviews; organisation-wide administration; database row-level security;
and RAG answer UI return in a deliberately designed surface.
