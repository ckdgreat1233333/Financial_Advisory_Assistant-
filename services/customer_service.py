from services.policy_service import PolicyService
from services.prompt_service import PromptService
from services.llm_service import LLMService
from services.audit_service import AuditService


class CustomerService:

    def __init__(self):

        self.policy = PolicyService()

        self.prompts = PromptService()

        self.llm = LLMService()

        self.audit = AuditService()

    def answer(

        self,

        question: str,

        mode="friendly",

    ):

        context = self.policy.retrieve_context(question)

        template = (

            "customer_prompt.txt"

            if mode == "friendly"

            else "compliance_prompt.txt"

        )

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