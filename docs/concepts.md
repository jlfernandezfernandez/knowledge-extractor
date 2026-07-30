# The concepts, explained so you can explain them

Every idea this project uses, why it is there, and the sentence to say when
someone asks you about it in an interview or a design review.

---

## 1. RAG, and what actually goes wrong with it

**Retrieval-Augmented Generation**: instead of hoping the model memorised your
company's facts, you retrieve relevant text at query time and put it in the
prompt. The model reasons; your database remembers.

The naive pipeline is: chop documents into chunks → embed each chunk → store
vectors → at query time embed the question, find the nearest chunks, paste them
in. It works in a demo and disappoints in production, for reasons that are
almost never about the model:

| Failure | What it looks like |
|---|---|
| **Chunk boundary loss** | A chunk says "this must be approved by the lead" — but *what* must be? The subject was two paragraphs up, in a different chunk. |
| **Contradiction** | The wiki says Tuesdays, the newer doc says Fridays. Both get retrieved. The model picks one, confidently. |
| **Lexical blindness** | Someone searches `ERR_4021` or `v2.3.1`. Embeddings encode *meaning*, and an error code has almost none — so it does not rank. |
| **Staleness with no signal** | Nothing records that the Tuesday fact was superseded, so it retrieves forever. |

**The move this project makes:** stop ingesting documents, ingest *claims*. A
claim is short, self-contained, and human-approved. That single decision
dissolves the first two failures — a claim cannot lose its context because it
was written not to have any, and contradictions are caught at write time by the
person who knows the answer.

> **Say it like this:** "Most RAG problems are ingestion problems wearing a
> retrieval costume. We moved the hard part — deciding what is true and what it
> means — to write time, where a human is available."

**The 2026 alternatives we did not need:** *contextual retrieval* (an LLM
rewrites each chunk to re-add its context before embedding — Anthropic reported
up to ~67% fewer retrieval failures) and *late chunking* (embed the whole
document first, then slice, so every span carries document-level attention).
Both exist to repair context that chunking destroyed. We never destroy it, so
we skip both. Worth knowing by name — they are the correct answer when you *are*
ingesting documents.

---

## 2. Embeddings

A model that turns text into a vector, positioned so that similar meanings land
near each other. "Cuándo desplegamos" and "when do we ship to production" end up
close even though they share no words and no language.

Two knobs that matter:

- **Dimensions** (384 / 768 / 1024). More is not free: it costs storage, index
  memory and query time. 384 is plenty for short claims.
- **Distance**. We use **cosine distance** (`<=>` in pgvector): `0` identical,
  `1` unrelated, `2` opposite. Measured on this project's default model with real
  Spanish claims:

  | Pair | Distance |
  |---|---|
  | "Desplegamos los martes" vs "…los viernes" | 0.37 |
  | "Desplegamos los martes" vs "El despliegue se hace los martes por la tarde" | 0.17 |
  | "We deploy on Tuesdays" vs "Desplegamos los martes" | 0.16 |
  | "Desplegamos los martes" vs "El buen café está en la planta 3" | 0.85 |

  That gap is why `CONFLICT_MAX_DISTANCE=0.55` works: real collisions cluster
  well below it, unrelated claims well above. **Re-measure it if you change the
  embedding model** — the numbers are a property of the model, not of the idea.

> **Say it like this:** "Cosine distance thresholds are model-specific. I
> calibrated ours by measuring real pairs, not by picking a round number."

---

## 3. Hybrid retrieval and Reciprocal Rank Fusion

Dense (vector) search finds meaning. Sparse/lexical search (BM25, or Postgres
`tsvector`) finds *tokens*. Each is blind where the other sees:

- Ask for `ERR_4021` — lexical nails it, dense shrugs.
- Ask "how do we handle a bad release" — dense finds the paraphrase, lexical
  finds nothing.

Production RAG in 2026 runs both. The problem: the two produce scores on
incompatible scales — a cosine distance and a `ts_rank_cd` score cannot be
added, and normalising them is fragile.

**Reciprocal Rank Fusion** sidesteps this by throwing the scores away and using
only *rank*:

```
score(doc) = Σ over channels  1 / (k + rank_in_that_channel)
```

`k` (we use 60, from the original RRF paper) damps the top ranks so one channel
cannot dominate. A document ranked #1 in both channels scores about twice a
document ranked #1 in only one. No calibration, no tuning, no training.

You can watch it work in this repo:

