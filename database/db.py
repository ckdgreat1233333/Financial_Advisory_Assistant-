"""
SQLite persistence layer for the Regulatory & Compliance Copilot.
Stores users, audit logs, and the version-controlled regulatory corpus registry.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "regulatory_copilot.db")


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
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            actor TEXT NOT NULL,
            eventType TEXT NOT NULL,
            riskLevel TEXT DEFAULT 'low',
            details TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS regulatory_docs (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            circular_no TEXT DEFAULT '',
            issue_date TEXT DEFAULT '',
            version TEXT DEFAULT 'v1.0',
            category TEXT DEFAULT 'circular',
            file_path TEXT DEFAULT '',
            file_hash TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            ingested_at TEXT DEFAULT (datetime('now'))
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


# ─── Audit Logs ───

def list_audit_logs(risk_level: str = "") -> list:
    conn = get_db()
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
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
            ("What documents are accepted for KYC?", "An officially valid document such as a passport, driving licence, Voter ID, Aadhaar card or NREGA job card is accepted for individual identity verification."),
            ("How often do I need to update my KYC?", "Low risk customers must update KYC at least once every ten years. Medium and high risk customers must update at least once every eight years."),
            ("Why has my account been restricted?", "If KYC records are not updated within the stipulated period, the bank may restrict the operation of the account. Please visit a branch to complete the updation."),
            ("How are account charges disclosed?", "Banks are required to display a schedule of charges and to notify customers of any change in charges before they take effect."),
            ("How do I file a complaint?", "You can register a complaint with the bank's internal grievance cell, which must acknowledge it promptly and resolve it within the prescribed timeline."),
            ("What happens if I am not satisfied with the bank's response?", "If your complaint is not resolved satisfactorily, you may escalate it to the Banking Ombudsman within the prescribed period after exhausting the bank's internal grievance mechanism."),
        ]
        conn.executemany("INSERT INTO faq (question, answer) VALUES (?,?)", faqs)
        conn.commit()
    conn.close()


# ─── Regulatory Docs (version-controlled knowledge store) ───

def list_regulatory_docs() -> list:
    conn = get_db()
    rows = conn.execute("SELECT * FROM regulatory_docs ORDER BY ingested_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_regulatory_doc(doc_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM regulatory_docs WHERE doc_id=?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_regulatory_doc(doc_id: str, title: str, circular_no: str = "", issue_date: str = "",
                          version: str = "v1.0", category: str = "circular",
                          file_path: str = "", file_hash: str = "") -> None:
    conn = get_db()
    conn.execute(
        """INSERT INTO regulatory_docs
           (doc_id, title, circular_no, issue_date, version, category, file_path, file_hash)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(doc_id) DO UPDATE SET
             title=excluded.title, circular_no=excluded.circular_no,
             issue_date=excluded.issue_date, version=excluded.version,
             category=excluded.category, file_path=excluded.file_path,
             file_hash=excluded.file_hash,
             ingested_at=datetime('now')""",
        (doc_id, title, circular_no, issue_date, version, category, file_path, file_hash)
    )
    conn.commit()
    conn.close()


def delete_regulatory_doc(doc_id: str) -> bool:
    conn = get_db()
    cur = conn.execute("DELETE FROM regulatory_docs WHERE doc_id=?", (doc_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# Initialize on import
init_db()
seed_faq()
