"""Embedding provider selection.

Provider changes require a matching schema width and re-embedded stored memories.
"""

from functools import lru_cache

from app.config import get_settings

# Titan V2 supports 1024, 512, and 256. all-MiniLM-L6-v2 is fixed at 384.
LOCAL_DIM = 384


@lru_cache
def _local_model():
    # sentence-transformers is intentionally absent from the default dependencies.
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
