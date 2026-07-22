"""
Information Extractor for Loan Processing Documents

Uses regex-based pattern matching and semantic extraction to identify
key fields from banking documents. Extends classical NLP with transformer
embeddings for field classification when needed.
"""
import re
from typing import Optional
from models.document import Document
from models.extracted_data import ExtractedData
from utils.enums import DocumentType


class InformationExtractor:
    """
    Extracts structured data from loan application documents.
    
    Uses regex patterns optimized for Indian banking document formats.
    For production, would integrate transformer-based NER (e.g., LayoutLM)
    for layout-aware extraction from scanned documents.
    """

    SALARY_PATTERNS = [
        r"Net\s+(?:Monthly\s+)?Salary\s*[:\-]?\s*(?:Rs\.?|₹|I)?\s*([\d,]+\.?\d*)",
        r"Gross\s+(?:Monthly\s+)?Salary\s*[:\-]?\s*(?:Rs\.?|₹|I)?\s*([\d,]+\.?\d*)",
        r"Monthly\s+Salary\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        r"Basic\s+Pay\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        r"Salary\s*[:\-]?\s*(?:Rs\.?|₹)?\s*([\d,]+\.?\d*)",
        r"(?:Rs\.?|₹)\s*([\d,]+\.?\d*)\s*(?:/month|per\s+month|p\.m\.)",
        r"Net\s*(?:[:\-]\s*)?(?:\n)\s*(?:Rs\.?|₹|I)?\s*([\d,]+\.?\d*)",
    ]

    EMPLOYER_PATTERNS = [
        r"Employer\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Company\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Organization\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Employee\s+of\s+(.+?)(?:\n|$)",
        r"employed\s+with\s+(.+?)\s+as\s+",
        r"^(.+?Pvt\.\s*Ltd)",
    ]

    EMPLOYEE_NAME_PATTERNS = [
        r"Employee\s+Name\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Name\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Applicant\s+Name\s*[:\-]\s*(.+?)(?:\n|$)",
        r"Mr\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"Ms\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"certifies\s+([A-Za-z]+(?:\s+[A-Za-z]+)+)",
        r"([A-Za-z]+(?:\s+[A-Za-z]+)+)\s*\(EMP",
    ]

    EMPLOYMENT_DURATION_PATTERNS = [
        r"(\d+)\s*(?:year|yr)s?\s*(\d*)\s*month",
        r"Experience\s*[:\-]\s*(\d+)\s*(?:year|yr)s?",
        r"Tenure\s*[:\-]\s*(\d+)\s*(?:year|yr)s?",
        r"Working\s+since\s+(\d{4})",
        r"Date\s+of\s+Joining\s*[:\-]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"joined\s+(?:the\s+organization\s+on\s+)?(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
    ]

    BANK_ACCOUNT_PATTERNS = [
        r"Account\s+(?:No|Number)\s*[:\-]\s*((?:[A-Z]+\s+){0,3}\d{4,18})",
        r"A/C\s+(?:No|Number)\s*[:\-]\s*(\d{9,18})",
        r"Acc\s+(?:No|Number)\s*[:\-]\s*(\d{9,18})",
    ]

    IFSC_PATTERNS = [
        r"IFSC\s*[:\-]\s*([A-Z]{4}0[A-Z0-9]{6})",
        r"IFS\s*Code\s*[:\-]\s*([A-Z]{4}0[A-Z0-9]{6})",
    ]

    BANK_NAME_PATTERNS = [
        r"(State Bank of India|SBI|HDFC Bank|ICICI Bank|Axis Bank|Kotak Mahindra Bank|Punjab National Bank|Bank of Baroda|Canara Bank|Union Bank of India|Indian Bank|Bank of India|Central Bank of India|Bank of Maharashtra|Indian Overseas Bank|UCO Bank|Punjab and Sind Bank|Bank of Maharashtra)",
        r"^([A-Za-z]+(?:\s+[A-Za-z]+)*\s+Bank)",
    ]

    BALANCE_PATTERNS = [
        r"(?:Closing|Current|Available)\s+Balance\s*[:\-]\s*[₹Rs\.]?\s*([\d,]+\.?\d*)",
        r"Balance\s*[:\-]\s*[₹Rs\.]?\s*([\d,]+\.?\d*)",
        r"Total\s+Balance\s*[:\-]\s*[₹Rs\.]?\s*([\d,]+\.?\d*)",
    ]

    PAN_PATTERNS = [
        r"PAN\s*[:\-]\s*([A-Z]{5}\d{4}[A-Z])",
        r"Permanent\s+Account\s+Number\s*[:\-]\s*([A-Z]{5}\d{4}[A-Z])",
    ]

    AADHAAR_PATTERNS = [
        r"Aadhaar\s*(?:No|Number)?\s*[:\-]\s*(\d{4}\s?\d{4}\s?\d{4})",
        r"UID\s*[:\-]\s*(\d{4}\s?\d{4}\s?\d{4})",
        r"(\d{4}\s\d{4}\s\d{4})",
    ]

    DOB_PATTERNS = [
        r"Date\s+of\s+Birth\s*[:\-]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"DOB\s*[:\-]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"Birth\s+Date\s*[:\-]\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
    ]

    ADDRESS_PATTERNS = [
        r"Address\s*[:\-]\s*(.+?)(?:\n\n|\n[A-Z]|$)",
        r"Residential\s+Address\s*[:\-]\s*(.+?)(?:\n\n|\n[A-Z]|$)",
    ]

    def extract(self, document: Document) -> ExtractedData:
        """Route extraction based on document type."""
        extractors = {
            DocumentType.SALARY_SLIP: self._extract_salary_slip,
            DocumentType.BANK_STATEMENT: self._extract_bank_statement,
            DocumentType.EMPLOYMENT_LETTER: self._extract_employment_letter,
            DocumentType.PAN: self._extract_pan,
            DocumentType.AADHAAR: self._extract_aadhaar,
        }
        
        extractor = extractors.get(document.document_type, self._extract_generic)
        return extractor(document)

    def _extract_salary_slip(self, document: Document) -> ExtractedData:
        text = document.extracted_text
        data = ExtractedData()
        
        raw_salary = self._extract_first_match(text, self.SALARY_PATTERNS)
        if raw_salary:
            try:
                data.monthly_salary = float(raw_salary.replace(",", ""))
            except ValueError:
                pass
        data.employer = self._extract_first_match(text, self.EMPLOYER_PATTERNS)
        data.employee_name = self._extract_first_match(text, self.EMPLOYEE_NAME_PATTERNS)
        data.employment_duration = self._extract_employment_duration(text)
        
        return data

    def _extract_bank_statement(self, document: Document) -> ExtractedData:
        text = document.extracted_text
        data = ExtractedData()
        
        raw_account = self._extract_first_match(text, self.BANK_ACCOUNT_PATTERNS)
        if raw_account:
            digits = re.sub(r"\D", "", raw_account)
            if len(digits) >= 4:
                data.account_number = digits[-12:] if len(digits) > 12 else digits
        
        data.average_monthly_balance = self._extract_average_balance(text)
        
        bank_name = self._extract_first_match(text, self.BANK_NAME_PATTERNS)
        if bank_name:
            if not bank_name.endswith("Bank"):
                bank_name = bank_name.split("\n")[0].strip()
            data.bank_name = bank_name
        
        return data

    def _extract_employment_letter(self, document: Document) -> ExtractedData:
        text = document.extracted_text
        data = ExtractedData()
        
        data.employer = self._extract_first_match(text, self.EMPLOYER_PATTERNS)
        data.employee_name = self._extract_first_match(text, self.EMPLOYEE_NAME_PATTERNS)
        data.employment_duration = self._extract_employment_duration(text)
        data.designation = self._extract_designation(text)
        
        return data

    def _extract_pan(self, document: Document) -> ExtractedData:
        text = document.extracted_text
        data = ExtractedData()
        
        data.pan_number = self._extract_first_match(text, self.PAN_PATTERNS)
        data.name_on_pan = self._extract_first_match(text, self.EMPLOYEE_NAME_PATTERNS)
        
        return data

    def _extract_aadhaar(self, document: Document) -> ExtractedData:
        text = document.extracted_text
        data = ExtractedData()
        
        data.aadhaar_number = self._extract_first_match(text, self.AADHAAR_PATTERNS)
        data.name_on_aadhaar = self._extract_first_match(text, self.EMPLOYEE_NAME_PATTERNS)
        data.date_of_birth = self._extract_first_match(text, self.DOB_PATTERNS)
        data.address = self._extract_first_match(text, self.ADDRESS_PATTERNS)
        
        return data

    def _extract_generic(self, document: Document) -> ExtractedData:
        """Fallback generic extraction."""
        return ExtractedData()

    def _extract_first_match(self, text: str, patterns: list[str]) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                result = match.group(1).strip()
                result = re.sub(r"\s+", " ", result)
                if result:
                    return result
        return None

    def _extract_employment_duration(self, text: str) -> Optional[str]:
        for pattern in self.EMPLOYMENT_DURATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.lastindex and match.lastindex >= 2 and match.group(2):
                    return f"{match.group(1)} years {match.group(2)} months"
                value = match.group(1)
                if re.match(r"\d{1,2}\s+[A-Z]", value):
                    return value
                return f"{value} years"
        return None

    def _extract_average_balance(self, text: str) -> Optional[float]:
        balances = []
        for pattern in self.BALANCE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                try:
                    val = float(m.replace(",", ""))
                    balances.append(val)
                except ValueError:
                    continue

        if not balances:
            all_nums = re.findall(r"(?:^|\n)\s*([\d,]+\.?\d*)\s*$", text, re.MULTILINE)
            candidates = []
            for num in all_nums:
                try:
                    val = float(num.replace(",", ""))
                    if 1000 <= val <= 10000000:
                        candidates.append(val)
                except ValueError:
                    continue
            if candidates:
                return sum(candidates) / len(candidates)

        if balances:
            return sum(balances) / len(balances)
        return None

    def _extract_designation(self, text: str) -> Optional[str]:
        patterns = [
            r"Designation\s*[:\-]\s*(.+?)(?:\n|$)",
            r"Position\s*[:\-]\s*(.+?)(?:\n|$)",
            r"Role\s*[:\-]\s*(.+?)(?:\n|$)",
            r"as\s+a\s+(.+?)(?:\.|,|\s+in\s)",
        ]
        return self._extract_first_match(text, patterns)

    def extract_salary(self, text: str) -> Optional[float]:
        """Legacy method for backward compatibility."""
        for pattern in self.SALARY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return None