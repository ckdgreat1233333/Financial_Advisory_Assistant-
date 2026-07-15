from enum import Enum
class ApplicationStatus(Enum):
    PENDING = "Pending"
    DOCUMENT_VERIFICATION = "Document Verification"
    POLICY_REVIEW = "Policy Review"
    RISK_ASSESSMENT = "Risk Assessment"
    MANUAL_REVIEW = "Manual Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class RiskLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    UNKNOWN = "Unknown"

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
    SALARY_SLIP = "Salary Slip"
    BANK_STATEMENT = "Bank Statement"
    PAN = "PAN Card"
    AADHAAR = "Aadhaar Card"
    EMPLOYMENT_LETTER = "Employment Letter"

class LoanType(Enum):
    HOME = "Home Loan"
    PERSONAL = "Personal Loan"
    VEHICLE = "Vehicle Loan"
    EDUCATION = "Education Loan"
    BUSINESS = "Business Loan"

class EligibilityStatus(Enum):
    PENDING = "Pending"
    ELIGIBLE = "Eligible"
    NOT_ELIGIBLE = "Not Eligible"
    MANUAL_REVIEW = "Manual Review"

class AuditSeverity(Enum):
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"
class AgentType(Enum):
    DOCUMENT_AGENT = "Document Agent"
    POLICY_AGENT = "Policy Agent"
    RISK_AGENT = "Risk Agent"
    CUSTOMER_AGENT = "Customer Agent"
    ORCHESTRATOR = "Orchestrator"
class Recommendation(Enum):
    CONTINUE = "Continue Processing"
    REQUEST_DOCUMENTS = "Request Additional Documents"
    MANUAL_REVIEW = "Manual Review"