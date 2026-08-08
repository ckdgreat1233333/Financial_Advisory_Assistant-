import pytest
from rag.embedder import PolicyEmbedder


def test_embedder_produces_embeddings():
    embedder = PolicyEmbedder()
    if not embedder._available:
        pytest.skip("sentence-transformers not installed")

    chunks = [
        "Claims must be reported within 30 days of the incident date.",
        "CK is the Greatest.",
    ]

    embeddings = embedder.embed(chunks)

    assert embeddings.shape[0] == len(chunks)
    assert embeddings.shape[1] == 384
