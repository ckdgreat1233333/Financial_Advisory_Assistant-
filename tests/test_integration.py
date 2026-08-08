"""
Integration Tests for the Insurance Claims Intelligence Platform

Tests the complete claim processing workflow:
1. Document extraction and validation
2. Policy coverage interpretation
3. Fraud screening
4. Escalation / human-in-the-loop checkpoint
5. Customer-facing chat and intent classification
"""
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from agents.orchestrator import ClaimsProcessingOrchestrator
from agents.policy_agent import PolicyInterpretationAgent
from agents.fraud_agent import FraudDetectionAgent
from agents.escalation_agent import EscalationDecisionAgent
from agents.customer_agent import CustomerAgent
from models.claim import Claim
from models.document import Document
from models.extracted_data import ClaimExtractedData
from models.policy import PolicyResult
from models.fraud import FraudAssessment
from models.escalation import EscalationDecision
from utils.enums import (
    ClaimStatus, ClaimType, DocumentType, FraudLevel, CoverageStatus,
    Recommendation, ValidationStatus, ValidationError,
    EscalationDecision as EscalationDecisionValue
)
from document_processing.extractor import InformationExtractor
from document_processing.validator import DocumentValidator
from services.policy_service import PolicyService
from services.fraud_service import FraudService


def make_claim(**overrides) -> Claim:
    recent = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    defaults = dict(
        claimant_name="John Doe",
        claimant_email="john@example.com",
        claimant_phone="9876543210",
        policy_number="POL-2026-0001",
        claim_type=ClaimType.AUTO,
        claim_amount=50000,
        incident_date=recent,
        loss_description="Collision damage to rear bumper",
        claim_status=ClaimStatus.RECEIVED,
    )
    defaults.update(overrides)
    return Claim(**defaults)


def make_doc(document_type: DocumentType, text: str) -> Document:
    return Document(
        document_name="doc.txt",
        document_type=document_type,
        file_path="/tmp/doc.txt",
        extracted_text=text,
        ocr_confidence=0.95,
        validation_status=ValidationStatus.VALID,
        validation_error=ValidationError.NONE,
        extraction_method="text_fallback",
    )


class TestInformationExtractor:
    """Test structured extraction from claim documents."""

    def setup_method(self):
        self.extractor = InformationExtractor()

    def test_extract_claim_form(self):
        text = (
            "Claimant Name: John Doe\n"
            "Policy No: POL-2026-0001\n"
            "Claim Amount: Rs 50,000\n"
            "Date of Incident: 15/01/2026\n"
            "Incident Location: 14 Main Street, Mumbai\n"
            "Loss Description: Collision damage to rear bumper\n"
            "Cause of Loss: Road Accident\n"
        )
        result = self.extractor.extract(make_doc(DocumentType.CLAIM_FORM, text))

        assert result.claimant_name == "John Doe"
        assert result.policy_number == "POL-2026-0001"
        assert result.claimed_amount == 50000.0
        assert result.incident_date == "2026-01-15"
        assert "Main Street" in result.incident_location
        assert "Collision" in result.loss_description

    def test_extract_policy_document(self):
        text = (
            "Policy No: POL-2026-0001\n"
            "Policy Inception: 01/06/2025\n"
            "Coverage Limit: Rs 200,000\n"
            "Prior Claims: 1\n"
        )
        result = self.extractor.extract(make_doc(DocumentType.POLICY_DOCUMENT, text))

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
        result = self.extractor.extract(make_doc(DocumentType.PROOF_OF_LOSS, text))

        assert result.reported_amount == 45000.0
        assert "Fire damaged" in result.loss_description

    def test_extract_claim_number(self):
        text = (
            "Claim Number: CLM-PROP-2026-44012\n"
            "Policy Number: PROP-2026-771455\n"
            "Insured\nVikram Rao\n"
        )
        result = self.extractor.extract(make_doc(DocumentType.CLAIM_FORM, text))

        assert result.claim_number == "CLM-PROP-2026-44012"
        assert result.policy_number == "PROP-2026-771455"

    def test_extract_bare_insured_name(self):
        """A bare 'Insured' label on its own line must yield the name, not
        surrounding field labels or prose from the statement body."""
        text = (
            "Claim Number\nCLM-PROP-2026-55091\n"
            "Policy Number\nPROP-2024-563281\n"
            "Insured\nVikram Rao\n"
            "Property\n18 Lake View Road, Bengaluru\n"
            "Statement\nI certify that the reported loss resulted from an\n"
            "insured weather event. An independent surveyor verified the damage.\n"
            "Insured Signature: ____\n"
        )
        result = self.extractor.extract(make_doc(DocumentType.PROOF_OF_LOSS, text))

        assert result.claimant_name == "Vikram Rao"

    def test_extract_medical_report(self):
        text = (
            "Claimant Name: Jane Smith\n"
            "Diagnosis: Fractured arm\n"
            "Treatment Cost: Rs 80,000\n"
        )
        result = self.extractor.extract(make_doc(DocumentType.MEDICAL_REPORT, text))

        assert result.diagnosis == "Fractured arm"
        assert result.treatment_cost == 80000.0


