from agents.document_agent import DocumentAgent
from agents.policy_agent import PolicyAgent
from agents.risk_agent import RiskAgent
from agents.customer_agent import CustomerAgent
from models.application import LoanApplication
from models.document import Document
from models.extracted_data import ExtractedData
from models.policy import PolicyResult
from models.risk import RiskAssessment
from utils.enums import ApplicationStatus, DocumentType
from typing import List
import uuid


class LoanProcessingOrchestrator:
    """
    Main coordinator for the Intelligent Loan Processing Assistant.

    Flow:
        Upload Documents
            ↓
        DocumentAgent (extract & validate)
            ↓
        PolicyAgent (compliance check)
            ↓
        RiskAgent (risk evaluation)
            ↓
        [Human Review Checkpoint if needed]
            ↓
        CustomerAgent (for customer queries)
    """

    def __init__(self):
        self.document_agent = DocumentAgent()
        self.policy_agent = PolicyAgent()
        self.risk_agent = RiskAgent()
        self.customer_agent = CustomerAgent()

    # -------------------------------
    # Internal Business Workflow
    # -------------------------------

    def process_application(
        self,
        application: LoanApplication,
        file_paths: List[str],
        document_types: List[str]
    ) -> dict:
        """
        Process a complete loan application with multiple documents.
        
        Args:
            application: LoanApplication with customer and loan details
            file_paths: List of file paths to uploaded documents
            document_types: List of document types corresponding to each file
            
        Returns:
            Dictionary with extracted data, policy result, risk assessment, and audit trail
        """
        extracted_data_list = []
        documents = []
        missing_docs = []

        required_doc_types = {
            DocumentType.SALARY_SLIP,
            DocumentType.BANK_STATEMENT,
            DocumentType.EMPLOYMENT_LETTER,
            DocumentType.PAN,
            DocumentType.AADHAAR
        }

        received_doc_types = set()

        for file_path, doc_type_str in zip(file_paths, document_types):
            doc_type = DocumentType[doc_type_str.upper().replace(" ", "_").replace("-", "_")]
            received_doc_types.add(doc_type)

            doc = self.document_agent.process(
                file_path=file_path,
                document_type=doc_type_str
            )
            documents.append(doc)

            if doc.validation_status.value == "Valid" and doc.metadata.get("extracted_data"):
                from models.extracted_data import ExtractedData
                ed = ExtractedData(**doc.metadata["extracted_data"])
                extracted_data_list.append(ed)

        missing_docs = [dt.value for dt in required_doc_types - received_doc_types]

        combined_extracted = self._combine_extracted_data(extracted_data_list)

        policy_result = self.policy_agent.check_compliance(
            application=application,
            extracted_data=combined_extracted,
            missing_docs=missing_docs
        )

        risk_assessment = self.risk_agent.evaluate(
            application=application,
            extracted_data=combined_extracted,
            policy_result=policy_result
        )

        application.application_status = self._determine_status(policy_result, risk_assessment)
        application.documents = documents
        application.risk = risk_assessment
        application.policy = policy_result

        needs_human_review = (
            policy_result.eligibility_status.value == "Manual Review" or
            risk_assessment.recommendation.value == "Manual Review"
        )

        return {
            "application_id": application.application_id,
            "application": application,
            "extracted_data": combined_extracted,
            "documents": documents,
            "policy_result": policy_result,
            "risk_assessment": risk_assessment,
            "missing_documents": missing_docs,
            "needs_human_review": needs_human_review,
            "human_review_reason": self._get_review_reason(policy_result, risk_assessment)
        }

    def _combine_extracted_data(self, data_list: List[ExtractedData]) -> ExtractedData:
        combined = ExtractedData()
        for data in data_list:
            for field in ["monthly_salary", "employer", "employee_name", "employment_duration", "account_number", "average_monthly_balance"]:
                value = getattr(data, field)
                if value is not None:
                    setattr(combined, field, value)
        return combined

    def _determine_status(self, policy_result: PolicyResult, risk_assessment: RiskAssessment) -> ApplicationStatus:
        if policy_result.eligibility_status.value == "Manual Review" or risk_assessment.recommendation.value == "Manual Review":
            return ApplicationStatus.MANUAL_REVIEW
        if policy_result.eligibility_status.value == "Not Eligible":
            return ApplicationStatus.REJECTED
        if policy_result.eligibility_status.value == "Eligible" and risk_assessment.risk_level.value == "Low":
            return ApplicationStatus.APPROVED
        return ApplicationStatus.POLICY_REVIEW

    def _get_review_reason(self, policy_result: PolicyResult, risk_assessment: RiskAssessment) -> str:
        reasons = []
        if policy_result.eligibility_status.value == "Manual Review":
            reasons.append("Policy requires manual review")
        if risk_assessment.recommendation.value == "Manual Review":
            reasons.append(f"High/Medium risk: {', '.join(risk_assessment.reasons)}")
        return "; ".join(reasons) if reasons else "No review needed"

    # -------------------------------
    # Human-in-the-Loop Checkpoint
    # -------------------------------

    def submit_human_decision(
        self,
        application_id: str,
        decision: str,
        reviewer: str,
        comments: str
    ) -> dict:
        """
        Human-in-the-loop checkpoint for manual review cases.
        """
        from models.audit import AuditEntry
        from utils.enums import AuditSeverity, AgentType
        from datetime import datetime

        audit_entry = AuditEntry(
            agent_name=AgentType.ORCHESTRATOR,
            action="Human Review Decision",
            reason=f"Decision: {decision}, Reviewer: {reviewer}, Comments: {comments}",
            severity=AuditSeverity.INFO
        )

        return {
            "application_id": application_id,
            "decision": decision,
            "reviewer": reviewer,
            "comments": comments,
            "audit_entry": audit_entry,
            "status": "completed"
        }

    # -------------------------------
    # Customer Workflow
    # -------------------------------

    def customer_chat(
        self,
        question: str,
        mode: str = "friendly",
    ) -> str:
        return self.customer_agent.answer(
            question=question,
            mode=mode,
        )