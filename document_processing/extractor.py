"""
Information Extractor for Insurance Claim Documents

Uses regex-based pattern matching and semantic extraction to identify
key fields from insurance claim documents.
"""
import re
from typing import Optional
from models.document import Document
from models.extracted_data import ClaimExtractedData
from utils.enums import DocumentType


class InformationExtractor:
    """
    Extracts structured data from insurance claim documents.
    """

    CLAIMANT_NAME_PATTERNS = [
        r"Claimant\s+Name\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"Policyholder\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"Insured\s+Name\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"^Insured\s*[:\-]?\s*(?!Signature)(\S+(?:\s+\S+)?)\s*$",
        r"Name\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"Mr\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"Ms\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"Mrs\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
    ]

    POLICY_NUMBER_PATTERNS = [
        r"Policy\s+(?:No|Number)\s*[:\-]?\s*([A-Za-z0-9\-/]+)",
        r"Policy\s*[:\-]?\s*([A-Za-z0-9\-/]+)",
        r"Certificate\s+(?:No|Number)\s*[:\-]?\s*([A-Za-z0-9\-/]+)",
    ]

    CLAIM_NUMBER_PATTERNS = [
        r"Claim\s+(?:No|Number)\s*[:\-]?\s*([A-Za-z0-9\-/]+)",
        r"Claim\s+Ref(?:erence)?\s*[:\-]?\s*([A-Za-z0-9\-/]+)",
    ]

    CLAIM_AMOUNT_PATTERNS = [
        r"Claim\s+(?:Amount|Value)\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
        r"Amount\s+Claimed\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
        r"Total\s+(?:Claimed|Claim)\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
        r"Amount\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
        r"(?:Rs\.?|₹|I|■)\s*([\d,]+\.?\d*)\s*(?:for|towards)?",
    ]

    INCIDENT_DATE_PATTERNS = [
        r"Date\s+of\s+(?:Incident|Loss|Accident)\s*[:\-]?\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"(?:Incident|Loss|Accident)\s+Date\s*[:\-]?\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4})",
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
    ]

    INCIDENT_LOCATION_PATTERNS = [
        r"(?:Incident|Loss|Accident)\s+Location\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Location\s+of\s+(?:Incident|Loss)\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Address\s*[:\-]\s*(.+?)(?:\n\n|\n[A-Z]|$)",
    ]

    LOSS_DESCRIPTION_PATTERNS = [
        r"Loss\s+Description\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z]|$)",
        r"Description\s+of\s+(?:Loss|Damage|Incident)\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z]|$)",
        r"Details\s+of\s+(?:Loss|Incident)\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z]|$)",
        r"Describe\s+the\s+(?:incident|loss)\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z]|$)",
        r"Claim\s+states\s+that\s*(.+?)(?:\n\n|\n[A-Z]|$)",
    ]

    CAUSE_OF_LOSS_PATTERNS = [
        r"Cause\s+of\s+(?:Loss|Damage|Incident)\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"Reason\s+for\s+Claim\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"Fire\s*[:\-]?\s*(\w+)",
        r"Theft\s*[:\-]?\s*(\w+)",
        r"Flood\s*[:\-]?\s*(\w+)",
        r"Accident\s*[:\-]?\s*(\w+)",
        r"^Cause\s*[:\-]?\s*(.+?)(?:\n|$)",
    ]

    REPORTED_AMOUNT_PATTERNS = [
        r"(?:Reported|Estimated|Assessed)\s+(?:Loss|Amount|Value)\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
        r"Damage\s+Value\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
        r"Market\s+Value\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
        r"Cost\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
    ]

    DIAGNOSIS_PATTERNS = [
        r"Diagnosis\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Condition\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Primary\s+Diagnosis\s*[:\-]\s*(.+?)(?:\n|$)",
    ]

    TREATMENT_COST_PATTERNS = [
        r"Treatment\s+(?:Cost|Expense|Charges)\s*[:\-]\s*(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        r"Hospital\s+(?:Bill|Charges|Expense)\s*[:\-]\s*(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        r"Total\s+Billed\s*[:\-]\s*(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        r"Bill\s+Amount\s*[:\-]\s*(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)",
    ]

    VEHICLE_PATTERNS = [
        r"Vehicle\s+(?:Registration|Reg\.?|No\.?)\s*[:\-]\s*([A-Za-z0-9\s\-]+?)(?:\n|$)",
        r"Reg\.?\s+No\.?\s*[:\-]\s*([A-Za-z0-9\s\-]+?)(?:\n|$)",
        r"Vehicle\s+(?:Make|Model)\s*[:\-]\s*(.+?)(?:\n|$)",
    ]

    POLICE_REPORT_PATTERNS = [
        r"Police\s+(?:Report|Station)\s*(?:No\.?)?\s*[:\-]\s*(.+?)(?:\n|$)",
        r"FIR\s+(?:No\.?|Number)\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Case\s+(?:No\.?|Number)\s*[:\-]\s*(.+?)(?:\n|$)",
    ]

    WITNESS_PATTERNS = [
        r"Witness(?:es)?\s*(?:Count|No\.?)?\s*[:\-]\s*(\d+)",
        r"Number\s+of\s+Witnesses\s*[:\-]\s*(\d+)",
    ]

    THIRD_PARTY_PATTERNS = [
        r"Third[- ]?Party\s+(?:Involved|Name)\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Other\s+Party\s*(?:Involved)?\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Towed\s*(?:to|by)\s*(.+?)(?:\n|$)",
    ]

    PROPERTY_PATTERNS = [
        r"Property\s+(?:Address|Location)\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Premises\s+Address\s*[:\-]\s*(.+?)(?:\n|$)",
    ]

    def extract(self, document: Document) -> ClaimExtractedData:
        """Route extraction based on document type."""
        extractors = {
            DocumentType.CLAIM_FORM: self._extract_claim_form,
            DocumentType.POLICY_DOCUMENT: self._extract_policy_document,
            DocumentType.PROOF_OF_LOSS: self._extract_proof_of_loss,
            DocumentType.MEDICAL_REPORT: self._extract_medical_report,
            DocumentType.POLICE_REPORT: self._extract_police_report,
            DocumentType.INVOICE_RECEIPT: self._extract_invoice,
            DocumentType.INCIDENT_REPORT: self._extract_incident_report,
        }

        extractor = extractors.get(document.document_type, self._extract_generic)
        return extractor(document)

    def _extract_claim_form(self, document: Document) -> ClaimExtractedData:
        text = document.extracted_text
        data = ClaimExtractedData()

        data.claimant_name = self._extract_first_match(text, self.CLAIMANT_NAME_PATTERNS)
        data.claim_number = self._extract_first_match(text, self.CLAIM_NUMBER_PATTERNS)
        data.policy_number = self._extract_first_match(text, self.POLICY_NUMBER_PATTERNS)
        data.incident_date = self._extract_date(text, self.INCIDENT_DATE_PATTERNS)
        data.incident_location = self._extract_first_match(text, self.INCIDENT_LOCATION_PATTERNS)
        data.loss_description = self._extract_first_match(text, self.LOSS_DESCRIPTION_PATTERNS)
        data.cause_of_loss = self._extract_first_match(text, self.CAUSE_OF_LOSS_PATTERNS)

        inception = self._extract_first_match(text, [
            r"Policy\s+Start\s*[:\-]?\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        ])
        if inception:
            data.policy_inception_date = self._normalize_date(inception)

        raw_amount = self._extract_first_match(text, self.CLAIM_AMOUNT_PATTERNS)
        if raw_amount:
            try:
                data.claimed_amount = float(raw_amount.replace(",", ""))
            except ValueError:
                pass

        return data

    def _extract_policy_document(self, document: Document) -> ClaimExtractedData:
        text = document.extracted_text
        data = ClaimExtractedData()

        data.policy_number = self._extract_first_match(text, self.POLICY_NUMBER_PATTERNS)
        data.claim_number = self._extract_first_match(text, self.CLAIM_NUMBER_PATTERNS)
        data.claimant_name = self._extract_first_match(text, self.CLAIMANT_NAME_PATTERNS)

        raw_limit = self._extract_first_match(text, self.TREATMENT_COST_PATTERNS + [
            r"(?:Contents?\s+Cover\s+)?Limit\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
            r"(?:Sum\s+Insured|Coverage\s+(?:Limit|Amount))\s*[:\-]?\s*(?:Rs\.?|₹|I|■)?\s*([\d,]+\.?\d*)",
        ])
        if raw_limit:
            try:
                data.coverage_limit = float(raw_limit.replace(",", ""))
            except ValueError:
                pass

        inception = self._extract_first_match(text, [
            r"(?:Policy|Date\s+of)\s+Inception\s*[:\-]?\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"Inception\s+Date\s*[:\-]?\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"Start\s+Date\s*[:\-]?\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"Policy\s+Start\s*[:\-]?\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"Policy\s+Period\s*[:\-]?\s*(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        ])
        if inception:
            data.policy_inception_date = self._normalize_date(inception)

        prior = self._extract_first_match(text, [
            r"Prior\s+Claims\s*[:\-]\s*(\d+)",
            r"No\.?\s+of\s+Prior\s+Claims\s*[:\-]\s*(\d+)",
        ])
        if prior:
            try:
                data.prior_claims = int(prior)
            except ValueError:
                pass

        return data

    def _extract_proof_of_loss(self, document: Document) -> ClaimExtractedData:
        text = document.extracted_text
        data = ClaimExtractedData()

        data.claim_number = self._extract_first_match(text, self.CLAIM_NUMBER_PATTERNS)
        data.policy_number = self._extract_first_match(text, self.POLICY_NUMBER_PATTERNS)
        data.claimant_name = self._extract_first_match(text, self.CLAIMANT_NAME_PATTERNS)
        data.loss_description = self._extract_first_match(text, self.LOSS_DESCRIPTION_PATTERNS)
        data.cause_of_loss = self._extract_first_match(text, self.CAUSE_OF_LOSS_PATTERNS)
        data.incident_date = self._extract_date(text, self.INCIDENT_DATE_PATTERNS)

        raw_reported = self._extract_first_match(text, self.REPORTED_AMOUNT_PATTERNS)
        if raw_reported:
            try:
                data.reported_amount = float(raw_reported.replace(",", ""))
            except ValueError:
                pass

        raw_claim = self._extract_first_match(text, self.CLAIM_AMOUNT_PATTERNS)
        if raw_claim:
            try:
                data.claimed_amount = float(raw_claim.replace(",", ""))
            except ValueError:
                pass

        witness = self._extract_first_match(text, self.WITNESS_PATTERNS)
        if witness:
            try:
                data.witness_count = int(witness)
            except ValueError:
                pass

        data.third_party_involved = self._extract_first_match(text, self.THIRD_PARTY_PATTERNS)

        return data

    def _extract_medical_report(self, document: Document) -> ClaimExtractedData:
        text = document.extracted_text
        data = ClaimExtractedData()

        data.claimant_name = self._extract_first_match(text, self.CLAIMANT_NAME_PATTERNS)
        data.diagnosis = self._extract_first_match(text, self.DIAGNOSIS_PATTERNS)

        raw_cost = self._extract_first_match(text, self.TREATMENT_COST_PATTERNS)
        if raw_cost:
            try:
                data.treatment_cost = float(raw_cost.replace(",", ""))
            except ValueError:
                pass

        raw_claim = self._extract_first_match(text, self.CLAIM_AMOUNT_PATTERNS)
        if raw_claim:
            try:
                data.claimed_amount = float(raw_claim.replace(",", ""))
            except ValueError:
                pass

        data.incident_date = self._extract_date(text, self.INCIDENT_DATE_PATTERNS)

        return data

    def _extract_police_report(self, document: Document) -> ClaimExtractedData:
        text = document.extracted_text
        data = ClaimExtractedData()

        data.loss_description = self._extract_first_match(text, self.LOSS_DESCRIPTION_PATTERNS)
        data.cause_of_loss = self._extract_first_match(text, self.CAUSE_OF_LOSS_PATTERNS)
        data.incident_date = self._extract_date(text, self.INCIDENT_DATE_PATTERNS)
        data.incident_location = self._extract_first_match(text, self.INCIDENT_LOCATION_PATTERNS)

        return data

    def _extract_invoice(self, document: Document) -> ClaimExtractedData:
        text = document.extracted_text
        data = ClaimExtractedData()

        raw_amount = self._extract_first_match(text, self.REPORTED_AMOUNT_PATTERNS)
        if raw_amount:
            try:
                data.reported_amount = float(raw_amount.replace(",", ""))
            except ValueError:
                pass

        return data

    def _extract_incident_report(self, document: Document) -> ClaimExtractedData:
        text = document.extracted_text
        data = ClaimExtractedData()

        data.loss_description = self._extract_first_match(text, self.LOSS_DESCRIPTION_PATTERNS)
        data.cause_of_loss = self._extract_first_match(text, self.CAUSE_OF_LOSS_PATTERNS)
        data.incident_date = self._extract_date(text, self.INCIDENT_DATE_PATTERNS)
        data.incident_location = self._extract_first_match(text, self.INCIDENT_LOCATION_PATTERNS)
        data.vehicle_registration = self._extract_first_match(text, self.VEHICLE_PATTERNS)
        data.property_address = self._extract_first_match(text, self.PROPERTY_PATTERNS)

        return data

    def _extract_generic(self, document: Document) -> ClaimExtractedData:
        """Fallback generic extraction."""
        return ClaimExtractedData()

    def _extract_first_match(self, text: str, patterns: list[str]) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                result = match.group(1).strip()
                result = re.sub(r"\s+", " ", result)
                if result:
                    return result
        return None

    def _extract_date(self, text: str, patterns: list[str]) -> Optional[str]:
        """Extract a date field and normalize it to yyyy-mm-dd when possible."""
        raw = self._extract_first_match(text, patterns)
        if raw:
            return self._normalize_date(raw)
        return None

    def _normalize_date(self, date_str: str) -> str:
        """Convert dd/mm/yyyy or dd-mmm-yyyy to yyyy-mm-dd when possible."""
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", date_str.strip())
        if m:
            d, mo, y = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        m = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", date_str.strip())
        if m:
            d, mo, y = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        m = re.match(r"^(\d{1,2})[-/]([A-Za-z]{3,9})[-/](\d{4})$", date_str.strip())
        if m:
            d, mon, y = m.groups()
            months = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
                "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
                "july": 7, "august": 8, "september": 9, "october": 10,
                "november": 11, "december": 12,
            }
            mo = months.get(mon.lower())
            if mo:
                return f"{y}-{mo:02d}-{int(d):02d}"
        return date_str
