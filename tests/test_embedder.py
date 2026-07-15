import time
from rag.embedder import PolicyEmbedder

start = time.time()

embedder = PolicyEmbedder()

chunks = [
    "Minimum salary is ₹30,000.",
    "CK is the Greatest.",
]

embeddings = embedder.embed(chunks)

end = time.time()

print(embeddings.shape)
print(f"Time: {end - start:.2f} seconds")