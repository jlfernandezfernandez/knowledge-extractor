# Decisions

What was chosen, what was rejected, and why. Short on purpose — the value is in
the rejected column.

---

### Ingest claims, not documents

**Chosen.** The retrieval unit is a short, self-contained, human-approved claim.

**Rejected:** document chunking with overlap; contextual retrieval; late
chunking. All three are repairs for context that chunking destroyed. We never
destroy it. *(They are the right answer for ingesting existing PDFs and wikis —
a plausible future mode, and a different code path.)*

**Cost:** someone has to sit through a review. That is the product, not a
regrettable side effect.

---

### LangGraph, not a LangChain chain

**Chosen.** The workflow stops twice for a human, durably.

**Rejected:** a chain plus a hand-rolled `sessions` table — which is what v0.1
of this project was. LangGraph's checkpointer replaced that table outright, so
this was a net *deletion*.

**Also rejected:** Temporal, Prefect. Correct for long-running workflows in
general, far heavier than this needs, and not LLM-shaped.

---

### Postgres + pgvector, not a dedicated vector database

**Chosen.** One database for vectors, lexical index, supersede history and
workflow checkpoints.

**Rejected:** Qdrant (faster at 1M+ vectors, better filtering), Chroma (nicer
for notebooks), Milvus (billion-scale). All would mean a *second* store for the
relational half — the history and the checkpoints. Team knowledge is thousands
of claims, not millions.

**Revisit when:** > ~1M claims, or filtered search gets slow.

---

### Hybrid retrieval with RRF, no reranker

**Chosen.** Dense + Postgres full-text, fused by rank. No score calibration, no
extra service.

