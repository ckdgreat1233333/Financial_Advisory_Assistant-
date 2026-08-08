from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from utils.enums import FraudLevel


@dataclass(kw_only=True)
class FraudCase:
    """
    A historical fraud case used for semantic matching.

    Each case carries a narrative description that is embedded into
    a dedicated FAISS index. Incoming claims are matched against this
    index to surface pattern similarities.
    """

    case_id: str

    case_type: str

    fraud_level: FraudLevel

    narrative: str

    fraud_indicators: list[str] = field(default_factory=list)

    resolution: str = ""

    created_at: datetime = field(default_factory=datetime.now)

    metadata: dict = field(default_factory=dict)
