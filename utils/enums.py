from enum import Enum

class ClaimStatus(Enum):
    RECEIVED = "Received"
    INTAKE = "Intake"
    TRIAGE = "Triage"
    POLICY_CHECK = "Policy Check"
    FRAUD_SCREEN = "Fraud Screening"
    ESCALATION_REVIEW = "Escalation Review"
    MANUAL_REVIEW = "Manual Review"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"

class ClaimType(Enum):
    AUTO = "Auto"
    HEALTH = "Health"
    PROPERTY = "Property"
    FIRE = "Fire"
    THEFT = "Theft"
    LIABILITY = "Liability"
    TRAVEL = "Travel"

class FraudLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    UNKNOWN = "Unknown"

class EscalationDecision(Enum):
    CONTINUE = "Continue Processing"
    REQUEST_DOCUMENTS = "Request Additional Documents"
    ESCALATE = "Escalate for Manual Review"
    APPROVE = "Recommend Acceptance"

class ValidationStatus(Enum):
    VALID = "Valid"
    INVALID = "Invalid"
    PENDING = "Pending"

class ValidationError(Enum):
    NONE = "None"
    PASSWORD_PROTECTED = "Password Protected"
    CORRUPTED = "Corrupted PDF"
    OCR_FAILED = "OCR Failed"
    FILE_MISSING = "Missing File"
    UNSUPPORTED_FORMAT = "Unsupported Format"

class DocumentType(Enum):
    CLAIM_FORM = "Claim Form"
    POLICY_DOCUMENT = "Policy Document"
    PROOF_OF_LOSS = "Proof of Loss"
    MEDICAL_REPORT = "Medical Report"
    POLICE_REPORT = "Police Report"
    INVOICE_RECEIPT = "Invoice / Receipt"
    INCIDENT_REPORT = "Incident Report"

class CoverageStatus(Enum):
    PENDING = "Pending"
    COVERED = "Covered"
    NOT_COVERED = "Not Covered"
    EXCLUDED = "Excluded"
    PARTIAL = "Partially Covered"
    MANUAL_REVIEW = "Manual Review"

class AuditSeverity(Enum):
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"

class AgentType(Enum):
    DOCUMENT_AGENT = "Document Agent"
    POLICY_AGENT = "Policy Interpretation Agent"
    FRAUD_AGENT = "Fraud Detection Agent"
    ESCALATION_AGENT = "Escalation Decision Agent"
    CUSTOMER_AGENT = "Customer Agent"
    ORCHESTRATOR = "Orchestrator"

class Recommendation(Enum):
    CONTINUE = "Continue Processing"
    REQUEST_DOCUMENTS = "Request Additional Documents"
    MANUAL_REVIEW = "Manual Review"

class IntentType(Enum):
    CLAIM_STATUS = "Claim Status"
    CLAIM_EXPLANATION = "Claim Explanation"
    POLICY_QUERY = "Policy Query"
    NEXT_STEPS = "Next Steps"
    DOCUMENT_PROCESSING = "Document Processing"
    GENERAL_QUERY = "General Query"

class FraudIndicator(Enum):
    MISSING_DOCUMENTS = "Missing Documents"
    AMOUNT_EXCEEDS_COVERAGE = "Claim Amount Exceeds Coverage"
    RECENT_POLICY_INCEPTION = "Policy Inception Too Recent"
    PRIOR_CLAIM_HISTORY = "Prior Claim History"
    SEMANTIC_CASE_SIMILARITY = "Semantic Similarity to Historical Fraud Cases"
    INCONSISTENT_DETAILS = "Inconsistent Claim Details"
    DOCUMENT_ANOMALY = "Document Anomaly"
    AI_DETECTED_PATTERNS = "Suspicious Patterns Detected by AI Analysis"
