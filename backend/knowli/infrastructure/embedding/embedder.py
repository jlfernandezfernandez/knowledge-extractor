"""Embeddings: local ONNX by default, any OpenAI-compatible endpoint if configured."""

import functools
import logging

from ... import config

logger = logging.getLogger(__name__)


@functools.cache
def _local_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=config.EMBEDDING_MODEL)


class ConfiguredEmbedder:
    """The one implementation of `domain.ports.Embedder`."""

    def warmup(self) -> None:
        """Pre-initialize local embedding model to prevent first-request cold-start latency."""
        try:
            _local_model()
        except Exception as error:
            logger.warning("FastEmbed warmup deferred: %s", error)

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
