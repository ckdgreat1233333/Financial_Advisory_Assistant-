"""Synthetic data generator for the Personalized Financial Advisory Assistant.

Produces deterministic (seeded) banking-domain data:
    data/customers/customers.csv       customer demographics + stated profile
    data/customers/transactions.csv    12 months of account transactions
    data/products/products.csv         structured product attribute catalog
    data/products/*.txt                narrative product corpus (RAG, clause format)
    data/goals/goal_definitions.json   goal definitions (horizon + risk guidance)

Run from the project root:
    python scripts/generate_data.py
"""
import csv
import json
import random
from datetime import date
from pathlib import Path

random.seed(42)

BASE = Path(__file__).resolve().parent.parent
CUSTOMERS_DIR = BASE / "data" / "customers"
PRODUCTS_DIR = BASE / "data" / "products"
GOALS_DIR = BASE / "data" / "goals"

FIRST_NAMES_M = ["Aarav", "Rohan", "Vikram", "Suresh", "Anil", "Karthik", "Rahul", "Deepak",
                 "Manoj", "Arjun", "Sanjay", "Prakash", "Naveen", "Harish", "Girish", "Mohan",
                 "Rajesh", "Vinod", "Ashok", "Nikhil", "Sameer", "Farhan", "Joseph", "Devan"]
FIRST_NAMES_F = ["Priya", "Anita", "Meera", "Lakshmi", "Divya", "Kavya", "Shreya", "Pooja",
                 "Nandini", "Radhika", "Sunita", "Geeta", "Swati", "Aisha", "Maya", "Rekha",
                 "Bhavna", "Sneha", "Ishita", "Tara", "Leela", "Fatima", "Anjali", "Ritu"]
SURNAMES = ["Sharma", "Patel", "Iyer", "Reddy", "Nair", "Gupta", "Joshi", "Menon", "Deshpande",
            "Kulkarni", "Rao", "Mehta", "Chopra", "Bhat", "Pillai", "Verma", "Malhotra", "Shetty",
            "Krishnan", "Banerjee", "Das", "Saxena", "Kapoor", "Trivedi"]

CITIES = {"Mumbai": 1.35, "Bengaluru": 1.25, "Delhi": 1.20, "Pune": 1.10, "Chennai": 1.05,
          "Hyderabad": 1.05, "Ahmedabad": 0.90, "Kolkata": 0.95, "Jaipur": 0.80, "Kochi": 0.85}

OCCUPATIONS = [
    ("Software Engineer", "salaried"), ("Bank Manager", "salaried"), ("School Teacher", "salaried"),
    ("Doctor", "self_employed"), ("Business Owner", "business"), ("Government Employee", "salaried"),
    ("Chartered Accountant", "self_employed"), ("Retail Manager", "salaried"),
    ("Consultant", "freelance"), ("Pharmacist", "salaried"), ("Architect", "freelance"),
    ("Insurance Agent", "commission"),
]

OCCUPATION_BASE_INCOME = {
    "Software Engineer": 135000, "Bank Manager": 110000, "School Teacher": 55000,
    "Doctor": 220000, "Business Owner": 185000, "Government Employee": 75000,
    "Chartered Accountant": 165000, "Retail Manager": 65000, "Consultant": 145000,
    "Pharmacist": 48000, "Architect": 95000, "Insurance Agent": 52000,
}

MONTHS = [(2025, m) for m in range(9, 13)] + [(2026, m) for m in range(1, 9)]

GOAL_DEFS = {
    "education": {
        "label": "Children's Education",
        "typical_horizon_months": [60, 180],
        "risk_guidance": "moderate",
        "description": "Building a corpus for school or higher-education fees, typically 5-15 years away.",
    },
    "retirement": {
        "label": "Retirement Corpus",
        "typical_horizon_months": [120, 360],
        "risk_guidance": "moderate",
        "description": "Long-horizon wealth accumulation for post-retirement income.",
    },
    "wealth": {
        "label": "Wealth Creation",
        "typical_horizon_months": [24, 120],
        "risk_guidance": "moderate",
        "description": "General long-term growth of surplus savings.",
    },
    "safety": {
        "label": "Emergency & Safety Buffer",
        "typical_horizon_months": [3, 12],
        "risk_guidance": "conservative",
        "description": "Highly liquid, capital-safe parking of an emergency fund.",
    },
    "tax": {
        "label": "Tax Saving",
        "typical_horizon_months": [36, 60],
        "risk_guidance": "moderate",
        "description": "Deploying investments eligible for deduction under Sec 80C.",
    },
}

