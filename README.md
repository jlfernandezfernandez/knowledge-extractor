# 🦉 Knowli

Human-in-the-loop knowledge extractor built with **FastAPI**, **LangGraph**, **PostgreSQL (pgvector)**, and **React**.

Knowli transforms text and voice recordings into a structured, auditable knowledge base with human review, automated conflict detection, and inline RAG citations.

## 🚀 Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start PostgreSQL, API, Frontend, and Audio STT (Speaches)
docker compose up --build
```

Open **[http://localhost:3000](http://localhost:3000)** (Demo account: `demo@knowli.local` / `demo`).

---

## 🛠️ Prerequisites & LLM Setup

Knowli connects to an OpenAI-compatible endpoint for text generation (Default: Ollama):

```bash
ollama pull qwen3.5:9b
OLLAMA_ORIGINS="*" ollama serve
```

> 💡 **Cloud Providers (OpenAI / Groq / OpenRouter):** Update `MODEL_*` and `TRANSCRIPTION_*` variables in `.env`.

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
