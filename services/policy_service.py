from rag.pipeline import RAGPipeline
from rag.chunker import PolicyChunker
from rag.embedder import PolicyEmbedder
from database.faiss_db import FAISSDatabase
from models.application import LoanApplication
from models.extracted_data import ExtractedData
from models.policy import PolicyResult, PolicyRules
from utils.enums import EligibilityStatus
from typing import Optional


class PolicyService:
    """
    Handles policy retrieval using RAG and rule-based compliance checking.
    """

    MIN_SALARY = 30000
    MAX_LOAN_MULTIPLIER = 20
    REQUIRED_DOCS = [
        "Salary Slip",
        "Bank Statement",
        "Employment Letter",
        "PAN Card",
        "Aadhaar Card"
    ]

    def __init__(self):
        self._pipeline_initialized = False
        self._pipeline = None

    def _ensure_pipeline(self):
        if not self._pipeline_initialized:
            self._pipeline = RAGPipeline(
                chunker=PolicyChunker(),
                embedder=PolicyEmbedder(),
                database=FAISSDatabase()
            )
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

    def check_compliance(
        self,
        application: LoanApplication,
        extracted_data: ExtractedData,
        missing_docs: list[str]
    ) -> PolicyResult:
        violations = []
        policy_sections = []

        salary = extracted_data.monthly_salary or application.monthly_salary
        if salary is not None and salary < self.MIN_SALARY:
            violations.append(f"Monthly salary ₹{salary:,.0f} below minimum ₹{self.MIN_SALARY:,} (Section 3)")
            policy_sections.append("Section 3 - Income Requirements")

        loan_amount = application.loan_amount
        if salary is not None and loan_amount > salary * self.MAX_LOAN_MULTIPLIER:
            violations.append(f"Loan amount ₹{loan_amount:,.0f} exceeds {self.MAX_LOAN_MULTIPLIER}x salary (Section 5)")
            policy_sections.append("Section 5 - Loan Amount Rules")

        if missing_docs:
            violations.append(f"Missing mandatory documents: {', '.join(missing_docs)} (Section 2)")
            policy_sections.append("Section 2 - Required Documents")

        if extracted_data.employment_duration:
            import re
            year_match = re.search(r'(\d+)\s*(?:year|yr)s?', extracted_data.employment_duration, re.IGNORECASE)
            month_match = re.search(r'(\d+)\s*month', extracted_data.employment_duration, re.IGNORECASE)
            if year_match or month_match:
                total_months = 0
                if year_match:
                    total_months += int(year_match.group(1)) * 12
                if month_match:
                    total_months += int(month_match.group(1))
                if total_months < 12:
                    violations.append(f"Employment duration {total_months} months < 12 months minimum (Section 4)")
                    policy_sections.append("Section 4 - Employment Requirements")

        eligibility = EligibilityStatus.ELIGIBLE if not violations else EligibilityStatus.NOT_ELIGIBLE
        if missing_docs or (salary is not None and salary < self.MIN_SALARY):
            eligibility = EligibilityStatus.MANUAL_REVIEW

        explanation = self._generate_explanation(violations, policy_sections, eligibility)

        return PolicyResult(
            eligibility_status=eligibility,
            policy_sections=list(set(policy_sections)),
            violations=violations,
            explanation=explanation,
            confidence_score=0.95 if not violations else 0.7,
            retrieved_chunks=[],
        )

    def _generate_explanation(
        self,
        violations: list[str],
        policy_sections: list[str],
        eligibility: EligibilityStatus
    ) -> str:
        if not violations:
            return "Application complies with all policy requirements."

        if eligibility == EligibilityStatus.MANUAL_REVIEW:
            return f"Manual review required. Issues: {'; '.join(violations)}"

        return f"Policy violations found: {'; '.join(violations)}. Refer to sections: {', '.join(set(policy_sections))}."