class TestDocumentValidator:
    """Test claim document validation logic."""

    def setup_method(self):
        self.validator = DocumentValidator()

    def test_valid_claim_form(self):
        text = "Claimant Name: John Doe\nPolicy No: POL-1\nClaim Amount: \u20b950,000\nDate of Incident: 15/01/2026"
        doc = make_doc(DocumentType.CLAIM_FORM, text)
        doc.validation_status = ValidationStatus.PENDING

        result = self.validator.validate(doc)

        assert result.validation_status == ValidationStatus.VALID
        assert result.validation_error == ValidationError.NONE

    def test_invalid_low_ocr_confidence(self):
        doc = make_doc(DocumentType.CLAIM_FORM, "Claimant Name: John Doe\nPolicy No: POL-1")
        doc.ocr_confidence = 0.5
        doc.validation_status = ValidationStatus.PENDING
        doc.extraction_method = "ocr"

        result = self.validator.validate(doc)

        assert result.validation_status == ValidationStatus.INVALID
        assert result.validation_error == ValidationError.OCR_FAILED

    def test_missing_fields_is_invalid(self):
        doc = make_doc(DocumentType.CLAIM_FORM, "Only a claimant name is present here.")
        doc.validation_status = ValidationStatus.PENDING

        result = self.validator.validate(doc)

        assert result.validation_status == ValidationStatus.INVALID
        assert "missing_fields" in result.metadata

    def test_corrupted_document_is_invalid(self):
        doc = make_doc(DocumentType.PROOF_OF_LOSS, "")
        doc.ocr_confidence = 0.0
        doc.validation_status = ValidationStatus.PENDING
        doc.validation_error = ValidationError.CORRUPTED

        result = self.validator.validate(doc)

        assert result.validation_status == ValidationStatus.INVALID


class TestPolicyService:
    """Test coverage interpretation against the insurance policy."""

    def setup_method(self):
        self.policy_service = PolicyService()

    def test_covered_claim(self):
        claim = make_claim(claim_type=ClaimType.AUTO, claim_amount=50000)
        extracted = ClaimExtractedData(
            claimed_amount=50000,
            coverage_limit=200000,
            incident_date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            cause_of_loss="Road Accident",
        )

        result = self.policy_service.interpret_coverage(claim, extracted, [])

        assert result.coverage_status == CoverageStatus.COVERED
        assert result.confidence_score >= 0.9
        assert any("Section 1" in c for c in result.policy_sections)

    def test_excluded_cause_of_loss(self):
        claim = make_claim(claim_type=ClaimType.AUTO, claim_amount=50000)
        extracted = ClaimExtractedData(
            claimed_amount=50000,
            coverage_limit=200000,
            cause_of_loss="Intentional damage",
        )

        result = self.policy_service.interpret_coverage(claim, extracted, [])

        assert result.coverage_status == CoverageStatus.NOT_COVERED
        assert "exclusion" in result.explanation.lower()

    def test_missing_documents_requires_manual_review(self):
        claim = make_claim()
        extracted = ClaimExtractedData(claimed_amount=50000, coverage_limit=200000)

        result = self.policy_service.interpret_coverage(claim, extracted, ["Proof of Loss"])

        assert result.coverage_status == CoverageStatus.MANUAL_REVIEW
        assert result.requires_manual_review is True
        assert "missing" in result.explanation.lower()

    def test_amount_exceeds_limit(self):
        claim = make_claim(claim_amount=500000)
        extracted = ClaimExtractedData(claimed_amount=500000, coverage_limit=200000)

        result = self.policy_service.interpret_coverage(claim, extracted, [])

        assert result.coverage_status == CoverageStatus.NOT_COVERED
        assert "exceeds coverage limit" in result.explanation.lower()


