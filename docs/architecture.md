# Architecture

```
      React 19 + Vite            MCP client            another team's agent
   (sidebar + the review)     (Claude, Cursor…)          (autonomous)
             │                        │                        │
             │ REST/JSON              │ stdio                  │ A2A JSON-RPC
             ▼                        ▼                        ▼
      ┌──────────────────────────────────────────────────────────────┐
      │           FastAPI  ·  knowli/interfaces/http/                │
      └───────────────┬──────────────────────────┬───────────────────┘
                      │                          │
 ┌────────────────────▼──────────────┐  ┌────────▼───────────────────┐
 │ LangGraph  application/review.py  │  │  Ask  application/ask.py   │
 │ the review workflow               │  │  hybrid + cite             │
 └────────────────────┬──────────────┘  └────────┬───────────────────┘
                      │                          │
              ┌───────▼──────────────────────────▼───────┐
              │        Postgres 17 + pgvector            │
              │  knowledge · tsvector · checkpoints      │
              │  workspace · knowledge_base · sessions   │
              └──────────────────────────────────────────┘
                      ▲                          ▲
             fastembed (ONNX, CPU)      any OpenAI-compatible LLM

      Dictation runs alongside:
      browser AudioWorklet ──WS──► infrastructure/speech/
      (Parakeet TDT via sherpa-onnx, segments closed by a voice-activity detector)
```

One database holds all three kinds of state: the vectors, the lexical index,
and LangGraph's workflow checkpoints. That is why a paused review survives a
restart, and why `docker compose up` is the entire infrastructure.

---

## Layers

`backend/knowli/` is four layers, and the dependencies only ever point inwards:
`interfaces` → `application` → `domain`, with `infrastructure` plugged in at the
edge through the ports `domain/ports.py` declares.

| Layer | What lives there |
|---|---|
| `domain/` | The vocabulary and the rules. `claim.py` and `conflict.py` are the types everything else speaks in; `knowledge_base.py` is the container claims live in, plus the `slugify` that decides when two names are one knowledge base; `policy.py` holds the pure `plan()` and which resolution each verdict allows; `ports.py` declares what the outside world must provide. No I/O, no framework, no SQL. |
| `application/` | `review.py` — the workflow: nodes, edges, the two `interrupt()` gates, and how the graph is assembled. `ask.py` — question answering with citations. `knowledge_bases.py` — which knowledge bases exist, which one a request means, and the recent-review listing. |
| `infrastructure/` | The implementations. `postgres/` (`pool.py`, `repository.py`, `schema.sql`) — all SQL lives here. `llm/` — the only place that knows a provider exists: `chat_model.py` reaches the model, `prompts.py` holds what we ask it, `schemas.py` the shapes it must answer in, and `extractor.py` puts the three together behind the port. `embedding/embedder.py` — fastembed in-process or a remote `/embeddings` endpoint. `speech/` — Parakeet or Whisper behind one `transcriber.py`. |
| `interfaces/` | The ways in. `http/` split by router — `review.py`, `knowledge.py`, `speech.py`, `health.py`, plus `sse.py` and the API DTOs in `schemas.py`. `a2a/server.py` — Agent Card and skills. `mcp/server.py` — tools over stdio. |

`config.py` sits above all four: environment, read once. `wiring.py` sits
beside it as the composition root — the one file where each port meets its
implementation. It is deliberately dumb: four lazy module-level singletons, three re-exports
and one function that actually builds something. No container, no framework. Without it the choice is between
an application layer that imports Postgres directly, which would make the ports
decorative, and scattering that import across every caller.

The rule the layout enforces is the one the flat version had, restated:
**`interfaces/` contains no business logic and `application/` contains no SQL.**
If you find yourself writing a query in a node, it belongs in
`infrastructure/postgres/repository.py`; if a router starts deciding anything,
it belongs in `application/` or `domain/`.

---

## A capture, request by request

Every route that touches claims resolves a knowledge base first, from an
optional `knowledge_base` slug, falling back to `DEFAULT_KNOWLEDGE_BASE`. A slug
nobody has is a **404 on every route**, never a silent fallback to the default —
and the error names the ones that do exist, because the caller may well be an
agent that has to pick again. Falling back quietly would file a claim about
kitchen returns into sofa deliveries and then compare it against them, which is
the exact failure the container exists to prevent.

### `POST /api/sessions`

1. Resolve the knowledge base and mint a `session_id` — it is LangGraph's
   `thread_id`.
