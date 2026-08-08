"""
Fraud Case Semantic Similarity Engine.

Loads the synthetic historical fraud case corpus, embeds each case
narrative into a dedicated FAISS index, and scores incoming claims
for semantic similarity against known fraud patterns.

Thresholds (configurable):
    HIGH    >= 0.85
    MEDIUM  >= 0.70
    LOW     <  0.70

The thresholds are calibrated for content-based matching against the
current corpus. Because the corpus is small and all claims share the same
insurance domain, naive cosine scores cluster around 0.5 even for benign
claims; raising the thresholds above that band keeps benign claims LOW
while still catching narratives that genuinely resemble historical fraud.
"""
import os
import re
from pathlib import Path

import numpy as np

from models.fraud_case import FraudCase
from utils.enums import FraudLevel

HIGH_SIM_THRESHOLD = 0.85
MEDIUM_SIM_THRESHOLD = 0.70

BASE_DIR = Path(__file__).resolve().parent.parent
FRAUD_CASES_DIR = str(BASE_DIR / "data" / "fraud_cases")
FRAUD_INDEX_PATH = str(BASE_DIR / "data" / "indexes" / "fraud_index.bin")


class FraudCaseService:
    """
    Builds and queries the fraud case similarity index.
    """

    def __init__(self, cases_dir: str | None = None, index_path: str | None = None):
        self.cases_dir = cases_dir or FRAUD_CASES_DIR
        self.index_path = index_path or FRAUD_INDEX_PATH
        self.embedder = None
        self.database = None
        self.cases: list[FraudCase] = []
        self._built = False

    def _ensure_runtime(self):
        """Lazily construct the embedding + vector DB runtime (optional deps)."""
        if self.embedder is None:
            from rag.embedder import PolicyEmbedder
            from database.faiss_db import FAISSDatabase
            self.embedder = PolicyEmbedder()
            self.database = FAISSDatabase()

    # -------------------------------
    # Corpus Loading
    # -------------------------------

    def load_cases(self) -> list[FraudCase]:
        """Parse fraud case files into FraudCase objects."""
        cases = []
        if os.path.isdir(self.cases_dir):
            for fname in sorted(os.listdir(self.cases_dir)):
                if fname.endswith(".txt"):
                    cases.append(self._parse_case(os.path.join(self.cases_dir, fname)))
        self.cases = cases
        return cases

    def _parse_case(self, path: str) -> FraudCase:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        fields = {
            "CASE_ID": "FC-000",
            "CASE_TYPE": "Unknown",
            "FRAUD_LEVEL": "Medium",
            "FRAUD_INDICATORS": "",
            "RESOLUTION": "",
        }
        narrative = ""
        in_narrative = False
        narrative_lines = []
        for line in raw.splitlines():
            if line.startswith("NARRATIVE:"):
                in_narrative = True
                continue
            if in_narrative:
                narrative_lines.append(line)
                continue
            for key in fields:
                if line.startswith(key + ":"):
                    fields[key] = line.split(":", 1)[1].strip()
        narrative = "\n".join(narrative_lines).strip()
        level_map = {"Low": FraudLevel.LOW, "Medium": FraudLevel.MEDIUM, "High": FraudLevel.HIGH}
        indicators = [i.strip() for i in fields["FRAUD_INDICATORS"].split(";") if i.strip()]
        return FraudCase(
            case_id=fields["CASE_ID"],
            case_type=fields["CASE_TYPE"],
            fraud_level=level_map.get(fields["FRAUD_LEVEL"], FraudLevel.MEDIUM),
            narrative=narrative or " ".join(fields.values()),
            fraud_indicators=indicators,
            resolution=fields["RESOLUTION"],
        )

    # -------------------------------
    # Index Building
    # -------------------------------

    def build_index(self, force: bool = False) -> None:
        """Embed all fraud case narratives into a normalized FAISS index."""
        if not self.cases:
            self.load_cases()
        if not self.cases:
            self._built = False
            return

        index_file = Path(self.index_path)
        self._ensure_runtime()
        if index_file.exists() and not force:
            self.database.load(self.index_path)
        else:
            texts = [self._embedding_text(c) for c in self.cases]
            embeddings = self.embedder.embed(texts)
            embeddings = self._normalize(embeddings)
            self.database.build(embeddings)
            self.database.save(self.index_path)

        self._built = True

    def _embedding_text(self, case: FraudCase) -> str:
        """Compose the text used to embed a fraud case."""
        return (
            f"Claim type: {case.case_type}. "
            f"Fraud indicators: {'; '.join(case.fraud_indicators)}. "
            f"{case.narrative}"
        )

    # -------------------------------
    # Similarity Scoring
    # -------------------------------

    def score_claim(self, claim_text: str, top_k: int = 3,
                    claim_type: str | None = None) -> list[dict]:
        """
        Score an incoming claim narrative against the fraud corpus.

        Returns a list of dicts with case_id, similarity (0-1),
        fraud_level, and matched indicators. Only cases whose type
        matches the claim type are considered.
        """
        if not self._built:
            self.build_index()
        if not self._built or self.database.index is None:
            return []

        query_embedding = self.embedder.embed_query(claim_text)
        query_embedding = self._normalize(query_embedding)
        distances, indices = self.database.search(query_embedding, k=len(self.cases))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.cases):
                continue
            case = self.cases[idx]
            if claim_type and case.case_type.lower() != claim_type.lower():
                continue
            similarity = float(max(0.0, 1.0 - (dist ** 2) / 2.0))
            results.append({
                "case_id": case.case_id,
                "case_type": case.case_type,
                "fraud_level": case.fraud_level.value,
                "similarity": round(similarity, 3),
                "matched_indicators": case.fraud_indicators,
                "resolution": case.resolution,
                "narrative": case.narrative[:300],
            })
        return sorted(results, key=lambda r: r["similarity"], reverse=True)[:top_k]

    def _normalize(self, embeddings: np.ndarray) -> np.ndarray:
        embeddings = embeddings.astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return embeddings / norms

    def get_thresholds(self) -> dict:
        return {
            "high": HIGH_SIM_THRESHOLD,
            "medium": MEDIUM_SIM_THRESHOLD,
        }

    def classify_similarity(self, similarity: float) -> str:
        if similarity >= HIGH_SIM_THRESHOLD:
            return "High"
        if similarity >= MEDIUM_SIM_THRESHOLD:
            return "Medium"
        return "Low"