PRODUCTS = [
    {
        "product_id": "prod_fd", "name": "Smart Fixed Deposit", "category": "deposit",
        "asset_class": "fixed_income", "risk_level": "low",
        "min_investment": 5000, "lock_in_months": 0,
        "expected_return_low": 6.50, "expected_return_high": 7.25,
        "liquidity": "medium", "goal_tags": "safety|wealth|education",
        "allowed_risk_profiles": "conservative|moderate|aggressive",
        "tax_benefit": "no", "senior_citizen_friendly": "yes",
        "min_horizon_months": 6, "max_allocation_pct": 100,
    },
    {
        "product_id": "prod_rd", "name": "Monthly Recurring Deposit", "category": "deposit",
        "asset_class": "fixed_income", "risk_level": "low",
        "min_investment": 1000, "lock_in_months": 12,
        "expected_return_low": 6.75, "expected_return_high": 7.10,
        "liquidity": "low", "goal_tags": "safety|education|wealth",
        "allowed_risk_profiles": "conservative|moderate|aggressive",
        "tax_benefit": "no", "senior_citizen_friendly": "yes",
        "min_horizon_months": 12, "max_allocation_pct": 100,
    },
    {
        "product_id": "prod_sweep", "name": "Sweep-in Savings Plus Account", "category": "savings",
        "asset_class": "cash", "risk_level": "low",
        "min_investment": 25000, "lock_in_months": 0,
        "expected_return_low": 3.50, "expected_return_high": 4.25,
        "liquidity": "high", "goal_tags": "safety",
        "allowed_risk_profiles": "conservative|moderate|aggressive",
        "tax_benefit": "no", "senior_citizen_friendly": "yes",
        "min_horizon_months": 0, "max_allocation_pct": 100,
    },
    {
        "product_id": "prod_ppf", "name": "Public Provident Fund", "category": "govt_savings",
        "asset_class": "fixed_income", "risk_level": "low",
        "min_investment": 500, "lock_in_months": 180,
        "expected_return_low": 7.10, "expected_return_high": 7.60,
        "liquidity": "low", "goal_tags": "retirement|safety|tax|education",
        "allowed_risk_profiles": "conservative|moderate|aggressive",
        "tax_benefit": "yes", "senior_citizen_friendly": "no",
        "min_horizon_months": 180, "max_allocation_pct": 40,
    },
    {
        "product_id": "prod_debt_mf", "name": "Corporate Bond Debt Fund", "category": "debt_fund",
        "asset_class": "debt", "risk_level": "moderate",
        "min_investment": 5000, "lock_in_months": 0,
        "expected_return_low": 6.80, "expected_return_high": 8.00,
        "liquidity": "medium", "goal_tags": "wealth|safety|education",
        "allowed_risk_profiles": "conservative|moderate|aggressive",
        "tax_benefit": "no", "senior_citizen_friendly": "yes",
        "min_horizon_months": 12, "max_allocation_pct": 60,
    },
    {
        "product_id": "prod_sgb", "name": "Sovereign Gold Bond", "category": "gold",
        "asset_class": "gold", "risk_level": "moderate",
        "min_investment": 7000, "lock_in_months": 60,
        "expected_return_low": 6.00, "expected_return_high": 9.00,
        "liquidity": "low", "goal_tags": "wealth",
        "allowed_risk_profiles": "moderate|aggressive",
        "tax_benefit": "no", "senior_citizen_friendly": "no",
        "min_horizon_months": 60, "max_allocation_pct": 15,
    },
    {
        "product_id": "prod_bal_adv", "name": "Balanced Advantage Fund", "category": "hybrid_fund",
        "asset_class": "hybrid", "risk_level": "moderate",
        "min_investment": 1000, "lock_in_months": 0,
        "expected_return_low": 8.50, "expected_return_high": 11.00,
        "liquidity": "medium", "goal_tags": "wealth|retirement|education",
        "allowed_risk_profiles": "moderate|aggressive",
        "tax_benefit": "no", "senior_citizen_friendly": "no",
        "min_horizon_months": 36, "max_allocation_pct": 50,
    },
    {
        "product_id": "prod_nps", "name": "National Pension System", "category": "pension",
        "asset_class": "mixed", "risk_level": "moderate",
        "min_investment": 500, "lock_in_months": 240,
        "expected_return_low": 9.00, "expected_return_high": 12.00,
        "liquidity": "low", "goal_tags": "retirement|tax",
        "allowed_risk_profiles": "moderate|aggressive",
        "tax_benefit": "yes", "senior_citizen_friendly": "no",
        "min_horizon_months": 120, "max_allocation_pct": 40,
    },
    {
        "product_id": "prod_index_sip", "name": "Nifty 50 Index Fund (SIP)", "category": "equity_fund",
        "asset_class": "equity", "risk_level": "high",
        "min_investment": 500, "lock_in_months": 0,
        "expected_return_low": 10.00, "expected_return_high": 13.00,
        "liquidity": "medium", "goal_tags": "wealth|retirement|education",
        "allowed_risk_profiles": "moderate|aggressive",
        "tax_benefit": "no", "senior_citizen_friendly": "no",
        "min_horizon_months": 36, "max_allocation_pct": 60,
    },
    {
        "product_id": "prod_largecap", "name": "Blue-Chip Large-Cap Equity Fund", "category": "equity_fund",
        "asset_class": "equity", "risk_level": "high",
        "min_investment": 1000, "lock_in_months": 0,
        "expected_return_low": 10.50, "expected_return_high": 14.00,
        "liquidity": "medium", "goal_tags": "wealth|retirement",
        "allowed_risk_profiles": "moderate|aggressive",
        "tax_benefit": "no", "senior_citizen_friendly": "no",
        "min_horizon_months": 36, "max_allocation_pct": 50,
    },
    {
        "product_id": "prod_elss", "name": "ELSS Tax Saver Fund", "category": "equity_fund",
        "asset_class": "equity", "risk_level": "high",
        "min_investment": 500, "lock_in_months": 36,
        "expected_return_low": 11.00, "expected_return_high": 14.50,
        "liquidity": "low", "goal_tags": "tax|wealth",
        "allowed_risk_profiles": "moderate|aggressive",
        "tax_benefit": "yes", "senior_citizen_friendly": "no",
        "min_horizon_months": 36, "max_allocation_pct": 30,
    },
    {
        "product_id": "prod_term_life", "name": "Shield Term Life Insurance", "category": "protection",
        "asset_class": "protection", "risk_level": "low",
        "min_investment": 6000, "lock_in_months": 12,
        "expected_return_low": 0.0, "expected_return_high": 0.0,
        "liquidity": "none", "goal_tags": "safety",
        "allowed_risk_profiles": "conservative|moderate|aggressive",
        "tax_benefit": "yes", "senior_citizen_friendly": "no",
        "min_horizon_months": 0, "max_allocation_pct": 10,
    },
    {
        "product_id": "prod_health", "name": "Comprehensive Family Health Cover", "category": "protection",
        "asset_class": "protection", "risk_level": "low",
        "min_investment": 9000, "lock_in_months": 12,
        "expected_return_low": 0.0, "expected_return_high": 0.0,
        "liquidity": "none", "goal_tags": "safety",
        "allowed_risk_profiles": "conservative|moderate|aggressive",
        "tax_benefit": "yes", "senior_citizen_friendly": "yes",
        "min_horizon_months": 0, "max_allocation_pct": 10,
    },
]


