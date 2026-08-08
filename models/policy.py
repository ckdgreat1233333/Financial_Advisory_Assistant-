from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from utils.enums import CoverageStatus


@dataclass(kw_only=True)
class PolicyResult:
    """
    Final output of the Policy Interpretation Agent.

    Contains both the coverage decision and all evidence used
    to reach that decision.
    """

    # ---------------------------------------------------------
    # Decision
    # ---------------------------------------------------------
    coverage_status: CoverageStatus

    confidence_score: float

    explanation: str

    # ---------------------------------------------------------
    # Coverage Details
    # ---------------------------------------------------------
    applicable_clauses: list[str] = field(default_factory=list)

    exclusions: list[str] = field(default_factory=list)

    policy_sections: list[str] = field(default_factory=list)

    # ---------------------------------------------------------
    # RAG Evidence
    # ---------------------------------------------------------
    retrieved_chunks: list[str] = field(default_factory=list)

    retrieved_sources: list[str] = field(default_factory=list)

    matched_clauses: list[str] = field(default_factory=list)

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
    Parsed insurance policy configuration.
    """

    minimum_policy_lapse_days: Optional[int] = None

    covered_events: list[str] = field(default_factory=list)

    exclusions: list[str] = field(default_factory=list)

    required_documents: list[str] = field(default_factory=list)

    coverage_limits: dict[str, float] = field(default_factory=dict)

    manual_review_conditions: list[str] = field(default_factory=list)

    fraud_conditions: list[str] = field(default_factory=list)
