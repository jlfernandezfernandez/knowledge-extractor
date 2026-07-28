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

---

### `json_schema`, not `function_calling`, for structured output

**Chosen.** Constrained decoding against the JSON schema.

**Rejected:** `function_calling`, which is the more widely supported method and
was the original choice. It fails on this project's nested `Extraction` schema
with a 4B local model: the model emits one tool call per claim instead of one
call containing a list of claims, and the wrapper's other fields — the summary
the whole second screen is built around — are dropped. The parse then finds no
`claims` key and returns an empty result. Silent, and total.

Both work on larger models. `LLM_STRUCTURED_METHOD` switches it back for
providers without `json_schema` support. Measurements in
[`local-models.md`](local-models.md#two-settings-this-needed-and-neither-is-optional).

---

### Thinking off for extraction

**Chosen.** `LLM_REASONING_EFFORT=none` by default.

**Rejected:** leaving the model's default thinking on and raising `max_tokens`
to accommodate it. Measured on `qwen3.5:4b`: thinking on burned 3910 completion
tokens without reaching the JSON; raising the ceiling made it work in **216
seconds** with *worse* claims; turning thinking off made it work in **8**.

Extraction and 4-way classification are not reasoning tasks. The reasoning
budget belongs to the human reading step 2.

---

### The review is a deck, not a form

**Chosen.** Four full-stage slides — say it, review, decide, saved — with a
stepper in the chrome, one idea per slide, and directional transitions.

The reasoning is that this interaction *is an interview*. A form asks you to
fill in fields you can see all at once; an interview asks one thing, waits, and
moves on. Slides match the second, and they make the review feel finite:
you can see there are four, and you can see which one you are on.

**Rejected:** the earlier left rail. It read as a table of contents — passive,
something you consult — rather than progress you are making. Nothing moved
between steps, so the flow felt like swapping panels in a settings screen.

**How the motion works.** Advancing sends the current slide out to the left and
brings the next in from the right; going back mirrors it exactly, so enter and
exit share a path and the spatial relationship holds. This uses the **View
Transitions API** rather than a hand-rolled carousel: the browser snapshots
both states itself, so slides of very different heights cross without a layout
jump and without keeping the outgoing React tree mounted. Browsers without it
get an instant swap, which is fine.

**The action bar is sticky.** A slide can be taller than the viewport — five
claims to review, three conflicts to settle — and the way forward must never be
something you scroll to find. Same position on every slide, so advancing
becomes muscle memory.

**The stepper has four dots for five states.** `detecting` is a loading state
between *review* and *decide*, so it advances the track without claiming a dot
of its own. An earlier version had a dot per backend stage, which meant the
first slide highlighted nothing and read as broken.

---

### No language picker

**Chosen.** Detect from the browser, remember the choice, and show no control.

**Rejected:** the language `<select>` that shipped with i18n. It sat in the
chrome of every screen, competing with the two things that matter there — where
you are, and how to ask a question — for a control almost nobody touches once.
The detector is right the first time; i18n stayed, the widget went.

---

### Conflict actions depend on the verdict

**The question this answers:** does "keep both" make sense?

**Only sometimes**, and offering it everywhere was a real bug. The 2026 RAG
literature splits knowledge conflicts into types — temporal, complementary,
duplicate, debatable — and the point of the taxonomy is that the *resolution*
differs per type. ConflictRAG classifies before resolving; the deterministic
recency work shows a plain recency prior beats asking a model which of two
dated facts is current.

Mapped onto this project's three actionable verdicts:

| Verdict | Offered | Default | Why |
|---|---|---|---|
| `conflict` | use yours · keep stored · combine | **use yours** | Keeping both leaves retrieval to surface two incompatible claims and the generator to pick one arbitrarily — the exact failure this project exists to prevent. So keep-both is **not offered**. The default follows the recency prior: the person telling you now is describing the current state. |
| `duplicate` | keep stored · use yours · combine | **keep stored** | Two copies of one fact dilute retrieval and inflate whatever the generator sees. Keep-both is **not offered** here either. |
| `refines` | keep both · combine · use yours | **keep both** | Complementary claims are the case where both *should* stand. Superseding one throws away information that was worth keeping. |

Enforced in `plan()`, not just hidden in the UI: an agent that posts
`keep_both` for a `conflict` gets a `ValueError`, because a rule that only
exists in the frontend is not a rule.

**Every overlap arrives pre-answered** with its verdict's default, so the common
path is read-and-continue instead of click-every-card, and the action bar shows
how many you changed. The human gate is unchanged — nothing is written until
someone presses Save — but the gate no longer demands a click per row to pass.

**Not adopted:** letting the model resolve conflicts on its own (that is the
"Detecting Is Not Resolving" gap, and it removes the person this product is
built around), and a knowledge-graph layer for factual-conflict detection
(`TruthfulRAG`) — heavy for a store of this size.

---

### Speech: Parakeet TDT, with segments as they land

**Chosen.** NVIDIA Parakeet TDT 0.6B v3, INT8 ONNX, through sherpa-onnx. 640 MB,
25 European languages with automatic language identification, ~10x realtime on
this laptop's CPU, and no hallucinated text over silence — a transducer has
nothing to hallucinate *with*, which is Whisper's well-known failure on empty
audio. It is also the model Orca ships, so anyone who has Orca already has the
weights on disk and the default path finds them.

**Live text comes from segmentation, not a streaming model.** A Silero VAD cuts
the audio on pauses and each closed segment is decoded on its own, so the
transcript grows a phrase at a time. The obvious alternative — re-decoding the
whole buffer every tick — gets slower the longer you speak, which is precisely
backwards.

Audio reaches the server over a WebSocket as 16 kHz PCM16, captured in an
`AudioWorklet`. The worklet matters: a `ScriptProcessorNode` runs on the main
thread and drops samples whenever React renders. The `AudioContext` is asked
for 16 kHz directly, so there is no resampling in JavaScript at all.

**Rejected:** Whisper as the default (batch only, so nothing appears until you
stop talking; kept as `SPEECH_PROVIDER=whisper` because it is what most people
already have) and cloud transcription (this whole project runs offline).
