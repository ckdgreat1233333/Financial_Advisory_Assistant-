from agents.document_agent import DocumentAgent
from agents.policy_agent import PolicyAgent
from agents.risk_agent import RiskAgent
from agents.customer_agent import CustomerAgent
from models.application import LoanApplication
from models.document import Document
from models.extracted_data import ExtractedData
from models.policy import PolicyResult
from models.risk import RiskAssessment
from models.audit import AuditEntry
from utils.enums import ApplicationStatus, DocumentType, AuditSeverity, AgentType, ValidationStatus, ValidationError
from typing import List, Any
from datetime import datetime
import uuid, dataclasses, json, os


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
        }

        received_doc_types = set()

        for file_path, doc_type_str in zip(file_paths, document_types):
            doc_type = DocumentType[doc_type_str.upper().replace(" ", "_").replace("-", "_")]
            received_doc_types.add(doc_type)

            doc_result = self.document_agent.process(
                file_path=file_path,
                document_type=doc_type_str
            )

            doc_obj = Document(
                document_name=os.path.basename(file_path),
                document_type=doc_type,
                file_path=file_path,
                extracted_text=doc_result.get("extracted_text", ""),
                ocr_confidence=doc_result.get("ocr_confidence"),
                validation_status=doc_result.get("validation_status", ValidationStatus.PENDING),
                validation_error=doc_result.get("validation_error", ValidationError.NONE),
                extraction_method=doc_result.get("extraction_method", "unknown"),
                metadata=doc_result.get("metadata", {}),
            )
            documents.append(doc_obj)

            vs = doc_result.get("validation_status")
            vs_value = vs.value if hasattr(vs, 'value') else str(vs)
            if vs_value == "Valid" and doc_result.get("metadata", {}).get("extracted_data"):
                from models.extracted_data import ExtractedData
                ed = ExtractedData(**doc_result["metadata"]["extracted_data"])
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

        audit_entries = []
        audit_entries.append(AuditEntry(
            agent_name=AgentType.DOCUMENT_AGENT,
            action="Document Processing",
            reason=f"Processed {len(documents)} document(s), missing: {missing_docs}",
            severity=AuditSeverity.INFO
        ))
        audit_entries.append(AuditEntry(
            agent_name=AgentType.POLICY_AGENT,
            action="Policy Compliance Check",
            reason=f"Status: {policy_result.eligibility_status.value}, Violations: {len(policy_result.violations)}",
            severity=AuditSeverity.WARNING if policy_result.violations else AuditSeverity.INFO
        ))
        audit_entries.append(AuditEntry(
            agent_name=AgentType.RISK_AGENT,
            action="Risk Evaluation",
            reason=f"Risk Level: {risk_assessment.risk_level.value}, Score: {risk_assessment.risk_score}, Recommendation: {risk_assessment.recommendation.value}",
            severity=AuditSeverity.WARNING if risk_assessment.risk_level.value in ("High", "Medium") else AuditSeverity.INFO
        ))

        return {
            "application_id": application.application_id,
            "application": application,
            "extracted_data": combined_extracted,
            "documents": documents,
            "policy_result": policy_result,
            "risk_assessment": risk_assessment,
            "missing_documents": missing_docs,
            "needs_human_review": needs_human_review,
            "human_review_reason": self._get_review_reason(policy_result, risk_assessment),
            "audit_entries": audit_entries
        }

    def serialize_result(self, result: dict) -> dict:
        """Convert orchestrator result dataclasses to JSON-ready dictionaries."""
        from enum import Enum as _Enum

        def _to_dict(obj: Any) -> Any:
            if obj is None:
                return None
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, _Enum):
                return obj.name if isinstance(obj, ApplicationStatus) else obj.value
            if dataclasses.is_dataclass(obj):
                d = {}
                for f in dataclasses.fields(obj):
                    d[f.name] = _to_dict(getattr(obj, f.name))
                return d
            if isinstance(obj, list):
                return [_to_dict(item) for item in obj]
            if isinstance(obj, dict):
                return {k: _to_dict(v) for k, v in obj.items()}
            return str(obj)

        app_status = result.get("application").application_status if result.get("application") else None
        serialized = {
            "application_id": result.get("application_id"),
            "application_status": app_status.name if app_status else None,
            "extracted_data": _to_dict(result.get("extracted_data")),
            "policy_result": _to_dict(result.get("policy_result")),
            "risk_assessment": _to_dict(result.get("risk_assessment")),
            "documents": _to_dict(result.get("documents", [])),
            "missing_documents": result.get("missing_documents", []),
            "needs_human_review": result.get("needs_human_review", False),
            "human_review_reason": result.get("human_review_reason", ""),
            "audit_entries": _to_dict(result.get("audit_entries", [])),
        }
        return serialized

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