"""
SQLite persistence layer for Loan Processing Assistant.
Stores users, applications, policy docs, and audit logs.
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "loan_assistant.db")


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

# ─── Applications ───

def list_applications(email: str = "", status: str = "", search: str = "") -> list:
    conn = get_db()
    query = "SELECT * FROM applications WHERE 1=1"
    params = []
    if email:
        query += " AND applicant_email=?"
        params.append(email)
    if status:
        query += " AND status=?"
        params.append(status)
    if search:
        query += " AND (customer_name LIKE ? OR id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    rows = conn.execute(query + " ORDER BY created_at DESC", params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_application(app_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def save_application(app_id: str, customer_name: str, customer_email: str, customer_phone: str,
                     loan_type: str, loan_amount: float, term_months: int = 12,
                     interest_rate: float = 8.5, status: str = "PENDING", metadata: str = "{}"):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO applications
           (id, customer_name, applicant_email, customer_phone, loan_type, loan_amount,
            term_months, interest_rate, status, metadata)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (app_id, customer_name, customer_email, customer_phone, loan_type,
         loan_amount, term_months, interest_rate, status, metadata)
    )
    conn.commit()
    conn.close()

def update_application(app_id: str, status: str, metadata: str = None):
    conn = get_db()
    conn.execute("UPDATE applications SET status=?, metadata=? WHERE id=?", (status, metadata or "{}", app_id))
    conn.commit()
    conn.close()

def update_application_status(app_id: str, status: str, metadata: dict = None):
    conn = get_db()
    if metadata is not None:
        existing = conn.execute("SELECT metadata FROM applications WHERE id=?", (app_id,)).fetchone()
        md = json.loads(existing["metadata"]) if existing else {}
        md.update(metadata)
        conn.execute("UPDATE applications SET status=?, metadata=? WHERE id=?", (status, json.dumps(md), app_id))
    else:
        conn.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
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
            ("What documents do I need to apply for a loan?", "You need three mandatory documents: (1) Salary Slip - last 3 months, (2) Bank Statement - last 6 months, (3) Employment Letter. Additional documents may be requested based on loan type."),
            ("How does the AI process my application?", "Our system uses three AI agents: Document Validation Agent checks your uploaded documents, Policy Compliance Agent verifies against lending policies, and Risk Evaluation Agent assesses your risk profile. Each agent provides a score and recommendation."),
            ("What do the risk levels mean?", "Low Risk: All documents verified, income stable, loan within limits. Medium Risk: Minor mismatches or missing optional info. High Risk: Missing mandatory documents, income below minimum, or false information."),
            ("How long does loan processing take?", "Document validation completes in minutes. Policy review and risk assessment take 1-2 business days. Final officer decision follows within 24 hours of review completion."),
            ("Is my data secure?", "All documents are encrypted at rest and in transit. Access is role-based and all actions are logged in an immutable audit trail."),
            ("Why was my application rejected?", "Common reasons: income below minimum threshold (₹30,000/month), loan amount exceeds 20x monthly salary, missing documents, or policy violations. Check with your loan officer for specific details."),
        ]
        conn.executemany("INSERT INTO faq (question, answer) VALUES (?,?)", faqs)
        conn.commit()
    conn.close()

def seed_policy_docs():
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) as c FROM policy_docs").fetchone()["c"]
    if existing == 0:
        docs = [
            ("pol-1", "Mortgage Underwriting Guidelines", "v4.2", "active", "2023-08-15", 48),
            ("pol-2", "Commercial Loan Credit Risk Limits", "v3.0", "active", "2023-09-01", 32),
            ("pol-3", "Retail & Consumer Lending Eligibility", "v2.5", "active", "2023-07-20", 24),
            ("pol-4", "Automated Identity & Fraud Detection", "v1.9", "archived", "2022-12-10", 15),
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
for col in [("applicant_email", "TEXT DEFAULT ''"), ("submitted_date", "TEXT DEFAULT (date('now'))"),
            ("term_months", "INTEGER DEFAULT 12"), ("interest_rate", "REAL DEFAULT 8.5")]:
    try:
        conn.execute(f"ALTER TABLE applications ADD COLUMN {col[0]} {col[1]}")
    except sqlite3.OperationalError:
        pass  # column already exists
conn.close()
seed_faq()
seed_policy_docs()
