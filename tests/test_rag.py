from rag.chunker import PolicyChunker
 
with open("data/policies/home_loan_policy.txt", "r", encoding="utf-8") as file:
    policy = file.read()

chunker = PolicyChunker()

chunks = chunker.chunk(policy)

print(f"Total Chunks: {len(chunks)}")

for i, chunk in enumerate(chunks, start=1):
    print(f"\n----- Chunk {i} -----")
    print(chunk[:200])