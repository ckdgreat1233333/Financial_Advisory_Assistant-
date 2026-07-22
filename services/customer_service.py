from services.policy_service import PolicyService
from services.prompt_service import PromptService
from services.llm_service import LLMService
from services.audit_service import AuditService


class CustomerService:

    def __init__(self, policy: PolicyService | None = None, llm: LLMService | None = None):

        self.policy = policy or PolicyService()

        self.prompts = PromptService()

        self.llm = llm or LLMService()

        self.audit = AuditService()

    def answer(

        self,

        question: str,

        mode="customer_advisory",

    ):

        context = self.policy.retrieve_context(question)

        mode_map = {
            "friendly": "customer_prompt.txt",
            "customer_advisory": "customer_prompt.txt",
            "compliance": "compliance_prompt.txt",
            "strict_compliance": "compliance_prompt.txt",
        }

        template = mode_map.get(mode, "customer_prompt.txt")

        prompt = self.prompts.load(

            template,

            question=question,

            context=context,

        )

        response = self.llm.generate(prompt)

        self.audit.log(

            actor="Customer Agent",

            action="Customer Query",

            details=question,

        )

        return response