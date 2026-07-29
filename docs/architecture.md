# Architecture

```
      React 19 + Vite            MCP client            another team's agent
      (the review UI)         (Claude, Cursor…)          (autonomous)
             │                        │                        │
             │ REST/JSON              │ stdio                  │ A2A JSON-RPC
             ▼                        ▼                        ▼
      ┌──────────────────────────────────────────────────────────────┐
      │                    FastAPI  ·  ke/api.py                     │
      └───────────────┬──────────────────────────┬───────────────────┘
                      │                          │
         ┌────────────▼─────────────┐   ┌────────▼──────────┐
         │  LangGraph  ke/graph.py  │   │  Ask   ke/ask.py  │
         │  the review workflow     │   │  hybrid + cite    │
         └────────────┬─────────────┘   └────────┬──────────┘
                      │                          │
              ┌───────▼──────────────────────────▼───────┐
              │        Postgres 17 + pgvector            │
              │  knowledge · tsvector · checkpoints      │
              └──────────────────────────────────────────┘
                      ▲                          ▲
             fastembed (ONNX, CPU)      any OpenAI-compatible LLM

      Dictation runs alongside: browser AudioWorklet ──WS──► ke/speech.py
      (Parakeet TDT via sherpa-onnx, segments closed by a voice-activity detector)
```

One database holds all three kinds of state: the vectors, the lexical index,
and LangGraph's workflow checkpoints. That is why a paused review survives a
restart, and why `docker compose up` is the entire infrastructure.

---

## Modules

| File | Responsibility |
|---|---|
| `ke/schemas.py` | Every contract in one place: what the LLM must return, what the API exchanges. Pydantic. |
| `ke/config.py` | Environment, read once. |
| `ke/llm.py` | `init_chat_model` + `with_structured_output`. The only file that knows a provider exists. |
| `ke/embed.py` | fastembed in-process, or a remote `/embeddings` endpoint. |
| `ke/store.py` | Schema, hybrid search, neighbours, insert/supersede, history. All SQL lives here. |
| `ke/graph.py` | The workflow: nodes, edges, the two `interrupt()` gates, and the pure `plan()` function. |
| `ke/ask.py` | Question answering with citations. |
| `ke/speech.py` | Parakeet or Whisper behind one interface; VAD segmentation for live text. |
| `ke/api.py` | HTTP. Thin — it translates requests into graph invocations. |
| `ke/mcp_server.py` | MCP tools over stdio. |
| `ke/a2a_server.py` | A2A Agent Card + skills. |

The rule the layout enforces: **`api.py` contains no business logic and
`graph.py` contains no SQL.** If you find yourself writing a query in a node,
it belongs in `store.py`.

---

## A capture, request by request

### `POST /api/sessions`

1. Mint a `session_id` — it is LangGraph's `thread_id`.
2. `graph.invoke({raw_text, author, source}, config)`.
3. The `extract` node runs one LLM call and produces claims + summary +
   open questions.
4. The `confirm` node calls `interrupt(...)`. State is written to Postgres, the
   run stops, the payload comes back.
5. Response: `stage: "confirm"` plus everything the human needs to review.

### `POST /api/sessions/{id}/confirm`

Resumes the paused `confirm` node, **keyed by interrupt id** (see below).

- With `claims` → route to `detect`. That node embeds each claim, pulls its
  nearest live neighbours, and asks the model to classify each pair. Then
  `resolve` interrupts. Response: `stage: "resolve"`.
- With `clarification` → route **back** to `extract`, with the answer appended
  to the source text. Response: `stage: "confirm"` again, re-extracted.

### `POST /api/sessions/{id}/resolve`

Resumes `resolve`. `commit` turns the human's decisions into writes via the pure
`plan()` function, embeds the surviving claims, inserts them, and sets
`superseded_by` on whatever lost. Response: `stage: "done"`.

### `WS /api/transcribe/live`

The browser streams 16 kHz PCM16 from an `AudioWorklet`. A voice-activity
detector closes each phrase, that segment alone is decoded, and the text is
pushed back. Decoding blocks, so it runs in a worker thread — otherwise a long
segment would stall the event loop and stop the socket draining.

### `POST /api/ask`

No graph involved. Embed the question → hybrid search → one LLM call with the
retrieved claims and instructions to cite ids → return the answer with its
sources, cited ones first.

---

## Two implementation details you would otherwise rediscover painfully

**1. The checkpointer needs its own autocommit pool.**
LangGraph's migrations use `CREATE INDEX CONCURRENTLY`, which Postgres refuses
inside a transaction block. `store.checkpoint_pool()` exists solely for this.

**2. Resume must be keyed by interrupt id.**
`Command(resume=value)` hands the *same* value to every interrupt reached during
that run. Since `confirm` and `resolve` are hit in the same invocation, the
confirm payload would be swallowed by the resolve gate instead of pausing there.
`Command(resume={interrupt.id: value})` resumes exactly one. This is what
`api._resume()` does.

---

## Data model

```sql
knowledge(
  id, title, statement, tags[], author, source,
  embedding vector(N),          -- HNSW, cosine
  search    tsvector GENERATED, -- GIN, 'simple' config
  superseded_by uuid REFERENCES knowledge(id),
  created_at
)
```

- **Live** = `superseded_by IS NULL`. Every retrieval path filters on it.
- **History** = a recursive CTE walking `superseded_by` backwards.
- `search` is a **generated column**, so the lexical index can never drift out
  of sync with the text.
- The text search config is `'simple'` on purpose: it does not stem, so it never
  mangles a language it was not configured for. A single-language deployment
  should switch to `'spanish'` or `'english'` and gain stemming.

LangGraph owns its own tables (`checkpoints`, `checkpoint_writes`, …) in the
same database. We never touch them directly.

---

## Frontend

`frontend/src/` — no router, no state library:

| File | Role |
|---|---|
| `types.ts` | Mirrors `schemas.py`. |
| `api.ts` | One typed `fetch` wrapper, plus the SSE progress reader. |
| `useDictation.ts` | Mic → `AudioWorklet` → WebSocket; segments come back as text. |
| `ui.tsx` | Button, stepper, progress, error. |
| `steps.tsx` | The four slides, including the conflict cards. |
| `AskCommand.tsx` | The ⌘K question palette. |
| `App.tsx` | Renders the slide matching `state.stage`. |
| `i18n.ts`, `locales/` | English and Spanish, detected from the browser. |

**The frontend has no workflow logic.** It renders whatever `stage` the backend
reports and posts back. The state machine lives in exactly one place — the
graph — which is what makes the deep link `/review/<id>` work: an agent opens a
review over MCP, a human finishes it in the browser, and neither side had to
agree on anything but the session id.
