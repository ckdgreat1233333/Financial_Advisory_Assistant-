from dataclasses import dataclass, field
from datetime import datetime
from utils.enums import AuditSeverity,AgentType
@dataclass(kw_only=True)
class AuditEntry:
    agent_name: AgentType
    action: str
    reason: str
    severity: AuditSeverity
    timestamp: datetime = field(default_factory=datetime.now)