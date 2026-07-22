from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Optional, Any

from models.audit import AuditEntry
from models.document import Document
from models.risk import RiskAssessment
from models.policy import PolicyResult
from models.extracted_data import ExtractedData

from utils.enums import (
    ApplicationStatus,
    LoanType,
)


@dataclass(kw_only=True)
class LoanApplication:
    """
    Represents a complete loan application throughout the processing pipeline.

    This object is the single source of truth passed between the
    DocumentAgent, PolicyAgent, RiskAgent and CustomerAgent.
    """

    # ----------------------------
    # Applicant Information
    # ----------------------------
    application_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    customer_name: str
    customer_age: int
    customer_phone: str

    loan_type: LoanType
    loan_amount: float
    monthly_salary: float
    employment_type: str

    # ----------------------------
    # Processing Results
    # ----------------------------
    documents: list[Document] = field(default_factory=list)

    extracted_data: Optional[ExtractedData] = None

    policy: Optional[PolicyResult] = None

    risk: Optional[RiskAssessment] = None

    # ----------------------------
    # Workflow
    # ----------------------------
    application_status: ApplicationStatus

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
            and self.risk is not None
        )