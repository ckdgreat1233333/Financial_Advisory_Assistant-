"""
FAISS vector database for storing policy document embeddings.
"""
import faiss
import numpy as np
import os
from typing import List
class FAISSDatabase:
    """
    FAISS-based vector database for efficient similarity search of policy documents.
    """

    def __init__(self):
        self.index = None
        self.dimension = None
        self.database_path = os.path.join(os.path.dirname(__file__), 'faiss_index.bin')

    def build(self, embeddings: np.ndarray) -> None:
        """
        Build FAISS index from embeddings.

        Args:
            embeddings: NumPy array of embeddings to index
        """
        embeddings = embeddings.astype(np.float32)
        self.dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings)

    def search(self, query_embedding: np.ndarray, k: int = 3) -> tuple:
        """
        Search for nearest neighbors in the index.

        Args:
            query_embedding: Query embedding vector
            k: Number of neighbors to return

        Returns:
            Tuple of (distances, indices)
        """
        query_embedding = query_embedding.astype(np.float32)
        distances, indices = self.index.search(query_embedding, k)
        return distances, indices

    def load(self, index_path: str) -> None:
        """
        Load FAISS index from disk.

        Args:
            index_path: Path to the saved FAISS index file
        """
        try:
            self.index = faiss.read_index(index_path)
            print(f"Loaded FAISS index from {index_path}")
        except Exception as e:
            print(f"Failed to load FAISS index: {e}")
            self.index = None

    def save(self, index_path: str) -> None:
        """
        Save FAISS index to disk.

        Args:
            index_path: Path to save the FAISS index file
        """
        try:
            if self.index is not None:
                os.makedirs(os.path.dirname(index_path), exist_ok=True)
                self.index.write(index_path)
                print(f"Saved FAISS index to {index_path}")
        except Exception as e:
            print(f"Failed to save FAISS index: {e}")

    def add_embeddings(self, embeddings: np.ndarray) -> None:
        """
        Add embeddings to the FAISS index.

        Args:
            embeddings: NumPy array of embeddings to add
        """
        if self.index is not None:
            embeddings = embeddings.astype(np.float32)
            self.index.add(embeddings)
