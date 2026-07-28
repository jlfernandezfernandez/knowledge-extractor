"""Model access, provider-agnostic.

Everything goes through LangChain's `init_chat_model` against an OpenAI-compatible
endpoint, so switching between Ollama, OpenRouter, OpenAI or Anthropic is three
environment variables and no code change.

`with_structured_output` is what makes this robust: the schema is sent to the
model and the reply is parsed into a Pydantic object. No regex, no fenced-JSON
scraping. `method="function_calling"` is used because it is the mode small local
models support most reliably.
"""

import functools

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from . import config


@functools.cache
def chat_model() -> BaseChatModel:
    return init_chat_model(
        config.LLM_MODEL,
        model_provider="openai",
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        temperature=0,
    )


def structured(schema):
    """A runnable that returns `schema` instances instead of free text."""
    return chat_model().with_structured_output(schema, method="function_calling")
