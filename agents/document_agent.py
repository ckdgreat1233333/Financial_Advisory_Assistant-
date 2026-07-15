import os

from document_processing.pdf_reader import PDFReader
from document_processing.validator import DocumentValidator
from document_processing.extractor import InformationExtractor

from models.document import Document
from models.extracted_data import ExtractedData

from utils.enums import (
    ValidationStatus,
    ValidationError,
    DocumentType,
)


class DocumentAgent:

    def __init__(self):
        self.reader = PDFReader()
        self.validator = DocumentValidator()
        self.extractor = InformationExtractor()

    def process(
        self,
        file_path: str,
        document_type: DocumentType,
    ) -> tuple[Document, ExtractedData | None]:

        text = self.reader.read(file_path)

        document = Document(
            document_name=os.path.basename(file_path),
            document_type=document_type,
            file_path=file_path,
            extracted_text=text,
            ocr_confidence=None,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="PyMuPDF",
        )

        document = self.validator.validate(document)

        if document.validation_status != ValidationStatus.VALID:
            return document, None

        extracted_data = self.extractor.extract(document)

        return document, extracted_data