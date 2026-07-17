from agents.document_agent import DocumentAgent
from agents.policy_agent import PolicyAgent
from agents.risk_agent import RiskAgent
from agents.customer_agent import CustomerAgent


class LoanProcessingOrchestrator:
    """
    Main coordinator for the Intelligent Loan Processing Assistant.

    Flow:
        Upload
          ↓
        DocumentAgent
          ↓
        PolicyAgent
          ↓
        RiskAgent
          ↓
        CustomerAgent
    """

    def __init__(self):
        self.document_agent = DocumentAgent()
        self.policy_agent = PolicyAgent()
        self.risk_agent = RiskAgent()
        self.customer_agent = CustomerAgent()

    # -------------------------------
    # Internal Business Workflow
    # -------------------------------

    def process_application(
        self,
        file_path: str,
        document_type: str,
        application,
    ):

        extracted_data = self.document_agent.process(
            file_path=file_path,
            document_type=document_type,
        )

        risk_report = self.risk_agent.evaluate(
            application=application,
            extracted_data=extracted_data,
        )

        return {
            "application": application,
            "extracted_data": extracted_data,
            "risk_report": risk_report,
        }

    # -------------------------------
    # Customer Workflow
    # -------------------------------

    def customer_chat(
        self,
        question: str,
        mode: str = "friendly",
    ):

        return self.customer_agent.answer(
            question=question,
            mode=mode,
        )