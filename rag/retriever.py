from rag.embedder import PolicyEmbedder
from database.faiss_db import FAISSDatabase


class PolicyRetriever:

    def __init__(
        self,
        embedder: PolicyEmbedder,
        database: FAISSDatabase,
        chunks: list[str],
    ):
        self.embedder = embedder
        self.database = database
        self.chunks = chunks

    def retrieve(
        self,
        query: str,
        k: int = 3,
    ) -> list[str]:

        query_embedding = self.embedder.embed_query(query)

        _, indices = self.database.search(
            query_embedding,
            k,
        )

        return [
            self.chunks[index]
            for index in indices[0]
        ]