2. `graph.invoke({raw_text, author, source, knowledge_base}, config)`.
3. The `extract` node runs one LLM call and produces claims + summary +
   open questions.
4. The `confirm` node calls `interrupt(...)`. State is written to Postgres, the
   run stops, the payload comes back.
5. Response: `stage: "confirm"` plus everything the human needs to review.

### `POST /api/sessions/{id}/confirm`

Resumes the paused `confirm` node, **keyed by interrupt id** (see below).

- With `claims` → route to `detect`. That node embeds each claim, pulls its
  nearest live neighbours **inside the session's knowledge base**, and asks the
  model to classify each pair. Then `resolve` interrupts. Response:
  `stage: "resolve"`.
- With `clarification` → route **back** to `extract`, with the answer appended
  to the source text. Response: `stage: "confirm"` again, re-extracted.

The knowledge base here is the *session's*, read back out of the graph state —
it was fixed when the capture started and a confirm has no business moving it.
`SessionState` carries it as a slug, so the frontend and any agent holding a
session know which one they are in.

### `POST /api/sessions/{id}/resolve`

Resumes `resolve`. `commit` turns the human's decisions into writes via the pure
`plan()` function, embeds the surviving claims, inserts them, and sets
`superseded_by` on whatever lost. Response: `stage: "done"`.

### `POST /api/sessions/{id}/back`

The way out of a gate that is not forwards. It walks the thread's checkpoint
history back to the one before the current gate and replays from there, so the
resolve gate lands on the confirm gate again with the claims as they were, and
nothing is re-extracted. The checkpointer does the work; no second copy of the
state is kept anywhere in the API. `SessionState` carries `raw_text` for exactly
this reason — stepping back off the confirm gate has to be able to put what the
person originally said back on the capture screen.

### `WS /api/transcribe/live`

The browser streams 16 kHz PCM16 from an `AudioWorklet`. A voice-activity
detector closes each phrase, that segment alone is decoded, and the text is
pushed back. Decoding blocks, so it runs in a worker thread — otherwise a long
segment would stall the event loop and stop the socket draining.

### `POST /api/ask`

No graph involved. Embed the question → hybrid search in one knowledge base →
one LLM call with the retrieved claims and instructions to cite ids → return the
answer with its sources, cited ones first.

### The rest of the surface

```
GET  /api/knowledge-bases          → {"items":[{"id","slug","name","claims"}]}
POST /api/knowledge-bases {"name"} → the created base; slug derived from the name
                                     409 if that slug already exists
GET  /api/sessions?knowledge_base=<slug>&limit=20   newest first
POST /api/sessions   body gains optional "knowledge_base"
POST /api/ask        body gains optional "knowledge_base"
GET  /api/knowledge/{id}/history
```

Note what is **not** there: a route that lists a knowledge base. There was one,
and nothing called it. The rail stopped listing the store when the store stopped
being small enough to list, and agents search over MCP and A2A rather than over
HTTP. Retrieval is `/api/ask`, search is a skill, and a paginated dump of an
organisation's knowledge is a feature to add when somebody asks for it — along
with the date index it would want, which went with it.

The slug is **derived from the name, never supplied**, so what a person types
and what a URL carries cannot disagree. Derivation folds accents and collapses
spellings: "Kitchen Returns", "kitchen returns" and "Kitchen  Returns!" are one
knowledge base with three spellings of its name. A second attempt at a taken
slug is a 409, not a `kitchen-returns-2` — somebody who thinks they are opening
yesterday's knowledge base should not be handed an empty new one with a number
on the end.

`GET /api/knowledge/{id}/history` takes no knowledge base, and not by oversight:
a claim id already names its scope, so the only thing a slug could do there is
disagree with the id it was handed.

---

## Two implementation details you would otherwise rediscover painfully

**1. The checkpointer needs its own autocommit pool.**
LangGraph's migrations use `CREATE INDEX CONCURRENTLY`, which Postgres refuses
inside a transaction block. `checkpoint_pool()` in
`infrastructure/postgres/pool.py` exists solely for this.

**2. Resume must be keyed by interrupt id.**
`Command(resume=value)` hands the *same* value to every interrupt reached during
that run. Since `confirm` and `resolve` are hit in the same invocation, the
confirm payload would be swallowed by the resolve gate instead of pausing there.
`Command(resume={interrupt.id: value})` resumes exactly one. This is what the
resume helper in `application/review.py` does — the routers never build a
`Command` themselves.

