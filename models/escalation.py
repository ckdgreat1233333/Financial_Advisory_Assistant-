from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from utils.enums import EscalationDecision, ClaimStatus


@dataclass(kw_only=True)
class EscalationDecision:
    """
    Final output of the Escalation Decision Agent.

    Combines the coverage interpretation (Policy Agent) and the
    fraud screening (Fraud Detection Agent) into a single decision
    about how to proceed — always keeping the final authority with
    a human claim officer.
    """

    decision: EscalationDecision

    confidence_score: float

    reasons: list[str] = field(default_factory=list)

    next_step: ClaimStatus = ClaimStatus.TRIAGE

    requires_human_review: bool = False

    # Human override support
    override_available: bool = True

    override_reason: Optional[str] = None

    generated_at: datetime = field(default_factory=datetime.now)

    # Decision rationale that officers can see
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "confidence_score": self.confidence_score,
            "reasons": self.reasons,
            "next_step": self.next_step.value if hasattr(self.next_step, "value") else self.next_step,
            "requires_human_review": self.requires_human_review,
            "override_available": self.override_available,
            "override_reason": self.override_reason,
            "generated_at": self.generated_at.isoformat(),
            "rationale": self.rationale,
        }
