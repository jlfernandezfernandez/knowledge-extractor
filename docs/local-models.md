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

**`qwen3.5:4b`** (released March 2026) is the recommendation. It is not the
newest Qwen — it is the newest one that *fits*, which is the question that
matters here. As of July 2026 the line has moved on, but not downwards in size:

| Version | Open weights | Sizes on Ollama | On a 16 GB Mac |
|---|---|---|---|
| **Qwen3.5** | yes | 0.8b · 2b · **4b** · 9b · 27b · 35b · 122b | ✅ |
| Qwen3.6 | yes | 27b · 35b only | ❌ 17 GB / 24 GB |
| Qwen3.7 / 3.8-Max | **no** — API only | — | ❌ |

Beyond size, it earns the slot:

- **Structured output that holds** — required. The pipeline constrains every
  call to a Pydantic schema; a model that cannot do that cannot run this
  project at all. See the two settings it needs, below.
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

## Measured on a MacBook Air M3 / 16 GB

`qwen3.5:4b` + fastembed, everything local, nothing hosted:

| Step | Time | Result |
|---|---|---|
| Capture → claims + summary | **20 s** | 5 claims from a 2-sentence brain-dump |
| Conflict detection | **11 s** | 2 of 5 claims had neighbours; the other 3 cost zero LLM calls |
| Commit | **< 0.1 s** | pure database work |
| Ask (hybrid retrieval + cited answer) | **5 s** | correct, and citing the right claim |

It found the real contradiction — a stored "22 días de vacaciones" against an
incoming "23 días" — called it a `conflict`, and explained why. It also
correctly called a vaguer restatement of a stored claim a `refines` rather than
a conflict. That is the hard part of the pipeline, and a 4B model does it.

### Two settings this needed, and neither is optional

Both are already the defaults in `.env.example`. They are here because without
them the pipeline returns **zero claims**, not slightly worse ones.

**`LLM_STRUCTURED_METHOD=json_schema`.** Asked for the nested `Extraction`
schema through `function_calling`, the model flattened it: one tool call per
claim, shaped like a bare claim, wrapper and summary dropped. The parse then
found no `claims` key and yielded an empty result. Constrained decoding against
the JSON schema holds the shape.

**`LLM_REASONING_EFFORT=none`.** Qwen3.5 thinks by default. On a plain
extraction it spent **3910 completion tokens** reasoning and never emitted the
JSON at all. Measured three ways:

| Configuration | Time | Result |
|---|---|---|
| thinking on, `max_tokens` 4096 | — | fails, budget exhausted mid-thought |
| thinking on, `max_tokens` 8000 | **216 s** | works, worse claims |
| **thinking off** | **8 s** | works, better claims |

Extraction is not a reasoning task. Set it back to `low`/`medium`/`high` if you
point this at a model that benefits, or to empty for a provider that rejects
the parameter.

### What 4B is not good enough for

Honest limits, seen in the same run:

- **It over-splits.** Two sentences became five claims. Three would be right.
- **Titles run long.** They should be short labels; it writes sentences.
- **It embellishes.** It rendered "Friday morning" as *"mover el despliegue a
  los fines de semana"* — Friday is not the weekend — and turned "every Sunday
  at 3am" into a summary claiming *"ocurre una vez al año"*.
- **It ignores the language instruction on secondary fields.** Claims came back
  in Spanish as asked; the conflict `reason` strings came back in English.

None of this is fatal **because of the design**: step 2 exists precisely so a
person deletes the invented claim before it is stored. That is the difference
between this and a pipeline that would have written all five straight into the
vector store.

If you want fewer of those corrections, `qwen3.5:9b` is the next step up that
still fits, and any hosted model removes the problem entirely — three env vars.

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
