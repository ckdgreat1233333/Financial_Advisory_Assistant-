from services.risk_service import RiskService
from models.application import LoanApplication
from models.extracted_data import ExtractedData
from models.policy import PolicyResult
from models.risk import RiskAssessment


class RiskAgent:

    def __init__(self):
        self.service = RiskService()

    def evaluate(
        self,
        application: LoanApplication,
        extracted_data: ExtractedData,
        policy_result: PolicyResult
    ) -> RiskAssessment:
        return self.service.evaluate(application, extracted_data, policy_result)