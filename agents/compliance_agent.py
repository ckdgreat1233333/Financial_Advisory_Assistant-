"""Compliance & Audit Copilot agent (internal track)."""
from services.regulatory_copilot import RegulatoryCopilot


class ComplianceAgent:

    def __init__(self, copilot: RegulatoryCopilot | None = None):
        self.copilot = copilot or RegulatoryCopilot()

    def answer(self, question: str, top_k: int = 4):
        return self.copilot.answer_internal(question, top_k=top_k)

    def retrieve(self, question: str, top_k: int = 4):
        return self.copilot.retrieve_excerpts(question, top_k=top_k)
