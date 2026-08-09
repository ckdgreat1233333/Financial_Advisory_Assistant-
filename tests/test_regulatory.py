"""Tests for the Regulatory & Compliance Copilot (banking domain)."""
import json

import pytest

from models.regulatory import RegulatoryChunk, RetrievedChunk
from regulatory import confidence as conf
from regulatory.chunker import RegulatoryChunker
from regulatory.parsing import extract_json, sanitize_ascii
from services.regulatory_copilot import (
    CUSTOMER_NO_ANSWER,
    INTERNAL_NO_ANSWER,
    RegulatoryCopilot,
)


# ── Fixtures / fakes ──────────────────────────────────────────────

def make_chunk(doc_id, ref, text, title=None):
    return RegulatoryChunk(
        chunk_id=f"{doc_id}-{ref.replace('.', '_')}",
        text=text,
        clause_ref=ref,
        document_id=doc_id,
        title=title or doc_id,
        circular_no="RBI/TEST/01",
        issue_date="01-Jan-2026",
        version="v1.0",
    )


class FakeEmbedder:
    def __init__(self, sim=0.4):
        self.sim = sim

    def similarity(self, a, b):
        return self.sim


class FakeStore:
    def __init__(self, results, embedder_sim=0.4):
        self.results = results
        self.embedder = FakeEmbedder(embedder_sim)

    def retrieve(self, query, k=4):
        return self.results


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.called = False
        self.last_prompt = ""

    def generate(self, prompt, temperature=0.1, max_tokens=1400):
        self.called = True
        self.last_prompt = prompt
        return self.response


def build_copilot(store, llm):
    return RegulatoryCopilot(llm=llm, store=store)


# ── Chunker ───────────────────────────────────────────────────────

class TestChunker:

    def test_parses_header_metadata(self):
        text = (
            "Circular No: RBI/2025-26/09\n"
            "Date: 01-Aug-2025\n"
            "Subject: Master Direction - KYC\n"
            "Version: v1.0\n"
            "Category: circular\n\n"
            "1. Applicability\nThese directions apply to all banks.\n"
        )
        chunker = RegulatoryChunker()
        meta = chunker.parse_metadata(text)
        assert meta["circular_no"] == "RBI/2025-26/09"
        assert meta["issue_date"] == "01-Aug-2025"
        assert meta["title"] == "Master Direction - KYC"
        assert meta["version"] == "v1.0"
        assert meta["category"] == "circular"

    def test_splits_nested_clauses(self):
        text = (
            "1. Applicability\nIntro text.\n"
            "1.1 Customer Due Diligence\nVerify identity.\n"
            "1.2 Risk Based Approach\nClassify customers.\n"
            "2. Exceptions\nNone.\n"
        )
        chunks = RegulatoryChunker().parse_document("doc", "doc.txt", text)
        refs = [c.clause_ref for c in chunks]
        assert refs == ["1", "1.1", "1.2", "2"]

    def test_prose_dates_are_not_split(self):
        text = (
            "1. Retention\nRecords shall be preserved.\n"
            "No bank shall keep records for only 5 years from the date of transaction.\n"
        )
        chunks = RegulatoryChunker().parse_document("doc", "doc.txt", text)
        assert len(chunks) == 1
        assert chunks[0].clause_ref == "1"

    def test_chunk_carries_traceability_metadata(self):
        text = (
            "Circular No: RBI/2025-26/14\n"
            "Date: 15-Sep-2025\n"
            "Subject: Disclosure of Charges\n"
            "1. Disclosure\nBanks shall display a schedule of charges.\n"
        )
        chunks = RegulatoryChunker().parse_document("charges", "charges.txt", text)
        c = chunks[0]
        assert c.document_id == "charges"
        assert c.circular_no == "RBI/2025-26/14"
        assert c.issue_date == "15-Sep-2025"
        assert c.chunk_id == "charges-1"


# ── Parsing helpers ───────────────────────────────────────────────

