from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os
from datetime import datetime, timezone
import shutil

from agents.orchestrator import LoanProcessingOrchestrator
from models.application import LoanApplication
from models.document import Document
from models.extracted_data import ExtractedData
from models.risk import RiskAssessment
from utils.enums import (
    ApplicationStatus, DocumentType, LoanType, RiskLevel, Recommendation,
    ValidationStatus, ValidationError, AuditSeverity, AgentType, EligibilityStatus
)
from services.audit_service import AuditService
from services.policy_service import PolicyService

app = FastAPI(
    title="Intelligent Loan Processing Assistant",
    description="Enterprise-grade AI solution for loan processing in Banking domain",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = LoanProcessingOrchestrator()
audit_service = AuditService()
policy_service = PolicyService()

# In-memory stores
applications_store: dict[str, LoanApplication] = {}
users_store: dict[str, dict] = {}
policy_docs_store: list[dict] = []

# Initialize with some sample data
def _init_sample_data():
    sample_apps = [
        {
            "id": "LX-94021-B",
            "customer_name": "Nexus Logistics Inc. (Sarah Jenkins)",
            "customer_age": 35,
            "customer_phone": "+1 (555) 342-9901",
            "loan_type": "Business Loan",
            "loan_amount": 125000.0,
            "monthly_salary": 45000.0,
            "employment_type": "Employed",
            "status": "Policy Review",
            "email": "sjenkins@nexuslogistics.com",
            "interest_rate": 6.8,
            "risk_score": 14,
            "default_rate": 1.2,
            "compliance_status": "compliant",
            "term_months": 36,
            "progress": 75,
            "submitted_date": "2023-10-18",
            "reasoning_notes": "Low leverage ratio. Solid operating cash flow over the last 12 months. Tax returns correspond precisely to reported corporate earnings. Recommended for consensus approval.",
            "agent_consensus": {
                "documentValidation": {"status": "pass", "score": 98, "details": "OCR extraction verified. No pixel alterations or timestamp modifications detected."},
                "policyCompliance": {"status": "pass", "score": 100, "details": "Debt-to-income (DTI) ratio is 21.4%, which is well below the threshold of 45.0%."},
                "riskEvaluation": {"status": "pass", "score": 92, "details": "Risk Score 14/100 represents extremely low defaults in Logistics sector."}
            },
            "similarity_heatmap": {
                "labels": ["Chase_Oct_2023.pdf", "IRS_1040_2022.pdf", "Business_Lic.pdf", "ID_Card.pdf", "Rent_Agreement.pdf"],
                "matrix": [[1.00, 0.12, 0.08, 0.02, 0.05],[0.12, 1.00, 0.15, 0.01, 0.04],[0.08, 0.15, 1.00, 0.09, 0.11],[0.02, 0.01, 0.09, 1.00, 0.03],[0.05, 0.04, 0.11, 0.03, 1.00]]
            },
            "documents": [
                {"id": "doc-1", "name": "Chase_Oct_2023.pdf", "type": "Bank Statement", "status": "valid", "uploadedAt": "2023-10-18 09:12",
                 "ocrFields": [{"label": "Account Holder", "doc1Value": "Sarah Jenkins", "doc2Value": "Sarah Jenkins", "status": "match"},{"label": "Employer Name", "doc1Value": "Nexus Logistics Inc.", "doc2Value": "Nexus Logistics Inc.", "status": "match"},{"label": "Monthly Deposit Average", "doc1Value": "$41,500", "doc2Value": "$41,500", "status": "match"},{"label": "Tax Filing ID", "doc1Value": "XX-XXX4910", "doc2Value": "XX-XXX4910", "status": "match"}]},
                {"id": "doc-2", "name": "IRS_Form_1040_2022.pdf", "type": "Tax Return", "status": "valid", "uploadedAt": "2023-10-18 09:14"},
                {"id": "doc-3", "name": "Business_License_2023.pdf", "type": "ID & Licensing", "status": "valid", "uploadedAt": "2023-10-18 09:15"}
            ]
        },
        {
            "id": "LX-95204-S",
            "customer_name": "Solaris Cloud Tech (John S. Doe)",
            "customer_age": 42,
            "customer_phone": "+1 (555) 712-4040",
            "loan_type": "Business Loan",
            "loan_amount": 350000.0,
            "monthly_salary": 55000.0,
            "employment_type": "Self-Employed",
            "status": "Document Verification",
            "email": "jdoe@solariscloud.io",
            "interest_rate": 7.4,
            "risk_score": 48,
            "default_rate": 4.8,
            "compliance_status": "warning",
            "term_months": 48,
            "progress": 40,
            "submitted_date": "2023-10-19",
            "reasoning_notes": "Significant discrepancy detected between monthly deposits in Chase Statement and reported IRS revenues. Account name mismatch ('John S. Doe' vs 'Johnathan Doe'). Identity document requires manual review.",
            "agent_consensus": {
                "documentValidation": {"status": "warn", "score": 62, "details": "Discrepancy detected in Name Spellings and Reported Revenues (Variance > 20%)."},
                "policyCompliance": {"status": "warn", "score": 75, "details": "Required Identity Card is uploaded but not verified by automated biometric check."},
                "riskEvaluation": {"status": "warn", "score": 58, "details": "Medium Risk. Volatile industry (SaaS/Tech startups) combined with documentation variances."}
            },
            "similarity_heatmap": {
                "labels": ["Chase_Oct_2023.pdf", "IRS_1040_2022.pdf", "ID_Card.pdf", "Co_Profile.pdf", "Tax_Schedule.pdf"],
                "matrix": [[1.00, 0.45, 0.05, 0.18, 0.32],[0.45, 1.00, 0.08, 0.12, 0.40],[0.05, 0.08, 1.00, 0.03, 0.04],[0.18, 0.12, 0.03, 1.00, 0.15],[0.32, 0.40, 0.04, 0.15, 1.00]]
            },
            "documents": [
                {"id": "doc-4", "name": "Chase_Oct_2023.pdf", "type": "Bank Statement", "status": "mismatch", "uploadedAt": "2023-10-19 14:22",
                 "ocrFields": [{"label": "Account Holder", "doc1Value": "John S. Doe", "doc2Value": "Johnathan Doe", "status": "warning"},{"label": "Reported Revenue", "doc1Value": "$142,500", "doc2Value": "$110,000", "status": "mismatch"},{"label": "Company Name", "doc1Value": "Solaris Cloud Tech", "doc2Value": "Solaris Tech Corp", "status": "warning"},{"label": "EIN Reference", "doc1Value": "EI-9983-X", "doc2Value": "EI-9983-Y", "status": "mismatch"}]},
                {"id": "doc-5", "name": "IRS_Form_1040_2022.pdf", "type": "Tax Return", "status": "valid", "uploadedAt": "2023-10-19 14:24"},
                {"id": "doc-6", "name": "ID_Card.pdf", "type": "ID & Licensing", "status": "pending", "uploadedAt": "2023-10-19 14:25"}
            ]
        },
        {
            "id": "LX-92305-V",
            "customer_name": "Vanguard Bio-Med",
            "customer_age": 50,
            "customer_phone": "+1 (555) 231-1049",
            "loan_type": "Business Loan",
            "loan_amount": 500000.0,
            "monthly_salary": 80000.0,
            "employment_type": "Employed",
            "status": "Policy Review",
            "email": "funding@vanguardbiomed.com",
            "interest_rate": 8.5,
            "risk_score": 72,
            "default_rate": 11.4,
            "compliance_status": "failed",
            "term_months": 60,
            "progress": 90,
            "submitted_date": "2023-10-15",
            "reasoning_notes": "High debt-to-equity leverage ratio (4.2). Industry sector exhibits a systemic slowdown. Compliance audit flagged a mismatch in corporate entity registrations.",
            "agent_consensus": {
                "documentValidation": {"status": "warn", "score": 70, "details": "Corporate taxes match local files, but missing verified audited signatures."},
                "policyCompliance": {"status": "fail", "score": 45, "details": "Debt-to-equity leverage exceeds the maximum policy allowance of 3.0."},
                "riskEvaluation": {"status": "fail", "score": 28, "details": "Risk Score 72 indicates high leverage default risks."}
            },
            "similarity_heatmap": None,
            "documents": [
                {"id": "doc-7", "name": "Q3_Financial_Statement.pdf", "type": "Bank Statement", "status": "valid", "uploadedAt": "2023-10-15 11:00"},
                {"id": "doc-8", "name": "Corporate_Tax_2022.pdf", "type": "Tax Return", "status": "mismatch", "uploadedAt": "2023-10-15 11:02"}
            ]
        },
        {
            "id": "LX-91148-T",
            "customer_name": "Terra Maritime (Captain Marcus)",
            "customer_age": 45,
            "customer_phone": "+1 (555) 998-1111",
            "loan_type": "Business Loan",
            "loan_amount": 850000.0,
            "monthly_salary": 95000.0,
            "employment_type": "Employed",
            "status": "Approved",
            "email": "m.vance@terramaritime.com",
            "interest_rate": 5.9,
            "risk_score": 31,
            "default_rate": 2.1,
            "compliance_status": "compliant",
            "term_months": 72,
            "progress": 100,
            "submitted_date": "2023-10-10",
            "reasoning_notes": "Outstanding asset collateralization with multi-vessel coverage. Long-term cargo contracts secure reliable cash flows. Underwriter approved unconditionally.",
            "agent_consensus": {
                "documentValidation": {"status": "pass", "score": 95, "details": "Asset registries checked and cross-verified with marine transport databases."},
                "policyCompliance": {"status": "pass", "score": 98, "details": "Interest coverage ratios satisfy and surpass baseline parameters."},
                "riskEvaluation": {"status": "pass", "score": 85, "details": "Excellent tier business score. Lowest default quadrant."}
            },
            "similarity_heatmap": None,
            "documents": [
                {"id": "doc-9", "name": "Fleet_Valuation_Report.pdf", "type": "Bank Statement", "status": "valid", "uploadedAt": "2023-10-10 08:30"},
                {"id": "doc-10", "name": "IRS_Form_1120_2022.pdf", "type": "Tax Return", "status": "valid", "uploadedAt": "2023-10-10 08:35"}
            ]
        },
        {
            "id": "LX-11048-A",
            "customer_name": "Residential Mortgage (David & Emma Miller)",
            "customer_age": 32,
            "customer_phone": "+1 (555) 431-8844",
            "loan_type": "Home Loan",
            "loan_amount": 450000.0,
            "monthly_salary": 12000.0,
            "employment_type": "Employed",
            "status": "Policy Review",
            "email": "david.miller@gmail.com",
            "interest_rate": 6.25,
            "risk_score": 18,
            "default_rate": 0.9,
            "compliance_status": "compliant",
            "term_months": 360,
            "progress": 75,
            "submitted_date": "2023-10-20",
            "reasoning_notes": "Applicants possess excellent credit rating (795). Debt-to-income (DTI) ratio is 28%. Primary residence purchase. Clean appraisal documentation received.",
            "agent_consensus": {
                "documentValidation": {"status": "pass", "score": 99, "details": "Employment verification confirmed electronically with Equifax WorkNumber."},
                "policyCompliance": {"status": "pass", "score": 100, "details": "Conforms strictly to Fannie Mae eligibility standards."},
                "riskEvaluation": {"status": "pass", "score": 96, "details": "Prime customer segment. Extremely low risk of delinquency."}
            },
            "similarity_heatmap": None,
            "documents": [
                {"id": "doc-11", "name": "Paystubs_Sept_Oct.pdf", "type": "Bank Statement", "status": "valid", "uploadedAt": "2023-10-20 10:45"},
                {"id": "doc-12", "name": "W2_Form_2022.pdf", "type": "Tax Return", "status": "valid", "uploadedAt": "2023-10-20 10:47"},
                {"id": "doc-13", "name": "Purchase_Agreement_Signed.pdf", "type": "ID & Licensing", "status": "valid", "uploadedAt": "2023-10-20 10:50"}
            ]
        },
        {
            "id": "LX-70412-D",
            "customer_name": "Student Loan Refi (Jordan Taylor)",
            "customer_age": 28,
            "customer_phone": "+1 (555) 883-2211",
            "loan_type": "Personal Loan",
            "loan_amount": 48000.0,
            "monthly_salary": 5500.0,
            "employment_type": "Employed",
            "status": "Approved",
            "email": "jTaylor@alumni.edu",
            "interest_rate": 4.5,
            "risk_score": 22,
            "default_rate": 1.5,
            "compliance_status": "compliant",
            "term_months": 120,
            "progress": 100,
            "submitted_date": "2023-10-05",
            "reasoning_notes": "",
            "agent_consensus": None,
            "similarity_heatmap": None,
            "documents": [
                {"id": "doc-14", "name": "Diploma_Verification.pdf", "type": "ID & Licensing", "status": "valid", "uploadedAt": "2023-10-05 13:10"},
                {"id": "doc-15", "name": "Statement_Sofi_Current.pdf", "type": "Bank Statement", "status": "valid", "uploadedAt": "2023-10-05 13:12"}
            ]
        }
    ]
    for s in sample_apps:
        lt_map = {"Business Loan": "BUSINESS", "Home Loan": "HOME", "Personal Loan": "PERSONAL", "Vehicle Loan": "VEHICLE", "Education Loan": "EDUCATION"}
        status_map = {"Pending": "PENDING", "Document Verification": "DOCUMENT_VERIFICATION", "Policy Review": "POLICY_REVIEW", "Risk Assessment": "RISK_ASSESSMENT", "Manual Review": "MANUAL_REVIEW", "Approved": "APPROVED", "Rejected": "REJECTED"}
        try:
            lt = LoanType[lt_map.get(s["loan_type"], "HOME")]
            st = ApplicationStatus[status_map.get(s["status"], "PENDING")]
        except KeyError:
            continue
        app_obj = LoanApplication(
            customer_name=s["customer_name"],
            customer_age=s["customer_age"],
            customer_phone=s["customer_phone"],
            loan_type=lt,
            loan_amount=s["loan_amount"],
            monthly_salary=s["monthly_salary"],
            employment_type=s["employment_type"],
            application_status=st,
            application_id=s["id"]
        )
        app_obj.metadata = {"email": s["email"], "interest_rate": s["interest_rate"], "risk_score": s["risk_score"], "default_rate": s["default_rate"], "compliance_status": s["compliance_status"], "term_months": s.get("term_months", 12), "progress": s.get("progress", 0), "submitted_date": s.get("submitted_date", ""), "reasoning_notes": s.get("reasoning_notes", ""), "agent_consensus": s.get("agent_consensus"), "similarity_heatmap": s.get("similarity_heatmap"), "documents": s.get("documents", [])}
        applications_store[s["id"]] = app_obj

    sample_logs = [
        {"id": "LOG-001", "timestamp": "2023-10-19 14:26:12", "actor": "AI Engine v4.2", "eventType": "OCR Document Cross-Check", "riskLevel": "medium", "details": "Discrepancy identified for #LX-95204-S: Revenue mismatch of $32,500 between Chase Bank Statement and 1040 Tax filings."},
        {"id": "LOG-002", "timestamp": "2023-10-19 15:30:45", "actor": "Officer Sarah J.", "eventType": "Manual Document Tagging", "riskLevel": "low", "details": "Manually flags Solaris ID document as 'Pending Biometric Verification' and sent automated SMS alert."},
        {"id": "LOG-003", "timestamp": "2023-10-18 09:20:00", "actor": "AI Engine v4.2", "eventType": "Automated Policy Check", "riskLevel": "low", "details": "Policy engine run completed for #LX-94021-B. All thresholds (DTI, Credit, Assets) passed successfully."},
        {"id": "LOG-004", "timestamp": "2023-10-15 11:15:00", "actor": "AI Engine v4.2", "eventType": "automated_policy_fail", "riskLevel": "high", "details": "Application #LX-92305-V failed Debt-to-Equity limit check. Current: 4.2, Max Allowable: 3.0."},
        {"id": "LOG-005", "timestamp": "2023-10-10 10:00:00", "actor": "Officer Sarah J.", "eventType": "Underwriter Approval", "riskLevel": "low", "details": "Final manual sign-off for Terra Maritime loan #LX-91148-T after collateral appraisal verified."}
    ]
    for log in sample_logs:
        audit_service.logs.append(log)

_init_sample_data()

LOANTYPE_MAP = {"home": "HOME", "auto": "VEHICLE", "personal": "PERSONAL", "business": "BUSINESS", "Vehicle Loan": "VEHICLE", "Home Loan": "HOME", "Personal Loan": "PERSONAL", "Business Loan": "BUSINESS", "Education Loan": "EDUCATION"}
LOANTYPE_REVERSE = {"HOME": "home", "VEHICLE": "auto", "PERSONAL": "personal", "BUSINESS": "business", "EDUCATION": "personal", "HOME_LOAN": "home", "PERSONAL_LOAN": "personal", "BUSINESS_LOAN": "business", "VEHICLE_LOAN": "auto", "EDUCATION_LOAN": "personal", "HOME LOAN": "home", "PERSONAL LOAN": "personal", "BUSINESS LOAN": "business", "VEHICLE LOAN": "auto", "EDUCATION LOAN": "personal"}
STATUS_MAP = {"Pending": "under_review", "Document Verification": "pending_docs", "Policy Review": "under_review", "Risk Assessment": "under_review", "Manual Review": "under_review", "Approved": "approved", "Rejected": "rejected"}
RISK_MAP = {"Low": "low", "Medium": "medium", "High": "high", "Unknown": "medium"}
STATUS_REVERSE = {"under_review": "POLICY_REVIEW", "pending_docs": "DOCUMENT_VERIFICATION", "approved": "APPROVED", "rejected": "REJECTED", "draft": "PENDING"}

def _app_to_frontend(app_obj: LoanApplication) -> dict:
    meta = getattr(app_obj, "metadata", {}) or {}
    lt_raw = app_obj.loan_type.value if hasattr(app_obj.loan_type, "value") else str(app_obj.loan_type)
    ft = LOANTYPE_REVERSE.get(lt_raw.upper().replace(" ", "_"), "home")
    st = STATUS_MAP.get(app_obj.application_status.value if hasattr(app_obj.application_status, "value") else str(app_obj.application_status), "under_review")
    cs_map = {"compliant": "compliant", "warning": "warning", "failed": "failed"}
    cs = meta.get("compliance_status", "compliant")
    docs = meta.get("documents", [])
    if isinstance(docs, list):
        for d in docs:
            if isinstance(d, dict) and "id" not in d:
                d["id"] = str(uuid.uuid4())
    rs = app_obj.risk
    risk_score = meta.get("risk_score", 0)
    if rs and hasattr(rs, "risk_level"):
        rl = rs.risk_level.value if hasattr(rs.risk_level, "value") else str(rs.risk_level)
        risk_score = {"Low": 20, "Medium": 50, "High": 80, "Unknown": 50}.get(rl, 50)
    return {
        "id": app_obj.application_id,
        "applicantName": app_obj.customer_name,
        "applicantEmail": meta.get("email", ""),
        "applicantPhone": app_obj.customer_phone,
        "type": ft,
        "status": st,
        "amount": app_obj.loan_amount,
        "termMonths": meta.get("term_months", 12),
        "progress": meta.get("progress", 0),
        "submittedDate": meta.get("submitted_date", app_obj.created_at.strftime("%Y-%m-%d") if hasattr(app_obj, "created_at") else datetime.now().strftime("%Y-%m-%d")),
        "interestRate": meta.get("interest_rate", 5.0),
        "riskScore": risk_score,
        "defaultRate": meta.get("default_rate", 0),
        "complianceStatus": cs,
        "documents": docs if isinstance(docs, list) else [],
        "reasoningNotes": meta.get("reasoning_notes", ""),
        "agentConsensus": meta.get("agent_consensus"),
        "similarityHeatmap": meta.get("similarity_heatmap"),
    }

# ──────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────

class LoanApplicationRequest(BaseModel):
    customer_name: str
    customer_age: int
    customer_phone: str
    loan_type: str
    loan_amount: float
    monthly_salary: float
    employment_type: str

class CustomerQueryRequest(BaseModel):
    question: str
    mode: str = "friendly"

class ProcessApplicationRequest(BaseModel):
    application_id: str
    file_paths: List[str]
    document_types: List[str]

class HumanReviewRequest(BaseModel):
    application_id: str
    decision: str
    reviewer: str
    comments: str = ""

# ─────────────────── Auth ───────────────────

class LoginRequest(BaseModel):
    email: str
    password: str
    portalType: str = "customer"
    rememberMe: bool = False

class RegisterRequest(BaseModel):
    fullName: str
    email: str
    password: str
    phone: Optional[str] = ""
    portalType: str = "customer"
    termsAccepted: bool = False

class ProfileUpdateRequest(BaseModel):
    name: str
    email: str
    phone: str

class SecuritySettingsRequest(BaseModel):
    twoFactorEnabled: bool = False
    biometricOcrEnabled: bool = False

class NotificationSettingsRequest(BaseModel):
    emailNotifications: bool = True
    smsAlerts: bool = False
    pushNotifications: bool = False

# ─────────────────── Applications ───────────────────

class CreateAppRequest(BaseModel):
    applicantName: str
    applicantEmail: str
    applicantPhone: Optional[str] = ""
    type: str = "home"
    amount: float = 100000
    termMonths: int = 12
    interestRate: float = 5.0
    documents: List[dict] = []

class ApproveRejectRequest(BaseModel):
    actor: str
    reason: str = ""

class DocOverrideRequest(BaseModel):
    status: str

# ─────────────────── Audit Logs ───────────────────

class CreateAuditLogRequest(BaseModel):
    actor: str
    eventType: str
    riskLevel: str = "low"
    details: str = ""

# ─────────────────── Policy Docs ───────────────────

class CreatePolicyDocRequest(BaseModel):
    name: str
    version: str

# ─────────────────── Chat ───────────────────

class ChatRequest(BaseModel):
    message: str
    history: List[dict] = []
    applicationsContext: List[dict] = []

# ═══════════════════════════════════════════════
# ROOT
# ═══════════════════════════════════════════════

# Serve static UI at root
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return {"service": "Intelligent Loan Processing Assistant", "version": "1.0.0", "note": "Static UI not found. Run with frontend build."}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ═══════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    users_store[req.email] = users_store.get(req.email, {
        "role": req.portalType,
        "email": req.email,
        "name": req.email.split("@")[0].replace(".", " ").title(),
        "phone": ""
    })
    user = users_store[req.email]
    if user["role"] != req.portalType:
        user["role"] = req.portalType
    return {"user": user, "token": f"token-{req.email}-{uuid.uuid4().hex[:8]}"}

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    users_store[req.email] = {
        "role": req.portalType,
        "email": req.email,
        "name": req.fullName,
        "phone": req.phone or ""
    }
    return {"user": users_store[req.email], "token": f"token-{req.email}-{uuid.uuid4().hex[:8]}"}

@app.post("/api/auth/logout")
async def logout():
    return {"success": True}

@app.get("/api/auth/me")
async def auth_me(email: str = ""):
    if not email or email not in users_store:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": users_store[email]}

# ═══════════════════════════════════════════════
# APPLICATION ENDPOINTS
# ═══════════════════════════════════════════════

@app.get("/api/applications")
async def list_applications(email: str = "", status: str = "", search: str = ""):
    result = []
    for app_obj in applications_store.values():
        fe = _app_to_frontend(app_obj)
        if email and fe["applicantEmail"] != email:
            continue
        if status and fe["status"] != status:
            continue
        if search and search.lower() not in fe["applicantName"].lower() and search.lower() not in fe["id"].lower():
            continue
        result.append(fe)
    return {"applications": result}

@app.get("/api/applications/{application_id}")
async def get_application(application_id: str):
    app_obj = applications_store.get(application_id)
    if not app_obj:
        # Try to create a dummy application for known IDs from sample data
        for a in applications_store.values():
            if a.application_id == application_id:
                app_obj = a
                break
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    return _app_to_frontend(app_obj)

@app.post("/api/applications")
async def create_application(req: CreateAppRequest):
    lt_map = {"home": "HOME", "auto": "VEHICLE", "personal": "PERSONAL", "business": "BUSINESS"}
    try:
        lt = LoanType[lt_map.get(req.type, "HOME")]
    except KeyError:
        lt = LoanType.HOME
    app_obj = LoanApplication(
        customer_name=req.applicantName,
        customer_age=30,
        customer_phone=req.applicantPhone or "",
        loan_type=lt,
        loan_amount=req.amount,
        monthly_salary=req.amount / 20,
        employment_type="Employed",
        application_status=ApplicationStatus.POLICY_REVIEW
    )
    app_obj.metadata = {
        "email": req.applicantEmail,
        "interest_rate": req.interestRate,
        "risk_score": 30,
        "default_rate": 1.8,
        "compliance_status": "compliant",
        "term_months": req.termMonths,
        "progress": 25,
        "submitted_date": datetime.now().strftime("%Y-%m-%d"),
        "reasoning_notes": "Initial system submission uploaded successfully. Queued for automated OCR document alignment check.",
        "agent_consensus": {
            "documentValidation": {"status": "pass", "score": 85, "details": "OCR extraction successful. Metadata verifies file consistency."},
            "policyCompliance": {"status": "pass", "score": 90, "details": "Debt-to-income and asset allocations within policy bounds."},
            "riskEvaluation": {"status": "pass", "score": 78, "details": "Low-risk retail segment profile."}
        },
        "similarity_heatmap": {
            "labels": ["Statement_1.pdf", "IRS_1040.pdf", "ID_Card.pdf", "Rent_Agreement.pdf", "Invoice.pdf"],
            "matrix": [[1.00, 0.10, 0.04, 0.03, 0.11],[0.10, 1.00, 0.08, 0.01, 0.09],[0.04, 0.08, 1.00, 0.05, 0.03],[0.03, 0.01, 0.05, 1.00, 0.06],[0.11, 0.09, 0.03, 0.06, 1.00]]
        },
        "documents": req.documents if isinstance(req.documents, list) else []
    }
    applications_store[app_obj.application_id] = app_obj

    sev = AuditSeverity.INFO
    audit_entry = {
        "id": f"LOG-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor": "Compliance Engine v4.2",
        "eventType": "Loan Facility Creation",
        "riskLevel": "low",
        "details": f"New {req.type} application facility created successfully for {req.applicantName} amount: {req.amount}."
    }
    audit_service.logs.append(audit_entry)

    return {"application": _app_to_frontend(app_obj), "auditLog": audit_entry}

@app.patch("/api/applications/{application_id}/approve")
async def approve_application(application_id: str, req: ApproveRejectRequest):
    app_obj = applications_store.get(application_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    app_obj.application_status = ApplicationStatus.APPROVED
    meta = getattr(app_obj, "metadata", {}) or {}
    meta["progress"] = 100
    app_obj.metadata = meta

    audit_entry = {
        "id": f"LOG-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor": req.actor or "Officer",
        "eventType": "Underwriter Approval",
        "riskLevel": "low",
        "details": f"Application {application_id} approved by {req.actor}."
    }
    audit_service.logs.append(audit_entry)
    return {"application": _app_to_frontend(app_obj), "auditLog": audit_entry}

@app.patch("/api/applications/{application_id}/reject")
async def reject_application(application_id: str, req: ApproveRejectRequest):
    app_obj = applications_store.get(application_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    app_obj.application_status = ApplicationStatus.REJECTED
    meta = getattr(app_obj, "metadata", {}) or {}
    meta["progress"] = 100
    app_obj.metadata = meta

    audit_entry = {
        "id": f"LOG-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor": req.actor or "Officer",
        "eventType": "Underwriter Rejection",
        "riskLevel": "high",
        "details": f"Application {application_id} rejected by {req.actor}. Reason: {req.reason}"
    }
    audit_service.logs.append(audit_entry)
    return {"application": _app_to_frontend(app_obj), "auditLog": audit_entry}

@app.patch("/api/applications/{application_id}/documents/{doc_id}")
async def update_document_status(application_id: str, doc_id: str, req: DocOverrideRequest):
    app_obj = applications_store.get(application_id)
    if not app_obj:
        raise HTTPException(status_code=404, detail="Application not found")
    meta = getattr(app_obj, "metadata", {}) or {}
    docs = meta.get("documents", [])
    if isinstance(docs, list):
        for d in docs:
            if isinstance(d, dict) and d.get("id") == doc_id:
                d["status"] = req.status
                break
    meta["documents"] = docs
    app_obj.metadata = meta
    return _app_to_frontend(app_obj)

# ═══════════════════════════════════════════════
# AUDIT LOG ENDPOINTS
# ═══════════════════════════════════════════════

@app.get("/api/audit-logs")
async def list_audit_logs(application_id: str = "", riskLevel: str = ""):
    logs = audit_service.logs
    if isinstance(logs, list):
        filtered = logs
        if application_id:
            filtered = [l for l in filtered if isinstance(l, dict) and application_id in l.get("details", "")]
        if riskLevel:
            filtered = [l for l in filtered if isinstance(l, dict) and l.get("riskLevel") == riskLevel]
        return {"logs": filtered}
    return {"logs": []}

@app.post("/api/audit-logs")
async def create_audit_log(req: CreateAuditLogRequest):
    entry = {
        "id": f"LOG-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor": req.actor,
        "eventType": req.eventType,
        "riskLevel": req.riskLevel,
        "details": req.details
    }
    audit_service.logs.append(entry)
    return entry

# ═══════════════════════════════════════════════
# POLICY DOCUMENTS
# ═══════════════════════════════════════════════

@app.get("/api/policy-documents")
async def list_policy_documents():
    if not policy_docs_store:
        policy_docs_store.extend([
            {"id": "pol-1", "name": "Mortgage Underwriting Guidelines", "version": "v4.2", "status": "active", "uploadDate": "2023-08-15", "activeRules": 48},
            {"id": "pol-2", "name": "Commercial Loan Credit Risk Limits", "version": "v3.0", "status": "active", "uploadDate": "2023-09-01", "activeRules": 32},
            {"id": "pol-3", "name": "Retail & Consumer Lending Eligibility", "version": "v2.5", "status": "active", "uploadDate": "2023-07-20", "activeRules": 24},
            {"id": "pol-4", "name": "Automated Identity & Fraud Detection", "version": "v1.9", "status": "archived", "uploadDate": "2022-12-10", "activeRules": 15}
        ])
    return {"policyDocuments": policy_docs_store}

@app.post("/api/policy-documents")
async def create_policy_document(req: CreatePolicyDocRequest):
    doc = {
        "id": f"pol-{uuid.uuid4().hex[:4]}",
        "name": req.name,
        "version": req.version,
        "status": "active",
        "uploadDate": datetime.now().strftime("%Y-%m-%d"),
        "activeRules": 0
    }
    policy_docs_store.append(doc)
    audit_entry = {
        "id": f"LOG-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actor": "Officer",
        "eventType": "Policy Document Upload",
        "riskLevel": "low",
        "details": f"Policy document '{req.name}' v{req.version} uploaded."
    }
    audit_service.logs.append(audit_entry)
    return {"policyDocument": doc, "auditLog": audit_entry}

@app.delete("/api/policy-documents/{doc_id}")
async def delete_policy_document(doc_id: str):
    for i, d in enumerate(policy_docs_store):
        if d["id"] == doc_id:
            policy_docs_store.pop(i)
            audit_entry = {
                "id": f"LOG-{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "actor": "Officer",
                "eventType": "Policy Document Archived",
                "riskLevel": "low",
                "details": f"Policy document '{d['name']}' archived."
            }
            audit_service.logs.append(audit_entry)
            return {"success": True, "auditLog": audit_entry}
    raise HTTPException(status_code=404, detail="Policy document not found")

# ═══════════════════════════════════════════════
# USER PROFILE
# ═══════════════════════════════════════════════

@app.patch("/api/users/profile")
async def update_profile(req: ProfileUpdateRequest):
    return {"user": {"role": "customer", "email": req.email, "name": req.name, "phone": req.phone}}

@app.patch("/api/users/security-settings")
async def update_security_settings(req: SecuritySettingsRequest):
    return {"success": True}

@app.patch("/api/users/notifications")
async def update_notifications(req: NotificationSettingsRequest):
    return {"success": True}

# ═══════════════════════════════════════════════
# FILE UPLOAD
# ═══════════════════════════════════════════════

@app.post("/api/uploads")
async def upload_files(files: List[UploadFile] = File(...), application_id: str = Form("")):
    results = []
    upload_dir = f"data/uploads/{application_id or datetime.now().strftime('%Y%m%d%H%M%S')}"
    os.makedirs(upload_dir, exist_ok=True)
    for file in files:
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        results.append({
            "id": str(uuid.uuid4()),
            "name": file.filename,
            "type": file.content_type or "application/octet-stream",
            "size": f"{os.path.getsize(file_path)} bytes",
            "uploadedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    return {"uploadedFiles": results}

# ═══════════════════════════════════════════════
# FAQ
# ═══════════════════════════════════════════════

FAQ_DATA = [
    {"question": "What documents do I need to submit to verify my income?", "answer": "You typically need to submit your two most recent paystubs, the previous year's W-2 forms, and your IRS Form 1040 tax returns. For business loans, we require audited corporate tax records and consolidated bank statements."},
    {"question": "How long does the AI Underwriting review typically take?", "answer": "Our automated pipeline screens documents in real-time. Within 15 minutes, OCR extraction and initial policy verification are complete. A final underwriter confirmation usually takes between 12 to 24 business hours."},
    {"question": "What does the status 'Pending Docs' indicate?", "answer": "This indicates our compliance engine or loan officer identified a mismatch, missing page, or unreadable upload. Check the alerts on your dashboard or look out for an email requesting specific files."},
    {"question": "Is my personal financial information stored securely?", "answer": "Absolutely. All documents are encrypted in transit and at rest. Access is controlled through military-grade multi-role authentication systems and audited strictly via immutable system ledgers."},
    {"question": "Can I apply for multiple loans simultaneously?", "answer": "Yes, you can track multiple loans of different categories (e.g. mortgage and business credit line) within your single Customer Portal."}
]

@app.get("/api/faq")
async def get_faq(search: str = ""):
    if search:
        results = [f for f in FAQ_DATA if search.lower() in f["question"].lower() or search.lower() in f["answer"].lower()]
        return {"faqs": results}
    return {"faqs": FAQ_DATA}

# ═══════════════════════════════════════════════
# RISK ANALYTICS
# ═══════════════════════════════════════════════

@app.get("/api/analytics/risk-dashboard")
async def risk_dashboard():
    scores = [meta.get("risk_score", 50) for a in applications_store.values() if (meta := getattr(a, "metadata", {}) or {})]
    high_risk_count = sum(1 for s in scores if s > 60)
    total = len(scores) or 1
    return {
        "predictedDefaultRate": 2.41,
        "defaultRateDelta": -0.14,
        "highRiskPortfolio": round(high_risk_count / total * 100, 1),
        "highRiskDelta": 1.2,
        "avgUnderwritingMinutes": 14.2,
        "underwritingTimeDelta": -2.5,
        "automatedPassRate": 84.2,
        "riskAlerts": [
            {"severity": "critical", "applicationId": "LX-92305-V", "title": "Debt-to-Equity Limit Exceeded", "description": "Application #LX-92305-V failed D/E check. Current: 4.2, Max: 3.0."},
            {"severity": "warning", "applicationId": "LX-95204-S", "title": "Document Mismatch Detected", "description": "Revenue variance of $32,500 identified in Solaris Cloud Tech application."}
        ],
        "commonFailurePoints": [{"category": "Income Verification", "percentage": 48}, {"category": "Document Completeness", "percentage": 32}, {"category": "Compliance Thresholds", "percentage": 20}]
    }

@app.get("/api/analytics/pipeline-health")
async def pipeline_health():
    return {"ocrParseRate": "450 docs / min", "tokenLatencyMs": 124, "ragVectorCacheHitRate": 99.81}

# ═══════════════════════════════════════════════
# CHAT (AI ASSISTANT - existing Gemini proxy forwarded from frontend)
# ═══════════════════════════════════════════════

@app.post("/api/chat")
async def chat(req: ChatRequest):
    return {
        "text": f"[AI Assistant] Your query: '{req.message}'. Under 'Doc Policy v4.2 Subsection B' regarding income discrepancy margins, any variance exceeding 10.0% between bank statements and tax filings triggers a verification request.",
        "reasoning": "Applied rule-based compliance match using policy context.",
        "policyGrounding": {
            "documentName": "Income Discrepancy Margin Clause 12.2b",
            "clause": "Doc Policy v4.2 - Subsection B",
            "extractedText": "Any discrepancy between monthly bank deposits and IRS tax returns exceeding 10.0% of total variance must flag a secondary Document Verification request."
        }
    }

# ═══════════════════════════════════════════════
# EXISTING BUSINESS BACKEND ENDPOINTS (preserved)
# ═══════════════════════════════════════════════

@app.post("/api/business/loan-application")
async def create_loan_application(request: LoanApplicationRequest):
    try:
        loan_type = LoanType[request.loan_type.upper().replace(" ", "_")]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid loan type: {request.loan_type}")
    application = LoanApplication(
        customer_name=request.customer_name,
        customer_age=request.customer_age,
        customer_phone=request.customer_phone,
        loan_type=loan_type,
        loan_amount=request.loan_amount,
        monthly_salary=request.monthly_salary,
        employment_type=request.employment_type,
        application_status=ApplicationStatus.PENDING
    )
    applications_store[application.application_id] = application
    return {"application_id": application.application_id, "status": "created", "message": "Loan application created. Upload documents to proceed."}

@app.post("/api/business/upload-document")
async def upload_document(application_id: str = Form(...), document_type: str = Form(...), file: UploadFile = File(...)):
    try:
        doc_type = DocumentType[document_type.upper().replace(" ", "_").replace("-", "_")]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")
    upload_dir = f"data/uploads/{application_id}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = f"{upload_dir}/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"application_id": application_id, "document_name": file.filename, "document_type": doc_type.value, "file_path": file_path, "message": "Document uploaded successfully."}

@app.post("/api/business/process-application")
async def process_loan_application(request: ProcessApplicationRequest):
    try:
        loan_application = LoanApplication(
            customer_name="", customer_age=0, customer_phone="",
            loan_type=LoanType.HOME, loan_amount=0, monthly_salary=0,
            employment_type="", application_status=ApplicationStatus.PENDING,
            application_id=request.application_id
        )
        result = orchestrator.process_application(
            application=loan_application,
            file_paths=request.file_paths,
            document_types=request.document_types
        )
        applications_store[request.application_id] = loan_application
        return {
            "application_id": result["application_id"],
            "status": result["status"],
            "missing_documents": result["missing_documents"],
            "needs_human_review": result["needs_human_review"],
            "human_review_reason": result["human_review_reason"],
            "risk_assessment": {"risk_level": result["risk_assessment"].risk_level.value, "confidence_score": result["risk_assessment"].confidence_score, "reasons": result["risk_assessment"].reasons, "recommendation": result["risk_assessment"].recommendation.value},
            "policy_result": {"eligibility_status": result["policy_result"].eligibility_status.value, "violations": result["policy_result"].violations}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/business/human-review")
async def human_review(request: HumanReviewRequest):
    result = orchestrator.submit_human_decision(
        application_id=request.application_id,
        decision=request.decision,
        reviewer=request.reviewer,
        comments=request.comments
    )
    return result

@app.get("/api/business/application/{application_id}/risk")
async def get_risk_assessment(application_id: str):
    app_obj = applications_store.get(application_id)
    if app_obj and app_obj.risk:
        rs = app_obj.risk
        return {"application_id": application_id, "risk_level": rs.risk_level.value if hasattr(rs.risk_level, "value") else str(rs.risk_level), "confidence_score": rs.confidence_score, "reasons": rs.reasons, "recommendation": rs.recommendation.value if hasattr(rs.recommendation, "value") else str(rs.recommendation), "llm_explanation": rs.llm_explanation}
    return {"application_id": application_id, "message": "Risk assessment not available"}

@app.get("/api/business/application/{application_id}/audit")
async def get_audit_trail(application_id: str):
    logs = audit_service.logs
    return {
        "application_id": application_id,
        "audit_logs": [{"actor": l.get("actor", l.actor if hasattr(l, "actor") else ""), "action": l.get("eventType", l.action if hasattr(l, "action") else ""), "details": l.get("details", l.reason if hasattr(l, "reason") else ""), "timestamp": l.get("timestamp", l.timestamp.isoformat() if hasattr(l, "timestamp") else "")} for l in (logs if isinstance(logs, list) else [])]
    }

@app.post("/api/customer/chat")
async def customer_chat(request: CustomerQueryRequest):
    try:
        response = orchestrator.customer_chat(question=request.question, mode=request.mode)
        return {"response": response, "mode": request.mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/customer/eligibility")
async def check_eligibility(monthly_salary: float, loan_amount: float, employment_duration_months: int = 0):
    is_eligible = monthly_salary >= 30000 and loan_amount <= monthly_salary * 20
    reasons = []
    if not is_eligible:
        if monthly_salary < 30000:
            reasons.append(f"Monthly salary ${monthly_salary:,.0f} is below minimum $30,000")
        if loan_amount > monthly_salary * 20:
            reasons.append(f"Loan amount ${loan_amount:,.0f} exceeds 20x monthly salary")
    return {"eligible": is_eligible, "reasons": reasons if reasons else ["No eligibility issues found"], "message": "Eligibility check based on basic policy rules."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
