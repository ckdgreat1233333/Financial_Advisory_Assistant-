from datetime import datetime

from models.audit import AuditEntry
from utils.enums import AuditSeverity, AgentType


class AuditService:
    """
    Creates an audit trail.

    Every important decision should
    create one Audit record.
    """

    def __init__(self):

        self.logs = []

    def log(
        self,
        actor: str,
        action: str,
        details: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        agent_type: AgentType = None,
    ):

        audit = AuditEntry(
            agent_name=agent_type or AgentType.ORCHESTRATOR,
            action=action,
            reason=details,
            severity=severity,
            timestamp=datetime.now(),
        )

        self.logs.append(audit)

        return audit

    def get_logs(self):

        return self.logs

    def clear(self):

        self.logs.clear()