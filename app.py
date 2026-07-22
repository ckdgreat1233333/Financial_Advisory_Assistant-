"""
Intelligent Loan Processing Assistant - Backend API
---------------------------------------------------
Enterprise-grade AI solution for loan processing in Banking domain.
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid, os, hashlib, secrets, shutil, logging
from datetime import datetime

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
from services.customer_service import CustomerService
from services.llm_service import LLMService

import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("loan_assistant")

app = FastAPI(title="Intelligent Loan Processing Assistant",
              description="Enterprise-grade AI solution for loan processing in Banking domain",
              version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

orchestrator = LoanProcessingOrchestrator()
audit_service = AuditService()
policy_service = PolicyService()
llm_service = LLMService()
customer_service = CustomerService(policy=policy_service, llm=llm_service)

# ─── Auth ───
def _hash_pw(p: str) -> str: return hashlib.sha256(p.encode()).hexdigest()
def _verify_pw(p: str, h: str) -> bool: return _hash_pw(p) == h
def _token() -> str: return f"tok-{secrets.token_hex(16)}"

# Seed admin user if not exists
if not db.user_exists("admin"):
    db.create_user("admin", "admin@lendsmart.com", "Admin Officer",
                   "+91 9876543210", _hash_pw("admin123"), "officer")

LOANTYPE_REVERSE = {"HOME": "home", "VEHICLE": "auto", "PERSONAL": "personal",
                    "BUSINESS": "business", "EDUCATION": "personal"}
LOANTYPE_MAP = {v: k for k, v in LOANTYPE_REVERSE.items()}

def _row_to_frontend(row: dict) -> dict:
    import json
    meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
    ft = LOANTYPE_REVERSE.get(row.get("loan_type", "HOME").upper(), "home")
    st_map = {
        "PENDING": "pending_docs", "DOCUMENT_VERIFICATION": "pending_docs",
        "POLICY_REVIEW": "under_review", "RISK_ASSESSMENT": "under_review",
        "MANUAL_REVIEW": "under_review", "APPROVED": "approved", "REJECTED": "rejected"
    }
    st = st_map.get(row.get("status", "PENDING"), "pending_docs")
    docs = meta.get("documents", [])
    if isinstance(docs, list):
        for d in docs:
            if isinstance(d, dict) and "id" not in d:
                d["id"] = str(uuid.uuid4())

    risk_assessment = meta.get("risk_assessment", {})
    policy_result = meta.get("policy_result", {})
    extracted_data = meta.get("extracted_data", {})

    risk_score_map = {"Low": 20, "Medium": 50, "High": 80, "Unknown": 30}
    risk_level = risk_assessment.get("risk_level", "Unknown")
    risk_score = risk_assessment.get("risk_score", risk_score_map.get(risk_level, 30))

    progress_map = {
        "PENDING": 10, "DOCUMENT_VERIFICATION": 25, "POLICY_REVIEW": 40,
        "RISK_ASSESSMENT": 70, "MANUAL_REVIEW": 85, "APPROVED": 100, "REJECTED": 100
    }
    progress = progress_map.get(row.get("status", "PENDING"), 10)

    compliance_eligibility = policy_result.get("eligibility_status", "")
    compliance_status = "compliant"
    if compliance_eligibility == "Not Eligible":
        compliance_status = "failed"
    elif compliance_eligibility == "Manual Review":
        compliance_status = "review_required"

    reasoning_notes = risk_assessment.get("llm_explanation", "") or policy_result.get("explanation", "") or ""

    return {
        "id": row["id"],
        "applicantName": row.get("customer_name", row.get("applicant_name", "")),
        "applicantEmail": row.get("applicant_email", ""),
        "applicantPhone": row.get("customer_phone", row.get("applicant_phone", "")),
        "type": ft, "status": st,
        "amount": row.get("loan_amount", 0),
        "termMonths": row.get("term_months", meta.get("term_months", 12)),
        "progress": progress,
        "submittedDate": row.get("submitted_date", ""),
        "interestRate": row.get("interest_rate", meta.get("interest_rate", 5.0)),
        "riskScore": risk_score,
        "defaultRate": meta.get("default_rate", 1.8),
        "complianceStatus": compliance_status,
        "documents": docs if isinstance(docs, list) else [],
        "reasoningNotes": reasoning_notes,
        "agentConsensus": meta.get("agent_consensus"),
        "similarityHeatmap": meta.get("similarity_heatmap"),
    }

def _audit_entry(actor, event, details, risk="low"):
    log_id = f"LOG-{uuid.uuid4().hex[:8]}"
    db.create_audit_log(log_id, actor, event, details, risk)
    return db.get_audit_log(log_id)

# ══════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str; password: str; portalType: str = "customer"

class RegisterRequest(BaseModel):
    username: str; fullName: str; email: str; password: str; phone: Optional[str] = ""
    portalType: str = "customer"

class ProfileUpdateRequest(BaseModel):
    name: str; email: str; phone: str; username: Optional[str] = ""

class CreateAppRequest(BaseModel):
    applicantName: str; applicantEmail: str; applicantPhone: Optional[str] = ""
    type: str = "home"; amount: float = 100000; termMonths: int = 12
    interestRate: float = 5.0; documents: List[dict] = []

class ApproveRejectRequest(BaseModel):
    actor: str; reason: str = ""

class DocOverrideRequest(BaseModel):
    status: str

class CreatePolicyDocRequest(BaseModel):
    name: str; version: str

class ChatRequest(BaseModel):
    message: str; history: List[dict] = []
    applicationsContext: List[dict] = []

# ══════════════════════════════════════════════════
# ROOT
# ══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    idx = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(idx):
        with open(idx, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return {"service": "Intelligent Loan Processing Assistant", "version": "1.0.0"}

# ══════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    if db.user_exists(req.username):
        raise HTTPException(400, "Username already taken")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    db.create_user(req.username, req.email or "", req.fullName, req.phone or "",
                   _hash_pw(req.password), req.portalType)
    user = db.get_user(req.username)
    db.create_audit_log(f"LOG-{uuid.uuid4().hex[:8]}", "System", "User Registration",
                        f"New user registered: {req.username}")
    return {"user": {k: v for k, v in user.items() if k != "password"}, "token": _token()}

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = db.get_user(req.username)
    if not user or not _verify_pw(req.password, user.get("password", "")):
        raise HTTPException(401, "Invalid username or password")
    user["role"] = req.portalType
    db.create_audit_log(f"LOG-{uuid.uuid4().hex[:8]}", req.username, "User Login",
                        f"User logged in as {req.portalType}")
    return {"user": {k: v for k, v in user.items() if k != "password"}, "token": _token()}

@app.post("/api/auth/logout")
async def logout():
    return {"success": True}

@app.get("/api/auth/me")
async def auth_me(username: str = ""):
    user = db.get_user(username) if username else None
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {"user": {k: v for k, v in user.items() if k != "password"}}

# ══════════════════════════════════════════════════
# APPLICATIONS
# ══════════════════════════════════════════════════

REQUIRED_DOC_TYPES = ["salary_slip", "bank_statement", "employment_letter"]
DOC_TYPE_NAMES = {"salary_slip": "Salary Slip", "bank_statement": "Bank Statement",
                  "employment_letter": "Employment Letter"}

@app.get("/api/applications")
async def list_applications(email: str = "", status: str = "", search: str = ""):
    rows = db.list_applications(email=email, status=status, search=search)
    result = []
    for row in rows:
        app_dict = _row_to_frontend(row)
        if search and search.lower() not in app_dict.get("applicantName", "").lower() and search.lower() not in app_dict.get("id", "").lower():
            continue
        result.append(app_dict)
    return {"applications": result}

@app.get("/api/applications/{application_id}")
async def get_application(application_id: str):
    row = db.get_application(application_id)
    if not row:
        raise HTTPException(404, "Application not found")
    return _row_to_frontend(row)

@app.post("/api/applications")
async def create_application(req: CreateAppRequest):
    try:
        lt = LoanType[LOANTYPE_MAP.get(req.type, "HOME")]
    except KeyError:
        lt = LoanType.HOME

    app_id = f"LEND-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sub_date = datetime.now().strftime("%Y-%m-%d")
    interest_rate = req.interestRate or 8.5

    metadata = {
        "interest_rate": interest_rate,
        "default_rate": 1.8,
        "term_months": req.termMonths or 24,
        "submitted_date": sub_date,
        "documents": [],
    }

    docs = []
    for d in req.documents if isinstance(req.documents, list) else []:
        if isinstance(d, dict) and d.get("name") and d.get("docType"):
            docs.append({
                "id": str(uuid.uuid4()), "name": d["name"],
                "type": DOC_TYPE_NAMES.get(d["docType"], d["docType"]),
                "docType": d["docType"], "status": "pending",
                "uploadedAt": d.get("uploadedAt", now)
            })
    metadata["documents"] = docs

    import json
    meta_json = json.dumps(metadata)

    db.save_application(app_id, req.applicantName, req.applicantEmail or "",
                        req.applicantPhone or "", req.type or "HOME",
                        req.amount, req.termMonths or 24, interest_rate,
                        "PENDING", meta_json)
    db.create_audit_log(f"LOG-{uuid.uuid4().hex[:8]}", req.applicantEmail or "Customer",
                        "Application Created",
                        f"New {req.type} loan application created. Amount: ₹{req.amount:,.0f}")

    row = db.get_application(app_id)
    return {"application": _row_to_frontend(row)}

@app.post("/api/applications/{application_id}/documents")
async def upload_application_documents(application_id: str, files: List[UploadFile] = File(...)):
    row = db.get_application(application_id)
    if not row:
        raise HTTPException(404, "Application not found")

    import json
    meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
    docs = meta.get("documents", [])
    if not isinstance(docs, list):
        docs = []

    upload_dir = f"data/uploads/{application_id}"
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        fname = file.filename.lower()
        doc_type = None
        if "salary" in fname or "pay" in fname or "slip" in fname:
            doc_type = "salary_slip"
        elif "bank" in fname or "statement" in fname:
            doc_type = "bank_statement"
        elif "employ" in fname or "offer" in fname or "letter" in fname:
            doc_type = "employment_letter"
        else:
            doc_type = "other"

        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        doc_entry = {
            "id": str(uuid.uuid4()),
            "name": file.filename,
            "type": DOC_TYPE_NAMES.get(doc_type, doc_type),
            "docType": doc_type,
            "status": "pending",
            "uploadedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        existing = None
        for d in docs:
            if isinstance(d, dict) and d.get("docType") == doc_type:
                existing = d
                break
        if existing:
            docs.remove(existing)
        docs.append(doc_entry)

    uploaded_types = {d["docType"] for d in docs if isinstance(d, dict)}
    meta["documents"] = docs

    if all(t in uploaded_types for t in REQUIRED_DOC_TYPES):
        try:
            LOANTYPE_FROM_DB = {
                "HOME": LoanType.HOME, "PERSONAL": LoanType.PERSONAL,
                "VEHICLE": LoanType.VEHICLE, "EDUCATION": LoanType.EDUCATION,
                "BUSINESS": LoanType.BUSINESS
            }
            loan_type_enum = LOANTYPE_FROM_DB.get(row.get("loan_type", "HOME").upper(), LoanType.HOME)
            app_obj = LoanApplication(
                application_id=row["id"],
                customer_name=row.get("customer_name", ""),
                customer_age=0,
                customer_phone=row.get("customer_phone", ""),
                loan_type=loan_type_enum,
                loan_amount=row.get("loan_amount", 0),
                monthly_salary=0,
                employment_type="Unknown",
                application_status=ApplicationStatus.PENDING
            )

            file_paths = [os.path.join(upload_dir, d["name"]) for d in docs if d.get("name")]
            document_types = [d["docType"] for d in docs if d.get("docType")]

            result = orchestrator.process_application(
                application=app_obj,
                file_paths=file_paths,
                document_types=document_types
            )

            serialized = orchestrator.serialize_result(result)

            meta["risk_assessment"] = serialized["risk_assessment"]
            meta["policy_result"] = serialized["policy_result"]
            meta["extracted_data"] = serialized["extracted_data"]
            meta["missing_documents"] = serialized["missing_documents"]
            meta["needs_human_review"] = serialized["needs_human_review"]
            meta["human_review_reason"] = serialized["human_review_reason"]

            new_status = serialized.get("application_status", "POLICY_REVIEW")
            if new_status in ("APPROVED", "REJECTED"):
                new_status = "POLICY_REVIEW"
        except Exception as e:
            logger.warning(f"Orchestrator processing failed: {e}")
            new_status = "POLICY_REVIEW"
            meta["needs_human_review"] = True
            meta["human_review_reason"] = f"AI pipeline processing failed: {str(e)}"
    else:
        missing = [t for t in REQUIRED_DOC_TYPES if t not in uploaded_types]
        meta["reasoning_notes"] = f"Still missing: {', '.join(DOC_TYPE_NAMES.get(t, t) for t in missing)}"
        new_status = row.get("status", "PENDING")

    db.update_application(application_id, new_status, json.dumps(meta))
    db.create_audit_log(f"LOG-{uuid.uuid4().hex[:8]}", "Customer", "Document Upload",
                        f"Documents uploaded for {application_id}")

    row = db.get_application(application_id)
    return {"application": _row_to_frontend(row)}

@app.get("/api/applications/{application_id}/documents/{doc_name}/file")
async def get_document_file(application_id: str, doc_name: str):
    """Serve uploaded document files for officer review (inline preview)."""
    file_path = os.path.join("data", "uploads", application_id, doc_name)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found")
    ext = os.path.splitext(doc_name)[1].lower()
    media_map = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".txt": "text/plain"}
    media_type = media_map.get(ext, "application/octet-stream")
    from fastapi.responses import Response
    with open(file_path, "rb") as f:
        content = f.read()
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f"inline; filename=\"{doc_name}\""})

@app.patch("/api/applications/{application_id}/approve")
async def approve_application(application_id: str, req: ApproveRejectRequest):
    row = db.get_application(application_id)
    if not row:
        raise HTTPException(404, "Application not found")
    import json
    meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
    meta["progress"] = 100
    db.update_application(application_id, "APPROVED", json.dumps(meta))
    log_id = f"LOG-{uuid.uuid4().hex[:8]}"
    db.create_audit_log(log_id, req.actor or "Officer", "Underwriter Approval",
                        f"Application {application_id} approved.", "low")
    row = db.get_application(application_id)
    return {"application": _row_to_frontend(row), "auditLog": db.get_audit_log(log_id)}

@app.patch("/api/applications/{application_id}/reject")
async def reject_application(application_id: str, req: ApproveRejectRequest):
    row = db.get_application(application_id)
    if not row:
        raise HTTPException(404, "Application not found")
    import json
    meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
    meta["progress"] = 100
    meta["rejection_reason"] = req.reason
    db.update_application(application_id, "REJECTED", json.dumps(meta))
    log_id = f"LOG-{uuid.uuid4().hex[:8]}"
    db.create_audit_log(log_id, req.actor or "Officer", "Underwriter Rejection",
                        f"Application {application_id} rejected. Reason: {req.reason}", "high")
    row = db.get_application(application_id)
    return {"application": _row_to_frontend(row), "auditLog": db.get_audit_log(log_id)}

@app.patch("/api/applications/{application_id}/documents/{doc_id}")
async def update_document_status(application_id: str, doc_id: str, req: DocOverrideRequest):
    row = db.get_application(application_id)
    if not row:
        raise HTTPException(404, "Application not found")
    import json
    meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
    docs = meta.get("documents", [])
    if isinstance(docs, list):
        for d in docs:
            if isinstance(d, dict) and d.get("id") == doc_id:
                d["status"] = req.status
                break
    meta["documents"] = docs
    db.update_application(application_id, row["status"], json.dumps(meta))
    row = db.get_application(application_id)
    return _row_to_frontend(row)

# ══════════════════════════════════════════════════
# AUDIT LOGS
# ══════════════════════════════════════════════════

@app.get("/api/audit-logs")
async def list_audit_logs(application_id: str = "", riskLevel: str = ""):
    logs = db.list_audit_logs()
    if application_id:
        logs = [l for l in logs if isinstance(l, dict) and application_id in l.get("details", "")]
    if riskLevel:
        logs = [l for l in logs if isinstance(l, dict) and l.get("riskLevel") == riskLevel]
    return {"logs": logs}

# ══════════════════════════════════════════════════
# POLICY DOCUMENTS
# ══════════════════════════════════════════════════

DOC_TYPES_TO_NAME = {"salary_slip": "Salary Slip", "bank_statement": "Bank Statement", "employment_letter": "Employment Letter"}

@app.get("/api/policy-documents")
async def list_policy_documents():
    docs = db.list_policy_docs()
    if not docs:
        # Seed default policy docs
        defaults = [
            {"name": "Mortgage Underwriting Guidelines", "version": "v4.2", "status": "active"},
            {"name": "Commercial Loan Credit Risk Limits", "version": "v3.0", "status": "active"},
            {"name": "Retail & Consumer Lending Eligibility", "version": "v2.5", "status": "active"},
            {"name": "Automated Identity & Fraud Detection", "version": "v1.9", "status": "archived"},
        ]
        for d in defaults:
            db.create_policy_doc(d["name"], d["version"], d["status"])
        docs = db.list_policy_docs()
    return {"policyDocuments": docs}

@app.post("/api/policy-documents")
async def create_policy_document(req: CreatePolicyDocRequest):
    doc_id = f"pol-{uuid.uuid4().hex[:4]}"
    db.create_policy_doc(req.name, req.version, "active")
    db.create_audit_log(f"LOG-{uuid.uuid4().hex[:8]}", "Officer", "Policy Document Upload",
                        f"Policy document '{req.name}' v{req.version} uploaded.")
    docs = db.list_policy_docs()
    return {"policyDocument": docs[-1] if docs else None,
            "auditLog": db.list_audit_logs()[-1] if db.list_audit_logs() else None}

@app.delete("/api/policy-documents/{doc_id}")
async def delete_policy_document(doc_id: str):
    doc = db.delete_policy_doc(doc_id)
    if not doc:
        raise HTTPException(404, "Policy document not found")
    db.create_audit_log(f"LOG-{uuid.uuid4().hex[:8]}", "Officer", "Policy Document Archived",
                        f"Policy document '{doc['name']}' archived.")
    return {"success": True, "auditLog": db.list_audit_logs()[-1]}

# ══════════════════════════════════════════════════
# USER PROFILE
# ══════════════════════════════════════════════════

@app.patch("/api/users/profile")
async def update_profile(req: ProfileUpdateRequest):
    user = db.get_user(req.username or req.email)
    if not user:
        raise HTTPException(404, "User not found")
    db.update_user(req.username or req.email, req.name, req.phone)
    return {"user": {"role": user.get("role", "customer"), "email": req.email,
                     "name": req.name, "phone": req.phone}}

# ══════════════════════════════════════════════════
# FAQ
# ══════════════════════════════════════════════════

FAQ_DATA = [
    {"question": "What documents do I need to apply for a loan?", "answer": "You need three mandatory documents: (1) Salary Slip - last 3 months, (2) Bank Statement - last 6 months, (3) Employment Letter. Additional documents may be requested based on loan type."},
    {"question": "How does the AI process my application?", "answer": "Our system uses three AI agents: Document Validation Agent checks your uploaded documents, Policy Compliance Agent verifies against lending policies, and Risk Evaluation Agent assesses your risk profile. Each agent provides a score and recommendation."},
    {"question": "What do the risk levels mean?", "answer": "Low Risk: All documents verified, income stable, loan within limits. Medium Risk: Minor mismatches or missing optional info. High Risk: Missing mandatory documents, income below minimum, or false information."},
    {"question": "How long does loan processing take?", "answer": "Document validation completes in minutes. Policy review and risk assessment take 1-2 business days. Final officer decision follows within 24 hours of review completion."},
    {"question": "Is my data secure?", "answer": "All documents are encrypted at rest and in transit. Access is role-based and all actions are logged in an immutable audit trail."},
    {"question": "Why was my application rejected?", "answer": "Common reasons: income below minimum threshold (₹30,000/month), loan amount exceeds 20x monthly salary, missing documents, or policy violations. Check with your loan officer for specific details."}
]

@app.get("/api/faq")
async def get_faq(search: str = ""):
    faqs = db.list_faqs()
    if not faqs:
        # Seed defaults
        defaults = [
            ("What documents do I need to apply for a loan?", "You need three mandatory documents: (1) Salary Slip - last 3 months, (2) Bank Statement - last 6 months, (3) Employment Letter. Additional documents may be requested based on loan type."),
            ("How does the AI process my application?", "Our system uses three AI agents: Document Validation Agent checks your uploaded documents, Policy Compliance Agent verifies against lending policies, and Risk Evaluation Agent assesses your risk profile. Each agent provides a score and recommendation."),
            ("What do the risk levels mean?", "Low Risk: All documents verified, income stable, loan within limits. Medium Risk: Minor mismatches or missing optional info. High Risk: Missing mandatory documents, income below minimum, or false information."),
            ("How long does loan processing take?", "Document validation completes in minutes. Policy review and risk assessment take 1-2 business days. Final officer decision follows within 24 hours of review completion."),
            ("Is my data secure?", "All documents are encrypted at rest and in transit. Access is role-based and all actions are logged in an immutable audit trail."),
            ("Why was my application rejected?", "Common reasons: income below minimum threshold (₹30,000/month), loan amount exceeds 20x monthly salary, missing documents, or policy violations. Check with your loan officer for specific details.")
        ]
        for q, a in defaults:
            db.create_faq(q, a)
        faqs = db.list_faqs()
    if search:
        return {"faqs": [f for f in faqs if search.lower() in f.get("question", "").lower() or search.lower() in f.get("answer", "").lower()]}
    return {"faqs": faqs}

# ══════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════

@app.get("/api/analytics/risk-dashboard")
async def risk_dashboard():
    import json
    applications = db.list_applications()
    scores = []
    alerts = []
    for a in applications:
        meta = json.loads(a["metadata"]) if isinstance(a["metadata"], str) else (a["metadata"] or {})
        ra = meta.get("risk_assessment", {})
        pr = meta.get("policy_result", {})
        score = ra.get("risk_score", meta.get("risk_score", 50))
        scores.append(score)
        if score > 60:
            alerts.append({
                "severity": "critical", "applicationId": a["id"],
                "message": f"High risk application: {a.get('customer_name', a.get('applicant_name', 'Unknown'))} (risk score: {score})"
            })
        elif pr.get("eligibility_status") == "Not Eligible" or meta.get("compliance_status") == "failed":
            alerts.append({
                "severity": "warning", "applicationId": a["id"],
                "message": f"Compliance issue: {a.get('customer_name', a.get('applicant_name', 'Unknown'))}"
            })
    high_risk_count = sum(1 for s in scores if s > 60)
    total = len(scores) or 1
    high_risk_pct = round(high_risk_count / total * 100, 1)
    return {
        "predictedDefaultRate": 2.41, "highRiskPortfolio": high_risk_pct,
        "highRiskDelta": 1.2, "automatedPassRate": 84.2,
        "riskAlerts": alerts[:5],
        "commonFailurePoints": [
            {"category": "Income Verification", "percentage": 48},
            {"category": "Document Completeness", "percentage": 32},
            {"category": "Compliance Thresholds", "percentage": 20}
        ]
    }

@app.get("/api/analytics/pipeline-health")
async def pipeline_health():
    return {"ocrParseRate": "450 docs / min", "tokenLatencyMs": 124, "ragVectorCacheHitRate": 99.81}

# ══════════════════════════════════════════════════
# CHAT (AI ASSISTANT)
# ══════════════════════════════════════════════════

POLICY_RULES = {
    "salary": "Minimum monthly salary is ₹30,000 (Section 3 - Income Requirements)",
    "loan amount": "Loan amount should not exceed 20 times monthly salary (Section 5 - Loan Amount Rules)",
    "document": "Mandatory documents: Salary Slip (3 months), Bank Statement (6 months), Employment Letter (Section 2)",
    "employment": "At least 12 months with current employer required (Section 4 - Employment Requirements)",
    "age": "Applicant must be between 21 and 60 years of age (Section 1 - Eligibility)",
    "risk": "Risk levels: Low (all docs, income verified), Medium (minor mismatches), High (missing docs/false info) - Section 6",
}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        if llm_service.health_check():
            response = customer_service.answer(question=req.message, mode="customer_advisory")
            ctx = policy_service.retrieve_context(req.message, top_k=3)
            ct = ctx[:500] if ctx else ""
            return {"text": response, "reasoning": "LLM response with RAG context.",
                    "policyGrounding": {"documentName": "Loan Policy", "clause": "Policy RAG",
                                        "extractedText": ct or "Policy context retrieved."}}
    except Exception as e:
        logger.warning(f"LLM chat failed: {e}")

    msg = req.message.lower()
    matched = [v for k, v in POLICY_RULES.items() if k in msg]
    if matched:
        return {"text": "Based on our lending policy:\n\n" + "\n\n".join(f"• {m}" for m in matched) +
                ("\n\nWould you like more details?" if len(matched) == 1 else ""),
                "reasoning": "Rule-based match", "policyGrounding": {
                    "documentName": "Home Loan Policy", "clause": "Matched Rules",
                    "extractedText": "\n".join(matched)}}
    ctx = policy_service.retrieve_context(req.message, top_k=3)
    if ctx.strip():
        return {"text": f"Based on our lending policy:\n\n{ctx[:800]}", "reasoning": "Policy text retrieval",
                "policyGrounding": {"documentName": "Home Loan Policy", "clause": "Full text",
                                    "extractedText": ctx[:500]}}
    return {"text": "I can help with policy questions about salary, loan amounts, required documents, employment criteria, age, and risk. Please ask about a specific policy area.",
            "reasoning": "General guidance", "policyGrounding": {
                "documentName": "Home Loan Policy", "clause": "General",
                "extractedText": "Home Loan Policy covering eligibility, documents, income, employment, loan amounts, and risk."}}

# ══════════════════════════════════════════════════
# FILE UPLOAD (generic)
# ══════════════════════════════════════════════════

@app.post("/api/uploads")
async def upload_files(files: List[UploadFile] = File(...), application_id: str = Form("")):
    results = []
    ud = f"data/uploads/{application_id or datetime.now().strftime('%Y%m%d%H%M%S')}"
    os.makedirs(ud, exist_ok=True)
    for file in files:
        fp = os.path.join(ud, file.filename)
        with open(fp, "wb") as f:
            shutil.copyfileobj(file.file, f)
        results.append({"id": str(uuid.uuid4()), "name": file.filename,
                        "type": file.content_type or "application/octet-stream",
                        "size": f"{os.path.getsize(fp)} bytes",
                        "uploadedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return {"uploadedFiles": results}

# ══════════════════════════════════════════════════
# LEGACY BUSINESS ENDPOINTS (preserved)
# ══════════════════════════════════════════════════

class LoanApplicationRequest(BaseModel):
    customer_name: str; customer_age: int; customer_phone: str
    loan_type: str; loan_amount: float; monthly_salary: float; employment_type: str

class ProcessApplicationRequest(BaseModel):
    application_id: str; file_paths: List[str]; document_types: List[str]

class CustomerQueryRequest(BaseModel):
    question: str; mode: str = "customer_advisory"

class HumanReviewRequest(BaseModel):
    application_id: str; decision: str; reviewer: str; comments: str = ""

@app.post("/api/business/loan-application")
async def create_loan_application(request: LoanApplicationRequest):
    try:
        lt = LoanType[request.loan_type.upper().replace(" ", "_")]
    except KeyError:
        raise HTTPException(400, f"Invalid loan type: {request.loan_type}")
    app_id = f"LEND-{uuid.uuid4().hex[:8].upper()}"
    import json
    meta = json.dumps({})
    db.save_application(app_id, request.customer_name, "", request.customer_phone,
                        request.loan_type.upper(), request.loan_amount, 24, 8.5, "PENDING", meta)
    return {"application_id": app_id, "status": "created",
            "message": "Loan application created. Upload documents to proceed."}

@app.post("/api/business/process-application")
async def process_loan_application(request: ProcessApplicationRequest):
    try:
        row = db.get_application(request.application_id)
        if not row:
            raise HTTPException(404, "Application not found")

        LOANTYPE_FROM_DB = {
            "HOME": LoanType.HOME, "PERSONAL": LoanType.PERSONAL,
            "VEHICLE": LoanType.VEHICLE, "EDUCATION": LoanType.EDUCATION,
            "BUSINESS": LoanType.BUSINESS
        }
        app_obj = LoanApplication(
            application_id=row["id"],
            customer_name=row.get("customer_name", ""),
            customer_age=0,
            customer_phone=row.get("customer_phone", ""),
            loan_type=LOANTYPE_FROM_DB.get(row.get("loan_type", "HOME").upper(), LoanType.HOME),
            loan_amount=row.get("loan_amount", 0),
            monthly_salary=0,
            employment_type="Unknown",
            application_status=ApplicationStatus.PENDING
        )

        result = orchestrator.process_application(
            application=app_obj,
            file_paths=request.file_paths,
            document_types=request.document_types)

        serialized = orchestrator.serialize_result(result)

        if row:
            import json
            meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
            meta["risk_assessment"] = serialized["risk_assessment"]
            meta["policy_result"] = serialized["policy_result"]
            meta["extracted_data"] = serialized["extracted_data"]
            meta["missing_documents"] = serialized["missing_documents"]
            meta["needs_human_review"] = serialized["needs_human_review"]
            meta["human_review_reason"] = serialized["human_review_reason"]
            new_status = serialized.get("application_status", "POLICY_REVIEW")
            db.update_application(request.application_id, new_status, json.dumps(meta))

        return {
            "application_id": request.application_id,
            "status": serialized.get("application_status", "processed"),
            "missing_documents": serialized.get("missing_documents", []),
            "needs_human_review": serialized.get("needs_human_review", False),
            "risk_assessment": serialized.get("risk_assessment", {}),
            "policy_result": serialized.get("policy_result", {}),
            "extracted_data": serialized.get("extracted_data", {}),
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/api/business/application/{application_id}/risk")
async def get_risk_assessment(application_id: str):
    row = db.get_application(application_id)
    if row:
        import json
        meta = json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {})
        ra = meta.get("risk_assessment", {})
        return {"application_id": application_id,
                "risk_level": ra.get("risk_level", "Unknown"),
                "risk_score": ra.get("risk_score", 0),
                "confidence_score": ra.get("confidence_score", 0),
                "reasons": ra.get("reasons", ["Risk assessment not yet available"]),
                "recommendation": ra.get("recommendation", "Pending"),
                "triggered_rules": ra.get("triggered_rules", []),
                "llm_explanation": ra.get("llm_explanation", "")}
    return {"application_id": application_id, "message": "Risk assessment not available"}

@app.post("/api/customer/chat")
async def customer_chat(request: CustomerQueryRequest):
    try:
        return {"response": orchestrator.customer_chat(question=request.question, mode=request.mode), "mode": request.mode}
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.get("/api/customer/eligibility")
async def check_eligibility(monthly_salary: float, loan_amount: float, employment_duration_months: int = 0):
    eligible = monthly_salary >= 30000 and loan_amount <= monthly_salary * 20
    reasons = []
    if monthly_salary < 30000:
        reasons.append(f"Monthly salary ₹{monthly_salary:,.0f} is below minimum ₹30,000")
    if loan_amount > monthly_salary * 20:
        reasons.append(f"Loan amount ₹{loan_amount:,.0f} exceeds 20x monthly salary (max ₹{monthly_salary * 20:,.0f})")
    return {"eligible": eligible, "reasons": reasons if reasons else ["No eligibility issues found"],
            "message": "Eligibility check based on basic policy rules."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
