"""Shared embedding wrapper for the advisory assistant.

Normalized embeddings so that L2 distance in the FAISS index maps directly
to cosine similarity. A single MiniLM instance is shared across the product
knowledge store and customer segmentation.
"""
import numpy as np

_CACHED_MODEL = None
_CACHE_FAILED = False


def _get_model():
    global _CACHED_MODEL, _CACHE_FAILED
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL
    if _CACHE_FAILED:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _CACHED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        return _CACHED_MODEL
    except ImportError:
        _CACHE_FAILED = True
        return None


class Embedder:

    def __init__(self):
        self.model = _get_model()
        self._available = self.model is not None

    def embed(self, chunks: list[str]) -> np.ndarray:
        if not self._available or self.model is None:
            raise ImportError(
                "sentence-transformers is required for embedding. Install with: pip install sentence-transformers"
            )
        return self.model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        if not self._available or self.model is None:
            raise ImportError(
                "sentence-transformers is required for embedding. Install with: pip install sentence-transformers"
            )
        return self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
