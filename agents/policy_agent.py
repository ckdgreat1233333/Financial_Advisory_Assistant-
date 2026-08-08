from services.policy_service import PolicyService
from models.claim import Claim
from models.extracted_data import ClaimExtractedData
from models.policy import PolicyResult


class PolicyInterpretationAgent:

    def __init__(self):
        self.policy = PolicyService()

    def interpret_coverage(
        self,
        claim: Claim,
        extracted_data: ClaimExtractedData,
        missing_docs: list[str]
    ) -> PolicyResult:
        return self.policy.interpret_coverage(claim, extracted_data, missing_docs)

    def check_compliance(
        self,
        claim: Claim,
        extracted_data: ClaimExtractedData,
        missing_docs: list[str]
    ) -> PolicyResult:
        return self.policy.interpret_coverage(claim, extracted_data, missing_docs)

    def search(self, query: str) -> str:
        return self.policy.retrieve_context(query)
