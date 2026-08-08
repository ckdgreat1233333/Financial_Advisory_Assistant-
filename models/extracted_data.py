from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass(kw_only=True)
class ClaimExtractedData:
    """
    Structured information extracted from insurance claim documents.

    This object is produced by the Document Agent and consumed by
    the Policy Interpretation Agent and Fraud Detection Agent.
    """

    # ---------------------------------------------------------
    # Claim Form
    # ---------------------------------------------------------
    claimant_name: Optional[str] = None
    claim_number: Optional[str] = None
    policy_number: Optional[str] = None
    claim_type: Optional[str] = None
    incident_date: Optional[str] = None
    incident_location: Optional[str] = None
    claimed_amount: Optional[float] = None
    loss_description: Optional[str] = None

    # ---------------------------------------------------------
    # Proof of Loss / Incident Report
    # ---------------------------------------------------------
    reported_amount: Optional[float] = None
    cause_of_loss: Optional[str] = None
    third_party_involved: Optional[str] = None
    witness_count: Optional[int] = None

    # ---------------------------------------------------------
    # Medical / Vehicle / Property (type specific)
    # ---------------------------------------------------------
    diagnosis: Optional[str] = None
    treatment_cost: Optional[float] = None
    vehicle_registration: Optional[str] = None
    property_address: Optional[str] = None

    # ---------------------------------------------------------
    # Prior claim context (from policy documents)
    # ---------------------------------------------------------
    prior_claims: Optional[int] = None
    policy_inception_date: Optional[str] = None
    coverage_limit: Optional[float] = None

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
            self.claimant_name is not None
            and self.claimed_amount is not None
            and self.loss_description is not None
        )
