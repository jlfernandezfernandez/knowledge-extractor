"""Model access, provider-agnostic.

Everything goes through LangChain's `init_chat_model` against an OpenAI-compatible
endpoint, so switching between Ollama, OpenRouter, OpenAI or Anthropic is a few
environment variables and no code change.

Three settings here were not guesses — they are what a 4B local model needed to
work at all, measured on `qwen3.5:4b`:

1. `method="json_schema"`, not `function_calling`. Asked for a nested schema
   (`Extraction`, which wraps a list of claims plus a summary) via function
   calling, the model flattened it: one tool call per claim, shaped like a bare
   claim, with the wrapper and the summary silently dropped — so the pipeline
   got zero claims. Constrained decoding against the JSON schema holds the
   shape. Larger models handle either.

2. `reasoning_effort` off by default. Qwen3.5 thinks by default, and on a plain
   extraction it spent 3910 completion tokens reasoning and never reached the
   JSON at all. Turning it off: 8s and correct. Leaving it on but raising
   `max_tokens` instead: 216s and worse claims. Extraction is not a reasoning
   task. Set `LLM_REASONING_EFFORT=` (empty) for providers that reject the
   parameter, or to `low`/`medium`/`high` if your model benefits.

3. A `max_tokens` ceiling, so a model that decides to think forever fails fast
   instead of hanging a review for four minutes.
"""

import functools

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from . import config


@functools.cache
def chat_model() -> BaseChatModel:
    extra = {}
    if config.LLM_REASONING_EFFORT:
        extra["reasoning_effort"] = config.LLM_REASONING_EFFORT
    return init_chat_model(
        config.LLM_MODEL,
        model_provider="openai",
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        temperature=0,
        max_tokens=config.LLM_MAX_TOKENS,
        **extra,
    )


def structured(schema):
    """A runnable that returns `schema` instances instead of free text."""
    return chat_model().with_structured_output(
        schema, method=config.LLM_STRUCTURED_METHOD
    )