class TestParsing:

    def test_extract_json_from_llm_text(self):
        raw = 'Sure! Here is your answer:\n\n{"answer": "x", "confidence": 0.8}\n\nHope this helps.'
        assert extract_json(raw)["answer"] == "x"

    def test_extract_json_empty(self):
        assert extract_json("") == {}
        assert extract_json("no json here") == {}

    def test_sanitize_ascii(self):
        assert sanitize_ascii("a\u2011b \u20b9100 \u201ccited\u201d") == "a-b Rs100 \"cited\""


# ── Confidence scoring ────────────────────────────────────────────

class TestConfidence:

    def test_retrieval_confidence_uses_top1(self):
        results = [
            RetrievedChunk(chunk=make_chunk("d", "1", "text"), similarity=0.8),
            RetrievedChunk(chunk=make_chunk("d", "2", "text"), similarity=0.5),
        ]
        assert conf.retrieval_confidence(results) == 0.8

    def test_retrieval_confidence_empty(self):
        assert conf.retrieval_confidence([]) == 0.0

    def test_combined_confidence_blend(self):
        assert conf.combined_confidence(0.8, 0.9) == round(0.6 * 0.8 + 0.4 * 0.9, 3)

    def test_confidence_levels(self):
        assert conf.confidence_level(0.9) == "High"
        assert conf.confidence_level(0.6) == "Medium"
        assert conf.confidence_level(0.3) == "Low"


# ── Copilot: internal track ───────────────────────────────────────

class TestInternalTrack:

    def test_grounded_answer_with_citations(self):
        chunk = make_chunk("rbi_kyc", "1.1", "Identity shall be verified using an officially valid document.")
        store = FakeStore([RetrievedChunk(chunk=chunk, similarity=0.8)], embedder_sim=0.3)
        llm = FakeLLM(json.dumps({
            "answer": "Identity is verified using an officially valid document.",
            "citations": [{"id": "ID:rbi_kyc-1_1", "clause": "1.1", "source": "KYC", "quote": "Identity shall be verified"}],
            "confidence": 0.9, "not_supported": False, "contradiction": False,
        }))
        answer = build_copilot(store, llm).answer_internal("How is identity verified?")
        assert answer.answered is True
        assert answer.confidence_level == "High"
        assert answer.needs_escalation is False
        assert len(answer.citations) == 1
        assert answer.citations[0].grounded is True
        assert llm.called is True

    def test_no_answer_below_retrieval_threshold(self):
        chunk = make_chunk("rbi_kyc", "1.1", "Identity shall be verified.")
        store = FakeStore([RetrievedChunk(chunk=chunk, similarity=0.3)])
        llm = FakeLLM("{}")
        answer = build_copilot(store, llm).answer_internal("What is the home loan rate?")
        assert answer.answered is False
        assert answer.answer == INTERNAL_NO_ANSWER
        assert answer.needs_escalation is True
        assert llm.called is False  # LLM must not be invoked below the retrieval floor

    def test_ungrounded_citation_escalates(self):
        chunk = make_chunk("rbi_kyc", "1.1", "Identity shall be verified.")
        store = FakeStore([RetrievedChunk(chunk=chunk, similarity=0.8)], embedder_sim=0.3)
        llm = FakeLLM(json.dumps({
            "answer": "The answer cites a fake clause.",
            "citations": [{"id": "ID:not_retrieved-99", "clause": "99", "source": "Fake", "quote": "nope"}],
            "confidence": 0.9, "not_supported": False, "contradiction": False,
        }))
        answer = build_copilot(store, llm).answer_internal("How is identity verified?")
        assert answer.answered is True
        assert answer.needs_escalation is True
        assert answer.citations[0].grounded is False

    def test_cross_document_conflict_escalates(self):
        chunk_a = make_chunk("master", "1.3", "KYC records updated every ten years.")
        chunk_b = make_chunk("amendment", "1", "KYC records updated every five years.")
        store = FakeStore(
            [RetrievedChunk(chunk=chunk_a, similarity=0.9), RetrievedChunk(chunk=chunk_b, similarity=0.8)],
            embedder_sim=0.81,
        )
        llm = FakeLLM(json.dumps({
            "answer": "KYC records are updated every ten years.",
            "citations": [{"id": "ID:master-1_3", "clause": "1.3", "source": "Master", "quote": "ten years"}],
            "confidence": 0.9, "not_supported": False, "contradiction": False,
        }))
        answer = build_copilot(store, llm).answer_internal("How often are KYC records updated?")
        assert answer.contradiction_detected is True
        assert answer.needs_escalation is True
        assert answer.escalation_reason is not None

    def test_not_supported_flag_returns_no_answer(self):
        chunk = make_chunk("rbi_kyc", "1.1", "Identity shall be verified.")
        store = FakeStore([RetrievedChunk(chunk=chunk, similarity=0.8)], embedder_sim=0.3)
        llm = FakeLLM(json.dumps({
            "answer": "", "citations": [], "confidence": 0.2,
            "not_supported": True, "contradiction": False,
        }))
        answer = build_copilot(store, llm).answer_internal("Anything here?")
        assert answer.answered is False
        assert answer.answer == INTERNAL_NO_ANSWER


