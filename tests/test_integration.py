"""
Integration Tests for Intelligent Loan Processing Assistant

Tests the complete loan application workflow:
1. Document upload and extraction
2. Policy compliance checking
3. Risk assessment
4. Human-in-the-loop checkpoint
5. Customer-facing chat
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from agents.orchestrator import LoanProcessingOrchestrator
from agents.document_agent import DocumentAgent
from agents.policy_agent import PolicyAgent
from agents.risk_agent import RiskAgent
from agents.customer_agent import CustomerAgent
from models.application import LoanApplication
from models.document import Document
from models.extracted_data import ExtractedData
from models.risk import RiskAssessment, RISK_SCENARIOS
from models.policy import PolicyResult
from utils.enums import (
    ApplicationStatus, DocumentType, LoanType, RiskLevel, 
    Recommendation, EligibilityStatus, ValidationStatus, ValidationError
)
from document_processing.extractor import InformationExtractor
from document_processing.validator import DocumentValidator
from services.risk_service import RiskService
from services.policy_service import PolicyService


class TestDocumentExtractor:
    """Test information extraction from various document types."""
    
    def setup_method(self):
        self.extractor = InformationExtractor()
    
    def test_extract_salary_slip(self):
        text = """
        Employee Name: John Doe
        Employer: ABC Corporation Ltd
        Monthly Salary: ₹50,000
        Employment Duration: 3 years 6 months
        """
        doc = Document(
            document_name="salary_slip.pdf",
            document_type=DocumentType.SALARY_SLIP,
            file_path="/tmp/salary_slip.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        
        result = self.extractor.extract(doc)
        
        assert result.monthly_salary == 50000.0
        assert result.employer == "ABC Corporation Ltd"
        assert result.employee_name == "John Doe"
        assert "3 years" in result.employment_duration
    
    def test_extract_bank_statement(self):
        text = """
        Account Number: 123456789012
        Bank: HDFC Bank
        Closing Balance: ₹45,000
        Current Balance: ₹42,500
        """
        doc = Document(
            document_name="bank_stmt.pdf",
            document_type=DocumentType.BANK_STATEMENT,
            file_path="/tmp/bank_stmt.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        
        result = self.extractor.extract(doc)
        
        assert result.account_number == "123456789012"
        assert result.average_monthly_balance == 43750.0
        assert result.metadata.get("bank_name") == "HDFC Bank"
    
    def test_extract_employment_letter(self):
        text = """
        Employee Name: Jane Smith
        Employer: XYZ Technologies Pvt Ltd
        Designation: Senior Software Engineer
        Date of Joining: 15/01/2022
        Experience: 2 years
        """
        doc = Document(
            document_name="emp_letter.pdf",
            document_type=DocumentType.EMPLOYMENT_LETTER,
            file_path="/tmp/emp_letter.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        
        result = self.extractor.extract(doc)
        
        assert result.employer == "XYZ Technologies Pvt Ltd"
        assert result.employee_name == "Jane Smith"
        assert result.designation == "Senior Software Engineer"
        assert "2 years" in result.employment_duration
    
    def test_extract_pan_card(self):
        text = """
        PAN: ABCDE1234F
        Name: John Doe
        """
        doc = Document(
            document_name="pan.pdf",
            document_type=DocumentType.PAN,
            file_path="/tmp/pan.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        
        result = self.extractor.extract(doc)
        
        assert result.pan_number == "ABCDE1234F"
        assert result.name_on_pan == "John Doe"
    
    def test_extract_aadhaar(self):
        text = """
        Aadhaar Number: 1234 5678 9012
        Name: John Doe
        Date of Birth: 01/01/1990
        Address: 123 Main Street, Bangalore, Karnataka 560001
        """
        doc = Document(
            document_name="aadhaar.pdf",
            document_type=DocumentType.AADHAAR,
            file_path="/tmp/aadhaar.pdf",
            extracted_text=text,
            ocr_confidence=0.95,
            validation_status=ValidationStatus.VALID,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        
        result = self.extractor.extract(doc)
        
        assert result.aadhaar_number == "1234 5678 9012"
        assert result.name_on_aadhaar == "John Doe"
        assert result.date_of_birth == "01/01/1990"
        assert "Main Street" in result.address


class TestDocumentValidator:
    """Test document validation logic."""
    
    def setup_method(self):
        self.validator = DocumentValidator()
    
    def test_valid_salary_slip(self):
        text = "Employee Name: John Doe\nEmployer: ABC Corp\nMonthly Salary: ₹50,000\nPeriod: Jan 2024"
        doc = Document(
            document_name="salary.pdf",
            document_type=DocumentType.SALARY_SLIP,
            file_path="/tmp/salary.pdf",
            extracted_text=text,
            ocr_confidence=0.9,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        
        result = self.validator.validate(doc)
        
        assert result.validation_status == ValidationStatus.VALID
        assert result.validation_error == ValidationError.NONE
    
    def test_invalid_low_ocr_confidence(self):
        doc = Document(
            document_name="salary.pdf",
            document_type=DocumentType.SALARY_SLIP,
            file_path="/tmp/salary.pdf",
            extracted_text="Employee Name: John Doe\nSalary: ₹50,000",
            ocr_confidence=0.5,  # Below threshold
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="ocr"
        )
        
        result = self.validator.validate(doc)
        
        assert result.validation_status == ValidationStatus.INVALID
        assert result.validation_error == ValidationError.OCR_FAILED
    
    def test_missing_required_fields(self):
        text = "Some random text without required fields"
        doc = Document(
            document_name="salary.pdf",
            document_type=DocumentType.SALARY_SLIP,
            file_path="/tmp/salary.pdf",
            extracted_text=text,
            ocr_confidence=0.9,
            validation_status=ValidationStatus.PENDING,
            validation_error=ValidationError.NONE,
            extraction_method="pdf_text_extraction"
        )
        
        result = self.validator.validate(doc)
        
        assert result.validation_status == ValidationStatus.INVALID
        assert "missing_fields" in result.metadata


class TestPolicyService:
    """Test policy compliance checking."""
    
    def setup_method(self):
        self.policy_service = PolicyService()
    
    def test_compliant_application(self):
        application = LoanApplication(
            customer_name="John Doe",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=600000,
            monthly_salary=50000,
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        extracted = ExtractedData(
            monthly_salary=50000,
            employer="ABC Corp",
            employment_duration="3 years",
            average_monthly_balance=45000
        )
        
        result = self.policy_service.check_compliance(application, extracted, [])
        
        assert result.eligibility_status == EligibilityStatus.ELIGIBLE
        assert len(result.violations) == 0
        assert result.confidence_score >= 0.9
    
    def test_income_below_minimum(self):
        application = LoanApplication(
            customer_name="John Doe",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=300000,
            monthly_salary=25000,
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        extracted = ExtractedData(
            monthly_salary=25000,
            employer="ABC Corp",
            employment_duration="2 years"
        )
        
        result = self.policy_service.check_compliance(application, extracted, [])
        
        assert result.eligibility_status == EligibilityStatus.MANUAL_REVIEW
        assert any("below minimum" in v.lower() for v in result.violations)
    
    def test_loan_exceeds_multiplier(self):
        application = LoanApplication(
            customer_name="John Doe",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=1500000,
            monthly_salary=40000,
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        extracted = ExtractedData(
            monthly_salary=40000,
            employer="ABC Corp",
            employment_duration="3 years"
        )
        
        result = self.policy_service.check_compliance(application, extracted, [])
        
        assert any("exceeds" in v.lower() for v in result.violations)
    
    def test_missing_mandatory_documents(self):
        application = LoanApplication(
            customer_name="John Doe",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=500000,
            monthly_salary=50000,
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        extracted = ExtractedData(
            monthly_salary=50000,
            employer="ABC Corp",
            employment_duration="2 years"
        )
        
        result = self.policy_service.check_compliance(
            application, extracted, ["Bank Statement", "Employment Letter"]
        )
        
        assert result.eligibility_status == EligibilityStatus.MANUAL_REVIEW
        assert any("missing mandatory" in v.lower() for v in result.violations)


class TestRiskService:
    """Test risk assessment logic."""
    
    def setup_method(self):
        self.risk_service = RiskService()
    
    def test_low_risk_scenario(self):
        """Test LOW RISK scenario from RISK_SCENARIOS."""
        scenario = RISK_SCENARIOS["LOW_RISK"]
        
        application = LoanApplication(
            customer_name="Test",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=scenario["application"]["loan_amount"],
            monthly_salary=scenario["application"]["monthly_salary"],
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        extracted = ExtractedData(
            monthly_salary=scenario["extracted_data"]["monthly_salary"],
            average_monthly_balance=scenario["extracted_data"]["average_monthly_balance"],
            employment_duration=scenario["extracted_data"]["employment_duration"]
        )
        
        policy_result = PolicyResult(
            eligibility_status=EligibilityStatus.ELIGIBLE,
            policy_sections=[],
            violations=[],
            explanation="Compliant",
            confidence_score=0.95,
            retrieved_chunks=[]
        )
        
        result = self.risk_service.evaluate(application, extracted, policy_result)
        
        assert result.risk_level == RiskLevel.LOW
        assert result.recommendation == Recommendation.CONTINUE
        assert result.confidence_score >= 0.8
    
    def test_high_risk_missing_docs(self):
        """Test HIGH RISK missing documents scenario."""
        scenario = RISK_SCENARIOS["HIGH_RISK_MISSING_DOCS"]
        
        application = LoanApplication(
            customer_name="Test",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=scenario["application"]["loan_amount"],
            monthly_salary=scenario["application"]["monthly_salary"],
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        extracted = ExtractedData(
            monthly_salary=scenario["extracted_data"]["monthly_salary"],
            employment_duration=scenario["extracted_data"]["employment_duration"]
        )
        
        policy_result = PolicyResult(
            eligibility_status=EligibilityStatus.MANUAL_REVIEW,
            policy_sections=["Section 2"],
            violations=["Missing mandatory documents: Bank Statement, Employment Letter (Section 2)"],
            explanation="Missing docs",
            confidence_score=0.7,
            retrieved_chunks=[]
        )
        
        result = self.risk_service.evaluate(application, extracted, policy_result)
        
        assert result.risk_level == RiskLevel.HIGH
        assert result.recommendation == Recommendation.MANUAL_REVIEW
        assert any("missing mandatory" in r.lower() for r in result.reasons)
    
    def test_medium_risk_employment_change(self):
        """Test MEDIUM RISK recent employment change."""
        scenario = RISK_SCENARIOS["MEDIUM_RISK_EMPLOYMENT_CHANGE"]
        
        application = LoanApplication(
            customer_name="Test",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=scenario["application"]["loan_amount"],
            monthly_salary=scenario["application"]["monthly_salary"],
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        extracted = ExtractedData(
            monthly_salary=scenario["extracted_data"]["monthly_salary"],
            average_monthly_balance=scenario["extracted_data"]["average_monthly_balance"],
            employment_duration=scenario["extracted_data"]["employment_duration"]
        )
        
        policy_result = PolicyResult(
            eligibility_status=EligibilityStatus.MANUAL_REVIEW,
            policy_sections=["Section 4"],
            violations=["Employment duration 8 months < 12 months minimum (Section 4)"],
            explanation="Recent job change",
            confidence_score=0.7,
            retrieved_chunks=[]
        )
        
        result = self.risk_service.evaluate(application, extracted, policy_result)
        
        assert result.risk_level == RiskLevel.MEDIUM
        assert result.recommendation == Recommendation.REQUEST_DOCUMENTS


class TestOrchestrator:
    """Test the complete orchestrator workflow."""
    
    def setup_method(self):
        self.orchestrator = LoanProcessingOrchestrator()
    
    @patch.object(LoanProcessingOrchestrator, 'document_agent')
    @patch.object(LoanProcessingOrchestrator, 'policy_agent')
    @patch.object(LoanProcessingOrchestrator, 'risk_agent')
    def test_complete_workflow(self, mock_risk, mock_policy, mock_doc):
        """Test end-to-end application processing."""
        
        # Mock document agent to return valid documents
        mock_documents = [
            Document(
                document_name="salary.pdf",
                document_type=DocumentType.SALARY_SLIP,
                file_path="/tmp/salary.pdf",
                extracted_text="Salary: ₹50,000",
                ocr_confidence=0.95,
                validation_status=ValidationStatus.VALID,
                validation_error=ValidationError.NONE,
                extraction_method="pdf_text_extraction",
                metadata={"extracted_data": {"monthly_salary": 50000, "employer": "ABC Corp", "employee_name": "John", "employment_duration": "3 years"}}
            ),
            Document(
                document_name="bank.pdf",
                document_type=DocumentType.BANK_STATEMENT,
                file_path="/tmp/bank.pdf",
                extracted_text="Account: 123456\nBalance: ₹45,000",
                ocr_confidence=0.95,
                validation_status=ValidationStatus.VALID,
                validation_error=ValidationError.NONE,
                extraction_method="pdf_text_extraction",
                metadata={"extracted_data": {"account_number": "123456", "average_monthly_balance": 45000}}
            ),
        ]
        
        mock_doc.process.side_effect = [d.__dict__ for d in mock_documents]
        
        # Mock policy agent
        mock_policy.check_compliance.return_value = PolicyResult(
            eligibility_status=EligibilityStatus.ELIGIBLE,
            policy_sections=[],
            violations=[],
            explanation="Compliant",
            confidence_score=0.95,
            retrieved_chunks=[]
        )
        
        # Mock risk agent
        mock_risk.evaluate.return_value = RiskAssessment(
            risk_level=RiskLevel.LOW,
            confidence_score=0.9,
            reasons=["All checks passed"],
            recommendation=Recommendation.CONTINUE
        )
        
        application = LoanApplication(
            customer_name="John Doe",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=600000,
            monthly_salary=50000,
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        result = self.orchestrator.process_application(
            application=application,
            file_paths=["/tmp/salary.pdf", "/tmp/bank.pdf"],
            document_types=["Salary Slip", "Bank Statement"]
        )
        
        assert "application_id" in result
        assert result["status"] == ApplicationStatus.APPROVED.value
        assert result["needs_human_review"] == False
        assert result["risk_assessment"].risk_level == RiskLevel.LOW
    
    def test_human_review_checkpoint(self):
        """Test human-in-the-loop checkpoint for high-risk cases."""
        application = LoanApplication(
            customer_name="John Doe",
            customer_age=30,
            customer_phone="9876543210",
            loan_type=LoanType.HOME,
            loan_amount=1500000,
            monthly_salary=40000,
            employment_type="Salaried",
            application_status=ApplicationStatus.PENDING
        )
        
        result = self.orchestrator.submit_human_decision(
            application_id=application.application_id,
            decision="APPROVED_WITH_CONDITIONS",
            reviewer="Senior Loan Officer",
            comments="Approved with additional collateral requirement"
        )
        
        assert result["decision"] == "APPROVED_WITH_CONDITIONS"
        assert result["reviewer"] == "Senior Loan Officer"
        assert result["status"] == "completed"
        assert result["audit_entry"].action == "Human Review Decision"


class TestCustomerAgent:
    """Test customer-facing assistant."""
    
    def setup_method(self):
        self.customer_agent = CustomerAgent()
    
    @patch.object(CustomerAgent, 'customer')
    def test_friendly_mode_response(self, mock_customer):
        mock_customer.answer.return_value = "Based on our policy, the minimum salary requirement is ₹30,000 per month."
        
        response = self.customer_agent.answer(
            question="What is the minimum salary for a home loan?",
            mode="friendly"
        )
        
        assert "₹30,000" in response
        mock_customer.answer.assert_called_once()
    
    @patch.object(CustomerAgent, 'customer')
    def test_compliance_mode_response(self, mock_customer):
        mock_customer.answer.return_value = "I cannot determine the answer from the available policy documents."
        
        response = self.customer_agent.answer(
            question="What is the interest rate for personal loan?",
            mode="compliance"
        )
        
        assert "cannot determine" in response
        mock_customer.answer.assert_called_once()


class TestIntentClassification:
    """Test ML-based intent classification."""
    
    def test_intent_classifier_loads(self):
        from ml.intent_classifier import IntentClassifier
        from utils.enums import IntentType
        
        classifier = IntentClassifier()
        
        result = classifier.predict("What documents are required for home loan?")
        assert result == IntentType.POLICY_QUERY
        
        result = classifier.predict("Upload my salary slip")
        assert result == IntentType.DOCUMENT_PROCESSING
        
        result = classifier.predict("Why was my application rejected?")
        assert result == IntentType.APPLICATION_STATUS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])