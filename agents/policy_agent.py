from services.policy_service import PolicyService
from models.application import LoanApplication
from models.extracted_data import ExtractedData
from models.policy import PolicyResult


class PolicyAgent:

    def __init__(self):
        self.policy = PolicyService()

    def check_compliance(
        self,
        application: LoanApplication,
        extracted_data: ExtractedData,
        missing_docs: list[str]
    ) -> PolicyResult:
        return self.policy.check_compliance(application, extracted_data, missing_docs)

    def search(self, query: str) -> str:
        return self.policy.retrieve_context(query)