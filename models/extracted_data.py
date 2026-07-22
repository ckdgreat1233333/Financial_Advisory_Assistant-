from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass(kw_only=True)
class ExtractedData:
    """
    Structured information extracted from customer documents.

    This object is produced by the Document Agent and consumed by
    the Policy Agent and Risk Agent.
    """

    # ---------------------------------------------------------
    # Salary Slip
    # ---------------------------------------------------------
    monthly_salary: Optional[float] = None
    employer: Optional[str] = None
    employee_name: Optional[str] = None
    employment_duration: Optional[str] = None
    designation: Optional[str] = None

    # ---------------------------------------------------------
    # Bank Statement
    # ---------------------------------------------------------
    account_number: Optional[str] = None
    average_monthly_balance: Optional[float] = None
    bank_name: Optional[str] = None

    # ---------------------------------------------------------
    # PAN Card
    # ---------------------------------------------------------
    pan_number: Optional[str] = None
    name_on_pan: Optional[str] = None

    # ---------------------------------------------------------
    # Aadhaar Card
    # ---------------------------------------------------------
    aadhaar_number: Optional[str] = None
    name_on_aadhaar: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None

    # ---------------------------------------------------------
    # Explainability
    # ---------------------------------------------------------

    # Overall extraction confidence
    confidence_score: Optional[float] = None

    # OCR engine confidence (if available)
    ocr_confidence: Optional[float] = None

    # Which documents contributed to these values
    source_documents: list[str] = field(default_factory=list)

    # Optional field-level provenance
    field_sources: dict[str, str] = field(default_factory=dict)

    # Validation warnings generated during extraction
    validation_warnings: list[str] = field(default_factory=list)

    # Additional runtime metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """
        Returns True if the minimum information required for
        policy evaluation is available.
        """
        return (
            self.monthly_salary is not None
            and self.employee_name is not None
        )