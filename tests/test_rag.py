from rag.chunker import PolicyChunker
from rag.embedder import PolicyEmbedder
from rag.pipeline import RAGPipeline
from database.faiss_db import FAISSDatabase


chunker = PolicyChunker()
embedder = PolicyEmbedder()
database = FAISSDatabase()

pipeline = RAGPipeline(
    chunker=chunker,
    embedder=embedder,
    database=database,
)

pipeline.build(
    policy_path="data/policies/home_loan_policy.txt",
    index_path="database/indexes/home_loan.index",
)

questions = [
    "What is the minimum salary?",
    "What documents are required?",
    "How much loan can I apply for?",
    "Who needs manual review?",
    "What is the employment requirement?",
]

for question in questions:

    print("=" * 80)
    print(f"Question: {question}")
    print()

    results = pipeline.retrieve(
        question,
        k=3,
    )

    for i, result in enumerate(results, start=1):
        print(f"Result {i}")
        print(result)
        print("-" * 80)