class TestFraudService:
    """Test rule-based fraud screening."""

    def setup_method(self):
        self.fraud_service = FraudService()
        self.fraud_service.llm.generate = MagicMock(return_value="Fraud screening explanation")

    def test_low_fraud_risk(self):
        claim = make_claim()
        extracted = ClaimExtractedData(
            claimed_amount=50000,
            coverage_limit=200000,
            policy_inception_date="2025-06-01",
            cause_of_loss="Road Accident",
        )
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
            policy_sections=["Section 1 - Coverage Scope"],
        )

        result = self.fraud_service.detect_fraud(claim, extracted, policy_result)

        assert result.fraud_level == FraudLevel.LOW
        assert result.recommendation == Recommendation.CONTINUE
        assert result.requires_manual_review is False

    def test_amount_exceeds_limit_flags_medium(self):
        claim = make_claim(claim_amount=250000)
        extracted = ClaimExtractedData(
            claimed_amount=250000,
            coverage_limit=200000,
            policy_inception_date="2025-06-01",
        )
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.NOT_COVERED,
            confidence_score=0.7,
            explanation="Amount exceeds limit",
            policy_sections=["Section 3 - Coverage Limits"],
        )

        result = self.fraud_service.detect_fraud(claim, extracted, policy_result)

        assert result.fraud_level == FraudLevel.MEDIUM
        assert FraudIndicator_AMOUNT in result.fraud_indicators

    def test_recent_inception_flags_indicator(self):
        from datetime import datetime
        recent = datetime.now().strftime("%d/%m/%Y")
        claim = make_claim()
        extracted = ClaimExtractedData(
            claimed_amount=50000,
            coverage_limit=200000,
            policy_inception_date=recent,
        )
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
            policy_sections=["Section 1 - Coverage Scope"],
        )

        result = self.fraud_service.detect_fraud(claim, extracted, policy_result)

        assert FraudIndicator_INCEPTION in result.fraud_indicators

    def test_recent_inception_flags_when_incident_close_to_inception(self):
        """The recent-inception signal is the gap between policy inception and
        the loss, not days since inception. A policy bought 13 days before the
        incident must be flagged even though it started weeks ago."""
        claim = make_claim(incident_date="2026-07-28")
        extracted = ClaimExtractedData(
            claimed_amount=50000,
            coverage_limit=200000,
            policy_inception_date="2026-07-15",
            incident_date="2026-07-28",
        )
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
            policy_sections=["Section 1 - Coverage Scope"],
        )

        result = self.fraud_service.detect_fraud(claim, extracted, policy_result)

        assert FraudIndicator_INCEPTION in result.fraud_indicators
        assert any("13 days after policy inception" in r for r in result.reasons)

    def test_fraud_narrative_inside_document_flags_high(self):
        """Fraud described only in the uploaded document body (not the typed
        loss description) must still be caught by semantic screening."""
        staged_narrative = (
            "CLAIM FORM\nLoss Description: Two vehicles owned by relatives of the same person "
            "collided and both filed claims. The accident occurred on a quiet street with no "
            "traffic cameras. The two drivers gave conflicting accounts during separate "
            "interviews. Both repair estimates were unusually high and issued by the same "
            "workshop. The vehicles had been insured for only three weeks.\nClaim Amount: Rs 100,000"
        )
        claim = make_claim(loss_description="Generic vehicle damage")
        extracted = ClaimExtractedData(
            claimed_amount=100000,
            coverage_limit=200000,
            policy_inception_date="2025-06-01",
            loss_description="Generic vehicle damage",
        )
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
            policy_sections=["Section 1 - Coverage Scope"],
        )
        docs = [make_doc(DocumentType.CLAIM_FORM, staged_narrative)]

        self.fraud_service._analyze_documents_with_llm = lambda *a, **k: {
            "inconsistencies": [], "fraud_indicators": ["Staged collision pattern"],
            "overall_risk": "High", "summary": "Staged collision indicators",
        }

        result = self.fraud_service.detect_fraud(claim, extracted, policy_result, docs)

        assert result.fraud_level == FraudLevel.HIGH
        assert result.requires_manual_review is True

    def test_benign_document_stays_low(self):
        """A routine claim form must not be flagged just because it uses the
        same structured layout as historical fraud cases."""
        benign_form = (
            "CLAIM FORM\nLoss Description: Windshield cracked by a falling branch during a "
            "storm.\nClaim Amount: Rs 25,000"
        )
        claim = make_claim(loss_description="Windshield cracked by falling branch")
        extracted = ClaimExtractedData(
            claimed_amount=25000,
            coverage_limit=200000,
            policy_inception_date="2025-06-01",
            loss_description="Windshield cracked by falling branch",
        )
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
            policy_sections=["Section 1 - Coverage Scope"],
        )
        docs = [make_doc(DocumentType.CLAIM_FORM, benign_form)]

        self.fraud_service._analyze_documents_with_llm = lambda *a, **k: {
            "inconsistencies": [], "fraud_indicators": [],
            "overall_risk": None, "summary": "",
        }

        result = self.fraud_service.detect_fraud(claim, extracted, policy_result, docs)

        assert result.fraud_level == FraudLevel.LOW
        assert result.requires_manual_review is False

    def test_cross_document_issues_flag_inconsistent_details(self):
        """Documents referencing different claim numbers, policy numbers or
        insured persons must never merge silently into a low-risk claim."""
        claim = make_claim()
        extracted = ClaimExtractedData(
            claimed_amount=50000,
            coverage_limit=200000,
            policy_inception_date="2025-06-01",
            cause_of_loss="Road Accident",
        )
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
            policy_sections=["Section 1 - Coverage Scope"],
        )
        issues = [
            "Documents reference different claim numbers: CLM-A, CLM-B",
            "Documents reference different policy numbers: POL-1, POL-2",
            "Documents identify different insured persons: John Doe, Jane Doe",
        ]

        result = self.fraud_service.detect_fraud(
            claim, extracted, policy_result, cross_document_issues=issues
        )

        assert result.fraud_level == FraudLevel.MEDIUM
        assert FraudIndicator_INCONSISTENT in result.fraud_indicators
        assert result.recommendation == Recommendation.MANUAL_REVIEW
        for issue in issues:
            assert issue in result.reasons


