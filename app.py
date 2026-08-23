"""
Personalized Financial Advisory Assistant - Backend API
-------------------------------------------------------
Banking domain. Supports relationship managers (business track) and customers
(customer track) with responsible, explainable, compliance-aligned GenAI.

Recommendation logic:
  - Deterministic suitability engine decides (guardrails against mis-selling)
  - Product knowledge RAG grounds every explanation
  - LLM only verbalizes engine output, never invents products
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import uuid, os, hashlib, secrets, logging

from services.llm_service import LLMService

import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("advisory")

app = FastAPI(title="Personalized Financial Advisory Assistant",
              description="Responsible, explainable, compliance-aligned financial advisory "
                          "for relationship managers and customers (banking domain)",
              version="2.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])

llm_service = LLMService()

advisory_service = None
try:
    from services.advisory_service import AdvisoryService
    advisory_service = AdvisoryService()
except Exception as exc:
    logger.warning(f"Advisory service unavailable: {exc}")

# ─── Auth helpers ───
def _hash_pw(p: str) -> str: return hashlib.sha256(p.encode()).hexdigest()
def _verify_pw(p: str, h: str) -> bool: return _hash_pw(p) == h
def _token() -> str: return f"tok-{secrets.token_hex(16)}"

if not db.user_exists("admin"):
    db.create_user("admin", "admin@bank.com", "Relationship Manager",
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

class RMAdvisoryRequest(BaseModel):
    customer_id: str
    question: str

class CustomerGoalRequest(BaseModel):
    customer_id: str
    goal: str = "wealth"
    amount: Optional[float] = None
    horizon_months: Optional[int] = None

# ══════════════════════════════════════════════════
# ROOT
# ══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    idx = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(idx):
        with open(idx, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return {"service": "Personalized Financial Advisory Assistant", "version": "2.0.0"}

# ══════════════════════════════════════════════════
# AUTH (role selection enables the two response flows)
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
    _audit_entry("System", "User Registration", f"New user registered: {req.username}")
    return {"user": {k: v for k, v in user.items() if k != "password"}, "token": _token()}

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = db.get_user(req.username)
    if not user or not _verify_pw(req.password, user.get("password", "")):
        raise HTTPException(401, "Invalid username or password")
    user["role"] = req.portalType
    _audit_entry(req.username, "User Login", f"User logged in as {req.portalType}")
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
# AUDIT LEDGER (accountability / human-in-the-loop evidence)
# ══════════════════════════════════════════════════

@app.get("/api/audit-logs")
async def list_audit_logs(riskLevel: str = ""):
    logs = db.list_audit_logs(risk_level=riskLevel)
    return {"logs": logs}

# ══════════════════════════════════════════════════
# PERSONALIZED FINANCIAL ADVISORY
# ══════════════════════════════════════════════════

@app.get("/api/advisory/customers")
async def advisory_customers(search: str = ""):
    return {"customers": db.list_customers(search=search)}


@app.get("/api/advisory/customers/{customer_id}/profile")
async def advisory_customer_profile(customer_id: str):
    if advisory_service is None:
        raise HTTPException(503, "Advisory service unavailable")
    try:
        profile = advisory_service.get_profile(customer_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    _audit_entry(customer_id, "Customer Profile View",
                 f"Profile built for {customer_id}", "low")
    return {"profile": profile.to_dict(), "summary": profile.summary_text()}


@app.post("/api/advisory/rm-query")
async def advisory_rm_query(req: RMAdvisoryRequest):
    """Business track - RM decision support. Profile summary, engine-scored
    recommendations with reasoning, risk flags and escalation status."""
    if advisory_service is None:
        raise HTTPException(503, "Advisory service unavailable")
    response = advisory_service.rm_query(req.customer_id, req.question, actor="rm")
    payload = response.to_dict(include_retrieved=True)
    _audit_entry(f"RM:{req.customer_id}", "RM Advisory Query",
                 req.question[:160], "high" if response.needs_human_override else "low")
    return payload


@app.post("/api/advisory/customer-goal")
async def advisory_customer_goal(req: CustomerGoalRequest):
    """Customer track - goal-based guidance. Plain language, disclaimers,
    non-promissory enforcement; blocked/escalated products never shown."""
    if advisory_service is None:
        raise HTTPException(503, "Advisory service unavailable")
    response = advisory_service.customer_goal(
        req.customer_id, req.goal, amount=req.amount,
        horizon_months=req.horizon_months, actor="customer")
    payload = response.to_dict(include_retrieved=False)
    _audit_entry(f"CU:{req.customer_id}", "Customer Goal Guidance",
                 f"{req.goal} | amount={req.amount}", "low")
    return payload


@app.get("/api/advisory/products")
async def advisory_products():
    conn = db.get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY risk_level, product_id").fetchall()
    conn.close()
    return {"products": [dict(r) for r in rows]}


@app.get("/api/advisory/segments")
async def advisory_segments():
    if advisory_service is None:
        raise HTTPException(503, "Advisory service unavailable")
    from profiling.segmentation import get_segmenter
    seg = get_segmenter()
    return {"segments": seg.describe_segments()}


@app.get("/api/advisory/sessions")
async def advisory_sessions(limit: int = 50):
    return {"sessions": db.list_advisory_sessions(limit=limit)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
