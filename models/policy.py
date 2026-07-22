from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from utils.enums import EligibilityStatus


@dataclass(kw_only=True)
class PolicyResult:
    """
    Final output of the Policy Agent.

    Contains both the compliance decision and all evidence used
    to reach that decision.
    """

    # ---------------------------------------------------------
    # Decision
    # ---------------------------------------------------------
    eligibility_status: EligibilityStatus

    confidence_score: float

    explanation: str

    # ---------------------------------------------------------
    # Compliance Details
    # ---------------------------------------------------------
    violations: list[str] = field(default_factory=list)

    policy_sections: list[str] = field(default_factory=list)

    # ---------------------------------------------------------
    # RAG Evidence
    # ---------------------------------------------------------
    retrieved_chunks: list[str] = field(default_factory=list)

    retrieved_sources: list[str] = field(default_factory=list)

    matched_rules: list[str] = field(default_factory=list)

    supporting_evidence: list[str] = field(default_factory=list)

    # ---------------------------------------------------------
    # Recommendation
    # ---------------------------------------------------------
    requires_manual_review: bool = False

    manual_review_reason: Optional[str] = None

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------
    evaluated_at: datetime = field(default_factory=datetime.now)

    model_version: Optional[str] = None

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(kw_only=True)
class PolicyRules:
    """
    Parsed loan policy configuration.
    """

    minimum_salary: Optional[int] = None

    preferred_employment: list[str] = field(default_factory=list)

    required_documents: list[str] = field(default_factory=list)

    maximum_loan_multiplier: Optional[float] = None

    manual_review_conditions: list[str] = field(default_factory=list)

    risk_conditions: list[str] = field(default_factory=list)