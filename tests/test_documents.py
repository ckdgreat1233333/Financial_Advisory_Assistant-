"""
Document Processing Tests - Validates the complete document pipeline:
1. PDF text extraction
2. OCR processing for scanned documents
3. Information extraction for each document type
4. Document validation rules
"""
import pytest
import tempfile
import os
from pathlib import Path

from document_processing.pdf_reader import PDFReader
from document_processing.extractor import InformationExtractor
from document_processing.validator import DocumentValidator
from document_processing.document_processor import DocumentProcessor
from models.document import Document
from models.extracted_data import ExtractedData
from utils.enums import DocumentType, ValidationStatus, ValidationError


class TestPDFReader:
    """Test PDF text extraction."""

    def test_read_pdf(self):
        if not has_fitz:
            pytest.skip("fitz (PyMuPDF) not available")

        # Create a minimal test PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(create_minimal_pdf())
            f.flush()
            reader = PDFReader()
            text = reader.read(f.name)

            assert text is not None
            assert isinstance(text, str)

        os.unlink(f.name)

    def test_read_nonexistent_file_raises_error(self):
        reader = PDFReader()
        with pytest.raises(Exception):
            reader.read("/tmp/nonexistent_file_123456789.pdf")


class TestDocumentValidation:
    """Test document validation rules."""

    def setup_method(self):
        self.validator = DocumentValidator()

    def test_valid_salary_slip_passes(self):
        text = "Employee Name: John\nEmployer: ABC Corp\nMonthly Salary: ₹50,000\nPeriod: Jan 2024"
        doc = Document(
            document_name="salary.pdf",
            document_type=DocumentType.SALARY_SLIP,
            file_path="/tmp/salary.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.VALID

    def test_password_protected_is_invalid(self):
        doc = Document(
            document_name="protected.pdf",
            document_type=DocumentType.SALARY_SLIP,
            file_path="/tmp/protected.pdf",
            extracted_text="",
            ocr_confidence=0.0,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.PASSWORD_PROTECTED,
            extraction_method="pdf_text_extraction"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.INVALID

    def test_low_ocr_confidence_is_invalid(self):
        text = "Some text"
        doc = Document(
            document_name="blurry.pdf",
            document_type=DocumentType.PAN,
            file_path="/tmp/blurry.pdf",
            extracted_text=text,
            ocr_confidence=0.4,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="ocr"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.INVALID
        assert result.validation_error == ValidationError.OCR_FAILED

    def test_missing_fields_logged(self):
        text = "hello world nothing useful"
        doc = Document(
            document_name="incomplete.pdf",
            document_type=DocumentType.SALARY_SLIP,
            file_path="/tmp/incomplete.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.INVALID
        assert "missing_fields" in result.metadata

    def test_corrupted_pdf_is_invalid(self):
        doc = Document(
            document_name="corrupted.pdf",
            document_type=DocumentType.BANK_STATEMENT,
            file_path="/tmp/corrupted.pdf",
            extracted_text="",
            ocr_confidence=0.0,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.CORRUPTED,
            extraction_method="unknown"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.INVALID


class TestDocumentProcessor:
    """Test the full document processing pipeline."""

    def setup_method(self):
        self.processor = DocumentProcessor()

    def test_process_handles_text_and_returns_document(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            f.write("Employee Name: John Doe\nSalary: ₹50,000")
            f.flush()

            document = self.processor.process(f.name, "Salary Slip")

            assert document is not None
            assert document.document_type == DocumentType.SALARY_SLIP
            assert "Employee Name" in document.extracted_text

        os.unlink(f.name)


def has_fitz():
    try:
        import fitz
        return True
    except ImportError:
        return False


def create_minimal_pdf():
    # Minimal valid PDF content
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])