def _name(i):
    first = random.choice(FIRST_NAMES_M + FIRST_NAMES_F)
    return f"{first} {random.choice(SURNAMES)}"


def generate_customers(n=150):
    customers = []
    used_names = set()
    for i in range(1, n + 1):
        cid = f"CUST{i:04d}"
        while True:
            name = _name(i)
            if name not in used_names:
                used_names.add(name)
                break
        gender = "F" if name.split()[0] in FIRST_NAMES_F else "M"
        city = random.choice(list(CITIES.keys()))
        occupation, emp_type = random.choice(OCCUPATIONS)
        age = random.randint(23, 68)
        base = OCCUPATION_BASE_INCOME[occupation]
        age_factor = 0.75 + min(age - 22, 25) * 0.02
        annual_income = int(base * age_factor * CITIES[city] * random.uniform(0.8, 1.25) / 1000) * 1000
        married = age >= 27 and random.random() < 0.72
        dependents = 0
        if married:
            dependents = random.choices([0, 1, 2], weights=[0.30, 0.45, 0.25])[0]
        kyc_status = random.choices(
            ["verified", "update_due", "pending"], weights=[0.88, 0.07, 0.05])[0]
        if age < 32:
            appetite = random.choices(["aggressive", "moderate", "conservative"],
                                      weights=[0.45, 0.40, 0.15])[0]
        elif age < 50:
            appetite = random.choices(["aggressive", "moderate", "conservative"],
                                      weights=[0.20, 0.50, 0.30])[0]
        else:
            appetite = random.choices(["aggressive", "moderate", "conservative"],
                                      weights=[0.08, 0.37, 0.55])[0]
        goals_pool = []
        if dependents > 0:
            goals_pool.append("education")
        goals_pool.append("wealth")
        goals_pool.append("safety")
        if age >= 38:
            goals_pool.append("retirement")
        if random.random() < 0.45:
            goals_pool.append("tax")
        goals = "|".join(sorted(set(goals_pool)))
        horizon = random.randint(*GOAL_DEFS["wealth"]["typical_horizon_months"])
        has_loan = random.random() < (0.55 if age < 45 else 0.30)
        monthly_income = annual_income // 12
        balance = int(monthly_income * random.uniform(0.5, 9.0) / 1000) * 1000
        holdings = []
        if random.random() < 0.62:
            holdings.append("prod_fd")
        if random.random() < 0.28:
            holdings.append("prod_ppf")
        if random.random() < 0.22 and appetite != "conservative":
            holdings.append(random.choice(["prod_index_sip", "prod_largecap", "prod_bal_adv"]))
        if random.random() < 0.18:
            holdings.append("prod_term_life")
        if random.random() < 0.24:
            holdings.append("prod_health")
        onboard_year = random.randint(2014, 2025)
        customers.append({
            "customer_id": cid, "name": name, "age": age, "gender": gender, "city": city,
            "occupation": occupation, "employment_type": emp_type,
            "annual_income": annual_income, "monthly_income": monthly_income,
            "marital_status": "married" if married else "single",
            "dependents": dependents, "kyc_status": kyc_status,
            "stated_risk_appetite": appetite,
            "investment_horizon_months": horizon, "goals": goals,
            "onboard_date": f"{onboard_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "savings_balance": balance, "has_loan": str(has_loan),
            "existing_products": "|".join(holdings),
        })
    return customers