```
query "23 dias"  →  0.03279  Vacaciones   ← both channels hit, roughly double
                    0.01613  Despliegues
query "cuando se sube a produccion"  →  Despliegues first (semantic only)
query "holiday policy"               →  Vacaciones first (semantic, cross-language)
```

The SQL is in `backend/knowli/infrastructure/postgres/repository.py` — two CTEs,
one `LEFT JOIN`, no extra service.

> **Say it like this:** "RRF fuses rankings, not scores, so you never have to
> calibrate a cosine distance against a BM25 score. That is the whole trick."

**What comes after this, if precision is not enough:** a **cross-encoder
reranker**. Retrieval uses a *bi-encoder* — query and document embedded
separately, which is why it is fast enough to search millions. A cross-encoder
reads query and document *together*, which is far more accurate and far too slow
for the whole corpus. So: retrieve ~100 cheaply, rerank to the top ~10 precisely.
We do not need it at this scale; know the name (`BGE-reranker`, `Cohere Rerank`)
and the reason.

---

## 4. The knowledge base: what a claim is compared against

Everything above assumes one question: *retrieve from where?* The naive answer
is "everything stored", and it holds for exactly as long as everything stored is
about one subject.

A **knowledge base** is the container claims live in. It is what a vector store
calls a **collection** (Qdrant, Chroma) or a **namespace** (Pinecone), and what
pgvector implements as a scoping column plus the indexes that support it. Above
it sits a **workspace**, so that a second tenant later is a `WHERE` clause
rather than a migration. One of each is seeded on startup —
`DEFAULT_WORKSPACE=default`, `DEFAULT_KNOWLEDGE_BASE=personal` — so a solo local
user never meets the concept.

**Both retrieval and conflict detection scope to one knowledge base**, and the
second one is the reason the container exists. Retrieval scoping is a quality
and a cost improvement; you would survive without it. Conflict detection
scoping is the difference between the product working and not working.

Consider a support organisation. One team handles kitchen returns and writes
*"a return has to be approved by the team lead first"*; another handles sofa
deliveries and writes *"a return does not need approval under €50"*. Put both in
one pile and the detector compares them, because it compares whatever is
*semantically near* — and they are: same vocabulary, same shape, same domain of
discourse. The model reading the pair cannot tell from the text alone that these
are different departments, so it does the reasonable thing and calls them a
contradiction. A human is then asked to break a tie between two facts that are
both simply true, and every available answer is wrong.

Measured on this project's default embedding model, with the *identical*
contradicting statement offered twice:

| Setup | Distance to the stored claim | Result |
|---|---|---|
| Stored claim and new claim in **different** knowledge bases | 0.289 | **zero conflicts** — the neighbour is not visible |
| Stored claim and new claim in the **same** knowledge base | 0.289 | a genuine `conflict` verdict |

The distance is the same either way, which is the point: nothing about the
embedding changed and nothing about the threshold changed. The scope decided
whether the two claims were ever in the same conversation.

> **Say it like this:** "Conflict detection is only meaningful inside a scope.
> Two teams can hold contradictory-looking facts that are both true, and the
> only thing that can tell them apart is a boundary you declare — not a
> similarity score."

**What this is not.** There are no users and no authentication, so a knowledge
base is a *subject* boundary, not a permission boundary. Nothing stops a caller
naming any slug. The tables were added early anyway, because scoping a
comparison is a data-model decision and retrofitting one over claims already
written is the expensive kind of change.

Two details fall out of it and are worth knowing:

- **An unknown slug is an error everywhere**, never a silent fallback to the
  default. An error costs a caller one retry; a fallback costs someone a wrong
  answer months later with no way to see where it came from. The message lists
  the slugs that do exist so a person can correct the request.
- **The slug is derived from the name, and folding is the whole job.** "Kitchen
  Returns", "kitchen returns" and "Kitchen  Returns!" have to collapse to one
  knowledge base, accents included, or they quietly become three that look
  identical in a sidebar.

---

## 5. Human-in-the-loop, and why this is a graph

The design claim of this project: **the model proposes, the human disposes.**
That means the workflow has to physically stop twice, and stay stopped —
possibly for hours, possibly until a different person opens the link.

That is not something a chain can do. A chain is a function: it starts, it runs,
it returns. There is nowhere for it to *pause*.

A **graph** with a **checkpointer** can. LangGraph's `interrupt()`:

1. writes the entire workflow state to Postgres,
2. stops the run,
3. returns the payload to whoever called it.

