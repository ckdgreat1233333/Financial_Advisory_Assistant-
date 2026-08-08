from services.policy_service import PolicyService
from services.prompt_service import PromptService
from services.llm_service import LLMService
from services.audit_service import AuditService
from utils.enums import IntentType


class CustomerService:

    def __init__(self, policy: PolicyService | None = None, llm: LLMService | None = None):

        self.policy = policy or PolicyService()

        self.prompts = PromptService()

        self.llm = llm or LLMService()

        self.audit = AuditService()

        self._classifier = None

        self._intent_map = {
            IntentType.POLICY_QUERY: "policy_prompt.txt",
            IntentType.CLAIM_EXPLANATION: "explanation_prompt.txt",
            IntentType.CLAIM_STATUS: "customer_prompt.txt",
            IntentType.NEXT_STEPS: "customer_prompt.txt",
            IntentType.DOCUMENT_PROCESSING: "customer_prompt.txt",
            IntentType.GENERAL_QUERY: "customer_prompt.txt",
        }

    def _get_classifier(self):
        if self._classifier is None:
            try:
                from ml.intent_classifier import IntentClassifier
                self._classifier = IntentClassifier()
            except Exception:
                self._classifier = False
        return self._classifier if self._classifier else None

    def classify_intent(self, question: str) -> IntentType:
        classifier = self._get_classifier()
        if classifier:
            try:
                return classifier.predict(question)
            except Exception:
                pass
        return IntentType.GENERAL_QUERY

    def answer(self, question: str, mode="customer_advisory"):

        intent = self.classify_intent(question)

        mode_map = {
            "friendly": "customer_prompt.txt",
            "customer_advisory": "customer_prompt.txt",
            "compliance": "compliance_prompt.txt",
            "strict_compliance": "compliance_prompt.txt",
        }

        template = self._intent_map.get(intent) or mode_map.get(mode, "customer_prompt.txt")

        context = self.policy.retrieve_context(question)

        prompt = self.prompts.load(
            template,
            question=question,
            context=context,
        )

        response = self.llm.generate(prompt)

        self.audit.log(
            actor="Customer Agent",
            action="Customer Query",
            details=f"Intent: {intent.value}, Question: {question}",
        )

        return response

    def explain_claim(self, decision: str, claim_information: str, reasons: str) -> str:
        """Explain a claim decision to a customer in plain language."""
        prompt = self.prompts.load(
            "explanation_prompt.txt",
            decision=decision,
            claim_information=claim_information,
            reasons=reasons,
        )
        try:
            return self.llm.generate(prompt)
        except Exception:
            return (
                f"Your claim is currently {decision.lower()}.\n\n"
                f"Here is what you should know:\n{reasons}\n\n"
                "This explanation is informational only. A claim officer makes the final decision. "
                "Please contact us if you have further questions."
            )
