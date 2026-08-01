# 🦉 Knowli

Human-in-the-loop knowledge extractor built with **FastAPI**, **LangGraph**, **PostgreSQL (pgvector)**, and **React**.

Knowli transforms text and voice recordings into a structured, auditable knowledge base with human review, automated conflict detection, and inline RAG citations.

## 🚀 Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start PostgreSQL, API, and Frontend
docker compose up --build
```

Open **[http://localhost:3000](http://localhost:3000)** (Demo account: `demo@knowli.local` / `demo`).

---

## 🛠️ Prerequisites & Local AI Setup

Knowli connects to OpenAI-compatible endpoints for LLM and Speech-to-Text (STT):

### 1. LLM (Default: Ollama)

```bash
ollama pull qwen3.5:9b
OLLAMA_ORIGINS="*" ollama serve
```

### 2. Audio Transcription (Default: Local Speaches / Faster-Whisper / Parakeet)

Run the included Speaches container via Docker Compose profile:

```bash
docker compose --profile stt up --build
```

> 💡 **Cloud APIs (OpenAI / Groq / OpenRouter):** Update `MODEL_*` and `TRANSCRIPTION_*` variables in `.env`.

---

## 🧪 Development & Tests

```bash
# Backend unit & integration tests
cd backend && uv run pytest

# Frontend tests & build
cd frontend && npm test && npm run build
```

---

## 📄 License

Apache-2.0
