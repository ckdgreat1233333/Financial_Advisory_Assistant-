"""
SQLite persistence layer for the Personalized Financial Advisory Assistant.
Stores users, audit logs, synthetic banking data (customers, transactions),
the product catalog, and the advisory session audit trail.
"""
import sqlite3
import os
import csv
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "advisory.db")
CUSTOMERS_CSV = os.path.join(BASE_DIR, "data", "customers", "customers.csv")
TRANSACTIONS_CSV = os.path.join(BASE_DIR, "data", "customers", "transactions.csv")
PRODUCTS_CSV = os.path.join(BASE_DIR, "data", "products", "products.csv")


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
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            city TEXT,
            occupation TEXT,
            employment_type TEXT,
            annual_income REAL,
            monthly_income REAL,
            marital_status TEXT,
            dependents INTEGER DEFAULT 0,
            kyc_status TEXT DEFAULT 'verified',
            stated_risk_appetite TEXT,
            investment_horizon_months INTEGER,
            goals TEXT DEFAULT '',
            onboard_date TEXT,
            savings_balance REAL DEFAULT 0,
            has_loan TEXT DEFAULT 'False',
            existing_products TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS transactions (
            txn_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            date TEXT NOT NULL,
            direction TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_txn_customer ON transactions(customer_id);
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            asset_class TEXT,
            risk_level TEXT,
            min_investment REAL,
            lock_in_months INTEGER DEFAULT 0,
            expected_return_low REAL,
            expected_return_high REAL,
            liquidity TEXT,
            goal_tags TEXT DEFAULT '',
            allowed_risk_profiles TEXT DEFAULT '',
            tax_benefit TEXT DEFAULT 'no',
            senior_citizen_friendly TEXT DEFAULT 'no',
            min_horizon_months INTEGER DEFAULT 0,
            max_allocation_pct INTEGER DEFAULT 100
        );
        CREATE TABLE IF NOT EXISTS advisory_sessions (
            session_id TEXT PRIMARY KEY,
            timestamp TEXT DEFAULT (datetime('now')),
            track TEXT NOT NULL,
            customer_id TEXT,
            actor TEXT DEFAULT '',
            question TEXT DEFAULT '',
            answered INTEGER DEFAULT 0,
            needs_human_override INTEGER DEFAULT 0,
            escalation_reason TEXT DEFAULT '',
            payload TEXT DEFAULT ''
        );
    """)
    conn.commit()
    conn.close()
    _seed_customers()
    _seed_transactions()
    _seed_products()


def _seed_customers():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) AS c FROM customers").fetchone()["c"]
    if count == 0 and os.path.exists(CUSTOMERS_CSV):
        with open(CUSTOMERS_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        conn.executemany(
            """INSERT OR REPLACE INTO customers VALUES
               (:customer_id,:name,:age,:gender,:city,:occupation,:employment_type,
                :annual_income,:monthly_income,:marital_status,:dependents,:kyc_status,
                :stated_risk_appetite,:investment_horizon_months,:goals,:onboard_date,
                :savings_balance,:has_loan,:existing_products)""",
            rows)
        conn.commit()
    conn.close()


def _seed_transactions():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) AS c FROM transactions").fetchone()["c"]
    if count == 0 and os.path.exists(TRANSACTIONS_CSV):
        with open(TRANSACTIONS_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        conn.executemany(
            "INSERT OR REPLACE INTO transactions VALUES (:txn_id,:customer_id,:date,:direction,:category,:amount,:description)",
            rows)
        conn.commit()
    conn.close()


def _seed_products():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0 and os.path.exists(PRODUCTS_CSV):
        with open(PRODUCTS_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            r["lock_in_months"] = int(float(r.get("lock_in_months") or 0))
            r["min_horizon_months"] = int(float(r.get("min_horizon_months") or 0))
        conn.executemany(
            """INSERT OR REPLACE INTO products VALUES
               (:product_id,:name,:category,:asset_class,:risk_level,:min_investment,
                :lock_in_months,:expected_return_low,:expected_return_high,:liquidity,
                :goal_tags,:allowed_risk_profiles,:tax_benefit,:senior_citizen_friendly,
                :min_horizon_months,:max_allocation_pct)""",
            rows)
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


# ─── Advisory: customers / transactions / products / sessions ───

def list_customers(search: str = "") -> list:
    conn = get_db()
    if search:
        rows = conn.execute(
            "SELECT customer_id, name, age, city, occupation, annual_income, "
            "stated_risk_appetite, kyc_status, goals FROM customers "
            "WHERE name LIKE ? OR customer_id LIKE ? ORDER BY customer_id",
            (f"%{search}%", f"%{search}%")).fetchall()
    else:
        rows = conn.execute(
            "SELECT customer_id, name, age, city, occupation, annual_income, "
            "stated_risk_appetite, kyc_status, goals FROM customers ORDER BY customer_id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_customer_row(customer_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM customers WHERE customer_id=?", (customer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_transactions(customer_id: str) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT txn_id, date, direction, category, amount, description "
        "FROM transactions WHERE customer_id=? ORDER BY date", (customer_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_customer_txn_summary(customer_id: str) -> dict:
    """Aggregate transactional signals used by the profile builder."""
    conn = get_db()
    row = conn.execute(
        """SELECT
             COUNT(*) AS txn_count,
             SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END) AS total_credits,
             SUM(CASE WHEN direction='debit' THEN amount ELSE 0 END) AS total_debits,
             AVG(CASE WHEN direction='credit' THEN amount END) AS avg_credit,
             SUM(CASE WHEN category='sip_investment' THEN amount ELSE 0 END) AS sip_total,
             SUM(CASE WHEN category='emi' THEN amount ELSE 0 END) AS emi_total,
             SUM(CASE WHEN category='dining_entertainment' OR category='shopping'
                      THEN amount ELSE 0 END) AS lifestyle_total,
             SUM(CASE WHEN category='rent' OR category='maintenance'
                      THEN amount ELSE 0 END) AS housing_total,
             SUM(CASE WHEN category='insurance_premium' THEN amount ELSE 0 END) AS insurance_total,
             SUM(CASE WHEN category='school_fees' THEN amount ELSE 0 END) AS education_total,
             MIN(date) AS first_date, MAX(date) AS last_date
           FROM transactions WHERE customer_id=?""",
        (customer_id,)).fetchone()
    conn.close()
    return dict(row)


def upsert_product(prod: dict) -> None:
    conn = get_db()
    conn.execute(
        """INSERT INTO products VALUES
           (:product_id,:name,:category,:asset_class,:risk_level,:min_investment,
            :lock_in_months,:expected_return_low,:expected_return_high,:liquidity,
            :goal_tags,:allowed_risk_profiles,:tax_benefit,:senior_citizen_friendly,
            :min_horizon_months,:max_allocation_pct)
           ON CONFLICT(product_id) DO UPDATE SET
             name=excluded.name, category=excluded.category, asset_class=excluded.asset_class,
             risk_level=excluded.risk_level, min_investment=excluded.min_investment,
             lock_in_months=excluded.lock_in_months,
             expected_return_low=excluded.expected_return_low,
             expected_return_high=excluded.expected_return_high,
             liquidity=excluded.liquidity, goal_tags=excluded.goal_tags,
             allowed_risk_profiles=excluded.allowed_risk_profiles,
             tax_benefit=excluded.tax_benefit,
             senior_citizen_friendly=excluded.senior_citizen_friendly,
             min_horizon_months=excluded.min_horizon_months,
             max_allocation_pct=excluded.max_allocation_pct""",
        prod)
    conn.commit()
    conn.close()


def get_product(product_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE product_id=?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_advisory_session(session_id: str, track: str, customer_id: str, actor: str,
                            question: str, answered: bool, needs_human_override: bool,
                            escalation_reason: str, payload: str) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO advisory_sessions VALUES (?,?,datetime('now'),?,?,?,?,?,?,?)",
        (session_id, track, customer_id, actor, question, int(answered),
         int(needs_human_override), escalation_reason or "", payload))
    conn.commit()
    conn.close()


def list_advisory_sessions(limit: int = 100) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT session_id, timestamp, track, customer_id, actor, question, answered, "
        "needs_human_override, escalation_reason FROM advisory_sessions "
        "ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialize on import
init_db()
