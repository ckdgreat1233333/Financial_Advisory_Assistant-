"""
RAG Pipeline Tests and ML/NLP Concepts Documentation
"""
import pytest
import os
import tempfile
from pathlib import Path

from rag.chunker import PolicyChunker
from rag.embedder import PolicyEmbedder
from rag.retriever import PolicyRetriever
from rag.pipeline import RAGPipeline
from database.faiss_db import FAISSDatabase
import numpy as np


def has_faiss():
    try:
        import faiss
        return True
    except ImportError:
        return False


class TestPolicyChunker:
    """Test document chunking strategy for RAG."""

    def setup_method(self):
        self.chunker = PolicyChunker()

    def test_chunks_by_section(self):
        policy_text = """
        Section 1 - Coverage Scope
        The policy covers Auto, Health and Property claims.

        Section 2 - Required Documents
        Claim Form (signed), Policy Document, Proof of Loss

        Section 3 - Reporting Timeline
        Claims must be reported within 30 days.
        """

        chunks = self.chunker.chunk(policy_text)

        assert len(chunks) >= 3
        assert any("Section 1" in chunk for chunk in chunks)
        assert any("Section 2" in chunk for chunk in chunks)
        assert any("Section 3" in chunk for chunk in chunks)

    def test_only_sections_returned(self):
        policy_text = """
        Header
        Section 1 - Coverage Scope
        Content 1

        Section 2 - Required Documents
        Content 2
        """

        chunks = self.chunker.chunk(policy_text)

        for chunk in chunks:
            assert chunk.startswith("Section"), f"Chunk does not start with 'Section': {chunk[:50]}"


class TestPolicyEmbedder:
    """Test transformer-based embedding strategy."""

    def setup_method(self):
        self.embedder = PolicyEmbedder()
        if not self.embedder._available:
            pytest.skip("sentence-transformers not installed")

    def test_embed_shape(self):
        chunks = [
            "Claims must be reported within 30 days of the incident.",
            "Required documents: Claim Form, Policy Document, Proof of Loss."
        ]

        embeddings = self.embedder.embed(chunks)

        assert embeddings.shape == (2, 384)
        assert isinstance(embeddings, np.ndarray)

    def test_embed_query_shape(self):
        query = "What is the reporting window?"

        embedding = self.embedder.embed_query(query)

        assert embedding.shape == (1, 384)

    def test_similar_documents_have_similar_embeddings(self):
        chunks = [
            "Claims must be reported within 30 days",
            "Incidents must be reported within 30 days",
            "The sky is blue and the sun is bright"
        ]

        embeddings = self.embedder.embed(chunks)

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms

        reporting_incident_sim = np.dot(normalized[0], normalized[1])
        reporting_unrelated_sim = np.dot(normalized[0], normalized[2])

        assert reporting_incident_sim > reporting_unrelated_sim, (
            f"Reporting-Incident similarity ({reporting_incident_sim:.3f}) should be higher "
            f"than Reporting-Unrelated similarity ({reporting_unrelated_sim:.3f})"
        )


class TestFAISSDatabase:
    """Test FAISS vector database for similarity search."""

    def setup_method(self):
        if not has_faiss():
            pytest.skip("faiss-cpu not installed")
        self.db = FAISSDatabase()

    def test_build_and_search(self):
        embeddings = np.random.rand(5, 384).astype(np.float32)

        self.db.build(embeddings)

        query = np.random.rand(1, 384).astype(np.float32)
        distances, indices = self.db.search(query, k=3)

        assert distances.shape == (1, 3)
        assert indices.shape == (1, 3)
        assert all(0 <= idx < 5 for idx in indices[0])

    def test_save_and_load(self, tmp_path):
        embeddings = np.random.rand(5, 384).astype(np.float32)
        self.db.build(embeddings)

        index_path = tmp_path / "test.index"
        self.db.save(str(index_path))

        new_db = FAISSDatabase()
        new_db.load(str(index_path))

        assert new_db.index is not None

        query = np.random.rand(1, 384).astype(np.float32)
        distances, indices = new_db.search(query, k=3)

        assert distances.shape == (1, 3)


class TestRAGPipeline:
    """Test the complete Retrieval-Augmented Generation pipeline."""

    def setup_method(self):
        self.chunker = PolicyChunker()
        self.embedder = PolicyEmbedder()
        self.database = FAISSDatabase()
        if not self.embedder._available:
            pytest.skip("sentence-transformers not installed")
        self.pipeline = RAGPipeline(
            chunker=self.chunker,
            embedder=self.embedder,
            database=self.database
        )

    def test_build_and_retrieve(self):
        policy_path = Path(__file__).resolve().parent.parent / "data" / "policies" / "insurance_policy.txt"

        if not policy_path.exists():
            pytest.skip(f"Policy file not found: {policy_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "test_insurance.index")
            self.pipeline.build(
                policy_path=str(policy_path),
                index_path=index_path
            )

            retrieved = self.pipeline.retrieve("What is the reporting window?", k=3)

            assert len(retrieved) >= 1
            assert len(retrieved) <= 3

    def test_retrieve_policy_rules(self):
        policy_path = Path(__file__).resolve().parent.parent / "data" / "policies" / "insurance_policy.txt"

        if not policy_path.exists():
            pytest.skip(f"Policy file not found: {policy_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "test_insurance.index")
            self.pipeline.build(
                policy_path=str(policy_path),
                index_path=index_path
            )

            questions_and_expected = [
                ("What documents are required for a claim?", "Claim Form"),
                ("When must a claim be reported?", "30 days"),
                ("Which events are covered?", "Auto"),
            ]

            for question, expected in questions_and_expected:
                retrieved = self.pipeline.retrieve(question, k=2)
                combined = " ".join(retrieved).lower()
                assert expected.lower() in combined, (
                    f"Question '{question}' should retrieve content mentioning '{expected}'"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
