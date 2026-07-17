from typing import List

from rag.embedder import PolicyEmbedder


class EmbeddingService:
    """
    Enterprise wrapper around the embedding model.

    This class hides the embedding implementation
    from the rest of the application.
    """

    def __init__(self):

        self.embedder = PolicyEmbedder()

    def generate_embedding(self, text: str):

        return self.embedder.embed([text])[0]

    def generate_embeddings(
        self,
        texts: List[str]
    ):

        return self.embedder.embed(texts)