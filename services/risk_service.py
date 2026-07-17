from services.policy_service import PolicyService
from services.prompt_service import PromptService
from services.llm_service import LLMService
from services.audit_service import AuditService


class RiskService:

    def __init__(self):

        self.policy = PolicyService()

        self.prompts = PromptService()

        self.llm = LLMService()

        self.audit = AuditService()

    def evaluate(

        self,

        application,

        extracted_data,

    ):

        search_query = f"""

Loan Amount : {application.loan_amount}

Income : {extracted_data.salary}

Employment : {extracted_data.employer}

"""

        context = self.policy.retrieve_context(search_query)

        prompt = self.prompts.load(

            "risk_prompt.txt",

            application=application,

            extracted_data=extracted_data,

            policy_context=context,

        )

        result = self.llm.generate(prompt)

        self.audit.log(

            actor="Risk Agent",

            action="Risk Assessment",

            details=result,

        )

        return result