"""The composition root: the single place where a port meets its implementation.

Everything above this file talks to `domain.ports`; nothing above it imports
psycopg, fastembed, LangChain or sherpa-onnx. Everything below it is an
implementation detail. If you want to know what this application is actually
made of, this file is the whole answer.

Deliberately dumb: four module-level singletons, three re-exports and one
function that actually builds something. No container, no settings framework. There is exactly one implementation of each port, so a
DI library would add a layer of indirection whose only job would be to hide
which one — and the constructors here take no arguments anyway. Connections,
models and pools are all created lazily inside the implementations, so importing
this module starts nothing.
"""

from .domain.ports import Catalog, ClaimExtractor, Embedder, KnowledgeRepository
from .infrastructure.embedding.embedder import ConfiguredEmbedder
from .infrastructure.llm.extractor import LangChainClaimExtractor
from .infrastructure.postgres import pool
from .infrastructure.postgres.repository import PostgresCatalog, PostgresKnowledgeRepository

# Re-exported, not wrapped. A function whose whole body is one forwarding call
# renames a thing without adding to it, and the rename is what you then have to
# look up. Importing them here still means no surface imports `infrastructure`.
from .infrastructure.postgres.pool import init as init_storage  # noqa: F401
from .infrastructure.speech.transcriber import available as speech_available  # noqa: F401
from .infrastructure.speech.transcriber import create as create_transcriber  # noqa: F401

repository: KnowledgeRepository = PostgresKnowledgeRepository()
# The claims and the catalog are two ports because they are not swapped
# together: move the claims to a vector store and this line does not change.
catalog: Catalog = PostgresCatalog()
embedder: Embedder = ConfiguredEmbedder()
extractor: ClaimExtractor = LangChainClaimExtractor()


def checkpointer():
    """LangGraph's Postgres checkpointer — the thing that makes a review parked
    on a human gate survive a restart, a different device, or a week."""
    from langgraph.checkpoint.postgres import PostgresSaver

    saver = PostgresSaver(pool.checkpoint_pool())
    saver.setup()  # runs its own migrations; idempotent
    return saver
