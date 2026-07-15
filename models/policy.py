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