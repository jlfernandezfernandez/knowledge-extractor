"""Embeddings: local ONNX by default, any OpenAI-compatible endpoint if configured."""

import functools

import httpx

from ... import config


@functools.cache
def _local_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=config.EMBED_MODEL)


class ConfiguredEmbedder:
    """The one implementation of `domain.ports.Embedder`.

    Which backend runs is a setting, not a subclass: both are three lines, and
    the only thing that must never differ between them is the dimension check
    below.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one vector per input, in order."""
        if not texts:
            return []

        if config.EMBED_PROVIDER == "remote":
            response = httpx.post(
                f"{config.EMBED_BASE_URL.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {config.EMBED_API_KEY}"},
                json={"model": config.EMBED_MODEL, "input": texts},
                timeout=120,
            )
            response.raise_for_status()
            data = sorted(response.json()["data"], key=lambda d: d["index"])
            vectors = [d["embedding"] for d in data]
        else:
            vectors = [list(map(float, v)) for v in _local_model().embed(texts)]

        for vector in vectors:
            if len(vector) != config.EMBED_DIM:
                raise ValueError(
                    f"EMBED_DIM is {config.EMBED_DIM} but {config.EMBED_MODEL} returned "
                    f"{len(vector)} dimensions. Fix EMBED_DIM and recreate the database "
                    f"(docker compose down -v)."
                )
        return vectors