class TestEscalationAgent:
    """Test the escalation / human-in-the-loop decision."""

    def setup_method(self):
        self.agent = EscalationDecisionAgent()

    def test_low_risk_continues(self):
        claim = make_claim()
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
        )
        fraud = FraudAssessment(
            fraud_level=FraudLevel.LOW,
            fraud_score=15.0,
            confidence_score=0.9,
            recommendation=Recommendation.CONTINUE,
            reasons=["No significant fraud indicators"],
        )

        result = self.agent.decide(claim, policy_result, fraud)

        assert result.requires_human_review is False
        assert result.decision == EscalationDecisionValue.CONTINUE
        assert result.next_step == ClaimStatus.INTAKE

    def test_high_fraud_always_escalates(self):
        claim = make_claim()
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
        )
        fraud = FraudAssessment(
            fraud_level=FraudLevel.HIGH,
            fraud_score=85.0,
            confidence_score=0.85,
            recommendation=Recommendation.MANUAL_REVIEW,
            reasons=["Strong similarity to historical fraud cases"],
        )

        result = self.agent.decide(claim, policy_result, fraud)

        assert result.requires_human_review is True
        assert result.decision == EscalationDecisionValue.ESCALATE
        assert result.next_step == ClaimStatus.MANUAL_REVIEW

    def test_coverage_uncertainty_escalates(self):
        claim = make_claim()
        policy_result = PolicyResult(
            coverage_status=CoverageStatus.MANUAL_REVIEW,
            confidence_score=0.6,
            explanation="Missing documents",
            requires_manual_review=True,
        )
        fraud = FraudAssessment(
            fraud_level=FraudLevel.LOW,
            fraud_score=15.0,
            confidence_score=0.9,
            recommendation=Recommendation.CONTINUE,
            reasons=["No significant fraud indicators"],
        )

        result = self.agent.decide(claim, policy_result, fraud)

        assert result.requires_human_review is True


