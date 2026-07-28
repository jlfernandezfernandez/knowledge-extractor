# Knowledge Extractor

Turn what a person *knows* into a curated vector knowledge base — with the person
in the loop the whole way.

Most RAG ingestion pipelines dump documents into a vector store and hope for the
best. Knowledge decays, contradicts itself, and nobody notices. Knowledge Extractor
makes ingestion a **review**:

1. **Capture** — someone talks or types, freely. No structure required.
2. **Confirm** — an LLM splits it into discrete, self-contained claims and shows
   them back. *"This is what I understood."* The person edits or deletes anything wrong.
3. **Resolve** — each claim is checked against what is already stored. Contradictions
   are shown as **git-style conflicts** and the person decides: take incoming, keep
   stored, keep both, or write a merge.
4. **Commit** — only then does anything land in the vector store. Nothing is ever
   deleted; a replaced claim is marked as superseded by the one that won, so the
   knowledge base has a history.

Other agents can talk to it over Google's **Agent2Agent (A2A)** protocol: they can
search the knowledge base freely, and they can *propose* knowledge — which opens a
review session for a human rather than writing straight to the store.

<!-- ponytail: no screenshot yet; the UI is one self-contained HTML file, run it. -->

## Why these pieces

| Piece | Choice | Why |
|---|---|---|
| Vector store | **Postgres + pgvector** | The vectors, the supersede history and the review sessions live in one database with one `docker compose up`. A dedicated vector DB would mean a second store for the relational half. |
| Embeddings | **fastembed** (ONNX, CPU) | No PyTorch, no GPU, no extra service — ~90 MB, multilingual by default. Swap in any OpenAI-compatible `/embeddings` endpoint with two env vars. |
| LLM | **any OpenAI-compatible endpoint** | Ollama, LM Studio, OpenRouter, OpenAI, Anthropic — one base URL and a model name. No vendor lock-in in the code. |
| Transcription | **faster-whisper** (optional) | Runs locally on CPU. Optional extra; skip it if you only type. |
| Agent interop | **A2A** (`a2a-sdk`) | v1.0 since April 2026, Linux Foundation governed. Optional extra. |
| UI | one HTML file, no build step | `git clone` → run. No npm, no bundler. |

Everything is open source and runs entirely on a laptop.

## Quick start

```bash
git clone https://github.com/<you>/knowledge-extractor && cd knowledge-extractor
cp .env.example .env          # then set LLM_API_BASE / LLM_API_KEY / LLM_MODEL
docker compose up -d          # Postgres 17 + pgvector
uv venv && uv pip install -e .
knowledge-extractor           # http://127.0.0.1:8000
```

First run downloads the embedding model (~90 MB) once.

Optional extras:

```bash
uv pip install -e '.[audio]'   # voice capture (faster-whisper, local, CPU)
uv pip install -e '.[a2a]'     # A2A agent server:  ke-a2a  → port 9999
```

Tested on an M-series MacBook Air, 16 GB, CPU only.

### Using a fully local stack

```bash
ollama pull qwen3 && ollama pull embeddinggemma
```

```dotenv
LLM_API_BASE=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen3
EMBED_API_BASE=http://localhost:11434/v1
EMBED_MODEL=embeddinggemma
EMBED_DIM=768
```

Changing `EMBED_DIM` changes the vector column width — recreate the database with
`docker compose down -v` when you switch embedding models.

## HTTP API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/capture` | `{text, author}` → opens a session, returns extracted claims |
| `POST` | `/api/transcribe` | audio upload → text (needs the `audio` extra) |
| `POST` | `/api/sessions/{id}/atoms` | the confirmed/edited claims → returns conflicts |
| `POST` | `/api/sessions/{id}/resolve` | `{decisions}` → writes to the store |
| `GET` | `/api/search?q=` | semantic search |
| `GET` | `/api/knowledge` | everything currently live |
| `GET` | `/api/health` | which models are configured |

A decision is keyed `"<atom_id>::<existing_id>"` and is one of `keep_new`,
`keep_old`, `keep_both`, or `merge` (with a `statement`).

## A2A

```bash
ke-a2a
# agent card: http://127.0.0.1:9999/.well-known/agent-card.json
```

Two skills:

- **`search_knowledge`** — semantic search over the curated store.
- **`submit_knowledge`** — proposes knowledge and returns a `review_url`. It does
  **not** write to the store. A human opens that URL, confirms what the model
  understood, and resolves any conflicts. That gate is the point of the project.

Select a skill with `metadata: {"skill": "submit_knowledge"}` on the message;
the default is search.

Calling it directly — note the JSON-RPC method is `SendMessage`, and the
`A2A-Version` header is **required** (without it the server assumes protocol 0.3
and rejects the call):

```bash
curl -s -X POST localhost:9999/ \
  -H 'Content-Type: application/json' -H 'A2A-Version: 1.0' \
  -d '{"jsonrpc":"2.0","id":"1","method":"SendMessage","params":{
       "message":{"messageId":"u1","role":"ROLE_USER",
                  "parts":[{"text":"when do we deploy?"}]}}}'
```

## Data model

```
knowledge(id, title, statement, tags[], author, source, embedding, superseded_by, created_at)
sessions (id, stage, payload jsonb, created_at)
```

`superseded_by` is the whole history mechanism: a claim that loses a conflict stays
in the table pointing at the claim that replaced it. Searches only see rows where
`superseded_by IS NULL`.

## Tests

```bash
python tests/test_pipeline.py     # no database or LLM needed
```

## License

Apache-2.0
