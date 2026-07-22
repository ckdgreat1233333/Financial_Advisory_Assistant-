from models.document import Document
from utils.enums import ValidationStatus, ValidationError, DocumentType
import re


class DocumentValidator:
    REQUIRED_FIELDS = {}

    def __init__(self):
        self.ocr_confidence_threshold = 0.75

    def validate(self, document: Document) -> Document:
        if document.validation_error == ValidationError.PASSWORD_PROTECTED:
            document.validation_status = ValidationStatus.INVALID
            return document

        if document.validation_error == ValidationError.CORRUPTED:
            document.validation_status = ValidationStatus.INVALID
            return document

        if document.validation_error == ValidationError.OCR_FAILED:
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
            "employee_name": [r"name", r"employee", r"employed", r"certifies", r"emp\s*\d+", r"\w+\s+\w+\s*\(emp"],
            "employer": [r"employer", r"company", r"organization", r"pvt\.?\s*ltd", r"technologies", r"ltd", r"corp"],
            "monthly_income": [r"salary", r"income", r"pay", r"₹", r"rs\.?\s*\d"],
            "salary_period": [r"month", r"period", r"date", r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", r"\d{4}"],
            "account_number": [r"account\s*(?:no|number|#|:)", r"a/c\s*(?:no|number)", r"acc\s*(?:no|number)"],
            "bank_name": [r"bank", r"state bank", r"hdfc", r"icici", r"axis", r"kotak"],
            "account_holder": [r"account\s*holder", r"holder\s*name", r"name"],
            "transactions": [r"transaction", r"debit", r"credit", r"balance"],
            "employment_duration": [r"duration", r"experience", r"year", r"month", r"since", r"joined"],
            "designation": [r"designation", r"position", r"role", r"title", r"engineer", r"manager", r"analyst", r"consultant"],
            "pan_number": [r"pan", r"permanent\s*account"],
            "name_on_pan": [r"name"],
            "aadhaar_number": [r"aadhaar", r"uid"],
            "name_on_aadhaar": [r"name"],
            "date_of_birth": [r"dob", r"date\s*of\s*birth", r"birth\s*date"],
            "address": [r"address", r"residential"]
        }

        patterns = field_patterns.get(field, [field.replace("_", " ")])
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _check_consistency(self, document: Document) -> list[str]:
        inconsistencies = []

        if document.document_type == DocumentType.SALARY_SLIP:
            salary_matches = re.findall(r"[₹rs\.?\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", document.extracted_text, re.IGNORECASE)
            if len(salary_matches) > 1:
                amounts = [float(s.replace(",", "")) for s in salary_matches if float(s.replace(",", "")) > 0]
                if len(amounts) > 1 and max(amounts) / min(amounts) > 2:
                    inconsistencies.append("Multiple salary amounts detected with large variance")

        if document.document_type == DocumentType.BANK_STATEMENT:
            balance_matches = re.findall(r"balance[:\s]*[₹rs\.?\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", document.extracted_text, re.IGNORECASE)
            if len(balance_matches) > 1:
                balances = [float(b.replace(",", "")) for b in balance_matches]
                if any(b < 0 for b in balances):
                    inconsistencies.append("Negative balance detected in statement")

        return inconsistencies

    @staticmethod
    def is_confident(score: float, threshold: float = 0.75) -> bool:
        return score >= threshold