def generate_transactions(customers):
    txns = []
    tid = 1
    for c in customers:
        monthly_income = c["monthly_income"]
        city_f = CITIES[c["city"]]
        owns_home = c["age"] > 45 and random.random() < 0.5
        sip_active = "sip" in " ".join(c["existing_products"]) or (
            c["stated_risk_appetite"] != "conservative" and random.random() < 0.55)
        sip_amt = int(monthly_income * ({"conservative": 0.08, "moderate": 0.15,
                                         "aggressive": 0.22}[c["stated_risk_appetite"]])
                      * random.uniform(0.7, 1.3) / 100) * 100
        emi_amt = int(monthly_income * random.uniform(0.15, 0.34)) if c["has_loan"] == "True" else 0
        insurance_premium_month = random.choice(MONTHS)[1]
        for (year, month) in MONTHS:
            day_base = date(year, month, 1)
            if c["employment_type"] == "business":
                income = monthly_income * random.uniform(0.65, 1.35)
            elif c["employment_type"] == "commission":
                income = monthly_income * random.uniform(0.4, 1.6)
            elif c["employment_type"] == "freelance":
                income = monthly_income * random.uniform(0.7, 1.3)
            else:
                income = monthly_income * random.uniform(0.98, 1.02)
            income = int(income / 100) * 100
            if income > 0:
                txns.append({
                    "txn_id": f"TXN{tid:06d}", "customer_id": c["customer_id"],
                    "date": str(day_base.replace(day=random.randint(1, 3))),
                    "direction": "credit", "category": "salary" if c["employment_type"] in ("salaried",) else "business_income",
                    "amount": income,
                    "description": "Monthly credit" if c["employment_type"] == "salaried" else "Business receipt",
                })
                tid += 1
            def debit(cat, amount, desc, day):
                nonlocal tid
                amount = max(int(amount / 10) * 10, 100)
                txns.append({"txn_id": f"TXN{tid:06d}", "customer_id": c["customer_id"],
                             "date": str(day_base.replace(day=min(day, 28))),
                             "direction": "debit", "category": cat, "amount": amount,
                             "description": desc})
                tid += 1
            if not owns_home:
                debit("rent", monthly_income * 0.22 * city_f * random.uniform(0.9, 1.1), "House rent", 5)
            else:
                debit("maintenance", monthly_income * 0.03 * random.uniform(0.8, 1.2), "Society maintenance", 5)
            debit("groceries", monthly_income * random.uniform(0.09, 0.16), "Groceries", random.randint(6, 20))
            debit("utilities", monthly_income * random.uniform(0.03, 0.06), "Electricity and water", 12)
            debit("transport", monthly_income * random.uniform(0.04, 0.09), "Fuel and commute", random.randint(10, 25))
            lifestyle_rate = 0.14 if c["age"] < 32 else 0.08
            debit("dining_entertainment", monthly_income * lifestyle_rate * random.uniform(0.6, 1.5),
                  "Dining and entertainment", random.randint(8, 26))
            if emi_amt:
                debit("emi", emi_amt * random.uniform(0.99, 1.01), "Loan EMI", 7)
            if sip_active and sip_amt >= 500:
                debit("sip_investment", sip_amt, "Mutual fund SIP", 10)
            if month == insurance_premium_month:
                debit("insurance_premium", monthly_income * random.uniform(0.5, 1.4), "Insurance premium", 18)
            if c["dependents"] > 0 and month % 3 == 0:
                debit("school_fees", monthly_income * random.uniform(0.4, 0.9) * c["dependents"],
                      "School fees", 15)
            if random.random() < 0.06:
                debit("medical", monthly_income * random.uniform(0.05, 0.4), "Medical expenses", random.randint(2, 27))
            if random.random() < 0.25:
                debit("shopping", monthly_income * random.uniform(0.03, 0.12), "Online shopping", random.randint(3, 27))
            if c["age"] >= 60 and random.random() < 0.9:
                credit_amt = int(monthly_income * random.uniform(0.02, 0.06) / 10) * 10
                txns.append({"txn_id": f"TXN{tid:06d}", "customer_id": c["customer_id"],
                             "date": str(day_base.replace(day=28)), "direction": "credit",
                             "category": "interest_payout", "amount": max(credit_amt, 200),
                             "description": "Deposit interest payout"})
                tid += 1
    return txns


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


