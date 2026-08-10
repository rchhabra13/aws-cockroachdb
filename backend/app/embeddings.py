"""Embedding provider selection.

EMBEDDING_PROVIDER chooses between Bedrock's Titan Text Embeddings V2 and a local
sentence-transformers model. Unlike the dialogue provider there is no fallback between
them: the two produce vectors of different widths, and a memory stored under one model
cannot be compared against a query embedded with the other. Silently switching would
return nonsense rather than an error.

Because of that, embedding_dim() must match the VECTOR width in schema/init.sql. Changing
provider means migrating the column and re-embedding every stored memory.
"""

from functools import lru_cache

from app.config import get_settings

# Titan V2 supports 1024, 512, and 256. all-MiniLM-L6-v2 is fixed at 384.
LOCAL_DIM = 384


@lru_cache
def _local_model():
    # Not installed in the container image: it pulls torch and the model weights, which
    # cost over a gigabyte for a path the deployed service does not use. Install
    # sentence-transformers locally to run with EMBEDDING_PROVIDER=local.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def embedding_dim() -> int:
    settings = get_settings()
    if settings.embedding_provider == "bedrock":
        return settings.bedrock_embedding_dimensions
    return LOCAL_DIM


def embed_text(text: str) -> list[float]:
    provider = get_settings().embedding_provider

    if provider == "bedrock":
        from app.providers.bedrock import embed_text as impl

        return impl(text)

    if provider == "local":
        return _local_model().encode(text).tolist()

    raise ValueError(f"unknown embedding provider: {provider!r}")
