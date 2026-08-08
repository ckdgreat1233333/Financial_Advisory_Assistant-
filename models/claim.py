from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Optional, Any

from models.audit import AuditEntry
from models.document import Document
from models.fraud import FraudAssessment
from models.policy import PolicyResult
from models.extracted_data import ClaimExtractedData

from utils.enums import (
    ClaimStatus,
    ClaimType,
)


@dataclass(kw_only=True)
class Claim:
    """
    Represents a complete insurance claim throughout the processing pipeline.

    This object is the single source of truth passed between the
    DocumentAgent, PolicyInterpretationAgent, FraudDetectionAgent and
    EscalationDecisionAgent.
    """

    # ----------------------------
    # Claimant Information
    # ----------------------------
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    claimant_name: str
    claimant_email: str = ""
    claimant_phone: str = ""

    # ----------------------------
    # Policy & Claim Details
    # ----------------------------
    policy_number: str = ""

    claim_type: ClaimType
    claim_amount: float
    incident_date: Optional[str] = None

    loss_description: str = ""

    # ----------------------------
    # Processing Results
    # ----------------------------
    documents: list[Document] = field(default_factory=list)

    extracted_data: Optional[ClaimExtractedData] = None

    policy: Optional[PolicyResult] = None

    fraud: Optional[FraudAssessment] = None

    escalation: Optional[Any] = None

    # ----------------------------
    # Workflow
    # ----------------------------
    claim_status: ClaimStatus

    audit_history: list[AuditEntry] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)

    # ----------------------------
    # Runtime Metadata
    # ----------------------------
    metadata: dict[str, Any] = field(default_factory=dict)

    # ----------------------------
    # Human Review
    # ----------------------------
    needs_human_review: bool = False

    human_review_reason: Optional[str] = None

    # ----------------------------
    # Convenience Helper
    # ----------------------------
    @property
    def is_complete(self) -> bool:
        """
        Returns True when all AI stages have completed.
        """
        return (
            self.extracted_data is not None
            and self.policy is not None
            and self.fraud is not None
        )
