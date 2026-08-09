"""Regulatory Transparency Assistant agent (customer track)."""
from services.regulatory_copilot import RegulatoryCopilot


class CustomerRegulatoryAgent:

    def __init__(self, copilot: RegulatoryCopilot | None = None):
        self.copilot = copilot or RegulatoryCopilot()

    def answer(self, question: str, top_k: int = 4):
        return self.copilot.answer_customer(question, top_k=top_k)
