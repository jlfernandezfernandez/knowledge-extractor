# Local models

Knowli can start without model credentials, which is useful for inspecting the
interface and running deterministic checks. To extract claims, compare overlap,
or answer questions, configure an OpenAI-compatible chat model.

## OpenAI

Copy the example environment file and set a key:

```bash
cp .env.example .env
# Edit .env:
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4.1-mini
```

Then start the full stack with `docker compose up --build`. `OPENAI_MODEL` is
optional; the Compose configuration defaults it to `gpt-4.1-mini`.

The adapter in `backend/knowli/infrastructure/llm/openai.py` requests
structured output for claim extraction, comparison, and answers. This keeps
JSON parsing and provider details at the integration edge.

## Embeddings

`backend/knowli/infrastructure/embedding/embedder.py` uses FastEmbed with the
multilingual MiniLM model by default. It runs locally through ONNX and downloads
its weights on first use. The PostgreSQL schema expects 384 dimensions; if you
change `EMBEDDING_MODEL`, keep `EMBED_DIM` compatible and recreate local data
when the dimension changes.

## Optional speech

Speech is disabled unless configured. To enable Parakeet, provide the path to a
downloaded model directory containing `encoder.int8.onnx`:

```bash
SPEECH_PROVIDER=parakeet
SPEECH_MODEL_DIR=/absolute/path/to/parakeet
```

The optional speech package is required for Parakeet support. Whisper is an
alternative:

```bash
SPEECH_PROVIDER=whisper
WHISPER_MODEL=small
```

Install its optional backend with `uv sync --directory backend --extra whisper`.
See `backend/knowli/infrastructure/speech/transcriber.py` for availability
checks and lazy loading. Speech failure does not prevent typed contributions.

## Deterministic end-to-end runs

The browser E2E setup uses deterministic model and embedding implementations
instead of a live provider. It is intentionally separate from normal local
startup so the portfolio path stays faithful to the configured runtime while
tests remain reproducible.
