from rag.pipeline import RAGPipeline


class PolicyAgent:

    def __init__(
        self,
        pipeline: RAGPipeline,
    ):
        self.pipeline = pipeline

    def get_policy(
        self,
        query: str,
        k: int = 3,
    ) -> list[str]:

        return self.pipeline.retrieve(
            query=query,
            k=k,
        )

    def get_policy_text(
        self,
        query: str,
        k: int = 3,
    ) -> str:

        chunks = self.get_policy(
            query=query,
            k=k,
        )

        return "\n\n".join(chunks)