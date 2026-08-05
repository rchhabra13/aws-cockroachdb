from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache
def _model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> list[float]:
    return _model().encode(text).tolist()
