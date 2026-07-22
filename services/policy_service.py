from pathlib import Path
import re

from rag.pipeline import RAGPipeline
from rag.chunker import PolicyChunker
from rag.embedder import PolicyEmbedder
from database.faiss_db import FAISSDatabase
from models.application import LoanApplication
from models.extracted_data import ExtractedData
from models.policy import PolicyResult, PolicyRules
from utils.enums import EligibilityStatus, RiskLevel
from typing import Optional


class PolicyParser:
    """Parses the loan policy document into structured rules."""

    def __init__(self, policy_path: str):
        self.policy_path = policy_path
        self.sections: dict[str, str] = {}
        self.section_numbers: dict[str, int] = {}
        self.min_salary: Optional[float] = None
        self.max_loan_multiplier: Optional[float] = None
        self.min_employment_months: Optional[int] = None
        self.min_age: Optional[int] = None
        self.max_age: Optional[int] = None
        self.required_documents: list[str] = []
        self.risk_rules: dict[RiskLevel, list[str]] = {}
        self.risk_condition_sections: dict[str, int] = {}
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
        """Infer which section a risk condition relates to by keyword overlap with section titles."""
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

        # Split on section boundaries with capturing groups
        # Result: [prefix, num1, title1, content1, num2, title2, content2, ...]
        raw_sections = re.split(r"={2,}\s*\n\s*Section\s+(\d+)\s*-\s*(.+?)\s*\n\s*={2,}", text)

        # Iterate: index 1 = section number, 2 = title, 3 = content, step by 3
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

        # Section 3 - Income Requirements
        sec = self.sections.get("Income Requirements", "")
        if sec:
            match = re.search(r"\u20b9([\d,]+)", sec)
            if match:
                self.min_salary = float(match.group(1).replace(",", ""))

        # Section 4 - Employment Requirements
        sec = self.sections.get("Employment Requirements", "")
        if sec:
            match = re.search(r"(\d+)\s*months", sec)
            if match:
                self.min_employment_months = int(match.group(1))

        # Section 5 - Loan Amount Rules
        sec = self.sections.get("Loan Amount Rules", "")
        if sec:
            match = re.search(r"(\d+)\s*times", sec)
            if match:
                self.max_loan_multiplier = float(match.group(1))

        # Section 1 - Eligibility
        sec = self.sections.get("Eligibility", "")
        if sec:
            age_match = re.search(r"between\s+(\d+)\s+and\s+(\d+)", sec)
            if age_match:
                self.min_age = int(age_match.group(1))
                self.max_age = int(age_match.group(2))

        # Section 6 - Risk Rules
        sec = self.sections.get("Risk Rules", "")
        if sec:
            current_level = None
            for line in sec.split("\n"):
                line = line.strip()
                if line == "Low Risk":
                    current_level = RiskLevel.LOW
                    self.risk_rules[current_level] = []
                elif line == "Medium Risk":
                    current_level = RiskLevel.MEDIUM
                    self.risk_rules[current_level] = []
                elif line == "High Risk":
                    current_level = RiskLevel.HIGH
                    self.risk_rules[current_level] = []
                elif line and current_level is not None:
                    self.risk_rules[current_level].append(line)
                    section_num = self._infer_section_for_condition(line)
                    if section_num is not None:
                        self.risk_condition_sections[line] = section_num


