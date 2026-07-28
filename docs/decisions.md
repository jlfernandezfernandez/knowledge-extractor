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

**Chosen.** A cool-white paper, ink with a blue cast, verdigris (`#0d7a6b`) as
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
