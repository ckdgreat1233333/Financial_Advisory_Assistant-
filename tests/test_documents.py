"""
Document Processing Tests - Validates the complete document pipeline:
1. PDF text extraction
2. OCR processing for scanned documents
3. Information extraction for each claim document type
4. Document validation rules
"""
import pytest
import tempfile
import os

from document_processing.pdf_reader import PDFReader
from document_processing.extractor import InformationExtractor
from document_processing.validator import DocumentValidator
from document_processing.document_processor import DocumentProcessor
from models.document import Document
from models.extracted_data import ClaimExtractedData
from utils.enums import DocumentType, ValidationStatus, ValidationError


class TestPDFReader:
    """Test PDF text extraction."""

    def test_read_pdf(self):
        if not has_fitz():
            pytest.skip("fitz (PyMuPDF) not available")

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
        nonexistent = os.path.join(tempfile.gettempdir(), "nonexistent_file_123456789.pdf")
        with pytest.raises(Exception):
            reader.read(nonexistent)


class TestDocumentValidation:
    """Test claim document validation rules."""

    def setup_method(self):
        self.validator = DocumentValidator()

    def test_valid_claim_form_passes(self):
        text = ("Claimant Name: John Doe\nPolicy No: POL-2026-0001\n"
                "Claim Amount: \u20b950,000\nDate of Incident: 15/01/2026\n"
                "Loss Description: Water damage to living room ceiling")
        doc = Document(
            document_name="claim_form.pdf",
            document_type=DocumentType.CLAIM_FORM,
            file_path="/tmp/claim_form.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.VALID

    def test_valid_policy_document_passes(self):
        text = "Policy No: POL-2026-0001\nCoverage Limit: \u20b9200,000\nSum Insured: \u20b9200,000"
        doc = Document(
            document_name="policy.pdf",
            document_type=DocumentType.POLICY_DOCUMENT,
            file_path="/tmp/policy.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.VALID

    def test_valid_proof_of_loss_passes(self):
        text = ("Reported Loss: \u20b945,000\nDescription of Loss: Fire damaged kitchen appliances\n"
                "Date of Incident: 15/01/2026")
        doc = Document(
            document_name="proof_of_loss.pdf",
            document_type=DocumentType.PROOF_OF_LOSS,
            file_path="/tmp/proof_of_loss.pdf",
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
            document_type=DocumentType.CLAIM_FORM,
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
            document_type=DocumentType.CLAIM_FORM,
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

    def test_missing_required_fields_is_invalid(self):
        doc = Document(
            document_name="incomplete.pdf",
            document_type=DocumentType.CLAIM_FORM,
            file_path="/tmp/incomplete.pdf",
            extracted_text="Only a claimant name appears here.",
            ocr_confidence=0.95,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="ocr"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.INVALID
        assert "missing_fields" in result.metadata

    def test_corrupted_pdf_is_invalid(self):
        doc = Document(
            document_name="corrupted.pdf",
            document_type=DocumentType.PROOF_OF_LOSS,
            file_path="/tmp/corrupted.pdf",
            extracted_text="",
            ocr_confidence=0.0,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.CORRUPTED,
            extraction_method="unknown"
        )
        result = self.validator.validate(doc)
        assert result.validation_status == ValidationStatus.INVALID


class TestInformationExtractor:
    """Test extraction of structured data from claim documents."""

    def setup_method(self):
        self.extractor = InformationExtractor()

    def test_extract_claim_form(self):
        text = (
            "Claimant Name: John Doe\n"
            "Policy No: POL-2026-0001\n"
            "Claim Amount: Rs 50,000\n"
            "Date of Incident: 15/01/2026\n"
            "Incident Location: 14 Main Street, Mumbai\n"
            "Loss Description: Water damage to living room ceiling\n"
            "Cause of Loss: Water Damage\n"
        )
        doc = Document(
            document_name="claim_form.txt",
            document_type=DocumentType.CLAIM_FORM,
            file_path="/tmp/claim_form.txt",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="text_fallback"
        )

        result = self.extractor.extract(doc)

        assert result.claimant_name == "John Doe"
        assert result.policy_number == "POL-2026-0001"
        assert result.claimed_amount == 50000.0
        assert result.incident_date == "2026-01-15"
        assert "Main Street" in result.incident_location
        assert "Water damage" in result.loss_description

    def test_extract_policy_document(self):
        text = (
            "Policy No: POL-2026-0001\n"
            "Policy Inception: 01/06/2025\n"
            "Coverage Limit: Rs 200,000\n"
            "Sum Insured: Rs 200,000\n"
            "Prior Claims: 1\n"
        )
        doc = Document(
            document_name="policy.txt",
            document_type=DocumentType.POLICY_DOCUMENT,
            file_path="/tmp/policy.txt",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="text_fallback"
        )

        result = self.extractor.extract(doc)

        assert result.policy_number == "POL-2026-0001"
        assert result.coverage_limit == 200000.0
        assert result.policy_inception_date == "2025-06-01"
        assert result.prior_claims == 1

    def test_extract_proof_of_loss(self):
        text = (
            "Reported Loss: Rs 45,000\n"
            "Description of Loss: Fire damaged kitchen appliances\n"
            "Date of Incident: 15/01/2026\n"
            "Witnesses: 2\n"
            "Third Party Involved: Neighbor\n"
        )
        doc = Document(
            document_name="proof_of_loss.txt",
            document_type=DocumentType.PROOF_OF_LOSS,
            file_path="/tmp/proof_of_loss.txt",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="text_fallback"
        )

        result = self.extractor.extract(doc)

        assert result.reported_amount == 45000.0
        assert "Fire damaged" in result.loss_description
        assert result.incident_date == "2026-01-15"
        assert result.witness_count == 2
        assert result.third_party_involved == "Neighbor"

    def test_extract_medical_report(self):
        text = (
            "Claimant Name: Jane Smith\n"
            "Diagnosis: Fractured arm\n"
            "Treatment Cost: Rs 80,000\n"
            "Date of Incident: 20/02/2026\n"
        )
        doc = Document(
            document_name="medical.txt",
            document_type=DocumentType.MEDICAL_REPORT,
            file_path="/tmp/medical.txt",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="text_fallback"
        )

        result = self.extractor.extract(doc)

        assert result.claimant_name == "Jane Smith"
        assert result.diagnosis == "Fractured arm"
        assert result.treatment_cost == 80000.0
        assert result.incident_date == "2026-02-20"


    def test_extract_table_layout_claim_form(self):
        """Claim forms from two-column PDF tables put the label on one line
        and the value on the next (no colon), with d-MMM-yyyy dates and a
        bullet-style currency glyph. These must still be extracted."""
        text = (
            "BlueShield Property Insurance Ltd.\n"
            "PROPERTY CLAIM FORM\n"
            "Field\n"
            "Value\n"
            "Claim Number\n"
            "CLM-2026-889921\n"
            "Policy Number\n"
            "PROP-2026-991204\n"
            "Policyholder\n"
            "Rahul Sharma\n"
            "Policy Start\n"
            "15-Jul-2026\n"
            "Date of Loss\n"
            "28-Jul-2026\n"
            "Date Reported\n"
            "27-Aug-2026\n"
            "Claim Amount\n"
            "I10,00,000\n"
            "Cause\n"
            "Burglary with complete loss of electronics\n"
        )
        doc = Document(
            document_name="claim_form.txt",
            document_type=DocumentType.CLAIM_FORM,
            file_path="/tmp/claim_form.txt",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="text_fallback"
        )

        result = self.extractor.extract(doc)

        assert result.claimant_name == "Rahul Sharma"
        assert result.policy_number == "PROP-2026-991204"
        assert result.claimed_amount == 1000000.0
        assert result.incident_date == "2026-07-28"
        assert result.policy_inception_date == "2026-07-15"
        assert "Burglary" in result.cause_of_loss

    def test_extract_table_layout_policy(self):
        """Policy schedules in table layout must yield coverage limit and
        inception from the period start, normalized to yyyy-mm-dd."""
        text = (
            "PROPERTY POLICY SCHEDULE\n"
            "Policy Number\n"
            "PROP-2026-991204\n"
            "Policy Period\n"
            "15-Jul-2026 to 14-Jul-2027\n"
            "Sum Insured\n"
            "I8,00,000\n"
            "Contents Cover Limit\n"
            "I5,00,000\n"
            "Deductible\n"
            "I5,000\n"
        )
        doc = Document(
            document_name="policy.txt",
            document_type=DocumentType.POLICY_DOCUMENT,
            file_path="/tmp/policy.txt",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="text_fallback"
        )

        result = self.extractor.extract(doc)

        assert result.policy_number == "PROP-2026-991204"
        assert result.coverage_limit == 500000.0
        assert result.policy_inception_date == "2026-07-15"


class TestDocumentProcessor:
    """Test the full document processing pipeline."""

    def setup_method(self):
        self.processor = DocumentProcessor()

    def test_process_valid_claim_form(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
            f.write("Claimant Name: John Doe\nPolicy No: POL-2026-0001\n"
                    "Claim Amount: \u20b950,000\nDate of Incident: 15/01/2026")
            f.flush()

            result = self.processor.process(f.name, "Claim Form")

            assert result is not None
            assert isinstance(result, dict)
            assert "extracted_text" in result
            assert "Claimant Name" in result["extracted_text"]
            assert result["validation_status"] == ValidationStatus.VALID
            assert "extracted_data" in result["metadata"]
            assert result["metadata"]["extracted_data"]["claimed_amount"] == 50000.0

        os.unlink(f.name)

    def test_process_unknown_type_returns_invalid(self):
        result = self.processor.process("/tmp/whatever.txt", "Not A Real Type")
        assert result["validation_status"] == ValidationStatus.INVALID


def has_fitz():
    try:
        import fitz
        return True
    except ImportError:
        return False


def create_minimal_pdf():
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