PRODUCT_DOC_TEMPLATE = """Subject: {name}
Category: {category}
Version: v1.0
Product ID: {pid}
Risk Level: {risk}
Min Investment: Rs. {min_inv:,}
Lock-in Period: {lock}
Expected Returns: {ret}
Goal Tags: {tags}

1. Overview
{overview}

2. Key Features
{features}

3. Suitability Profile
{suitability}

4. Risk Factors And Warnings
{risks}

5. Charges Liquidity And Taxation
{charges}
"""


def product_overview(p):
    pid, name = p["product_id"], p["name"]
    texts = {
        "prod_fd": (
            "A term deposit placed with the bank for a fixed tenor at a contracted interest rate. "
            "Interest accrues quarterly and may be paid out or compounded. Tenors range from 7 days to 10 years."),
        "prod_rd": (
            "A deposit where a fixed installment is auto-debited every month for a chosen tenor "
            "of 12 to 120 months. At maturity the depositor receives principal plus compounded interest."),
        "prod_sweep": (
            "A savings account linked to fixed deposits. Balances above a chosen threshold are "
            "automatically swept into FD units in multiples of Rs. 1,000 and reverse-swept when withdrawals exceed the balance."),
        "prod_ppf": (
            "A government-backed long-term savings scheme with a 15-year tenure, extendable in 5-year blocks. "
            "Contributions up to Rs. 1.5 lakh per year qualify for Section 80C deduction and interest is fully exempt."),
        "prod_debt_mf": (
            "An open-ended debt scheme investing predominantly in AAA-rated corporate bonds, "
            "government securities and money-market instruments. Returns are market-linked and not guaranteed."),
        "prod_sgb": (
            "Government securities denominated in grams of gold. They pay a fixed 2.5 percent interest "
            "per annum in addition to tracking the market price of gold at redemption. Eight-year maturity with exit windows from year five."),
        "prod_bal_adv": (
            "A dynamically managed hybrid fund that shifts allocation between equity and debt based on "
            "market valuation cues. Equity exposure can range from roughly 30 to 80 percent, so NAV moves with markets in both directions."),
        "prod_nps": (
            "A contributory pension scheme regulated by PFRDA. Contributions are invested across equity, "
            "corporate bonds and government securities according to a chosen auto or active life-cycle strategy until age 60."),
        "prod_index_sip": (
            "A systematic investment plan into an open-ended index fund replicating the Nifty 50 TRI. "
            "The portfolio holds the same stocks as the index, so unit value rises and falls directly with the market."),
        "prod_largecap": (
            "An actively managed equity fund investing at least 80 percent of assets in the top 100 listed "
            "companies by market capitalisation. Returns depend entirely on stock-market performance."),
        "prod_elss": (
            "An equity-linked savings scheme with a statutory lock-in of 36 months per installment. "
            "Investments qualify for Section 80C deduction up to Rs. 1.5 lakh per year under the old tax regime."),
        "prod_term_life": (
            "Pure risk-cover life insurance for a chosen sum assured and policy term. There is no maturity "
            "benefit; the nominee receives the sum assured only if the life assured passes away during the term."),
        "prod_health": (
            "Indemnity health insurance covering hospitalisation for the family with cashless treatment "
            "across network hospitals, annual renewal, and restoration of sum insured on partial utilisation."),
    }
    return texts[pid]


