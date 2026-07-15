from dataclasses import dataclass,field
from utils.enums import RiskLevel,Recommendation
from datetime import datetime
@dataclass(kw_only=True)
class RiskAssessment:
    risk_level: RiskLevel
    confidence_score: float
    reasons: list[str]
    recommendation: Recommendation
    generated_at: datetime = field(default_factory=datetime.now)