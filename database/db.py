"""
SQLite persistence layer for Insurance Claims Intelligence Platform.
Stores users, claims, fraud cases, policy docs, and audit logs.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "insurance_claim.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            password TEXT NOT NULL,
            role TEXT DEFAULT 'customer'
        );
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            applicant_email TEXT DEFAULT '',
            customer_phone TEXT DEFAULT '',
            loan_type TEXT NOT NULL,
            loan_amount REAL NOT NULL,
            term_months INTEGER DEFAULT 12,
            interest_rate REAL DEFAULT 8.5,
            submitted_date TEXT DEFAULT (date('now')),
            status TEXT DEFAULT 'PENDING',
            created_at TEXT DEFAULT (datetime('now')),
            metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            claimant_name TEXT NOT NULL,
            claimant_email TEXT DEFAULT '',
            claimant_phone TEXT DEFAULT '',
            policy_number TEXT DEFAULT '',
            claim_type TEXT NOT NULL,
            claim_amount REAL NOT NULL,
            incident_date TEXT DEFAULT '',
            submitted_date TEXT DEFAULT (date('now')),
            status TEXT DEFAULT 'RECEIVED',
            created_at TEXT DEFAULT (datetime('now')),
            metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS fraud_cases (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            case_type TEXT NOT NULL,
            fraud_level TEXT NOT NULL,
            narrative TEXT DEFAULT '',
            fraud_indicators TEXT DEFAULT '',
            resolution TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            actor TEXT NOT NULL,
            eventType TEXT NOT NULL,
            riskLevel TEXT DEFAULT 'low',
            details TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS policy_docs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT DEFAULT 'v1.0',
            status TEXT DEFAULT 'active',
            uploadDate TEXT DEFAULT (date('now')),
            activeRules INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


# ─── Users ───

def user_exists(username: str) -> bool:
    conn = get_db()
    row = conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return row is not None


def get_user(username_or_email: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username=? OR email=?", (username_or_email, username_or_email)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username: str, email: str, name: str, phone: str, password: str, role: str = "customer"):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO users (username, email, name, phone, password, role) VALUES (?,?,?,?,?,?)",
        (username, email, name, phone, password, role)
    )
    conn.commit()
    conn.close()


def update_user(username: str, name: str = None, email: str = None, phone: str = None):
    conn = get_db()
    fields = []
    vals = []
    if name is not None:
        fields.append("name=?")
        vals.append(name)
    if email is not None:
        fields.append("email=?")
        vals.append(email)
    if phone is not None:
        fields.append("phone=?")
        vals.append(phone)
    if fields:
        conn.execute(f"UPDATE users SET {','.join(fields)} WHERE username=?", vals + [username])
        conn.commit()
    conn.close()


def list_users() -> list:
    conn = get_db()
    rows = conn.execute("SELECT username, email, name, phone, role FROM users ORDER BY username").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(username: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ─── Claims ───

def list_claims(email: str = "", status: str = "", search: str = "") -> list:
    conn = get_db()
    query = "SELECT * FROM claims WHERE 1=1"
    params = []
    if email:
        query += " AND claimant_email=?"
        params.append(email)
    if status:
        query += " AND status=?"
        params.append(status)
    if search:
        query += " AND (claimant_name LIKE ? OR id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    rows = conn.execute(query + " ORDER BY created_at DESC", params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_claim(claim_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_claim(claim_id: str, claimant_name: str, claimant_email: str, claimant_phone: str,
               policy_number: str, claim_type: str, claim_amount: float, incident_date: str = "",
               status: str = "RECEIVED", metadata: str = "{}"):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO claims
           (id, claimant_name, claimant_email, claimant_phone, policy_number,
            claim_type, claim_amount, incident_date, status, metadata)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (claim_id, claimant_name, claimant_email, claimant_phone, policy_number,
         claim_type, claim_amount, incident_date, status, metadata)
    )
    conn.commit()
    conn.close()


def update_claim(claim_id: str, status: str, metadata: str = None):
    conn = get_db()
    conn.execute("UPDATE claims SET status=?, metadata=? WHERE id=?", (status, metadata or "{}", claim_id))
    conn.commit()
    conn.close()


# ─── Fraud Cases ───

def list_fraud_cases() -> list:
    conn = get_db()
    rows = conn.execute("SELECT * FROM fraud_cases ORDER BY case_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_fraud_case(case_id: str, case_type: str, fraud_level: str, narrative: str,
                    fraud_indicators: str = "", resolution: str = ""):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO fraud_cases (id, case_id, case_type, fraud_level, narrative, fraud_indicators, resolution) "
        "VALUES (?,?,?,?,?,?,?)",
        (case_id, case_id, case_type, fraud_level, narrative, fraud_indicators, resolution)
    )
    conn.commit()
    conn.close()


def seed_fraud_cases(cases: list):
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) as c FROM fraud_cases").fetchone()["c"]
    if existing == 0:
        for c in cases:
            conn.execute(
                "INSERT OR REPLACE INTO fraud_cases (id, case_id, case_type, fraud_level, narrative, fraud_indicators, resolution) "
                "VALUES (?,?,?,?,?,?,?)",
                (c["id"], c["id"], c["case_type"], c["fraud_level"], c["narrative"],
                 c.get("fraud_indicators", ""), c.get("resolution", ""))
            )
        conn.commit()
    conn.close()


# ─── Audit Logs ───

def list_audit_logs(application_id: str = "", risk_level: str = "") -> list:
    conn = get_db()
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if application_id:
        query += " AND details LIKE ?"
        params.append(f"%{application_id}%")
    if risk_level:
        query += " AND riskLevel=?"
        params.append(risk_level)
    rows = conn.execute(query + " ORDER BY timestamp DESC", params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_audit_log(entry_id: str, actor: str, event_type: str, details: str, risk_level: str = "low"):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_logs (id, actor, eventType, riskLevel, details) VALUES (?,?,?,?,?)",
        (entry_id, actor, event_type, risk_level, details)
    )
    conn.commit()
    conn.close()


def get_audit_log(entry_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM audit_logs WHERE id=?", (entry_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Policy Docs ───

def list_policy_docs() -> list:
    conn = get_db()
    rows = conn.execute("SELECT * FROM policy_docs ORDER BY uploadDate DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_policy_doc(doc_id: str, name: str, version: str, status: str = "active",
                      upload_date: str = "", active_rules: int = 0):
    if not upload_date:
        upload_date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    conn.execute(
        "INSERT INTO policy_docs (id, name, version, status, uploadDate, activeRules) VALUES (?,?,?,?,?,?)",
        (doc_id, name, version, status, upload_date, active_rules)
    )
    conn.commit()
    conn.close()


def delete_policy_doc(doc_id: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM policy_docs WHERE id=?", (doc_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ─── FAQ ───

def list_faqs(search: str = "") -> list:
    conn = get_db()
    if search:
        rows = conn.execute(
            "SELECT * FROM faq WHERE question LIKE ? OR answer LIKE ?",
            (f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM faq").fetchall()
    conn.close()
    return [{"id": r["id"], "question": r["question"], "answer": r["answer"]} for r in rows]


def create_faq(question: str, answer: str):
    conn = get_db()
    conn.execute("INSERT INTO faq (question, answer) VALUES (?,?)", (question, answer))
    conn.commit()
    conn.close()


def seed_faq():
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) as c FROM faq").fetchone()["c"]
    if existing == 0:
        faqs = [
            ("What documents do I need to file a claim?", "You need three mandatory documents: (1) Signed Claim Form, (2) Policy Document, (3) Proof of Loss statement. Additional documents depend on the claim type — medical reports for health, police reports for theft or accidents, and invoices for property damage."),
            ("How does the AI process my claim?", "Our system uses four AI agents: Document Validation Agent checks your submitted documents, Policy Interpretation Agent checks whether the claim is covered, Fraud Detection Agent screens against historical patterns, and Escalation Decision Agent decides whether a claim officer needs to review. Each agent provides a score and recommendation."),
            ("What do the fraud risk levels mean?", "Low Risk: Claim details consistent, amount within limits, no pattern similarity. Medium Risk: Minor inconsistencies or claim filed shortly after policy purchase. High Risk: Multiple inconsistencies or strong similarity to historical fraud patterns — this always requires a claim officer's review."),
            ("How long does claim processing take?", "Document validation completes in minutes. Coverage review and fraud screening take 1-2 business days. Final claim officer decision follows within 24 hours of review completion."),
            ("Is my data secure?", "All documents are encrypted at rest and in transit. Access is role-based and all actions are logged in an immutable audit trail."),
            ("Why was my claim rejected?", "Common reasons: the event is excluded by the policy, the claim was filed after the reporting window, documents are missing, or the claim amount exceeds coverage. A claim officer can share the specific reasons for your claim."),
        ]
        conn.executemany("INSERT INTO faq (question, answer) VALUES (?,?)", faqs)
        conn.commit()
    conn.close()


def seed_policy_docs():
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) as c FROM policy_docs").fetchone()["c"]
    if existing == 0:
        docs = [
            ("pol-1", "Motor Insurance Claim Guidelines", "v4.2", "active", "2023-08-15", 42),
            ("pol-2", "Health Insurance Coverage Rules", "v3.0", "active", "2023-09-01", 36),
            ("pol-3", "Property & Fire Claim Policy", "v2.5", "active", "2023-07-20", 28),
            ("pol-4", "Fraud Detection Framework", "v1.9", "archived", "2022-12-10", 18),
        ]
        conn.executemany(
            "INSERT INTO policy_docs (id, name, version, status, uploadDate, activeRules) VALUES (?,?,?,?,?,?)",
            docs
        )
        conn.commit()
    conn.close()


# Initialize on import
init_db()
# Migrate existing DB if needed
conn = get_db()
try:
    conn.execute("ALTER TABLE applications ADD COLUMN applicant_email TEXT DEFAULT ''")
except sqlite3.OperationalError:
    pass
conn.close()
seed_faq()
seed_policy_docs()
