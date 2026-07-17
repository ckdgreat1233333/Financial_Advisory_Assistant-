from datetime import datetime

from models.audit import Audit


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
    ):

        audit = Audit(

            timestamp=datetime.now(),

            actor=actor,

            action=action,

            details=details,

        )

        self.logs.append(audit)

        return audit

    def get_logs(self):

        return self.logs

    def clear(self):

        self.logs.clear()