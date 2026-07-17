from dataclasses import dataclass,field
from datetime import datetime
from utils.enums import EligibilityStatus
@dataclass(kw_only=True)
class PolicyResult:
    eligibility_status: EligibilityStatus
    policy_sections: list[str]
    violations: list[str]
    explanation: str
    confidence_score: float
    retrieved_chunks: list[str]
    evaluated_at: datetime = field(default_factory=datetime.now)
@dataclass(kw_only=True)
class PolicyRules:

    minimum_salary: int | None = None

    preferred_employment: list[str] = field(
        default_factory=list
    )

    required_documents: list[str] = field(
        default_factory=list
    )

    maximum_loan_multiplier: float | None = None

    manual_review_conditions: list[str] = field(
        default_factory=list
    )

    risk_conditions: list[str] = field(
        default_factory=list
    )