from agents.document_agent import DocumentAgent
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
from models.audit import AuditEntry
from utils.enums import ClaimStatus, DocumentType, AuditSeverity, AgentType, ValidationStatus, ValidationError
from typing import List, Any
from datetime import datetime
import uuid, dataclasses, json, os


class ClaimsProcessingOrchestrator:
    """
    Main coordinator for the Insurance Claims Intelligence Platform.

    Flow:
        Claim Documents Uploaded
            ↓
        DocumentAgent (extract & validate claim text)
            ↓
        PolicyInterpretationAgent (coverage check)
            ↓
        FraudDetectionAgent (rules + historical case similarity)
            ↓
        EscalationDecisionAgent (confidence thresholds → HITL)
            ↓
        [Human Review Checkpoint if escalated]
            ↓
        CustomerAgent (claim status / explanation queries)
    """

    def __init__(self):
        self.document_agent = DocumentAgent()
        self.policy_agent = PolicyInterpretationAgent()
        self.fraud_agent = FraudDetectionAgent()
        self.escalation_agent = EscalationDecisionAgent()
        self.customer_agent = CustomerAgent()

    # -------------------------------
    # Internal Claim Workflow
    # -------------------------------

    def process_claim(
        self,
        claim: Claim,
        file_paths: List[str],
        document_types: List[str]
    ) -> dict:
        """
        Process a complete insurance claim with multiple documents.

        Args:
            claim: Claim with claimant and claim details
            file_paths: List of file paths to uploaded documents
            document_types: List of document types corresponding to each file

        Returns:
            Dictionary with extracted data, coverage result, fraud assessment,
            escalation decision, and audit trail
        """
        extracted_data_list = []
        documents = []
        missing_docs = []

        required_doc_types = {
            DocumentType.CLAIM_FORM,
            DocumentType.POLICY_DOCUMENT,
            DocumentType.PROOF_OF_LOSS,
        }

        received_doc_types = set()

        for file_path, doc_type_str in zip(file_paths, document_types):
            try:
                doc_type = DocumentType[doc_type_str.upper().replace(" ", "_").replace("-", "_")]
            except KeyError:
                continue
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
                ed = ClaimExtractedData(**doc_result["metadata"]["extracted_data"])
                extracted_data_list.append(ed)

        missing_docs = [dt.value for dt in required_doc_types - received_doc_types]

        cross_document_issues = self._check_cross_document_consistency(extracted_data_list)

        combined_extracted = self._combine_extracted_data(extracted_data_list)

        # Apply claim-level context that may not be in documents
        if not combined_extracted.claimant_name and claim.claimant_name:
            combined_extracted.claimant_name = claim.claimant_name
        if not combined_extracted.claimed_amount and claim.claim_amount:
            combined_extracted.claimed_amount = claim.claim_amount
        if not combined_extracted.loss_description and claim.loss_description:
            combined_extracted.loss_description = claim.loss_description
        if not combined_extracted.policy_number and claim.policy_number:
            combined_extracted.policy_number = claim.policy_number

        policy_result = self.policy_agent.interpret_coverage(
            claim=claim,
            extracted_data=combined_extracted,
            missing_docs=missing_docs
        )

        fraud_assessment = self.fraud_agent.evaluate(
            claim=claim,
            extracted_data=combined_extracted,
            policy_result=policy_result,
            documents=documents,
            cross_document_issues=cross_document_issues
        )

        escalation = self.escalation_agent.decide(
            claim=claim,
            policy_result=policy_result,
            fraud_assessment=fraud_assessment
        )

        claim.claim_status = self._determine_status(escalation, policy_result, fraud_assessment)
        claim.documents = documents
        claim.fraud = fraud_assessment
        claim.policy = policy_result
        claim.escalation = escalation

        needs_human_review = (
            escalation.requires_human_review or
            policy_result.requires_manual_review or
            fraud_assessment.requires_manual_review
        )

        claim.needs_human_review = needs_human_review
        claim.human_review_reason = self._get_review_reason(policy_result, fraud_assessment, escalation)

        audit_entries = []
        audit_entries.append(AuditEntry(
            agent_name=AgentType.DOCUMENT_AGENT,
            action="Claim Document Processing",
            reason=f"Processed {len(documents)} document(s), missing: {missing_docs}",
            severity=AuditSeverity.INFO
        ))
        audit_entries.append(AuditEntry(
            agent_name=AgentType.POLICY_AGENT,
            action="Coverage Interpretation",
            reason=f"Coverage: {policy_result.coverage_status.value}, Issues: {len(policy_result.policy_sections)}",
            severity=AuditSeverity.WARNING if policy_result.coverage_status.value not in ("Covered",) else AuditSeverity.INFO
        ))
        audit_entries.append(AuditEntry(
            agent_name=AgentType.FRAUD_AGENT,
            action="Fraud Screening",
            reason=f"Fraud Level: {fraud_assessment.fraud_level.value}, Score: {fraud_assessment.fraud_score}, "
                   f"Similarity: {fraud_assessment.similarity_score:.2f}" if fraud_assessment.similarity_score is not None else f"Similarity: N/A",
            severity=AuditSeverity.WARNING if fraud_assessment.fraud_level.value in ("High", "Medium") else AuditSeverity.INFO
        ))
        audit_entries.append(AuditEntry(
            agent_name=AgentType.ESCALATION_AGENT,
            action="Escalation Decision",
            reason=f"Decision: {escalation.decision.value}, Requires Human Review: {escalation.requires_human_review}",
            severity=AuditSeverity.WARNING if escalation.requires_human_review else AuditSeverity.INFO
        ))

        return {
            "claim_id": claim.claim_id,
            "claim": claim,
            "extracted_data": combined_extracted,
            "documents": documents,
            "policy_result": policy_result,
            "fraud_assessment": fraud_assessment,
            "escalation_decision": escalation,
            "missing_documents": missing_docs,
            "needs_human_review": needs_human_review,
            "human_review_reason": self._get_review_reason(policy_result, fraud_assessment, escalation),
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
                return obj.name if isinstance(obj, ClaimStatus) else obj.value
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

        claim_status = result.get("claim").claim_status if result.get("claim") else None
        serialized = {
            "claim_id": result.get("claim_id"),
            "claim_status": claim_status.name if claim_status else None,
            "extracted_data": _to_dict(result.get("extracted_data")),
            "policy_result": _to_dict(result.get("policy_result")),
            "fraud_assessment": _to_dict(result.get("fraud_assessment")),
            "escalation_decision": _to_dict(result.get("escalation_decision")),
            "documents": _to_dict(result.get("documents", [])),
            "missing_documents": result.get("missing_documents", []),
            "needs_human_review": result.get("needs_human_review", False),
            "human_review_reason": result.get("human_review_reason", ""),
            "audit_entries": _to_dict(result.get("audit_entries", [])),
        }
        return serialized

    def _combine_extracted_data(self, data_list: List[ClaimExtractedData]) -> ClaimExtractedData:
        combined = ClaimExtractedData()
        for data in data_list:
            for field in [
                "claimant_name", "claim_number", "policy_number", "claim_type", "incident_date",
                "incident_location", "claimed_amount", "loss_description",
                "reported_amount", "cause_of_loss", "prior_claims",
                "policy_inception_date", "coverage_limit", "diagnosis",
                "treatment_cost", "vehicle_registration", "property_address"
            ]:
                value = getattr(data, field)
                if value is not None:
                    setattr(combined, field, value)
        return combined

    def _check_cross_document_consistency(self, data_list: List[ClaimExtractedData]) -> List[str]:
        """Detect documents that belong to different claims/policies/insureds."""
        issues = []

        claims = sorted({d.claim_number for d in data_list if d.claim_number})
        policies = sorted({d.policy_number for d in data_list if d.policy_number})
        claimants = sorted({d.claimant_name for d in data_list if d.claimant_name})

        if len(claims) > 1:
            issues.append(f"Documents reference different claim numbers: {', '.join(claims)}")
        if len(policies) > 1:
            issues.append(f"Documents reference different policy numbers: {', '.join(policies)}")
        if len(claimants) > 1:
            issues.append(f"Documents identify different insured persons: {', '.join(claimants)}")

        return issues

    def _determine_status(self, escalation: EscalationDecision, policy_result: PolicyResult,
                          fraud_assessment: FraudAssessment) -> ClaimStatus:
        if escalation.requires_human_review:
            return ClaimStatus.MANUAL_REVIEW
        if fraud_assessment.fraud_level.value == "High":
            return ClaimStatus.FRAUD_SCREEN
        return ClaimStatus.INTAKE

    def _get_review_reason(self, policy_result: PolicyResult, fraud_assessment: FraudAssessment,
                           escalation: EscalationDecision) -> str:
        reasons = []
        if escalation.requires_human_review:
            reasons.append("Escalation decision requires manual review")
        if policy_result.requires_manual_review:
            reasons.append("Coverage interpretation requires manual review")
        if fraud_assessment.requires_manual_review:
            reasons.append(f"High fraud risk: {'; '.join(fraud_assessment.reasons)}")
        return "; ".join(reasons) if reasons else "No review needed"

    # -------------------------------
    # Human-in-the-Loop Checkpoint
    # -------------------------------

    def submit_human_decision(
        self,
        claim_id: str,
        decision: str,
        reviewer: str,
        comments: str
    ) -> dict:
        """
        Human-in-the-loop checkpoint for escalated claims.

        The human officer makes the final decision. All overrides are
        recorded in the audit trail.
        """
        from models.audit import AuditEntry
        from utils.enums import AuditSeverity, AgentType

        audit_entry = AuditEntry(
            agent_name=AgentType.ORCHESTRATOR,
            action="Human Review Decision",
            reason=f"Decision: {decision}, Reviewer: {reviewer}, Comments: {comments}",
            severity=AuditSeverity.INFO
        )

        return {
            "claim_id": claim_id,
            "decision": decision,
            "reviewer": reviewer,
            "comments": comments,
            "audit_entry": audit_entry,
            "status": "completed"
        }

    # -------------------------------
    # Customer Workflow
    # -------------------------------

    def customer_chat(self, question: str, mode: str = "friendly") -> str:
        return self.customer_agent.answer(
            question=question,
            mode=mode,
        )
