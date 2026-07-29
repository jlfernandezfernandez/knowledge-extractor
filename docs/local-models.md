# Running it on your laptop

Everything here runs offline, on CPU, with no API key. Three models, ~7.5 GB
total, all swappable through environment variables.

| Job | Default | Size | Why |
|---|---|---|---|
| Generating | `qwen3.5:9b` via Ollama | 6.6 GB | Newest Qwen that fits a 16 GB machine |
| Embedding | `paraphrase-multilingual-MiniLM` via fastembed | 90 MB | In-process ONNX, no extra service, no PyTorch |
| Transcribing | Parakeet TDT 0.6B v3 via sherpa-onnx | 640 MB | 25 languages, auto language ID, live segments |

## The generator

```bash
ollama pull qwen3.5:9b
```

A 16 GB Mac is really an **~11 GB budget** once macOS and your apps have taken
their share, and long context eats more on top of the weights. The target is not
the biggest model that loads, it is the best one that leaves you room to work.

`qwen3.5:9b` is not the newest Qwen. It is the newest one that **fits**, which is
the question that matters here:

| Version | Open weights | Sizes on Ollama | On 16 GB |
|---|---|---|---|
| **Qwen3.5** | yes | 0.8b · 2b · 4b · **9b** · 27b · 35b · 122b | ✅ |
| Qwen3.6 | yes | 27b and 35b only | ❌ 17 / 24 GB |
| Qwen3.7, 3.8-Max | **no**, API only | — | ❌ |

### Two settings it needs

Already the defaults in `.env.example`, and not optional: without them the
pipeline returns **zero claims**, not slightly worse ones.

**`LLM_STRUCTURED_METHOD=json_schema`.** Asked for the nested `Extraction`
schema through `function_calling`, a small model flattens it: one tool call per
claim, wrapper and summary dropped, so the parse finds no `claims` key and
yields nothing. Constrained decoding against the JSON schema holds the shape.

**`LLM_REASONING_EFFORT=none`.** Qwen3.5 thinks by default. On a plain
extraction it spent 3910 completion tokens reasoning and never emitted the JSON.
Measured three ways:

| Configuration | Time | Result |
|---|---|---|
| thinking on, `max_tokens` 4096 | — | fails, budget gone mid-thought |
| thinking on, `max_tokens` 8000 | 216 s | works, worse claims |
| **thinking off** | 8 s | works, better claims |

Extraction is not a reasoning task. Set it to `low`/`medium`/`high` for a model
that benefits, or empty for a provider that rejects the parameter.

### 4b vs 9b, same input

The 4b works and loads faster, but it needs more correcting:

| | `qwen3.5:4b` | `qwen3.5:9b` |
|---|---|---|
| Two sentences became | 5 claims | 3 claims |
| Summary opened with | "The user reports…" | the fact |
| Language instruction on `reason` | ignored, replied in English | followed |
| Faithfulness | wrote "Friday morning" as "the weekend" | accurate |
| Capture → claims | 20 s | 27 s |

Drop to `qwen3.5:4b` if 6.6 GB is too much. Step 2 exists to catch what it gets
wrong, which is the point of the design. Any hosted model removes the problem
entirely: three environment variables, no code change.

## The transcriber

Parakeet TDT 0.6B v3, INT8 ONNX. 25 European languages with **automatic language
identification**, so there is nothing to configure per speaker. Roughly 10x
realtime on an M3 CPU. Being a transducer it does not invent text over silence,
which is Whisper's well-known failure on empty audio.

The default `SPEECH_MODEL_DIR` points at the copy Orca keeps, so if you have
Orca there is nothing to download. Otherwise take
`sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8` from the
[sherpa-onnx model releases](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models)
and point `SPEECH_MODEL_DIR` at the unpacked folder. The 628 KB voice-activity
model is fetched automatically on first use.

```dotenv
SPEECH_PROVIDER=parakeet          # or: whisper
SPEECH_MODEL_DIR=/path/to/parakeet-tdt-0.6b-v3-int8
```

`SPEECH_PROVIDER=whisper` uses faster-whisper instead
(`uv pip install -e '.[whisper]'`). It transcribes in one batch, so nothing
appears until you stop talking.

## The embedder

The default needs no Ollama at all: fastembed runs a 384-dimension multilingual
ONNX model in-process. Upgrade when retrieval quality matters more than startup
time:

```dotenv
EMBED_PROVIDER=remote
EMBED_BASE_URL=http://localhost:11434/v1
EMBED_MODEL=qwen3-embedding:0.6b
EMBED_DIM=1024
```

> **`EMBED_DIM` is the width of a Postgres column.** Changing the embedding
> model means recreating the table with `docker compose down -v`, and
> re-measuring `CONFLICT_MAX_DISTANCE` — the calibration in
> [`concepts.md`](concepts.md#2-embeddings) is a property of the model.

## Going hosted

Same three variables, no code change.

```dotenv
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=deepseek/deepseek-chat
```

## Which steps need a good model?

| Step | Sensitivity | Why |
|---|---|---|
| Extraction | high | Writing genuinely self-contained claims is the hard judgement |
| Conflict comparison | medium | A four-way classification with both texts in front of it |
| Answering | medium | Grounded in retrieved claims; retrieval did the work |
| Retrieval | none | No LLM involved — that is the embedder and Postgres |

A small model disappoints at extraction first.

## Measured end to end

`qwen3.5:9b` + fastembed + Parakeet on a MacBook Air M3 / 16 GB, all local:

| Step | Time |
|---|---|
| Capture → claims and summary | 27 s |
| Conflict detection | 11 s |
| Save | < 0.1 s |
| Ask (hybrid retrieval + cited answer) | 5 s |

## Sources

- [qwen3.5 on Ollama](https://ollama.com/library/qwen3.5)
- [Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
- [Best local LLM for a 16 GB Mac, 2026](https://atomic.chat/blog/guides/best-local-llm-16gb-mac)