Nothing is running while the human thinks — no held connection, no timer, no
in-memory session. Resuming is `Command(resume=value)` against the same
`thread_id`. The paused review is *a row in a table*.

```
extract ──► confirm ──┬─► detect ──► resolve ──► commit ──► END
   ▲                  │      (human)      (human)
   └──── clarify ─────┘
```

Consequences worth naming out loud:

- A review survives a server restart, a laptop closing, a week.
- A person can return to a paused review in the browser and finish it later.
- The `clarify` edge is possible *because* it is a graph: answering the model's
  open questions routes **back** to extraction with extra context, instead of
  moving forward. A chain would have to be re-run from scratch.
- **The review can also go backwards.** `POST /api/sessions/{id}/back` replays
  the thread from the checkpoint before the current gate, so the resolve gate
  becomes the confirm gate again with the claims exactly as they were. Nothing
  extra had to be stored to allow it — every earlier state is already a row.
  This is the checkpointer earning its keep a second time: once for pausing,
  once for rewinding.

> **Say it like this:** "The human gates are `interrupt()` calls. That makes the
> pause durable — the session is a checkpoint in Postgres, not a connection
> being held open."

### Two things this cost us, both real

Both are documented in the code, and both are the kind of detail that only shows
up when you actually build it:

1. **The checkpointer needs its own autocommit connection pool.** LangGraph's
   migrations use `CREATE INDEX CONCURRENTLY`, which Postgres refuses to run
   inside a transaction block.
2. **You must resume by interrupt id.** A bare `Command(resume=value)` hands the
   *same* value to every interrupt reached during that run — so resuming the
   confirm gate would make the resolve gate swallow the confirm payload instead
   of pausing. `Command(resume={interrupt_id: value})` resumes exactly one.

---

## 6. Structured output

Asking a model for JSON and parsing the reply is a losing game: fenced blocks,
preambles, trailing prose, single quotes.

`with_structured_output(Schema)` sends the Pydantic schema to the model as a
**tool/function definition** and lets the provider's constrained decoding
guarantee the shape. You get a typed object, not a string.

The claim and conflict types live in `domain/`, and both edges are built on
them: `infrastructure/llm/schemas.py` wraps them in what the model must return,
`interfaces/http/schemas.py` in what the API exchanges. The vocabulary is
therefore declared **once** and is simultaneously the model's contract, the
API's validation, the OpenAPI spec, and the source of truth the TypeScript
types mirror — while each edge is still free to have a shape of its own.

> **Say it like this:** "One Pydantic model is the LLM contract, the API
> contract and the docs. If it drifts, everything fails loudly in one place."

---

## 7. Versioned knowledge

Nothing is deleted. A claim that loses a conflict keeps its row and gets a
`superseded_by` pointer to the claim that replaced it.

- Live view: `WHERE superseded_by IS NULL`.
- History: a recursive CTE walking the chain backwards.

This is deliberately git's model, and the UI leans on it — but note where the
analogy is *not* useful: git conflict markers (`<<<<<<< HEAD`) are famously
hostile, so the interface shows stored and incoming side by side and dims the
losing one instead of asking a non-engineer to read merge syntax. Steal the data
model, not the ergonomics.

> **Say it like this:** "The store is append-only. You can always ask what we
> used to believe and when it changed."

---

## 8. Where the tokens actually go

Per capture, roughly:

| Call | Purpose |
|---|---|
| 1 | extract claims from the raw text |
| 0–N | one comparison call per claim that has near neighbours |
| 0 | committing — pure database work, no model involved |

The conflict step is the expensive one, and it is bounded three times: by the
knowledge base (nothing outside it is a candidate at all), by `CONFLICT_TOP_K`
(how many neighbours) and by `CONFLICT_MAX_DISTANCE` (a claim with no close
neighbours costs *zero* LLM calls). The distance cutoff is a cost control as
much as a quality one, and so, incidentally, is the scope: a support
organisation with twelve knowledge bases is not paying for twelve queues' worth
of near-misses on every capture.

---

## Further reading

- Reciprocal Rank Fusion — Cormack et al., 2009 (the `k=60` comes from here)
- Contextual Retrieval — Anthropic, 2024
- Late chunking — Jina AI, 2024
- LangGraph human-in-the-loop — <https://docs.langchain.com/oss/python/langgraph/>
- pgvector — <https://github.com/pgvector/pgvector>