**Rejected for now:** a cross-encoder reranker. It is the correct next upgrade
if precision disappoints; it costs a model and a hop, and at this corpus size
RRF is enough. See [`concepts.md`](concepts.md#3-hybrid-retrieval-and-reciprocal-rank-fusion).

---

### fastembed by default, not Ollama

**Chosen.** In-process ONNX. No PyTorch, no GPU, no second service. `git clone`
→ it runs.

**Rejected as the default:** requiring Ollama. It is the better *upgrade* and
one env var away, but making a demo depend on a background service is how demos
die.

---

### React + Vite SPA, not Next.js

**Chosen.** Vite + React 19 + TypeScript + Tailwind v4.

**Rejected:** Next.js. There is nothing to server-render — it is an authenticated
internal tool behind a Python API — so Next would add a second server, a second
deploy target and an RSC model for zero benefit. *(Next.js is the right default
when SEO, streaming SSR or edge rendering matter. They do not here.)*

**Also rejected:** TanStack Start (genuinely good, benchmarks well, but a
sharper tool than a four-step wizard needs); a state library; a router. Four
sequential steps driven by `state.stage` need neither.

**Also rejected mid-build:** TanStack Query, which was installed and then
uninstalled. Four sequential one-shot mutations and no cache to invalidate — it
was ceremony.

---

### Human gates apply to agents too

**Chosen.** `submit_knowledge` over MCP or A2A returns a review URL. It does not
write.

**Rejected:** an "agent write" path with an audit log. Auditable garbage is
still garbage, and the moment agents can write unattended, the knowledge base
becomes the thing this project exists to prevent.

---

### `'simple'` text search config

**Chosen.** No stemming, so it never mangles a language it was not configured
for. Mixed-language teams are the target.

**Rejected:** `'spanish'` / `'english'`. Better recall — for exactly one
language. Switch if your team is monolingual; it is a one-line change plus a
reindex.

---

### Design: verdigris on cool paper

**Chosen.** A cool-white paper, ink with a blue cast, verdigris (`#0b7364`) as
the single identity colour — the patina of something that has been accumulating
— and clay reserved *only* for conflict state, so seeing it always means a human
must decide. Bricolage Grotesque for display, Public Sans for text, JetBrains
Mono for claims, because claims are data.

**Rejected:** cream `#F4F1EA` + high-contrast serif + terracotta — which is what
v0.1 of this project actually looked like, and is also the single most common
AI-generated design of 2026. Also rejected: near-black + acid green, and the
hairline-rule broadsheet. All three are defaults rather than decisions.

**The signature:** the conflict **ledger** — stored and incoming side by side,
the losing side receding rather than disappearing, merge opening a third lane
below. Git's data model, deliberately *not* git's conflict markers: `<<<<<<<`
is hostile to the non-engineers this tool is aimed at.

---

### i18n with react-i18next, Spanish and English

**Chosen.** `react-i18next` + `i18next-browser-languagedetector`. Language is
detected from the browser, the explicit choice is remembered in
`localStorage`, and `document.documentElement.lang` is kept in sync so screen
readers and `:lang()` styling are correct.

Plurals go through i18next's `_one` / `_other` suffixes rather than
`n === 1 ? … : …` in the components — Spanish and English happen to agree on
plural rules, and hand-rolled ternaries are exactly what breaks when the third
language does not.

The Spanish catalogue is typed as `typeof en`, so a missing or misspelled key
is a **compile error**, not a string that silently falls back at runtime.

**Rejected:** a 40-line `Intl`-based hook, which is what the size of this app
argues for. Overruled deliberately: `react-i18next` is what these codebases
actually use, and the point of this project includes being able to work in one.

**Not translated:** claims themselves. The model is told to write in the
language the person spoke, and the knowledge base stores whatever they said.
Retrieval is cross-language anyway — the embeddings match "holiday policy"
against a Spanish claim (see [`concepts.md`](concepts.md#2-embeddings)).

---

### Real progress over Server-Sent Events, not a spinner

**Chosen.** `POST /api/sessions` and `/confirm` serve JSON by default and SSE
when the caller sends `Accept: text/event-stream`. The events are LangGraph's
own node updates, forwarded — so "Found 4 claims · comparing against 128 stored
claims" is counting real things.

`EventSource` only speaks GET, so the browser reads the stream off `fetch` and
splits on the blank-line frame delimiter, carrying the tail between chunks.

**Rejected:** a spinner. The conflict step makes one LLM call per claim with
neighbours; on a local 4B model that is genuinely slow, and hiding it behind a
spinning circle is the difference between "working" and "broken" to a user.
**Also rejected:** token-level streaming — the nodes use structured output, so
there is no prose to stream, and faking one would be theatre.

Agent callers over MCP and A2A never ask for the stream, so they are unaffected.

---

### Motion: CSS only, no animation library

**Chosen.** CSS transitions, `@keyframes` for one-shot entrances, and a small
set of tokens. Custom easing curves, because the built-in ones are too weak to
read as intentional:

```
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);   /* entering, exiting */
--press: 160ms;  --state: 200ms;  --step: 260ms;
```

`ease-in` is absent on purpose: it delays the first moment of movement, which is
exactly when the user is looking, so it feels slower than `ease-out` at the same
duration.

Duration follows **frequency**, not importance:

| Element | Frequency | Motion |
|---|---|---|
| Button press | constant | `scale(0.97)`, 160ms |
| Losing side of a conflict receding | occasional | opacity, 200ms |
| Step change, claim stagger | once per capture | 260ms, 45ms stagger |
| **Command palette** | dozens per day | **none** |

**Rejected:** Motion/Framer Motion. Its shorthand props (`x`, `y`, `scale`) run
on `requestAnimationFrame` on the main thread and drop frames exactly when the
app is busy — which here is while an LLM response is being parsed. CSS
animations run off the main thread. Springs would earn their place for
interruptible gestures; there are none in this UI.

**Rejected:** animating the ⌘K palette. It is keyboard-initiated and opened
constantly; an entrance animation there stops reading as polish and starts
reading as lag. Raycast opens instantly for the same reason. The backdrop
fades, because that is a colour change rather than movement.

**Kept:** `sonner` for toasts — good defaults, and its own animation is
interruptible when toasts stack.

Nothing animates from `scale(0)`; entrances start at 6px of travel and
`scale(0.995)`, because nothing in the real world appears from nothing. Reduced
motion keeps the opacity fades that carry meaning and drops the movement.
