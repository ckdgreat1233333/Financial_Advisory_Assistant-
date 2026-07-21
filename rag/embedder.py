class PolicyEmbedder:

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self._available = True
        except ImportError:
            self._available = False
            self.model = None

    def embed(self, chunks: list[str]):
        if not self._available:
            raise ImportError("sentence-transformers is required for embedding. Install with: pip install sentence-transformers")
        import numpy as np
        embeddings = self.model.encode(
            chunks,
            convert_to_numpy=True,
        )
        return embeddings

    def embed_query(self, query: str):
        if not self._available:
            raise ImportError("sentence-transformers is required for embedding. Install with: pip install sentence-transformers")
        import numpy as np
        embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
        )
        return embedding