from dataclasses import dataclass, field
from utils.enums import RiskLevel, Recommendation
from datetime import datetime
from typing import Optional


@dataclass(kw_only=True)
class RiskAssessment:
    risk_level: RiskLevel
    confidence_score: float
    reasons: list[str]
    recommendation: Recommendation
    generated_at: datetime = field(default_factory=datetime.now)
    llm_explanation: Optional[str] = None


# Sample Risk Scenarios for Documentation & Testing
# These demonstrate the rule-based risk evaluation logic per Section 6.2E requirements
# (Define Low/Medium/High risk + show at least 2 sample risk scenarios)

RISK_SCENARIOS = {
    "LOW_RISK": {
        "description": "Complete application with all documents, stable income, loan within limits",
        "application": {
            "loan_amount": 600000,
            "monthly_salary": 50000,
            "employment_duration_months": 36,
        },
        "documents_submitted": [
            "Salary Slip (3 months)",
            "Bank Statement (6 months)", 
            "Employment Letter",
            "PAN Card",
            "Aadhaar Card"
        ],
        "extracted_data": {
            "monthly_salary": 50000,
            "average_monthly_balance": 45000,
            "employment_duration": "3 years",
        },
        "expected_risk_level": RiskLevel.LOW,
        "expected_reasons": [
            "All mandatory documents submitted",
            "Income verified: salary slip matches bank credits",
            "Employment stable: 36 months with current employer",
            "Loan amount within limits: 6L <= 20x salary (1Cr)"
        ],
        "expected_recommendation": Recommendation.CONTINUE
    },
    "MEDIUM_RISK_EMPLOYMENT_CHANGE": {
        "description": "Recent job change within 6-12 months, otherwise clean application",
        "application": {
            "loan_amount": 500000,
            "monthly_salary": 45000,
            "employment_duration_months": 8,
        },
        "documents_submitted": [
            "Salary Slip (3 months)",
            "Bank Statement (6 months)",
            "Employment Letter",
            "PAN Card",
            "Aadhaar Card"
        ],
        "extracted_data": {
            "monthly_salary": 45000,
            "average_monthly_balance": 40000,
            "employment_duration": "8 months",
        },
        "expected_risk_level": RiskLevel.MEDIUM,
        "expected_reasons": [
            "All mandatory documents submitted",
            "Income verified",
            "Recent employment change: 8 months < 12 months minimum (Section 4)",
            "Loan amount within limits: 5L <= 20x salary (90L)"
        ],
        "expected_recommendation": Recommendation.REQUEST_DOCUMENTS
    },
    "HIGH_RISK_MISSING_DOCS": {
        "description": "Missing mandatory documents (Bank Statement, Employment Letter)",
        "application": {
            "loan_amount": 800000,
            "monthly_salary": 55000,
            "employment_duration_months": 18,
        },
        "documents_submitted": [
            "Salary Slip (3 months)",
            "PAN Card",
            "Aadhaar Card"
        ],
        "extracted_data": {
            "monthly_salary": 55000,
            "employment_duration": "18 months",
        },
        "expected_risk_level": RiskLevel.HIGH,
        "expected_reasons": [
            "Missing mandatory documents: Bank Statement, Employment Letter (Section 2)",
            "Income verified from salary slip",
            "Employment stable: 18 months",
            "Loan amount within limits: 8L <= 20x salary (1.1Cr)"
        ],
        "expected_recommendation": Recommendation.MANUAL_REVIEW
    },
}