class TestOrchestrator:
    """Test the complete orchestrator workflow."""

    def setup_method(self):
        self.orchestrator = ClaimsProcessingOrchestrator()

    def test_complete_workflow(self):
        self.orchestrator.document_agent.process = MagicMock(return_value={
            "extracted_text": "Claimant Name: John Doe\nClaim Amount: \u20b950,000",
            "ocr_confidence": 0.95,
            "extraction_method": "text_fallback",
            "validation_status": ValidationStatus.VALID,
            "validation_error": ValidationError.NONE,
            "metadata": {
                "extracted_data": {
                    "claimant_name": "John Doe", "claimed_amount": 50000,
                    "coverage_limit": 200000, "policy_inception_date": "2025-06-01"
                }
            }
        })

        self.orchestrator.policy_agent.interpret_coverage = MagicMock(return_value=PolicyResult(
            coverage_status=CoverageStatus.COVERED,
            confidence_score=0.95,
            explanation="Covered",
            policy_sections=["Section 1 - Coverage Scope"],
        ))

        self.orchestrator.fraud_agent.evaluate = MagicMock(return_value=FraudAssessment(
            fraud_level=FraudLevel.LOW,
            fraud_score=15.0,
            confidence_score=0.9,
            recommendation=Recommendation.CONTINUE,
            reasons=["No significant fraud indicators"],
        ))

        claim = make_claim()
        result = self.orchestrator.process_claim(
            claim=claim,
            file_paths=["/tmp/claim_form.txt", "/tmp/policy.txt", "/tmp/proof.txt"],
            document_types=["Claim Form", "Policy Document", "Proof of Loss"],
        )

        assert "claim_id" in result
        assert result["needs_human_review"] is False
        assert result["fraud_assessment"].fraud_level == FraudLevel.LOW
        assert len(result["documents"]) == 3
        assert result["missing_documents"] == []

    def test_mixed_claims_are_flagged_inconsistent(self):
        """Uploads mixing documents from different claims must surface every
        conflicting identifier instead of merging them silently."""
        from models.extracted_data import ClaimExtractedData
        data_list = [
            ClaimExtractedData(claim_number="CLM-PROP-2026-44012", policy_number="PROP-2026-771455", claimant_name="Vikram Rao"),
            ClaimExtractedData(claim_number="CLM-2026-889921", policy_number="PROP-2026-991204", claimant_name="Rahul Sharma"),
            ClaimExtractedData(claim_number="CLM-PROP-2026-55091", policy_number="PROP-2024-563281", claimant_name=None),
        ]

        issues = self.orchestrator._check_cross_document_consistency(data_list)

        assert len(issues) == 3
        assert any("different claim numbers" in i for i in issues)
        assert any("different policy numbers" in i for i in issues)
        assert any("different insured persons" in i for i in issues)
        assert "CLM-PROP-2026-44012" in issues[0] and "CLM-2026-889921" in issues[0]

    def test_same_claim_documents_are_consistent(self):
        from models.extracted_data import ClaimExtractedData
        data_list = [
            ClaimExtractedData(claim_number="CLM-A", policy_number="POL-1", claimant_name="John Doe"),
            ClaimExtractedData(claim_number="CLM-A", policy_number="POL-1", claimant_name=None),
        ]

        issues = self.orchestrator._check_cross_document_consistency(data_list)

        assert issues == []

    def test_missing_documents_reported(self):
        self.orchestrator.document_agent.process = MagicMock(return_value={
            "extracted_text": "",
            "ocr_confidence": 0.9,
            "extraction_method": "text_fallback",
            "validation_status": ValidationStatus.INVALID,
            "validation_error": ValidationError.FILE_MISSING,
            "metadata": {},
        })

        claim = make_claim()
        result = self.orchestrator.process_claim(
            claim=claim,
            file_paths=["/tmp/claim_form.txt"],
            document_types=["Claim Form"],
        )

        assert set(result["missing_documents"]) == {"Policy Document", "Proof of Loss"}

    def test_serialize_result(self):
        self.orchestrator.document_agent.process = MagicMock(return_value={
            "extracted_text": "",
            "ocr_confidence": 0.0,
            "extraction_method": "failed",
            "validation_status": ValidationStatus.INVALID,
            "validation_error": ValidationError.CORRUPTED,
            "metadata": {},
        })

        claim = make_claim()
        result = self.orchestrator.process_claim(
            claim=claim,
            file_paths=["/tmp/claim_form.txt"],
            document_types=["Claim Form"],
        )

        serialized = self.orchestrator.serialize_result(result)

        assert serialized["claim_id"] == claim.claim_id
        assert "policy_result" in serialized
        assert "fraud_assessment" in serialized
        assert "audit_entries" in serialized

    def test_human_review_checkpoint(self):
        claim = make_claim()

        result = self.orchestrator.submit_human_decision(
            claim_id=claim.claim_id,
            decision="REJECTED",
            reviewer="Senior Claims Officer",
            comments="Loss occurred before policy inception",
        )

        assert result["decision"] == "REJECTED"
        assert result["reviewer"] == "Senior Claims Officer"
        assert result["status"] == "completed"
        assert result["audit_entry"].action == "Human Review Decision"