---

## Data model

```sql
workspace(id, slug UNIQUE, name, created_at)

knowledge_base(
  id, workspace_id REFERENCES workspace(id), slug, name, created_at,
  UNIQUE (workspace_id, slug)   -- per workspace, not globally
)

knowledge(
  id, title, statement, tags[], author, source,
  knowledge_base_id uuid NOT NULL REFERENCES knowledge_base(id),
  embedding vector(N),          -- HNSW, cosine
  search    tsvector GENERATED, -- GIN, 'simple' config
  superseded_by uuid REFERENCES knowledge(id),
  created_at
)

review_session(
  id,                           -- the LangGraph thread id
  knowledge_base_id REFERENCES knowledge_base(id),
  author, stage, summary, created_at, updated_at
)
```

- **Live** = `superseded_by IS NULL`. Every retrieval path filters on it.
- **History** = a recursive CTE walking `superseded_by` backwards.
- `search` is a **generated column**, so the lexical index can never drift out
  of sync with the text.
- The text search config is `'simple'` on purpose: it does not stem, so it never
  mangles a language it was not configured for. A single-language deployment
  should switch to `'spanish'` or `'english'` and gain stemming.
- The uniqueness of a knowledge-base slug is per workspace: two companies may
  both want a `support` knowledge base and neither should be told the name is
  taken.

`DEFAULT_WORKSPACE` and `DEFAULT_KNOWLEDGE_BASE` are inserted on every startup
with `ON CONFLICT DO NOTHING`, which is the whole idempotency story — the schema
file runs each time the API boots and has to be a no-op after the first one.

There is no user table and no owner column, deliberately. `workspace` and
`knowledge_base` exist now so that adding people later is a new table plus a
join, instead of a migration that has to touch every claim ever written.

**`review_session` is an index over the checkpointer, not a second source of
truth.** The session state — the claims, the conflicts, which gate it is parked
on — still lives in LangGraph's checkpoint tables and is still read from there.
This row carries only what a *list* needs, because rendering the last twenty
captures out of the checkpointer would mean deserialising twenty whole graph
states to read a stage and one sentence off each. It is what lets the UI show
reviews parked on a human gate at all: before it, a review someone walked away
from was durable but invisible.

LangGraph owns its own tables (`checkpoints`, `checkpoint_writes`, …) in the
same database. We never touch them directly.

### Migrating in place

An install that has been collecting claims for months has to keep them. The
scope column arrives nullable with its foreign key already attached — `ADD
COLUMN IF NOT EXISTS` covers the constraint too, which a separate `ADD
CONSTRAINT` has no way to do — then one `UPDATE` backfills every existing row
into the default knowledge base, and only then does `SET NOT NULL` run. On a
fresh database the backfill matches nothing and the same three statements hold.

### The indexes, which did not all get the same answer

This is the part worth understanding, because two of the three indexes could be
scoped and one could not.

**The vector index stays global and alone.** pgvector indexes exactly one vector
column and nothing beside it: there is no composite HNSW to build, no
`(knowledge_base_id, embedding)`. So a scoped vector search is a *filter over an
approximate scan* — the scan visits its `ef_search` candidates in total and
hands back only those that happen to be in this knowledge base. Ask for five
neighbours, get two. That is the worst possible way to be wrong here, because
missing neighbours look exactly like *no conflicts*: the detector reports a
clean claim and a contradiction goes in silently.

The fix is pgvector 0.8's iterative scan, which keeps pulling from the index
until enough rows survive the filter. The repository issues

```sql
SET LOCAL hnsw.iterative_scan = strict_order
```

before **both** vector queries. `strict_order` rather than `relaxed_order`
because both callers care about order: RRF ranks by it, and `neighbours` cuts by
distance.

Partitioning `knowledge` by knowledge base would give a genuinely scoped vector
index, and it is the thing to reach for once one base is big enough to swamp the
others. Not built — it is machinery a few thousand claims do not justify.

**The lexical index can be scoped, so it is**, with the knowledge base leading,
because the query filters on it by equality and only then ranks — which is the
order a composite index wants:

```sql
gin (knowledge_base_id, search)                          -- needs btree_gin
```

`btree_gin` is what lets a GIN index mix a plain column with a tsvector. It is a
contrib extension bundled with Postgres, so `CREATE EXTENSION` is the entire
cost — not a new dependency. The old global index is **dropped** rather than
left alongside: it would be a second copy of the same rows for the planner to
weigh and for every write to maintain. Dropping it by its old name is what
migrates an existing install; on a fresh one it does nothing.

