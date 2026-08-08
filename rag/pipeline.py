from pathlib import Path

from rag.chunker import PolicyChunker
from rag.embedder import PolicyEmbedder
from rag.retriever import PolicyRetriever
from database.faiss_db import FAISSDatabase


class RAGPipeline:

    def __init__(
        self,
        chunker: PolicyChunker,
        embedder: PolicyEmbedder,
        database: FAISSDatabase,
    ):
        self.chunker = chunker
        self.embedder = embedder
        self.database = database

        self.chunks: list[str] = []
        self.retriever: PolicyRetriever | None = None

    def build(
        self,
        policy_path: str,
        index_path: str,
    ):

        with open(
            policy_path,
            "r",
            encoding="utf-8",
        ) as file:
            policy = file.read()

        self.chunks = self.chunker.chunk(policy)

        index_file = Path(index_path)
        loaded = False

        if index_file.exists():
            self.database.load(index_path)

            if (
                self.database.index is not None
                and self.database.index.ntotal == len(self.chunks)
            ):
                loaded = True

        if not loaded:
            embeddings = self.embedder.embed(
                self.chunks
            )

            self.database.build(
                embeddings
            )

            self.database.save(
                index_path
            )

        self.retriever = PolicyRetriever(
            self.embedder,
            self.database,
            self.chunks,
        )

    def retrieve(
        self,
        query: str,
        k: int = 3,
    ) -> list[str]:

        if self.retriever is None:
            raise ValueError(
                "Pipeline has not been built."
            )

        return self.retriever.retrieve(
            query,
            k,
        )