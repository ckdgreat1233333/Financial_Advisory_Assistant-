"""
Regulatory & Compliance Copilot - Backend API
---------------------------------------------
Banking domain. Grounded answers to RBI circulars and internal compliance
policies via RAG with strict hallucination prevention, citation enforcement,
confidence scoring, and human-in-the-loop escalation.

Two response layers:
  - Internal track (compliance & audit teams) - citations + escalation.
  - Customer track (transparency assistant)  - plain language + disclaimer.
"""
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid, os, hashlib, secrets, shutil, logging
from datetime import datetime

from services.llm_service import LLMService
from services.regulatory_copilot import RegulatoryCopilot
from utils.enums import AuditSeverity

import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("regulatory_copilot")

app = FastAPI(title="Regulatory & Compliance Copilot",
              description="Grounded regulatory QA over RBI circulars and internal policies for banking compliance teams and customers",
              version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

llm_service = LLMService()

try:
    regulatory_copilot = RegulatoryCopilot()
except Exception as exc:
    logger.warning(f"Regulatory copilot unavailable: {exc}")
    regulatory_copilot = None

# ─── Auth helpers ───
def _hash_pw(p: str) -> str: return hashlib.sha256(p.encode()).hexdigest()
def _verify_pw(p: str, h: str) -> bool: return _hash_pw(p) == h
def _token() -> str: return f"tok-{secrets.token_hex(16)}"

if not db.user_exists("admin"):
    db.create_user("admin", "admin@bankreg.com", "Compliance Officer",
                   "+91 9876543210", _hash_pw("admin123"), "officer")

# ─── Audit helper ───
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

class RegulatoryQueryRequest(BaseModel):
    question: str

# ══════════════════════════════════════════════════
# ROOT
# ══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    idx = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(idx):
        with open(idx, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return {"service": "Regulatory & Compliance Copilot", "version": "1.0.0"}

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

@app.get("/api/users")
async def list_users():
    return {"users": db.list_users()}

@app.delete("/api/users/{username}")
async def remove_user(username: str):
    if not db.delete_user(username):
        raise HTTPException(404, "User not found")
    db.create_audit_log(f"LOG-{uuid.uuid4().hex[:8]}", "Admin", "User Deletion",
                        f"User {username} removed")
    return {"success": True}

# ══════════════════════════════════════════════════
# AUDIT LOGS
# ══════════════════════════════════════════════════

@app.get("/api/audit-logs")
async def list_audit_logs(riskLevel: str = ""):
    logs = db.list_audit_logs(risk_level=riskLevel)
    return {"logs": logs}

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

@app.get("/api/faq")
async def get_faq(search: str = ""):
    faqs = db.list_faqs(search=search)
    return {"faqs": faqs}

# ══════════════════════════════════════════════════
# REGULATORY & COMPLIANCE COPILOT
# ══════════════════════════════════════════════════

@app.post("/api/regulatory/query")
async def regulatory_query(req: RegulatoryQueryRequest):
    """Internal track - compliance & audit teams. Returns grounded answer
    with citations, confidence score, and escalation recommendation."""
    if regulatory_copilot is None:
        raise HTTPException(503, "Regulatory copilot unavailable")
    answer = regulatory_copilot.answer_internal(req.question)
    payload = answer.to_dict(include_retrieved=True)
    _audit_entry(req.question[:60] or "regulatory-query", "Regulatory Query",
                 f"Internal query: {req.question[:120]}",
                 "high" if answer.needs_escalation else "low")
    return payload

@app.post("/api/regulatory/customer-query")
async def regulatory_customer_query(req: RegulatoryQueryRequest):
    """Customer track - transparency assistant. Returns plain-language answer
    with disclaimer. Internal retrieval details are never exposed."""
    if regulatory_copilot is None:
        raise HTTPException(503, "Regulatory copilot unavailable")
    answer = regulatory_copilot.answer_customer(req.question)
    payload = answer.to_dict(include_retrieved=False)
    _audit_entry(req.question[:60] or "customer-regulatory-query", "Customer Regulatory Query",
                 f"Customer query: {req.question[:120]}", "low")
    return payload

@app.get("/api/regulatory/documents")
async def regulatory_documents():
    """List the version-controlled regulatory corpus (approved documents)."""
    return {"documents": db.list_regulatory_docs()}

@app.post("/api/regulatory/documents")
async def ingest_regulatory_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    circular_no: str = Form(""),
    issue_date: str = Form(""),
    version: str = Form(""),
    category: str = Form("circular"),
):
    """Ingest a new approved regulatory document (txt / pdf / md).

    The file is stored in the approved corpus directory and the FAISS index
    is rebuilt so the copilot immediately answers from it.
    """
    if regulatory_copilot is None:
        raise HTTPException(503, "Regulatory copilot unavailable")

    fname = file.filename or "document.txt"
    ext = os.path.splitext(fname)[1].lower()
    if ext not in (".txt", ".pdf", ".md"):
        raise HTTPException(400, "Only .txt, .pdf and .md files are supported")

    corpus_dir = regulatory_copilot.store.corpus_dir
    os.makedirs(corpus_dir, exist_ok=True)

    # Prefix the filename with a slug from the optional title to keep a stable doc_id.
    doc_id = os.path.splitext(fname)[0].replace(" ", "_").lower()
    dest = corpus_dir / f"{doc_id}{ext}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Rebuild the store from the corpus so the new document is retrievable.
    regulatory_copilot.store.ingest()

    row = db.get_regulatory_doc(doc_id)
    if row and (title or circular_no or issue_date or version):
        db.upsert_regulatory_doc(
            doc_id=doc_id,
            title=title or row["title"],
            circular_no=circular_no or row["circular_no"],
            issue_date=issue_date or row["issue_date"],
            version=version or row["version"],
            category=category or row["category"],
            file_path=row["file_path"],
            file_hash=row["file_hash"],
        )
        row = db.get_regulatory_doc(doc_id)

    _audit_entry("Compliance Officer", "Regulatory Document Ingest",
                 f"Document '{fname}' ingested into the regulatory corpus.", "low")
    return {"document": row, "ingested": True}

@app.delete("/api/regulatory/documents/{doc_id}")
async def delete_regulatory_document(doc_id: str):
    """Remove a document from the approved corpus and rebuild the index."""
    if regulatory_copilot is None:
        raise HTTPException(503, "Regulatory copilot unavailable")

    row = db.get_regulatory_doc(doc_id)
    if not row:
        raise HTTPException(404, "Regulatory document not found")

    file_path = row.get("file_path", "")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    db.delete_regulatory_doc(doc_id)
    regulatory_copilot.store.ingest()
    _audit_entry("Compliance Officer", "Regulatory Document Archived",
                 f"Document '{doc_id}' archived from the regulatory corpus.", "medium")
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
