from models.escalation import EscalationDecision
from models.policy import PolicyResult
from models.fraud import FraudAssessment
from models.claim import Claim
from services.fraud_case_service import HIGH_SIM_THRESHOLD, MEDIUM_SIM_THRESHOLD
from utils.enums import EscalationDecision as Decision, ClaimStatus, FraudLevel, CoverageStatus


# Confidence thresholds that trigger manual review (configurable).
# Shared with the fraud semantic engine so there is a single source of truth.
HIGH_FRAUD_REVIEW_THRESHOLD = HIGH_SIM_THRESHOLD
MEDIUM_SIMILARITY_REVIEW_THRESHOLD = MEDIUM_SIM_THRESHOLD


class EscalationDecisionAgent:
    """
    Combines policy interpretation and fraud screening outputs to decide
    how a claim should proceed. The final authority always remains with
    a human claim officer.

    Human-in-the-loop design:
        - Any claim flagged High fraud risk is ALWAYS escalated.
        - Medium fraud risk + coverage uncertainty is escalated.
        - Officer override is always possible and recorded in the audit trail.
    """

    def decide(
        self,
        claim: Claim,
        policy_result: PolicyResult,
        fraud_assessment: FraudAssessment
    ) -> EscalationDecision:
        reasons = []
        confidence = 0.9

        # 1. Fraud level analysis
        if fraud_assessment.fraud_level == FraudLevel.HIGH:
            reasons.append(
                "High fraud risk flagged; mandatory human review required (Section 6 - Escalation Rules)"
            )
        elif fraud_assessment.fraud_level == FraudLevel.MEDIUM:
            reasons.append("Medium fraud risk detected; review recommended")

        # 2. Semantic similarity signal
        if fraud_assessment.similarity_score is not None:
            if fraud_assessment.similarity_score >= HIGH_FRAUD_REVIEW_THRESHOLD:
                reasons.append(
                    f"Strong similarity ({fraud_assessment.similarity_score:.0%}) to historical fraud cases"
                )
            elif fraud_assessment.similarity_score >= MEDIUM_SIMILARITY_REVIEW_THRESHOLD:
                reasons.append(
                    f"Moderate similarity ({fraud_assessment.similarity_score:.0%}) to historical fraud cases"
                )

        # 3. Coverage uncertainty
        if policy_result.coverage_status == CoverageStatus.MANUAL_REVIEW:
            reasons.append("Coverage requires manual interpretation (missing documents)")
        elif policy_result.coverage_status == CoverageStatus.NOT_COVERED:
            reasons.append("Claim appears outside policy coverage")

        # 4. Confidence-based escalation
        requires_review = (
            fraud_assessment.fraud_level == FraudLevel.HIGH
            or fraud_assessment.requires_manual_review
            or policy_result.coverage_status == CoverageStatus.MANUAL_REVIEW
            or (
                fraud_assessment.fraud_level == FraudLevel.MEDIUM
                and policy_result.coverage_status != CoverageStatus.COVERED
            )
        )

        if requires_review:
            confidence = min(0.75, confidence - 0.15)
            decision = Decision.ESCALATE
            next_step = ClaimStatus.MANUAL_REVIEW
        elif policy_result.coverage_status == CoverageStatus.NOT_COVERED:
            confidence = 0.8
            decision = Decision.ESCALATE
            next_step = ClaimStatus.MANUAL_REVIEW
            requires_review = True
        else:
            decision = Decision.CONTINUE
            next_step = ClaimStatus.INTAKE

        rationale = self._build_rationale(reasons)

        return EscalationDecision(
            decision=decision,
            confidence_score=round(confidence, 2),
            reasons=reasons,
            next_step=next_step,
            requires_human_review=requires_review,
            rationale=rationale,
        )

    def _build_rationale(self, reasons: list[str]) -> str:
        if not reasons:
            return "No escalations triggered. Claim can continue through normal processing."
        lines = ["Escalation Decision Rationale:", "------------------------------"]
        lines.extend(f"- {r}" for r in reasons)
        lines.append("\nNote: Final decision always requires claim officer review.")
        return "\n".join(lines)
