from sentence_transformers import SentenceTransformer
import numpy as np


class PolicyEmbedder:

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(self, chunks: list[str]) -> np.ndarray:
        embeddings = self.model.encode(
            chunks,
            convert_to_numpy=True,
        )

        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
        )

        return embedding