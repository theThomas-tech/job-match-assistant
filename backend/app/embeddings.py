"""Text embeddings: turn text into a list of numbers so similar meanings end up close together.

Runs locally and free with fastembed (ONNX runtime, no PyTorch). The model is downloaded
once (~70 MB) the first time it's used.
"""

from functools import lru_cache
from typing import Protocol

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384  # vector size produced by this model; the database columns use it too


class Embedder(Protocol):
    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed documents (job postings, profiles)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a short search query, e.g. "remote LLM engineer"."""
        ...


class FastEmbedder:
    def __init__(self, model_name: str = EMBEDDING_MODEL) -> None:
        from fastembed import TextEmbedding  # imported here so tests never load the real model

        self.model_name = model_name
        self._model = TextEmbedding(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts, batch_size=32)]

    def embed_query(self, text: str) -> list[float]:
        # bge models work best when short queries get their "search query" instruction prefix,
        # which query_embed adds.
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache
def get_embedder() -> Embedder:
    """One shared embedder (loading the model takes a second or two). Also a FastAPI dependency."""
    return FastEmbedder()