# ── Copilot: customer track ───────────────────────────────────────

class TestCustomerTrack:

    def test_plain_language_answer_with_disclaimer(self):
        chunk = make_chunk("rbi_kyc", "1.1", "Identity verified using an officially valid document.")
        store = FakeStore([RetrievedChunk(chunk=chunk, similarity=0.8)], embedder_sim=0.3)
        llm = FakeLLM(json.dumps({
            "answer": "You just need one government-issued identity document.",
            "confidence": 0.85, "not_supported": False, "needs_human": False,
        }))
        answer = build_copilot(store, llm).answer_customer("What do I need to open an account?")
        assert answer.answered is True
        assert answer.disclaimer is not None
        assert answer.answer == "You just need one government-issued identity document."

    def test_needs_human_redirects(self):
        chunk = make_chunk("rbi_kyc", "1.1", "Identity verified.")
        store = FakeStore([RetrievedChunk(chunk=chunk, similarity=0.8)], embedder_sim=0.3)
        llm = FakeLLM(json.dumps({
            "answer": "This needs a bank official.", "confidence": 0.5,
            "not_supported": False, "needs_human": True,
        }))
        answer = build_copilot(store, llm).answer_customer("Am I entitled to compensation?")
        assert answer.answered is False
        assert answer.needs_escalation is True

    def test_no_answer_message(self):
        chunk = make_chunk("rbi_kyc", "1.1", "Identity verified.")
        store = FakeStore([RetrievedChunk(chunk=chunk, similarity=0.2)])
        llm = FakeLLM("{}")
        answer = build_copilot(store, llm).answer_customer("Home loan rate?")
        assert answer.answered is False
        assert answer.answer == CUSTOMER_NO_ANSWER


# ── Model serialization ───────────────────────────────────────────

class TestSerialization:

    def test_answer_to_dict(self):
        from models.regulatory import RegulatoryAnswer
        answer = RegulatoryAnswer(
            track="internal", question="q", answered=True, answer="a",
            retrieval_confidence=0.8, confidence=0.85, confidence_level="High",
        )
        payload = answer.to_dict()
        assert payload["track"] == "internal"
        assert payload["confidence"] == 0.85
        assert payload["citations"] == []


# ── Store integration (real embedding + faiss) ────────────────────

class TestStoreIntegration:
    """Builds a tiny store from a temp corpus to verify the ingest pipeline."""

    def test_ingest_and_retrieve(self, tmp_path):
        import faiss  # noqa: F401  (fail fast if faiss missing)
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        doc = (
            "Circular No: RBI/TEST/01\nDate: 01-Jan-2026\nSubject: Test Circular\n"
            "1. KYC Documents\nA passport is a valid identity document.\n"
            "1.1 Charges\nCharges shall be disclosed.\n"
            "2. Retention\nRecords kept for five years.\n"
        )
        (corpus / "test_circular.txt").write_text(doc, encoding="utf-8")

        from regulatory.store import RegulatoryKnowledgeStore
        store = RegulatoryKnowledgeStore(
            corpus_dir=str(corpus),
            index_path=str(tmp_path / "idx.bin"),
            meta_path=str(tmp_path / "chunks.json"),
            register=False,
        )
        assert store._ready is True
        assert len(store.chunks) == 3
        results = store.retrieve("What document is valid for identity?", k=2)
        assert len(results) >= 1
        assert results[0].similarity > 0.3