class TestCustomerAgent:
    """Test the customer-facing claims assistant."""

    def setup_method(self):
        self.customer_agent = CustomerAgent()

    def test_friendly_mode_response(self):
        self.customer_agent.customer = MagicMock()
        self.customer_agent.customer.answer.return_value = (
            "Based on our policy, claims must be reported within 30 days of the incident."
        )

        response = self.customer_agent.answer(
            question="How long do I have to report a claim?",
            mode="friendly"
        )

        assert "30 days" in response
        self.customer_agent.customer.answer.assert_called_once()

    def test_compliance_mode_response(self):
        self.customer_agent.customer = MagicMock()
        self.customer_agent.customer.answer.return_value = (
            "I cannot determine the answer from the available policy documents."
        )

        response = self.customer_agent.answer(
            question="What is my exact payout?",
            mode="compliance"
        )

        assert "cannot determine" in response
        self.customer_agent.customer.answer.assert_called_once()


class TestIntentClassification:
    """Test ML-based intent classification."""

    def test_intent_classifier_loads(self):
        from ml.intent_classifier import IntentClassifier
        from utils.enums import IntentType

        classifier = IntentClassifier()

        result = classifier.predict("What is the coverage for fire damage?")
        assert result == IntentType.POLICY_QUERY

        result = classifier.predict("Upload my claim form")
        assert result == IntentType.DOCUMENT_PROCESSING

        result = classifier.predict("Why was my claim rejected?")
        assert result == IntentType.CLAIM_EXPLANATION


# Reusable indicator constants (avoid long enum lines)
FraudIndicator_AMOUNT = "Claim Amount Exceeds Coverage"
FraudIndicator_INCEPTION = "Policy Inception Too Recent"
FraudIndicator_INCONSISTENT = "Inconsistent Claim Details"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
