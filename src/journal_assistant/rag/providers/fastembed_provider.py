"""Local ONNX embeddings; document and query texts stay on this computer."""
from __future__ import annotations

from pathlib import Path

class EmbeddingModelNotReady(RuntimeError):
    """The local embedding runtime or model is unavailable."""

class FastEmbedProvider:
    def __init__(self, *, model_name: str, cache_directory: Path):
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise EmbeddingModelNotReady("Install the pinned fastembed package from requirements.txt.") from exc
        cache_directory.mkdir(parents=True, exist_ok=True)
        try:
            self.model = TextEmbedding(model_name=model_name, cache_dir=str(cache_directory))
        except Exception as exc:
            raise EmbeddingModelNotReady(f"Could not load local embedding model {model_name}: {exc}") from exc
        self.model_name = model_name

    def embed_documents(self, texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []
        return [vector.tolist() for vector in self.model.embed(texts, batch_size=batch_size)]

    def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            return []
        return next(vector.tolist() for vector in self.model.query_embed([query]))