def product_features(p):
    pid = p["product_id"]
    common = (f"Minimum investment: Rs. {p['min_investment']:,}. "
              f"Liquidity classification: {p['liquidity']}. ")
    feats = {
        "prod_fd": "Premature closure permitted with a 0.5-1.0 percent rate penalty. Nomination available. Senior citizens earn 0.50 percent higher interest.",
        "prod_rd": "Installments auto-debited on a chosen day each month. One missed installment attracts a small penalty; six consecutive misses close the deposit.",
        "prod_sweep": "Fully liquid at par value up to the sweep threshold. FD leg earns deposit rates without breaking the full deposit.",
        "prod_ppf": "Annual contribution between Rs. 500 and Rs. 1.5 lakh. Partial withdrawal permitted from year seven; loans against balance from year three.",
        "prod_debt_mf": "Daily NAV, SIP from Rs. 500 per month, exit load nil beyond seven days. Credit-rating and duration risk apply.",
        "prod_sgb": "Interest credited half-yearly to the bank account. Tradable on secondary market from year five. Capital gains on redemption are tax-exempt.",
        "prod_bal_adv": "SIP supported from Rs. 1,000 per month. Allocation shifts reviewed daily. Exit load 1 percent within 15 days only.",
        "prod_nps": "Tier-I account is locked until age 60 with partial withdrawal for defined needs after three years. Up to 75 percent equity allowed under active choice.",
        "prod_index_sip": "Lowest expense ratio among equity funds since there is no active management. Any-day pause, step-up or stop of SIP without penalty.",
        "prod_largecap": "Fund manager discretion adds tracking difference versus the index. SIP step-up facility available.",
        "prod_elss": "Every installment locks for 36 months from its own date. After lock-in, redemption is fully at the investor's discretion.",
        "prod_term_life": "Sum assured from Rs. 50 lakh to Rs. 5 crore. Premium rates fixed at entry for the whole term. Riders for critical illness and accident available.",
        "prod_health": "Sum insured options from Rs. 5 lakh to Rs. 1 crore. Pre and post hospitalisation covered 60 and 90 days respectively. Waiting periods apply for pre-existing conditions.",
    }
    return common + feats[pid]


