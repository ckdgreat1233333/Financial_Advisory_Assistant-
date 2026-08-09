from enum import Enum

class AuditSeverity(Enum):
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"

class AgentType(Enum):
    COPILOT = "Regulatory Copilot"
    COMPLIANCE_AGENT = "Compliance & Audit Agent"
    CUSTOMER_AGENT = "Regulatory Transparency Agent"
    ORCHESTRATOR = "Orchestrator"
