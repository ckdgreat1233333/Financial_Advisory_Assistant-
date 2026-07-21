from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Optional, Any
from models.audit import AuditEntry
from models.document import Document
from utils.enums import (
    ApplicationStatus,
    LoanType,
)
from models.risk import RiskAssessment
from models.policy import PolicyResult


@dataclass(kw_only=True)
class LoanApplication:
    application_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    customer_name: str
    customer_age: int
    customer_phone: str
    loan_type: LoanType
    loan_amount: float
    monthly_salary: float
    employment_type: str
    documents: list[Document] = field(default_factory=list)
    application_status: ApplicationStatus
    risk: Optional[RiskAssessment] = None
    policy: Optional[PolicyResult] = None
    audit_history: list[AuditEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)