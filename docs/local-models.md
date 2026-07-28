# Running it on your own laptop

Everything here runs offline, on CPU/Metal, with no API key. This page is the
answer to "which model, and will it fit?"

## The budget

A **16 GB Mac is really an ~11 GB model budget** once macOS, your browser and
the apps you actually work in have taken their share. Long context eats more on
top of the weights — a 256K-token window is not free. So the target is not "the
biggest model that loads", it is "the best model that leaves you room to work".

## The two to install

```bash
ollama pull qwen3.5:4b            # ~3.4 GB — the generator
ollama pull qwen3-embedding:0.6b  # ~1.2 GB — the retriever  (optional)
```

**`qwen3.5:4b`** (released March 2026) is the recommendation, and not only on
size:

- **Native tool calling** — required. The pipeline uses
  `with_structured_output(method="function_calling")`, so a model that cannot
  emit tool calls cannot run this project at all.
- **Natively multimodal** (text, image, video) — which is exactly where this
  project is heading: capture from photos, whiteboards and screenshots.
- **Thinking mode** and a **256K context window**.
- ~2.5 GB resident. You can leave it running and still open Docker and an IDE.

Ollama added an **MLX backend on Apple Silicon in March 2026**, which closed most
of the speed gap with native MLX-LM — so on a Mac, Ollama is now both the easiest
*and* a fast option.

**Embeddings.** The default needs no Ollama at all: `fastembed` runs a 384-dim
multilingual ONNX model in-process, ~90 MB, no PyTorch. Good enough, and one
fewer moving part. Upgrade to `qwen3-embedding` when retrieval quality starts
mattering more than startup time — it is the strongest local multilingual
option (0.6B scores ~70.7 on MTEB-eng-v2) and it is 1024-dim.

## Configuring it

```dotenv
# backend/.env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen3.5:4b

EMBED_PROVIDER=local        # fastembed, in-process
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBED_DIM=384
```

Switching to Ollama embeddings:

```dotenv
EMBED_PROVIDER=remote
EMBED_BASE_URL=http://localhost:11434/v1
EMBED_MODEL=qwen3-embedding:0.6b
EMBED_DIM=1024
```

> ⚠️ **`EMBED_DIM` is the width of a Postgres column.** Changing the embedding
> model means recreating the table: `docker compose down -v`. And re-measure
> `CONFLICT_MAX_DISTANCE` afterwards — the calibration in
> [`concepts.md`](concepts.md#2-embeddings) is a property of the model.

## Going hosted

Same three variables. Nothing in the code changes.

```dotenv
# OpenRouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=deepseek/deepseek-chat

# Anthropic
LLM_BASE_URL=https://api.anthropic.com/v1
LLM_MODEL=claude-opus-5
```

## Sizing, roughly

| Class | Example | Resident | Verdict on 16 GB |
|---|---|---|---|
| ~1B | `qwen3.5:0.8b` | ~1 GB | too weak for reliable structured extraction |
| **~4B** | **`qwen3.5:4b`** | **~2.5 GB** | **the sweet spot for this workload** |
| ~9B | `qwen3.5:9b` | ~6 GB | better claims; tight if Docker + IDE are open |
| 27B+ | `qwen3.5:27b` | 16 GB+ | not on this machine |

## Which parts need the model to be good?

Useful to know before blaming the model:

| Step | Sensitivity | Why |
|---|---|---|
| **Extraction** | high | Writing genuinely self-contained claims is the hard judgement in the whole pipeline. |
| **Conflict comparison** | medium | Mostly a 4-way classification with both texts in front of it. |
| **Answering** | medium | Grounded in retrieved claims; the retrieval did the work. |
| **Retrieval** | n/a | No LLM involved — that is the embedding model and Postgres. |

If a small model is disappointing, it will disappoint at extraction first. Try a
9B before concluding the approach is wrong.

## Sources

- [Best local LLM for a 16 GB Mac, 2026](https://atomic.chat/blog/guides/best-local-llm-16gb-mac)
- [qwen3.5 on Ollama](https://ollama.com/library/qwen3.5)
- [qwen3-embedding on Ollama](https://ollama.com/library/qwen3-embedding)
- [Ollama embedding models benchmarked, 2026](https://www.morphllm.com/ollama-embedding-models)
