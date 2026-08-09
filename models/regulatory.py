"""Data models for the Regulatory & Compliance Copilot (banking domain)."""
from dataclasses import dataclass, field


@dataclass
class RegulatoryDocument:
    """A versioned regulatory document (RBI circular, internal policy, audit checklist)."""
    doc_id: str
    title: str
    circular_no: str
    issue_date: str
    version: str
    file_path: str
    file_hash: str
    category: str = "circular"


@dataclass
class RegulatoryChunk:
    """A clause-level chunk of a regulatory document with full provenance metadata."""
    chunk_id: str
    text: str
    clause_ref: str
    document_id: str
    title: str
    circular_no: str
    issue_date: str
    version: str


@dataclass
class RetrievedChunk:
    """A retrieved chunk together with its similarity score."""
    chunk: RegulatoryChunk
    similarity: float


@dataclass
class Citation:
    """A citation attached to an answer, with grounding status."""
    chunk_id: str
    clause_ref: str
    source: str
    circular_no: str
    quote: str
    grounded: bool = True


@dataclass
class RegulatoryAnswer:
    """A structured, traceable copilot answer."""
    track: str
    question: str
    answered: bool
    answer: str
    citations: list[Citation] = field(default_factory=list)
    retrieved: list[RetrievedChunk] = field(default_factory=list)
    retrieval_confidence: float = 0.0
    answer_confidence: float = 0.0
    confidence: float = 0.0
    confidence_level: str = "Low"
    needs_escalation: bool = False
    escalation_reason: str | None = None
    contradiction_detected: bool = False
    disclaimer: str | None = None

    def to_dict(self, include_retrieved: bool = True) -> dict:
        return {
            "track": self.track,
            "question": self.question,
            "answered": self.answered,
            "answer": self.answer,
            "citations": [
                {
                    "chunk_id": c.chunk_id,
                    "clause_ref": c.clause_ref,
                    "source": c.source,
                    "circular_no": c.circular_no,
                    "quote": c.quote,
                    "grounded": c.grounded,
                }
                for c in self.citations
            ],
            "retrieved": (
                [
                    {
                        "chunk_id": r.chunk.chunk_id,
                        "clause_ref": r.chunk.clause_ref,
                        "source": r.chunk.title,
                        "circular_no": r.chunk.circular_no,
                        "version": r.chunk.version,
                        "similarity": round(r.similarity, 3),
                        "text": r.chunk.text,
                    }
                    for r in self.retrieved
                ]
                if include_retrieved
                else []
            ),
            "retrieval_confidence": self.retrieval_confidence,
            "answer_confidence": self.answer_confidence,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "needs_escalation": self.needs_escalation,
            "escalation_reason": self.escalation_reason,
            "contradiction_detected": self.contradiction_detected,
            "disclaimer": self.disclaimer,
        }
