from rag.pipeline import RAGPipeline


class PolicyService:
    """
    Handles policy retrieval using RAG.

    No Agent should directly call the
    Retriever or Vector Store.
    """

    def __init__(self):

        self.pipeline = RAGPipeline()

    def retrieve_policy(
        self,
        query: str,
        top_k: int = 5,
    ):

        return self.pipeline.retrieve(
            query=query,
            k=top_k,
        )

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> str:

        chunks = self.retrieve_policy(
            query,
            top_k,
        )

        return "\n\n".join(chunks)