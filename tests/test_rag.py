"""
RAG Pipeline Tests and ML/NLP Concepts Documentation

This file serves dual purposes:
1. Tests the RAG (Retrieval-Augmented Generation) pipeline functionality
2. Documents where ML and NLP concepts are used in the system

ML & NLP Concepts Used:
------------------------

1. **Vector Embeddings (Transformer-based)**
   - Type: SentenceTransformer 'all-MiniLM-L6-v2' 
   - Why Transformers over classical NLP:
     * Captures semantic meaning of entire sentences, not just keyword matching
     * Understands context and word relationships (e.g., "income" ≈ "salary" ≈ "earnings")
     * Can match queries to policies even when terminology differs
   - Used in: rag/embedder.py -> PolicyEmbedder.embed()

2. **Similarity Search (Cosine/L2 Distance via FAISS)**
   - Type: FAISS IndexFlatL2 (L2 distance for dense vector search)
   - Why not cosine similarity directly: FAISS L2 on normalized vectors is equivalent to cosine
   - Similarity score range: ~0 (identical) to ~2 (opposite vectors)
   - Used in: database/faiss_db.py -> FAISSDatabase.search()
   
3. **Text Classification (TF-IDF + Logistic Regression)**
   - Type: Intent Classification pipeline
   - Metrics: precision, recall, f1-score from sklearn.metrics.classification_report
   - Classes: POLICY_QUERY, DOCUMENT_PROCESSING, RISK_QUERY, APPLICATION_STATUS, GENERAL_QUERY
   - Why this approach: Fast, interpretable, works well with limited training data
   - Used in: ml/model.py -> IntentModelTrainer, ml/intent_classifier.py -> IntentClassifier

4. **Regex-based Information Extraction (Classical NLP)**
   - Pattern matching for structured fields from banking documents
   - Supplements transformer embeddings for high-precision field extraction
   - Used in: document_processing/extractor.py -> InformationExtractor

5. **Document Chunking Strategy**
   - Splits policy by section headers (Section N - Title)
   - Intelligent overlap to prevent context loss at boundaries
   - Used in: rag/chunker.py -> PolicyChunker
"""
import pytest
import os
import sys
from pathlib import Path

from rag.chunker import PolicyChunker
from rag.embedder import PolicyEmbedder
from rag.retriever import PolicyRetriever
from rag.pipeline import RAGPipeline
from database.faiss_db import FAISSDatabase
import numpy as np


class TestPolicyChunker:
    """Test document chunking strategy for RAG."""
    
    def setup_method(self):
        self.chunker = PolicyChunker()
    
    def test_chunks_by_section(self):
        policy_text = """
        Section 1 - Eligibility
        Applicant must be between 21 and 60 years of age.
        
        Section 2 - Required Documents
        Salary Slip (last 3 months)
        
        Section 3 - Income Requirements
        Minimum monthly salary: ₹30,000
        """
        
        chunks = self.chunker.chunk(policy_text)
        
        assert len(chunks) >= 3
        assert any("Section 1" in chunk for chunk in chunks)
        assert any("Section 2" in chunk for chunk in chunks)
        assert any("Section 3" in chunk for chunk in chunks)
    
    def test_only_sections_returned(self):
        policy_text = """
        Header
        Section 1 - Eligibility
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
    
    def test_embed_shape(self):
        chunks = [
            "Minimum salary is ₹30,000 per month.",
            "Required documents: Salary Slip, Bank Statement."
        ]
        
        embeddings = self.embedder.embed(chunks)
        
        # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        assert embeddings.shape == (2, 384)
        assert isinstance(embeddings, np.ndarray)
    
    def test_embed_query_shape(self):
        query = "What is the minimum salary?"
        
        embedding = self.embedder.embed_query(query)
        
        # Query embeddings should also be 384-dimensional
        assert embedding.shape == (1, 384)
    
    def test_similar_documents_have_similar_embeddings(self):
        """Semantic similarity: related queries should have similar embeddings.
        
        This demonstrates why Transformers outperform classical NLP approaches:
        - "salary" and "income" are semantically related and will have similar vectors
        - Classical keyword matching would miss this relationship entirely
        """
        chunks = [
            "Monthly salary requirement is ₹30,000",
            "Minimum income needed for loan is ₹30,000",
            "The sky is blue and the sun is bright"
        ]
        
        embeddings = self.embedder.embed(chunks)
        
        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms
        
        # Salary vs Income (should be more similar)
        salary_income_sim = np.dot(normalized[0], normalized[1])
        # Salary vs Unrelated (should be less similar)
        salary_unrelated_sim = np.dot(normalized[0], normalized[2])
        
        assert salary_income_sim > salary_unrelated_sim, (
            f"Salary-Income similarity ({salary_income_sim:.3f}) should be higher "
            f"than Salary-Unrelated similarity ({salary_unrelated_sim:.3f})"
        )


class TestFAISSDatabase:
    """Test FAISS vector database for similarity search."""
    
    def setup_method(self):
        self.db = FAISSDatabase()
    
    def test_build_and_search(self):
        # Create dummy embeddings (384-dim like MiniLM)
        embeddings = np.random.rand(5, 384).astype(np.float32)
        
        self.db.build(embeddings)
        
        # Search with a query vector
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
        
        assert new_db.is_loaded()
        
        query = np.random.rand(1, 384).astype(np.float32)
        distances, indices = new_db.search(query, k=3)
        
        assert distances.shape == (1, 3)


class TestRAGPipeline:
    """Test the complete Retrieval-Augmented Generation pipeline."""
    
    def setup_method(self):
        self.chunker = PolicyChunker()
        self.embedder = PolicyEmbedder()
        self.database = FAISSDatabase()
        self.pipeline = RAGPipeline(
            chunker=self.chunker,
            embedder=self.embedder,
            database=self.database
        )
    
    def test_build_and_retrieve(self):
        policy_path = Path(__file__).parent.parent / "data" / "policies" / "home_loan_policy.txt"
        
        if not policy_path.exists():
            pytest.skip(f"Policy file not found: {policy_path}")
        
        self.pipeline.build(
            policy_path=str(policy_path),
            index_path="database/indexes/test_home_loan.index"
        )
        
        retrieved = self.pipeline.retrieve("What is the minimum salary?", k=3)
        
        assert len(retrieved) >= 1
        assert len(retrieved) <= 3
        assert any("salary" in chunk.lower() or "income" in chunk.lower() for chunk in retrieved)
    
    def test_retrieve_policy_rules(self):
        policy_path = Path(__file__).parent.parent / "data" / "policies" / "home_loan_policy.txt"
        
        if not policy_path.exists():
            pytest.skip(f"Policy file not found: {policy_path}")
        
        self.pipeline.build(
            policy_path=str(policy_path),
            index_path="database/indexes/test_home_loan.index"
        )
        
        questions_and_expected = [
            ("What documents are needed for loan application?", "Section 2"),
            ("What happens if documents are missing?", "manual review"),
            ("What is the employment requirement?", "12 months"),
        ]
        
        for question, expected in questions_and_expected:
            retrieved = self.pipeline.retrieve(question, k=2)
            combined = " ".join(retrieved).lower()
            assert expected.lower() in combined, (
                f"Question '{question}' should retrieve content mentioning '{expected}'"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])