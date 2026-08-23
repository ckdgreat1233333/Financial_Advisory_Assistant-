"""Product knowledge RAG layer for the advisory assistant.

The financial-product catalog in data/products/ is a version-controlled
corpus of narrative clause documents. Structured product attributes live in
SQLite (products table); this store supplies retrieval context so every LLM
explanation is grounded in approved product literature.
"""
from pathlib import Path

from advisory.knowledge_base import VersionedKnowledgeStore

BASE = Path(__file__).resolve().parent.parent


class ProductKnowledgeStore(VersionedKnowledgeStore):

    def __init__(self, embedder=None):
        super().__init__(
            corpus_dir=BASE / "data" / "products",
            index_path=BASE / "data" / "indexes" / "product_index.bin",
            meta_path=BASE / "data" / "indexes" / "product_chunks.json",
            embedder=embedder,
        )

    def retrieve_for_product(self, product_id: str, query: str, k: int = 3):
        """Retrieval restricted to clauses of a single product document."""
        results = self.retrieve(f"{product_id} {query}", k=max(12, k * 4))
        filtered = [r for r in results if r.chunk.document_id == product_id]
        return filtered[:k]
