"""Embeddings: local ONNX by default, any OpenAI-compatible endpoint if configured."""

import functools

from ... import config


@functools.cache
def _local_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=config.EMBEDDING_MODEL)


class ConfiguredEmbedder:
    """The one implementation of `domain.ports.Embedder`.

    The local model stays lazy: FastEmbed downloads and initializes it only
    when an authenticated route actually needs embeddings.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one vector per input, in order."""
        if not texts:
            return []

        vectors = [list(map(float, vector)) for vector in _local_model().embed(texts)]

        for vector in vectors:
            if len(vector) != config.EMBED_DIM:
                raise ValueError(
                f"EMBED_DIM is {config.EMBED_DIM} but {config.EMBEDDING_MODEL} returned "
                    f"{len(vector)} dimensions. Fix EMBED_DIM and recreate the database "
                    f"(docker compose down -v)."
                )
        return vectors