def product_suitability(p):
    profiles = p["allowed_risk_profiles"].split("|")
    tags = p["goal_tags"].replace("|", ", ")
    base = (f"Recommended for investors with a computed risk capacity of {' or '.join(profiles)}. "
            f"Investment horizon should be at least {p['min_horizon_months']} months. "
            f"Aligns with goals: {tags}. ")
    suit = {
        "prod_fd": "First-time investors, emergency reserves, and capital-preservation allocations near a goal date. Suitable as the stability core of any portfolio.",
        "prod_rd": "Savers building discipline toward a dated goal such as school fees due in one to three years.",
        "prod_sweep": "Idle operating balances above one month of expenses that still need same-day access.",
        "prod_ppf": "Long-horizon conservative savers, especially parents earmarking education funds and retirees' spouses seeking EEE taxation.",
        "prod_debt_mf": "Conservative-to-moderate investors parking funds beyond one year who accept small NAV fluctuation for better post-tax yield than deposits.",
        "prod_sgb": "Investors wanting gold exposure without storage cost, sized below 15 percent of the portfolio.",
        "prod_bal_adv": "Moderate-risk investors entering equity gradually, or those uneasy with full equity volatility.",
        "prod_nps": "Salaried earners building a dedicated retirement corpus alongside EPF, wanting extra Section 80CCD(1B) deduction of Rs. 50,000.",
        "prod_index_sip": "Long-horizon investors preferring market returns at minimal cost over stock-picking risk.",
        "prod_largecap": "Moderate-to-aggressive investors comfortable with multi-year equity cycles.",
        "prod_elss": "Tax-paying investors in the old regime with a minimum three-year commitment.",
        "prod_term_life": "Any earner whose household depends on their income, especially with loans or dependents. Cover of roughly ten times annual income is a common planning benchmark.",
        "prod_health": "Every household; medical inflation routinely outruns self-insurance capacity.",
    }
    return base + suit[p["product_id"]]


def product_risks(p):
    risks = {
        "prod_fd": "Premature withdrawal earns a lower rate. Interest is fully taxable at slab rate. Bank failure risk mitigated but DICGC insurance caps at Rs. 5 lakh per bank per depositor.",
        "prod_rd": "Missed installments reduce maturity value. Interest taxable at slab. Premature closure converts the deposit to a savings rate for the completed period.",
        "prod_sweep": "Swept FD units broken early earn a penalised rate. Returns lag inflation over long periods.",
        "prod_ppf": "Fifteen-year illiquidity is the primary constraint. Rates reset quarterly by the government and may drift down.",
        "prod_debt_mf": "Not insured or guaranteed. A downgrade of held paper or rising-rate shock can produce negative returns over short windows.",
        "prod_sgb": "Gold price can fall sharply and stay down for years. Five-year minimum holding before the first exit window.",
        "prod_bal_adv": "Equity-leg drawdowns of 10-25 percent are historically normal. Returns are uncertain and never guaranteed.",
        "prod_nps": "Locked until 60 except narrow exceptions. Annuity purchase of at least 40 percent of the corpus at exit is mandatory and annuity rates then prevailing apply.",
        "prod_index_sip": "Full market risk: the index has fallen more than 35 percent peak-to-trough in past crises. Recovery has historically taken one to three years, which is not a promise of future recovery.",
        "prod_largecap": "Manager risk on top of market risk. Drawdowns similar to the index; poor manager selection can underperform the index over long stretches.",
        "prod_elss": "Thirty-six-month lock-in applies even if markets fall, so exit timing is impossible. Full equity volatility applies.",
        "prod_term_life": "No money back at any point. Claims can be repudiated for non-disclosure of medical history at proposal stage. Premiums rise steeply if purchased late.",
        "prod_health": "Premiums increase with age band and medical inflation. Co-pay, room-rent caps and disease-specific waiting periods limit certain claims.",
    }
    return risks[p["product_id"]]


