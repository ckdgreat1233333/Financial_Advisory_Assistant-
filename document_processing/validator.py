from models.document import Document
from utils.enums import ValidationStatus, ValidationError, DocumentType
import re


class DocumentValidator:
    REQUIRED_FIELDS = {
        DocumentType.CLAIM_FORM: ["claimant_name", "policy_number", "claim_amount", "incident_date"],
        DocumentType.POLICY_DOCUMENT: ["policy_number", "coverage_limit"],
        DocumentType.PROOF_OF_LOSS: ["loss_description", "reported_amount"],
        DocumentType.MEDICAL_REPORT: ["diagnosis", "treatment_cost"],
        DocumentType.POLICE_REPORT: ["incident_date", "incident_location"],
        DocumentType.INCIDENT_REPORT: ["loss_description", "incident_date"],
    }

    def __init__(self):
        self.ocr_confidence_threshold = 0.75

    def validate(self, document: Document) -> Document:
        if document.validation_error in (ValidationError.PASSWORD_PROTECTED,
                                         ValidationError.CORRUPTED,
                                         ValidationError.OCR_FAILED):
            document.validation_status = ValidationStatus.INVALID
            return document

        if document.ocr_confidence and document.ocr_confidence < self.ocr_confidence_threshold:
            document.validation_status = ValidationStatus.INVALID
            document.validation_error = ValidationError.OCR_FAILED
            return document

        missing_fields = self._check_required_fields(document)
        if missing_fields:
            document.validation_status = ValidationStatus.INVALID
            document.metadata["missing_fields"] = missing_fields
            return document

        inconsistencies = self._check_consistency(document)
        if inconsistencies:
            document.metadata["inconsistencies"] = inconsistencies

        document.validation_status = ValidationStatus.VALID
        document.validation_error = ValidationError.NONE
        return document

    def _check_required_fields(self, document: Document) -> list[str]:
        required = self.REQUIRED_FIELDS.get(document.document_type, [])
        missing = []
        text_lower = document.extracted_text.lower()

        for field in required:
            if not self._field_exists_in_text(field, text_lower):
                missing.append(field)

        return missing

    def _field_exists_in_text(self, field: str, text: str) -> bool:
        field_patterns = {
            "claimant_name": [r"claimant", r"policyholder", r"insured", r"name"],
            "policy_number": [r"policy", r"certificate"],
            "claim_amount": [r"claim\s*(?:amount|value)?", r"amount\s+claimed", r"amount"],
            "incident_date": [r"incident", r"loss\s+date", r"accident", r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b"],
            "incident_location": [r"location", r"address", r"city", r"place"],
            "loss_description": [r"loss", r"description", r"incident", r"details"],
            "reported_amount": [r"reported", r"estimated", r"assessed", r"damage\s+value", r"amount"],
            "coverage_limit": [r"coverage", r"sum\s+insured", r"limit"],
            "diagnosis": [r"diagnosis", r"condition", r"treatment"],
            "treatment_cost": [r"treatment", r"hospital", r"bill", r"cost"],
        }

        patterns = field_patterns.get(field, [field.replace("_", " ")])
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _check_consistency(self, document: Document) -> list[str]:
        inconsistencies = []

        if document.document_type == DocumentType.CLAIM_FORM:
            amounts = re.findall(r"[₹rs\.?\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", document.extracted_text, re.IGNORECASE)
            if len(amounts) > 1:
                parsed = []
                for a in amounts:
                    try:
                        val = float(a.replace(",", ""))
                        if val > 0:
                            parsed.append(val)
                    except ValueError:
                        continue
                if len(parsed) > 1 and max(parsed) / min(parsed) > 2:
                    inconsistencies.append("Multiple claim amounts detected with large variance")

        if document.document_type == DocumentType.PROOF_OF_LOSS:
            desc_matches = re.findall(r"(?i)description\s*of\s*(?:loss|damage)", document.extracted_text)
            if not desc_matches:
                inconsistencies.append("Proof of loss missing loss description")

        return inconsistencies

    @staticmethod
    def is_confident(score: float, threshold: float = 0.75) -> bool:
        return score >= threshold
