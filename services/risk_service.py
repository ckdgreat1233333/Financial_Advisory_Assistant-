import re
from services.policy_service import PolicyService
from services.prompt_service import PromptService
from services.llm_service import LLMService
from services.audit_service import AuditService
from models.risk import RiskAssessment
from models.application import LoanApplication
from models.extracted_data import ExtractedData
from models.policy import PolicyResult
from utils.enums import RiskLevel, Recommendation
from datetime import datetime


class RiskService:
    """
    Rule-based risk evaluation using policy-defined risk rules.
    
    All risk rules and thresholds come from the policy document,
    never hardcoded in Python.
    """

    def __init__(self):
        self.policy = PolicyService()
        self.prompts = PromptService()
        self.llm = LLMService()
        self.audit = AuditService()

    def _get_policy_rules(self):
        self.policy._ensure_rules()
        return self.policy._rules

    def _get_risk_rules(self) -> dict[RiskLevel, list[str]]:
        rules = self._get_policy_rules()
        if rules.risk_rules:
            return rules.risk_rules
        return {level: [] for level in RiskLevel}

    def _extract_section(self, text: str) -> int | None:
        m = re.search(r"Section\s+(\d+)", text)
        return int(m.group(1)) if m else None

    def _match_violation_to_risk_rule(self, violation: str, condition: str) -> bool:
        """Check if a violation matches a risk condition using section reference + keyword overlap."""
        rules = self._get_policy_rules()
        stop_words = rules._get_stop_words()

        v_section = self._extract_section(violation)
        c_section = rules.risk_condition_sections.get(condition)

        if v_section is not None and c_section is not None:
            if v_section != c_section:
                return False

        v_words = set(re.sub(r"[^a-z0-9\s]", " ", violation.lower()).split())
        c_words = set(re.sub(r"[^a-z0-9\s]", " ", condition.lower()).split())
        if not c_words or not v_words:
            return False
        v_keywords = v_words - stop_words
        c_keywords = c_words - stop_words
        if not c_keywords:
            return False
        overlap = v_keywords & c_keywords
        return len(overlap) / len(c_keywords) >= 0.3

    def _match_violations(self, violations: list[str], condition: str) -> list[str]:
        return [v for v in violations if self._match_violation_to_risk_rule(v, condition)]

    def _get_risk_score(self, risk_level: RiskLevel, risk_factors: list[str]) -> float:
        base_scores = {RiskLevel.LOW: 20, RiskLevel.MEDIUM: 50, RiskLevel.HIGH: 80}
        score = base_scores.get(risk_level, 30)
        adjustment = min(len(risk_factors) * 3, 15)
        return float(min(score + adjustment, 100))

    def evaluate(
        self,
        application: LoanApplication,
        extracted_data: ExtractedData,
        policy_result: PolicyResult
    ) -> RiskAssessment:
        risk_factors = []
        triggered_rules = []
        risk_level = RiskLevel.LOW
        confidence = 0.9
        risk_rules = self._get_risk_rules()

        if policy_result.violations:
            for violation in policy_result.violations:
                risk_factors.append(violation)

            for level in [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
                conditions = risk_rules.get(level, [])
                matched = False
                for condition in conditions:
                    matches = self._match_violations(policy_result.violations, condition)
                    if matches:
                        triggered_rules.append(condition)
                        matched = True
                if matched:
                    risk_level = level
                    confidence = {RiskLevel.HIGH: 0.85, RiskLevel.MEDIUM: 0.8, RiskLevel.LOW: 0.9}[level]
                    break

        if not risk_factors:
            risk_factors = ["No significant risk factors identified"]
            triggered_rules = risk_rules.get(RiskLevel.LOW, [])

        recommendation = self._get_recommendation(risk_level, policy_result)
        risk_score = self._get_risk_score(risk_level, risk_factors)

        supporting_policy_parts = set()
        policy_sections = policy_result.policy_sections if hasattr(policy_result, 'policy_sections') else []
        for section in policy_sections:
            supporting_policy_parts.add(f"Refer to {section}")

        assessment = RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            confidence_score=confidence,
            reasons=risk_factors,
            recommendation=recommendation,
            triggered_rules=triggered_rules,
            supporting_policy=list(supporting_policy_parts) if supporting_policy_parts else None,
            generated_at=datetime.now()
        )

        self.audit.log(
            actor="Risk Agent",
            action="Risk Assessment",
            details=f"Risk Level: {risk_level.value}, Score: {risk_score}, Factors: {len(risk_factors)}"
        )

        self._explain_with_llm(assessment, application, extracted_data, policy_result)

        return assessment

    def _get_recommendation(self, risk_level: RiskLevel, policy_result: PolicyResult) -> Recommendation:
        if risk_level == RiskLevel.HIGH:
            return Recommendation.MANUAL_REVIEW
        elif risk_level == RiskLevel.MEDIUM:
            if policy_result.eligibility_status.value == "Manual Review":
                return Recommendation.MANUAL_REVIEW
            return Recommendation.REQUEST_DOCUMENTS
        return Recommendation.CONTINUE

    def _explain_with_llm(
        self,
        assessment: RiskAssessment,
        application: LoanApplication,
        extracted_data: ExtractedData,
        policy_result: PolicyResult
    ):
        try:
            loan_info = f"Amount: ₹{application.loan_amount:,.0f}, Income: ₹{extracted_data.monthly_salary or application.monthly_salary:,.0f}"
            risk_factors_text = "; ".join(assessment.reasons)
            triggered_text = "; ".join(assessment.triggered_rules) if assessment.triggered_rules else "None"
            prompt = self.prompts.load(
                "risk_prompt.txt",
                loan_information=loan_info,
                risk_level=assessment.risk_level.value,
                risk_factors=risk_factors_text,
                triggered_rules=triggered_text,
                recommendation=assessment.recommendation.value,
                risk_score=str(assessment.risk_score),
            )
            llm_explanation = self.llm.generate(prompt)
            assessment.llm_explanation = llm_explanation
        except Exception as e:
            assessment.llm_explanation = (
                f"Risk Assessment Summary:\n"
                f"Risk Level: {assessment.risk_level.value} (Score: {assessment.risk_score:.0f})\n"
                f"Confidence: {assessment.confidence_score:.0%}\n"
                f"Triggered Rules: {'; '.join(assessment.triggered_rules) if assessment.triggered_rules else 'None'}\n"
                f"Risk Factors: {'; '.join(assessment.reasons)}\n"
                f"Recommendation: {assessment.recommendation.value}\n"
                f"LLM explanation unavailable: {str(e)}"
            )