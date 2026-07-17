import faiss
import numpy as np


class FAISSDatabase:

    def __init__(self):
        self.index = None

    def build(
        self,
        embeddings: np.ndarray,
    ):

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(dimension)

        self.index.add(
            embeddings.astype(np.float32)
        )

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 3,
    ):

        if self.index is None:
            raise ValueError(
                "FAISS index has not been built or loaded."
            )

        k = min(k, self.index.ntotal)

        distances, indices = self.index.search(
            query_embedding.astype(np.float32),
            k,
        )

        return distances, indices

    def save(
        self,
        file_path: str,
    ):

        if self.index is None:
            raise ValueError(
                "No FAISS index to save."
            )

        faiss.write_index(
            self.index,
            file_path,
        )

    def load(
        self,
        file_path: str,
    ):

        self.index = faiss.read_index(
            file_path
        )

    def is_loaded(self) -> bool:

        return self.index is not None