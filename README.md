# Knowli

Human-in-the-loop knowledge extractor built with FastAPI, LangGraph, PostgreSQL, and React.

## Prerequisites & Local AI Setup

Knowli uses OpenAI-compatible endpoints for LLM and Speech-to-Text (STT) transcription. By default it expects local models:

### 1. Text LLM (Default: Ollama)
```bash
ollama pull qwen3.5:9b
ollama serve
```

### 2. Audio Transcription (Default: Local Whisper / Speaches)
Expects an OpenAI-compatible `/audio/transcriptions` service running locally on port 8000 (e.g. [Speaches](https://github.com/speaches-ai/speaches)).

> **Using Cloud Providers (OpenAI / Groq / OpenRouter):**
> Change `MODEL_*` and `TRANSCRIPTION_*` variables in `.env`.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000) (Demo account: `demo@knowli.local` / `demo`).

## Development & Tests

```bash
# Backend unit tests
uv run --directory backend pytest --ignore=tests/integration -q

# Frontend tests & build
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

## License

Apache-2.0
