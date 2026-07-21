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
    Rule-based risk evaluation with LLM explanation.
    
    Risk Scenarios (per Section 6.2E requirements):
    
    Scenario 1 - LOW RISK:
    - All mandatory documents submitted and valid
    - Monthly salary ₹60,000 (above ₹30,000 minimum)
    - Employment 36 months at current employer
    - Loan amount ₹8,00,000 (13.3x monthly salary, within 20x limit)
    - Bank statement shows consistent salary credits
    - Expected: RiskLevel.LOW, Recommendation.CONTINUE
    
    Scenario 2 - HIGH RISK:
    - Missing Bank Statement (mandatory document)
    - Monthly salary ₹25,000 (below ₹30,000 minimum)
    - Employment 8 months (below 12-month requirement)
    - Loan amount ₹15,00,000 (60x monthly salary, exceeds 20x limit)
    - Salary slip shows ₹25,000 but bank statement shows ₹20,000 credits
    - Expected: RiskLevel.HIGH, Recommendation.MANUAL_REVIEW
    """

    RISK_RULES = {
        RiskLevel.LOW: [
            "All mandatory documents submitted",
            "Income verified",
            "Employment stable (12+ months)",
            "Loan amount within policy limits"
        ],
        RiskLevel.MEDIUM: [
            "Minor mismatch between salary slip and bank statement",
            "Recent employment change (6-12 months)",
            "Missing optional information"
        ],
        RiskLevel.HIGH: [
            "Missing mandatory documents",
            "False or inconsistent financial information",
            "Income below minimum requirement",
            "Loan amount significantly exceeds policy limits"
        ]
    }

    def __init__(self):
        self.policy = PolicyService()
        self.prompts = PromptService()
        self.llm = LLMService()
        self.audit = AuditService()

    def evaluate(
        self,
        application: LoanApplication,
        extracted_data: ExtractedData,
        policy_result: PolicyResult
    ) -> RiskAssessment:
        risk_factors = []
        risk_level = RiskLevel.LOW
        confidence = 0.9

        salary = extracted_data.monthly_salary or application.monthly_salary
        loan_amount = application.loan_amount

        if policy_result.violations:
            for violation in policy_result.violations:
                risk_factors.append(violation)

            if any("missing mandatory" in v.lower() for v in policy_result.violations):
                risk_level = RiskLevel.HIGH
                confidence = 0.85
            elif any("below minimum" in v.lower() or "exceeds" in v.lower() for v in policy_result.violations):
                risk_level = RiskLevel.HIGH
                confidence = 0.85
            else:
                risk_level = RiskLevel.MEDIUM
                confidence = 0.8

        if salary is not None and loan_amount is not None:
            ratio = loan_amount / (salary * 12) if salary > 0 else 0
            if ratio > 1.5:
                risk_factors.append(f"Loan-to-annual-income ratio {ratio:.1f}x exceeds prudent limits")
                if risk_level != RiskLevel.HIGH:
                    risk_level = RiskLevel.MEDIUM
                    confidence = 0.75

        if extracted_data.average_monthly_balance is not None and salary is not None:
            if extracted_data.average_monthly_balance < salary * 0.3:
                risk_factors.append("Low average monthly balance relative to declared income")
                if risk_level == RiskLevel.LOW:
                    risk_level = RiskLevel.MEDIUM
                    confidence = 0.75

        if not risk_factors:
            risk_factors = ["No significant risk factors identified"]

        recommendation = self._get_recommendation(risk_level, policy_result)

        assessment = RiskAssessment(
            risk_level=risk_level,
            confidence_score=confidence,
            reasons=risk_factors,
            recommendation=recommendation,
            generated_at=datetime.now()
        )

        self.audit.log(
            actor="Risk Agent",
            action="Risk Assessment",
            details=f"Risk Level: {risk_level.value}, Factors: {len(risk_factors)}"
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
            prompt = self.prompts.load(
                "risk_prompt.txt",
                loan_information=loan_info,
                risk_level=assessment.risk_level.value,
                risk_factors=risk_factors_text
            )
            llm_explanation = self.llm.generate(prompt)
            assessment.llm_explanation = llm_explanation
        except Exception as e:
            assessment.llm_explanation = f"LLM explanation unavailable: {str(e)}"