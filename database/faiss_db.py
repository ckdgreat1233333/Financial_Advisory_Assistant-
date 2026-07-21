class FAISSDatabase:

    def __init__(self):
        self.index = None
        try:
            import faiss
            self._available = True
        except ImportError:
            self._available = False

    def build(self, embeddings):
        if not self._available:
            raise ImportError("faiss is required for vector search. Install with: pip install faiss-cpu")
        import faiss
        import numpy as np
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype(np.float32))

    def search(self, query_embedding, k: int = 3):
        if self.index is None:
            raise ValueError("FAISS index has not been built or loaded.")
        import faiss
        import numpy as np
        k = min(k, self.index.ntotal)
        distances, indices = self.index.search(
            query_embedding.astype(np.float32),
            k,
        )
        return distances, indices

    def save(self, file_path: str):
        if self.index is None:
            raise ValueError("No FAISS index to save.")
        import faiss
        faiss.write_index(self.index, file_path)

    def load(self, file_path: str):
        if not self._available:
            raise ImportError("faiss is required for vector search. Install with: pip install faiss-cpu")
        import faiss
        self.index = faiss.read_index(file_path)

    def is_loaded(self) -> bool:
        return self.index is not None