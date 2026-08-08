from document_processing.pdf_reader import PDFReader
from document_processing.ocr import OCRProcessor
from document_processing.extractor import InformationExtractor
from document_processing.validator import DocumentValidator
from models.document import Document
from models.extracted_data import ClaimExtractedData
from utils.enums import DocumentType, ValidationStatus, ValidationError
from datetime import datetime
import uuid
import os


class DocumentProcessor:
    def __init__(self):
        self.pdf_reader = PDFReader()
        self.ocr_processor = OCRProcessor()
        self.extractor = InformationExtractor()
        self.validator = DocumentValidator()

    def process(self, file_path: str, document_type: str) -> dict:
        try:
            doc_type = DocumentType[document_type.upper().replace(" ", "_").replace("-", "_")]
        except KeyError:
            return {
                "extracted_text": "",
                "ocr_confidence": 0.0,
                "extraction_method": "unknown",
                "validation_status": ValidationStatus.INVALID,
                "validation_error": f"Unknown document type: {document_type}",
                "metadata": {}
            }

        extracted_text, ocr_confidence, extraction_method = self._extract_text(file_path)

        document = Document(
            document_name=file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1],
            document_type=doc_type,
            file_path=file_path,
            extracted_text=extracted_text,
            ocr_confidence=ocr_confidence,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method=extraction_method,
            metadata={},
            processed_at=datetime.now(),
            id=str(uuid.uuid4())
        )

        validated_doc = self.validator.validate(document)

        result = {
            "extracted_text": validated_doc.extracted_text,
            "ocr_confidence": validated_doc.ocr_confidence,
            "extraction_method": validated_doc.extraction_method,
            "validation_status": validated_doc.validation_status,
            "validation_error": validated_doc.validation_error,
            "metadata": validated_doc.metadata
        }

        if validated_doc.validation_status == ValidationStatus.VALID:
            extracted_data = self.extractor.extract(validated_doc)
            result["metadata"]["extracted_data"] = extracted_data.__dict__

        return result

    def _extract_text(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            try:
                import fitz
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                if text.strip():
                    return text, 1.0, "pdf_text_extraction"
            except Exception:
                pass

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                if text.strip():
                    return text, 0.9, "text_fallback"
            except Exception:
                pass

            try:
                text, confidence = self.ocr_processor.extract_text(file_path)
                return text, confidence, "ocr"
            except Exception:
                return "", 0.0, "failed"

        elif ext in [".png", ".jpg", ".jpeg"]:
            try:
                text, confidence = self.ocr_processor.extract_text(file_path)
                return text, confidence, "ocr"
            except Exception:
                return "", 0.0, "failed"

        elif ext == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                if text.strip():
                    return text, 0.9, "text_fallback"
                return "", 0.0, "failed"
            except Exception:
                return "", 0.0, "failed"

        else:
            raise ValueError(f"Unsupported file format: {ext}")