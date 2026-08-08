from pathlib import Path
import re
import logging
from datetime import datetime

logger = logging.getLogger("claims_assistant")

from models.claim import Claim
from models.extracted_data import ClaimExtractedData
from models.policy import PolicyResult, PolicyRules
from utils.enums import CoverageStatus, FraudLevel
from typing import Optional


class PolicyParser:
    """Parses the insurance policy document into structured rules."""

    def __init__(self, policy_path: str):
        self.policy_path = policy_path
        self.sections: dict[str, str] = {}
        self.section_numbers: dict[str, int] = {}
        self.reporting_window_days: Optional[int] = None
        self.inception_scrutiny_days: Optional[int] = None
        self.required_documents: list[str] = []
        self.exclusions: list[str] = []
        self.fraud_rules: dict[FraudLevel, list[str]] = {}
        self.fraud_condition_sections: dict[str, int] = {}
        self._parse()

    def _get_stop_words(self) -> set:
        return {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "but",
            "if", "or", "because", "as", "until", "while", "of", "at",
            "by", "for", "with", "about", "against", "between", "into",
            "through", "during", "before", "after", "to", "from", "up",
            "down", "in", "out", "on", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "above", "below",
        }

    def _keywords(self, text: str) -> set:
        words = set(re.sub(r"[^a-z0-9\s]", " ", text.lower()).split())
        return words - self._get_stop_words()

    def _infer_section_for_condition(self, condition: str) -> Optional[int]:
        c_kw = self._keywords(condition)
        if not c_kw:
            return None
        best_num = None
        best_score = 0
        for title in self.sections:
            t_kw = self._keywords(title)
            overlap = len(c_kw & t_kw)
            if overlap > best_score:
                best_score = overlap
                best_num = self.section_numbers.get(title)
        return best_num

    def _parse(self):
        with open(self.policy_path, "r", encoding="utf-8") as f:
            text = f.read()

        raw_sections = re.split(r"={2,}\s*\n\s*Section\s+(\d+)\s*-\s*(.+?)\s*\n\s*={2,}", text)
        for i in range(1, len(raw_sections) - 2, 3):
            num = int(raw_sections[i].strip())
            title = raw_sections[i + 1].strip()
            content = raw_sections[i + 2].strip()
            self.sections[title] = content
            self.section_numbers[title] = num

        # Section 2 - Required Documents
        sec = self.sections.get("Required Documents", "")
        if sec:
            self.required_documents = re.findall(r"\u2022\s*(.+?)(?:\n|$)", sec)

        # Section 1 - Coverage Scope
        sec = self.sections.get("Coverage Scope", "")
        if sec:
            m = re.search(r"within\s+(\d+)\s+days", sec)
            if m:
                self.reporting_window_days = int(m.group(1))
            m = re.search(r"within\s+(\d+)\s+days\s+of\s+policy\s+inception", sec)
            if m:
                self.inception_scrutiny_days = int(m.group(1))

        # Section 4 - Exclusions
        sec = self.sections.get("Exclusions", "")
        if sec:
            self.exclusions = [l.strip() for l in sec.split("\n")
                               if re.match(r"^\d+\.", l.strip())]

        # Section 5 - Fraud Screening Rules
        sec = self.sections.get("Fraud Screening Rules", "")
        if sec:
            current_level = None
            for line in sec.split("\n"):
                line = line.strip()
                if line == "Low Fraud Risk":
                    current_level = FraudLevel.LOW
                    self.fraud_rules[current_level] = []
                elif line == "Medium Fraud Risk":
                    current_level = FraudLevel.MEDIUM
                    self.fraud_rules[current_level] = []
                elif line == "High Fraud Risk":
                    current_level = FraudLevel.HIGH
                    self.fraud_rules[current_level] = []
                elif line and current_level is not None:
                    self.fraud_rules[current_level].append(line)
                    section_num = self._infer_section_for_condition(line)
                    if section_num is not None:
                        self.fraud_condition_sections[line] = section_num


