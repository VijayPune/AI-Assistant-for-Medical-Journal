"""Hybrid retrieval orchestration and source-label assignment."""
from __future__ import annotations

from .store import SQLiteHybridStore, reciprocal_rank_fusion

def search(store: SQLiteHybridStore, query: str, *, embedding: list[float] | None = None,
          top_k: int = 6, filters: dict | None = None,
          allowed_roles: set[str] | None = None,
          minimum_semantic_similarity: float | None = None) -> list[dict]:
    if not query.strip():
        return []
    lexical = store.lexical_search(query, limit=80, filters=filters, allowed_roles=allowed_roles)
    semantic = store.vector_search(embedding, limit=80, filters=filters, allowed_roles=allowed_roles) if embedding else []
    if semantic and minimum_semantic_similarity is not None and semantic[0]["semantic_similarity"] < minimum_semantic_similarity:
        return []
    results = reciprocal_rank_fusion(lexical, semantic, top_k=top_k)
    for index, item in enumerate(results, start=1):
        item["source_label"] = f"S{index}"
    return results