There is deliberately **no index ordering a knowledge base by date**. There was
one, for the "browse everything" read that no surface asked for once the sidebar
stopped listing the store; it went out with the route. `count` uses the equality
half and is happy with a scan at this size. Add it back with the query that
needs it, rather than carrying it on every write until then.

---

## Two store ports, not one

`domain/ports.py` declares two protocols where there used to be one, and the
split is the interesting part. Both are implemented in the same file —
`infrastructure/postgres/repository.py` — so the split buys nothing today except
being able to say what would move and what would not.

**`KnowledgeRepository` is the claims.** `hybrid_search`, `neighbours`, `count`
and `insert` all take a `KnowledgeBase`, and they take it **first**.
That is not decoration. Every vector store has this argument — Qdrant and Chroma
call it a collection, Pinecone a namespace — and each takes it as the first
argument of every call, because for them it is the *handle* rather than a
filter. Shaping the port that way keeps the pgvector implementation honest about
the fact that it is a `WHERE` clause here and would be a handle elsewhere. It is
a `KnowledgeBase` and not a bare id for the same reason: pgvector needs `id`, a
Qdrant adapter would need `slug` as a collection name, and the port has no
business picking a winner.

Two methods deliberately do not take it. `history` and `supersede` work on claim
ids, which are uuids and globally unique, so the scope could only be redundant
or wrong — and the supersede chain is inside one knowledge base by construction,
because a claim can only supersede one it was compared against and comparison is
already scoped. Note what this is *not*: with no users and no auth, it is not an
authorisation boundary and never was one.

**`Catalog` is the knowledge bases and the session listing.** A second port
rather than five more methods on the first, because the two halves are not
swapped together. Move the claims to Qdrant and the catalog stays in Postgres: a
vector store has no opinion about which collections a product offers, and it
certainly has no table of half-finished human reviews. Keeping them apart is
what makes "ship pgvector, shape the port so Qdrant could be added" a true
statement rather than a hopeful one.

`Catalog` takes no workspace argument anywhere. The table exists so that a
second workspace later is a `WHERE` clause instead of a migration, but there is
no way to select one yet, and threading a constant through five signatures is
flexibility nobody can exercise. The implementation resolves
`config.DEFAULT_WORKSPACE`; that is the one line to change.

### What a Qdrant adapter would actually have to write

Only `KnowledgeRepository`: a per-collection upsert with the payload (`title`,
`statement`, `tags`, `author`, `source`, `superseded_by`, `created_at`), a
cosine search filtered on `superseded_by IS NULL`, a payload update for
`supersede`, a count, and something for the lexical half of hybrid search — Qdrant sparse vectors, or fusion against
a text index left in Postgres. `history` and the whole of `Catalog` stay where
they are.

**No second adapter was built.** Only pgvector ships, and the port has exactly
one implementation. The paragraph above is an estimate of the work, not a
tested claim of pluggability.

---

## Frontend

`frontend/src/` — React 19, Tailwind v4, shadcn/ui on Base UI. No router, no
state library. Two panes, ChatGPT-style:

| Pane | Role |
|---|---|
| Sidebar | Which knowledge base you are in, and what you have captured lately. |
| Main column | The review: the four slides, including the conflict cards, with a way forward and a way back at every gate. |

The sidebar used to list every stored claim. It no longer does — that is
meaningless at the scale this now targets. It is a **knowledge-base picker**,
each base with its live claim count and a dialog to create one, plus **your own
recent captures**, where a review parked on a human gate is marked as waiting
for you and can be reopened with a click.

⌘K names the knowledge base it is querying, because the palette covers the rail
and the same question has different answers in different knowledge bases.

Underneath both: one typed `fetch` wrapper plus the SSE progress reader, the
dictation hook (mic → `AudioWorklet` → WebSocket, segments come back as text),
TypeScript types mirroring the API's Pydantic schemas, the ⌘K question palette,
and English and Spanish catalogues detected from the browser.

**The frontend has no workflow logic.** It renders whatever `stage` the backend
reports and posts back. The state machine lives in exactly one place — the
graph — which is what makes the deep link `/review/<id>` work: an agent opens a
review over MCP, a human finishes it in the browser, and neither side had to
agree on anything but the session id.