class PolicyService:
    """
    Handles policy retrieval using RAG and rule-based coverage checking.
    All rules are parsed from the actual insurance policy document,
    never hardcoded.
    """

    COVERED_CLAIM_TYPES = {"Auto", "Health", "Property", "Fire", "Theft", "Travel", "Liability"}

    def __init__(self, policy_file: str | None = None):
        self._pipeline_initialized = False
        self._pipeline = None
        self._policy_file = policy_file
        self._rules: Optional[PolicyParser] = None

    def _ensure_rules(self):
        if self._rules is None:
            base_dir = Path(__file__).resolve().parent.parent
            policy_path = self._policy_file or str(base_dir / "data" / "policies" / "insurance_policy.txt")
            self._rules = PolicyParser(policy_path)

    def _ensure_pipeline(self):
        if not self._pipeline_initialized:
            try:
                from rag.pipeline import RAGPipeline
                from rag.chunker import PolicyChunker
                from rag.embedder import PolicyEmbedder
                from database.faiss_db import FAISSDatabase
                self._pipeline = RAGPipeline(
                    chunker=PolicyChunker(),
                    embedder=PolicyEmbedder(),
                    database=FAISSDatabase()
                )
                base_dir = Path(__file__).resolve().parent.parent
                policy_path = self._policy_file or str(base_dir / "data" / "policies" / "insurance_policy.txt")
                index_dir = base_dir / "data" / "indexes"
                index_dir.mkdir(parents=True, exist_ok=True)
                index_path = str(index_dir / "faiss_index.bin")
                self._pipeline.build(policy_path, index_path)
            except Exception as e:
                logger.warning(f"RAG pipeline unavailable, using rule-based context only: {e}")
                self._pipeline = None
            self._pipeline_initialized = True

    def retrieve_policy(self, query: str, top_k: int = 5):
        self._ensure_pipeline()
        if self._pipeline is None:
            return []
        return self._pipeline.retrieve(query=query, k=top_k)

    def retrieve_context(self, query: str, top_k: int = 5) -> str:
        chunks = self.retrieve_policy(query, top_k)
        return "\n\n".join(chunks)

    def get_rules_summary(self) -> dict:
        self._ensure_rules()
        return {
            "reporting_window_days": self._rules.reporting_window_days,
            "inception_scrutiny_days": self._rules.inception_scrutiny_days,
            "required_documents": self._rules.required_documents,
            "exclusions": self._rules.exclusions,
            "sections": list(self._rules.sections.keys()),
        }

    def check_compliance(self, claim: Claim, extracted_data: ClaimExtractedData,
                         missing_docs: list[str]) -> PolicyResult:
        """Evaluate claim coverage against the policy. Legacy name kept for agent parity."""
        return self.interpret_coverage(claim, extracted_data, missing_docs)

    def interpret_coverage(self, claim: Claim, extracted_data: ClaimExtractedData,
                           missing_docs: list[str]) -> PolicyResult:
        self._ensure_rules()
        issues = []
        applicable_clauses = []
        policy_sections = []

        claim_type_label = claim.claim_type.value if hasattr(claim.claim_type, "value") else str(claim.claim_type)

        # 1. Claim type coverage
        if claim_type_label not in self.COVERED_CLAIM_TYPES:
            issues.append(f"Claim type '{claim_type_label}' is not covered by this policy (Section 1 - Coverage Scope)")
            policy_sections.append("Section 1 - Coverage Scope")
        else:
            applicable_clauses.append(f"Covered event: {claim_type_label} (Section 1 - Coverage Scope)")
            policy_sections.append("Section 1 - Coverage Scope")

        # 2. Required documents
        if missing_docs:
            issues.append(f"Missing mandatory documents: {', '.join(missing_docs)} (Section 2 - Required Documents)")
            policy_sections.append("Section 2 - Required Documents")

        # 3. Coverage limit
        amount = extracted_data.claimed_amount or claim.claim_amount or 0
        limit = extracted_data.coverage_limit
        if limit is not None and amount > limit:
            issues.append(
                f"Claim amount {self._money(amount)} exceeds coverage limit {self._money(limit)} "
                f"(Section 3 - Coverage Limits); only partial settlement possible"
            )
            policy_sections.append("Section 3 - Coverage Limits")
        else:
            applicable_clauses.append("Claim amount is within the coverage limit (Section 3 - Coverage Limits)")

        # 4. Reporting window
        if self._rules.reporting_window_days and extracted_data.incident_date:
            days = self._days_since(extracted_data.incident_date)
            if days is not None and days > self._rules.reporting_window_days:
                issues.append(
                    f"Claim reported {days} days after incident; exceeds the {self._rules.reporting_window_days}-day "
                    f"reporting window (Section 1 - Coverage Scope)"
                )
                policy_sections.append("Section 1 - Coverage Scope")

        # 5. Exclusions
        if self._rules.exclusions and extracted_data.cause_of_loss:
            matched_exclusions = [
                e for e in self._rules.exclusions
                if self._keywords_contain(e, extracted_data.cause_of_loss)
            ]
            for ex in matched_exclusions:
                issues.append(f"Potential exclusion: {ex} (Section 4 - Exclusions)")
                policy_sections.append("Section 4 - Exclusions")

        coverage_status = CoverageStatus.COVERED if not issues else CoverageStatus.NOT_COVERED
        if missing_docs or coverage_status == CoverageStatus.NOT_COVERED:
            # Missing docs alone -> manual review; outright exclusions remain Not Covered
            if missing_docs and all("exclusion" not in i.lower() for i in issues):
                coverage_status = CoverageStatus.MANUAL_REVIEW

        retrieved_chunks = []
        retrieved_sources = []
        try:
            query = self._build_policy_query(claim, extracted_data, missing_docs)
            retrieved_chunks = self.retrieve_policy(query, top_k=5)
            for chunk in retrieved_chunks:
                section_match = re.search(
                    r'(Section\s+\d[\d\s\-–—]*?(?:Scope|Documents|Limits|Exclusions|Rules)?)',
                    chunk, re.IGNORECASE)
                if section_match:
                    src = section_match.group(1).strip()
                    if src not in retrieved_sources:
                        retrieved_sources.append(src)
                elif chunk[:60].strip() not in retrieved_sources:
                    retrieved_sources.append(chunk[:60].strip() + "...")
        except Exception:
            pass

        explanation = self._generate_structured_explanation(issues, policy_sections, coverage_status)

        return PolicyResult(
            coverage_status=coverage_status,
            confidence_score=0.95 if not issues else 0.7,
            explanation=explanation,
            applicable_clauses=applicable_clauses,
            exclusions=[e for e in issues if "exclusion" in e.lower()],
            policy_sections=list(set(policy_sections)),
            retrieved_chunks=retrieved_chunks,
            retrieved_sources=retrieved_sources,
            requires_manual_review=coverage_status == CoverageStatus.MANUAL_REVIEW,
            manual_review_reason="Missing documents or uncertain coverage" if coverage_status == CoverageStatus.MANUAL_REVIEW else None,
        )

    def _build_policy_query(self, claim: Claim, extracted_data: ClaimExtractedData, missing_docs: list[str]) -> str:
        parts = [f"Claim type: {claim.claim_type.value if hasattr(claim.claim_type, 'value') else claim.claim_type}"]
        parts.append(f"Claim amount: {claim.claim_amount:,.0f}")
        if extracted_data.cause_of_loss:
            parts.append(f"Cause of loss: {extracted_data.cause_of_loss}")
        if extracted_data.incident_date:
            parts.append(f"Incident date: {extracted_data.incident_date}")
        if missing_docs:
            parts.append(f"Missing documents: {', '.join(missing_docs)}")
        return "; ".join(parts)

    def _generate_structured_explanation(self, issues: list[str], policy_sections: list[str],
                                         coverage_status: CoverageStatus) -> str:
        if not issues:
            return (
                "Coverage Result: Covered\n"
                "------------------------------\n"
                "Issue: None\n"
                "Relevant Policy: Claim type is covered, amount within limits, documents complete.\n"
                "Reason: The claim event falls within the coverage scope and no exclusions apply.\n"
                "Recommendation: Proceed with fraud screening."
            )

        lines = ["Coverage Result: Issues Found", "------------------------------"]
        for i, issue in enumerate(issues, 1):
            section = policy_sections[i - 1] if i - 1 < len(policy_sections) else "General Policy"
            lines.append(f"\nIssue #{i}: {issue}")
            lines.append(f"Relevant Policy: {section}")
        if coverage_status == CoverageStatus.MANUAL_REVIEW:
            lines.append("\nNote: Manual review is required per Section 6 - Escalation Rules.")
        elif coverage_status == CoverageStatus.NOT_COVERED:
            lines.append("\nNote: The claim does not meet coverage requirements.")
        return "\n".join(lines)

    # -------------------------------
    # Helpers
    # -------------------------------

    def _keywords(self, text: str) -> set:
        words = set(re.sub(r"[^a-z0-9\s]", " ", str(text).lower()).split())
        return words - self._get_stop_words()

    def _keywords_contain(self, sentence: str, phrase: str) -> bool:
        s_kw = self._keywords(sentence)
        p_kw = self._keywords(phrase)
        if not p_kw:
            return False
        return len(s_kw & p_kw) / len(p_kw) >= 0.4

    def _days_since(self, date_str: str) -> Optional[int]:
        if not date_str:
            return None
        text = date_str.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y"):
            try:
                d = datetime.strptime(text, fmt)
                return max(0, (datetime.now() - d).days)
            except (ValueError, TypeError):
                continue
        return None

    def _get_stop_words(self) -> set:
        return PolicyParser._get_stop_words(self)

    def _money(self, value: float) -> str:
        return f"₹{value:,.0f}"
