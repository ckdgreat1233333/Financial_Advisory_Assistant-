"""Confidence scoring, thresholds, and cross-chunk validation controls.

These thresholds are single-source-of-truth constants so the copilot's
behaviour ("no answer" vs answer vs escalate) is explicit and explainable.

Calibration note: similarities are cosine scores on normalized MiniLM
embeddings. Relevant regulatory clauses typically score 0.5-0.8 against a
well-formed query; unrelated content sits well below 0.4.
"""
from models.regulatory import RetrievedChunk

# Below this top-1 similarity we do NOT call the LLM at all. Silence is
# better than hallucination: the user gets "Information not found".
NO_ANSWER_SIM_THRESHOLD = 0.45

# Below this combined confidence the answer is escalated to a human reviewer.
ESCALATE_CONFIDENCE_THRESHOLD = 0.55

# At/above this combined confidence the answer is delivered with confidence.
CONFIDENT_THRESHOLD = 0.75

# Pairwise-similarity band across *different* documents that we treat as a
# possible contradiction -> escalate instead of auto-answering. Kept narrow
# to avoid false positives on clauses that merely share a topic.
CONFLICT_LOW = 0.70
CONFLICT_HIGH = 0.95


def retrieval_confidence(top: list[RetrievedChunk]) -> float:
    """Confidence derived purely from retrieval (top-1 similarity)."""
    if not top:
        return 0.0
    return round(float(top[0].similarity), 3)


def combined_confidence(retrieval_conf: float, llm_conf: float | None) -> float:
    """Blend retrieval confidence with the LLM's self-assessed confidence."""
    if llm_conf is None or retrieval_conf <= 0:
        return round(float(retrieval_conf), 3)
    return round(0.6 * float(retrieval_conf) + 0.4 * float(llm_conf), 3)


def confidence_level(conf: float) -> str:
    if conf >= CONFIDENT_THRESHOLD:
        return "High"
    if conf >= ESCALATE_CONFIDENCE_THRESHOLD:
        return "Medium"
    return "Low"


def detect_conflicts(chunks: list[RetrievedChunk], embedder) -> list[tuple[str, str, float]]:
    """Cross-check retrieved chunks for possible contradictions.

    Two chunks from *different* documents whose similarity falls in the
    conflict band are flagged. High similarity usually means they agree;
    moderate-high similarity with different wording/sources is the risky zone
    where a human should adjudicate rather than the AI picking one side.
    """
    conflicts: list[tuple[str, str, float]] = []
    if len(chunks) < 2:
        return conflicts
    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            a = chunks[i].chunk
            b = chunks[j].chunk
            if a.document_id == b.document_id:
                continue
            sim = embedder.similarity(a.text, b.text)
            if CONFLICT_LOW <= sim <= CONFLICT_HIGH:
                conflicts.append((a.chunk_id, b.chunk_id, round(sim, 3)))
    return conflicts
