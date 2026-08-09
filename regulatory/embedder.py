"""Embedder wrapper for regulatory text. Normalized embeddings so that L2
distance in the FAISS index maps directly to cosine similarity."""
import numpy as np


class _BaseEmbedder:

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self._available = True
        except ImportError:
            self._available = False
            self.model = None


class RegulatoryEmbedder(_BaseEmbedder):

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

    def similarity(self, text_a: str, text_b: str) -> float:
        """Cosine similarity between two texts (embeddings are normalized)."""
        if not self._available or self.model is None:
            return 0.0
        emb = self.model.encode(
            [text_a, text_b], convert_to_numpy=True, normalize_embeddings=True
        )
        return float(np.dot(emb[0], emb[1]))
