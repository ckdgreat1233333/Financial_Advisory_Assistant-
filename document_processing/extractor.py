import re
from models.document import Document
from models.extracted_data import ExtractedData
class InformationExtractor:
    def extract_salary(self, text: str) -> float | None:
        salary_pattern = r"Monthly Salary\s*:\s*[₹Rs.\s]*([\d,]+)"
        match = re.search(salary_pattern, text, re.IGNORECASE)
        if not match:
            return None
        salary = match.group(1).replace(",", "")
        return float(salary)
    def extract(self, document: Document) -> ExtractedData:
        text = document.extracted_text
        data = ExtractedData()
        data.monthly_salary = self.extract_salary(text)
        return data