from services.fraud_service import FraudService
from models.claim import Claim
from models.extracted_data import ClaimExtractedData
from models.policy import PolicyResult
from models.fraud import FraudAssessment


class FraudDetectionAgent:

    def __init__(self):
        self.service = FraudService()

    def evaluate(
        self,
        claim: Claim,
        extracted_data: ClaimExtractedData,
        policy_result: PolicyResult,
        documents: list | None = None,
        cross_document_issues: list[str] | None = None,
    ) -> FraudAssessment:
        return self.service.detect_fraud(
            claim, extracted_data, policy_result,
            documents=documents, cross_document_issues=cross_document_issues,
        )

    def score_similarity(self, claim_text: str) -> list[dict]:
        return self.service.case_service.score_claim(claim_text)