def product_charges(p):
    ch = {
        "prod_fd": "No entry charge. TDS applies on interest above Rs. 40,000 per year (Rs. 50,000 for seniors) unless Form 15G/15H is filed.",
        "prod_rd": "Penalty of Rs. 50-Rs. 150 per missed installment depending on the amount. TDS rules identical to fixed deposits.",
        "prod_sweep": "No account fee beyond the standard schedule of charges. Sweep operations themselves are free.",
        "prod_ppf": "Zero charges. Contribution capped at Rs. 1.5 lakh per financial year across all PPF accounts.",
        "prod_debt_mf": "Expense ratio up to about 0.5 percent direct plan. Exit load nil after seven days. Taxation: LTCG above Rs. 1.25 lakh taxed at 12.5 percent.",
        "prod_sgb": "Issued at market gold price plus zero premium; 2.5 percent yearly interest paid by RBI. Redemption proceeds exempt from capital-gains tax.",
        "prod_bal_adv": "Expense ratio around 0.8-1.1 percent regular plan. Equity-oriented taxation: 12.5 percent LTCG beyond exemption.",
        "prod_nps": "Charge architecture under 0.1 percent per year plus record-keeping fees. Withdrawal corpus taxed as per prevailing rules; 60 percent lump sum at 60 currently exempt.",
        "prod_index_sip": "Expense ratio near 0.2 percent direct. STCG 20 percent within twelve months; LTCG 12.5 percent beyond Rs. 1.25 lakh yearly gain.",
        "prod_largecap": "Expense ratio around 1.0-1.6 percent regular plan. Equity taxation as above.",
        "prod_elss": "Expense ratio near 1.0-1.8 percent regular plan. Lock-in prevents exit-load complexity. Equity taxation applies.",
        "prod_term_life": "Annual premium level for the term; GST applies. No surrender value exists because there is no investment component.",
        "prod_health": "Annual premium revisable by insurer with IRDAI approval; GST applies. No-claim bonus raises sum insured without extra premium.",
    }
    return ch[p["product_id"]]


LOCK_TEXT = {0: "None (open-ended)"}


def lock_text(months):
    if months == 0:
        return "None (open-ended)"
    return f"{months} months"


def ret_text(low, high):
    if low == 0 and high == 0:
        return "Not applicable (protection product, no maturity value)"
    return f"{low}-{high} percent per annum (indicative, NOT guaranteed)"


def write_product_corpus(products):
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    for p in products:
        text = PRODUCT_DOC_TEMPLATE.format(
            name=p["name"], category=p["category"].replace("_", " ").title(), version="v1.0",
            pid=p["product_id"], risk=p["risk_level"].upper(),
            min_inv=p["min_investment"], lock=lock_text(p["lock_in_months"]),
            ret=ret_text(p["expected_return_low"], p["expected_return_high"]),
            tags=p["goal_tags"].replace("|", ", "),
            overview=product_overview(p), features=product_features(p),
            suitability=product_suitability(p), risks=product_risks(p),
            charges=product_charges(p),
        )
        (PRODUCTS_DIR / f"{p['product_id']}.txt").write_text(text, encoding="utf-8")




def main():
    CUSTOMERS_DIR.mkdir(parents=True, exist_ok=True)
    GOALS_DIR.mkdir(parents=True, exist_ok=True)

    customers = generate_customers()
    cust_fields = list(customers[0].keys())
    write_csv(CUSTOMERS_DIR / "customers.csv", customers, cust_fields)

    txns = generate_transactions(customers)
    txn_fields = ["txn_id", "customer_id", "date", "direction", "category", "amount", "description"]
    write_csv(CUSTOMERS_DIR / "transactions.csv", txns, txn_fields)

    prod_fields = list(PRODUCTS[0].keys())
    write_csv(PRODUCTS_DIR / "products.csv", PRODUCTS, prod_fields)
    write_product_corpus(PRODUCTS)

    (GOALS_DIR / "goal_definitions.json").write_text(
        json.dumps(GOAL_DEFS, indent=2), encoding="utf-8")

    print(f"customers:      {len(customers)} rows -> data/customers/customers.csv")
    print(f"transactions:   {len(txns)} rows -> data/customers/transactions.csv")
    print(f"products:       {len(PRODUCTS)} catalog entries -> data/products/")
    print(f"goals:          {len(GOAL_DEFS)} definitions -> data/goals/goal_definitions.json")


if __name__ == "__main__":
    main()