class PolicyService:
    """
    Handles policy retrieval using RAG and rule-based compliance checking.
    All rules are parsed from the actual policy document, never hardcoded.
    """

    def __init__(self, policy_file: str | None = None):
        self._pipeline_initialized = False
        self._pipeline = None
        self._policy_file = policy_file
        self._rules: Optional[PolicyParser] = None

    def _ensure_rules(self):
        if self._rules is None:
            base_dir = Path(__file__).resolve().parent.parent
            policy_path = self._policy_file or str(base_dir / "data" / "policies" / "home_loan_policy.txt")
            self._rules = PolicyParser(policy_path)

    def _ensure_pipeline(self):
        if not self._pipeline_initialized:
            self._pipeline = RAGPipeline(
                chunker=PolicyChunker(),
                embedder=PolicyEmbedder(),
                database=FAISSDatabase()
            )
            base_dir = Path(__file__).resolve().parent.parent
            policy_path = self._policy_file or str(base_dir / "data" / "policies" / "home_loan_policy.txt")
            index_dir = base_dir / "data" / "indexes"
            index_dir.mkdir(parents=True, exist_ok=True)
            index_path = str(index_dir / "faiss_index.bin")
            self._pipeline.build(policy_path, index_path)
            self._pipeline_initialized = True

    def retrieve_policy(
        self,
        query: str,
        top_k: int = 5,
    ):
        self._ensure_pipeline()
        return self._pipeline.retrieve(
            query=query,
            k=top_k,
        )

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> str:
        chunks = self.retrieve_policy(
            query,
            top_k,
        )
        return "\n\n".join(chunks)

    def _build_policy_query(self, application: LoanApplication, extracted_data: ExtractedData, missing_docs: list[str]) -> str:
        parts = [f"Loan type: {application.loan_type.value}"]
        salary = extracted_data.monthly_salary or application.monthly_salary
        if salary is not None:
            parts.append(f"Monthly salary: Rs.{salary:,.0f}")
        parts.append(f"Loan amount: Rs.{application.loan_amount:,.0f}")
        if missing_docs:
            parts.append(f"Missing documents: {', '.join(missing_docs)}")
        if extracted_data.employment_duration:
            parts.append(f"Employment duration: {extracted_data.employment_duration}")
        return "; ".join(parts)

    def get_rules_summary(self) -> dict:
        """Return parsed rules for inspection/debugging."""
        self._ensure_rules()
        return {
            "min_salary": self._rules.min_salary,
            "max_loan_multiplier": self._rules.max_loan_multiplier,
            "min_employment_months": self._rules.min_employment_months,
            "min_age": self._rules.min_age,
            "max_age": self._rules.max_age,
            "required_documents": self._rules.required_documents,
            "sections": list(self._rules.sections.keys()),
        }

    def check_compliance(
        self,
        application: LoanApplication,
        extracted_data: ExtractedData,
        missing_docs: list[str]
    ) -> PolicyResult:
        self._ensure_rules()
        violations = []
        policy_sections = []

        salary = extracted_data.monthly_salary or application.monthly_salary
        min_sal = self._rules.min_salary
        max_mult = self._rules.max_loan_multiplier
        min_emp = self._rules.min_employment_months

        if min_sal is not None and salary is not None and salary < min_sal:
            violations.append(f"Monthly salary Rs.{salary:,.0f} below minimum Rs.{min_sal:,.0f} (Section 3 - Income Requirements)")
            policy_sections.append("Section 3 - Income Requirements")

        loan_amount = application.loan_amount
        if max_mult is not None and salary is not None and salary > 0 and loan_amount > salary * max_mult:
            violations.append(f"Loan amount Rs.{loan_amount:,.0f} exceeds {int(max_mult)}x monthly salary (Section 5 - Loan Amount Rules)")
            policy_sections.append("Section 5 - Loan Amount Rules")

        if missing_docs:
            violations.append(f"Missing mandatory documents: {', '.join(missing_docs)} (Section 2 - Required Documents)")
            policy_sections.append("Section 2 - Required Documents")

        if min_emp is not None and extracted_data.employment_duration:
            year_match = re.search(r'(\d+)\s*(?:year|yr)s?', extracted_data.employment_duration, re.IGNORECASE)
            month_match = re.search(r'(\d+)\s*month', extracted_data.employment_duration, re.IGNORECASE)
            if year_match or month_match:
                total_months = 0
                if year_match:
                    total_months += int(year_match.group(1)) * 12
                if month_match:
                    total_months += int(month_match.group(1))
                if total_months < min_emp:
                    violations.append(f"Employment duration {total_months} months < {min_emp} months minimum (Section 4 - Employment Requirements)")
                    policy_sections.append("Section 4 - Employment Requirements")

        eligibility = EligibilityStatus.ELIGIBLE if not violations else EligibilityStatus.NOT_ELIGIBLE
        if missing_docs or (min_sal is not None and salary is not None and salary < min_sal):
            eligibility = EligibilityStatus.MANUAL_REVIEW

        retrieved_chunks = []
        retrieved_sources = []
        try:
            query = self._build_policy_query(application, extracted_data, missing_docs)
            retrieved_chunks = self.retrieve_policy(query, top_k=5)
            for chunk in retrieved_chunks:
                section_match = re.search(r'(Section\s+\d[\d\s\-–—]*?(?:Requirement|Rules|Limits|Eligibility|Condition|Policy)?)', chunk, re.IGNORECASE)
                if section_match:
                    src = section_match.group(1).strip()
                    if src not in retrieved_sources:
                        retrieved_sources.append(src)
                elif chunk[:60].strip() not in retrieved_sources:
                    retrieved_sources.append(chunk[:60].strip() + "...")
        except Exception:
            pass

        explanation = self._generate_structured_explanation(violations, policy_sections, eligibility)

        return PolicyResult(
            eligibility_status=eligibility,
            policy_sections=list(set(policy_sections)),
            violations=violations,
            explanation=explanation,
            confidence_score=0.95 if not violations else 0.7,
            retrieved_chunks=retrieved_chunks,
            retrieved_sources=retrieved_sources,
        )

    def _generate_structured_explanation(
        self,
        violations: list[str],
        policy_sections: list[str],
        eligibility: EligibilityStatus
    ) -> str:
        if not violations:
            return (
                "Compliance Result: All Clear\n"
                "------------------------------\n"
                "Violation: None\n"
                "Relevant Policy: All applicable policy sections satisfied\n"
                "Reason: All mandatory documents submitted, income verified, loan amount within limits, employment requirements met.\n"
                "Recommendation: Continue with loan processing."
            )

        lines = [
            "Compliance Result: Issues Found",
            "------------------------------",
        ]
        for i, violation in enumerate(violations, 1):
            section = policy_sections[i - 1] if i - 1 < len(policy_sections) else "General Policy"
            lines.append(f"\nViolation #{i}: {violation}")
            lines.append(f"Relevant Policy: {section}")
            lines.append(f"Recommendation: {'Upload missing documents' if 'Missing' in violation else 'Verify income details or contact officer'}")

        if eligibility == EligibilityStatus.MANUAL_REVIEW:
            lines.append("\nNote: Manual review is required per Section 7 - Manual Review Rules.")
        elif eligibility == EligibilityStatus.NOT_ELIGIBLE:
            lines.append("\nNote: Application does not meet minimum policy requirements.")

        return "\n".join(lines)
