# Knowledge Extractor

**Get what one person knows into something everyone can query — without letting
a model decide what is true.**

Companies do not lose knowledge because nobody wrote it down. They lose it
because the person who has it never had a low-friction way to give it up, and
because when they finally did, it quietly contradicted something already in the
wiki and nobody noticed.

Knowledge Extractor makes knowledge capture a **review**, in four steps:

| | | |
|---|---|---|
| **1. Say it** | Talk or type. No structure, no template, no form. | |
| **2. Read it back** | The model splits it into discrete, self-contained claims and shows them to you. *"This is what I understood."* You edit, discard, or answer its open questions and make it try again. | ⏸ **human gate** |
| **3. Decide** | Each claim is checked against what is already stored. Anything that collides is shown side by side — stored vs yours — and you are the tie-breaker. | ⏸ **human gate** |
| **4. Commit** | Only now is anything written. Nothing is ever deleted: a claim that loses is kept and marked as superseded by the one that won. |

Progress is real, not a spinner: the pipeline forwards LangGraph's own node
updates over SSE, so you see *"Found 4 claims · comparing against 128 stored
claims"* while it works.

Then the other half: **ask it questions** (⌘K). Answers come only from claims a human
approved, and cite the exact claims they used.

Other agents get the same surface. It speaks **A2A** (agent-to-agent) and
**MCP** (model-to-tools), so a coding assistant or another team's agent can
search and ask — and can *propose* knowledge, which opens a review for a human
rather than writing to the store.

---

## Why this is different from "dump the docs into a vector DB"

Ordinary RAG ingests documents and hopes. This ingests *claims*, and a person
signs off on each one. Three things follow from that, and they are the whole
point:

- **No chunking problem.** The retrieval unit is a claim that was written to
  stand alone. There is no window size to tune and no chunk that lost its
  context on page 34. Contextual retrieval is done by a human at write time
  instead of guessed at read time.
- **Contradictions surface at write time**, when the person who knows the answer
  is right there, instead of at read time when the model confidently averages
  two incompatible facts.
- **Knowledge has lineage.** `superseded_by` chains mean you can always ask
  *"what did we used to believe, and when did that change?"*

---

## Stack

Chosen to be current *and* boring enough to be employable — these are the tools
teams actually run in production in 2026.

| Layer | Choice | Why this one |
|---|---|---|
| Workflow | **LangGraph** | The product is a stateful multi-step workflow that has to *stop and wait for a human twice*. That is exactly what `interrupt()` + a checkpointer are for. A LangChain chain has nowhere to stop. |
| Model access | **LangChain** `init_chat_model` + `with_structured_output` | One line to swap Ollama ↔ OpenRouter ↔ OpenAI ↔ Anthropic. Output is constrained by a Pydantic schema, so there is no JSON scraping. |
| Store | **Postgres + pgvector** | Vectors, lexical index, supersede history and the paused workflow checkpoints all live in one database, started by one `docker compose up`. |
| Retrieval | **Hybrid** (pgvector + Postgres full-text, fused with RRF) | Embeddings miss exact tokens — error codes, version numbers, acronyms. Keyword search misses paraphrase and cross-language. Production RAG uses both. |
| Embeddings | **fastembed** (ONNX, CPU) | ~90 MB, multilingual, no PyTorch, no GPU, no extra service. Swappable for any OpenAI-compatible `/embeddings` endpoint. |
| API | **FastAPI** | Pydantic schemas are already there; OpenAPI docs come free at `/docs`. |
| Frontend | **React 19 + TypeScript + Vite + Tailwind v4** | The default enterprise SPA stack. No SSR here on purpose — see `docs/decisions.md`. |
| i18n | **react-i18next** (English, Spanish) | Browser-detected and remembered, with no picker cluttering the chrome. The Spanish catalogue is type-checked against the English one. |
| Motion | **CSS + View Transitions** | No animation library. The review is a four-slide deck; the browser cross-fades the slides itself, and CSS runs off the main thread — where you want it while an LLM response is being parsed. |
| Agent surfaces | **A2A** (`a2a-sdk`) and **MCP** (`mcp`) | The two protocols that matter, and they are complementary rather than competing. `docs/protocols.md` explains the difference. |

Everything is open source and runs on a laptop, offline, with no API key.

---

## Quick start

```bash
git clone https://github.com/jlfernandezfernandez/knowledge-extractor
cd knowledge-extractor
docker compose up -d                      # Postgres 17 + pgvector

# Backend
cd backend
cp .env.example .env                      # defaults point at a local Ollama
uv venv && uv pip install -e .
ke-api                                    # http://127.0.0.1:8000  (docs at /docs)

# Frontend
cd ../frontend
npm install && npm run dev                # http://localhost:5173
```

### Running it fully local (recommended on a 16 GB Mac)

```bash
ollama pull qwen3.5:4b            # ~3.4 GB — multimodal, thinking mode, tool calling
ollama pull qwen3-embedding:0.6b  # optional, stronger multilingual embeddings
```

The `.env.example` defaults are already set for this — including two settings a
4B model needs in order to work at all. Measured on a MacBook Air M3 / 16 GB:
20 s to extract, 11 s to detect conflicts, 5 s to answer a question, entirely
offline. `docs/local-models.md` has the numbers, the two settings, and an
honest list of what 4B still gets wrong.

### Optional extras

```bash
cd backend
uv pip install -e '.[audio]'   # voice capture, local, CPU (faster-whisper)
uv pip install -e '.[a2a]'     # ke-a2a  → agent-to-agent server on :9999
uv pip install -e '.[mcp]'     # ke-mcp  → MCP server over stdio
```

---

## Documentation

Written to be read in order. The goal is that after reading them you can
rebuild this — or argue with the choices — without the code in front of you.

| | |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | How the pieces fit, and what happens on each request |
| [`docs/concepts.md`](docs/concepts.md) | The concepts behind it — RAG, hybrid retrieval, RRF, human-in-the-loop, checkpointing — explained so you can explain them |
| [`docs/protocols.md`](docs/protocols.md) | A2A, MCP and the 2026 agent-interoperability landscape |
| [`docs/local-models.md`](docs/local-models.md) | Which models fit on a laptop, and how to swap them |
| [`docs/decisions.md`](docs/decisions.md) | What was chosen, what was rejected, and why |

---

## Tests

```bash
cd backend && .venv/bin/python -m pytest    # no database or model needed
```

## Status

Working end to end: capture → confirm → conflicts → commit, streamed progress,
hybrid search, cited answers (⌘K), English and Spanish, A2A and MCP surfaces.
Not yet: multimodal capture (images and files), authentication, and per-team
isolation. See the issues.

## License

Apache-2.0
