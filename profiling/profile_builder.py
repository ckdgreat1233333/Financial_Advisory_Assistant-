"""Builds enriched CustomerProfile objects from raw rows and transactions.

The profiler is deterministic and rule-based: every derived feature can be
traced to a specific data source, which is what makes downstream advice
explainable.
"""
from __future__ import annotations

import database.db as db
from models.advisory import CustomerProfile

INVESTMENT_CATEGORIES = {"prod_index_sip", "prod_largecap", "prod_bal_adv", "prod_elss",
                         "prod_debt_mf", "prod_nps", "prod_ppf"}
INSURANCE_PRODUCTS = {"prod_term_life", "prod_health"}


class ProfileBuilder:

    def build(self, customer_id: str) -> CustomerProfile:
        row = db.get_customer_row(customer_id)
        if not row:
            raise ValueError(f"Customer '{customer_id}' not found")
        summary = db.get_customer_txn_summary(customer_id)
        profile = self._from_rows(row)
        self._derive_behaviour(profile, row, summary)
        return profile

    def build_all(self) -> dict[str, CustomerProfile]:
        profiles = {}
        for c in db.list_customers():
            try:
                profiles[c["customer_id"]] = self.build(c["customer_id"])
            except ValueError:
                continue
        return profiles

    def _from_rows(self, row: dict) -> CustomerProfile:
        goals = [g for g in (row.get("goals") or "").split("|") if g]
        holdings = [h for h in (row.get("existing_products") or "").split("|") if h]
        return CustomerProfile(
            customer_id=row["customer_id"],
            name=row["name"],
            age=int(row["age"] or 0),
            city=row.get("city", ""),
            occupation=row.get("occupation", ""),
            employment_type=row.get("employment_type", ""),
            annual_income=float(row.get("annual_income") or 0),
            monthly_income=float(row.get("monthly_income") or 0),
            marital_status=row.get("marital_status", "single"),
            dependents=int(row.get("dependents") or 0),
            kyc_status=row.get("kyc_status", "verified"),
            stated_risk_appetite=row.get("stated_risk_appetite", "moderate"),
            investment_horizon_months=int(row.get("investment_horizon_months") or 0),
            goals=goals,
            has_loan=str(row.get("has_loan")).lower() == "true",
            savings_balance=float(row.get("savings_balance") or 0),
            existing_products=holdings,
        )

    def _derive_behaviour(self, p: CustomerProfile, row: dict, t: dict) -> None:
        months = max(1, self._months_between(t))
        avg_credit = (t.get("total_credits") or 0.0) / months
        avg_debit = (t.get("total_debits") or 0.0) / months
        credits = t.get("total_credits") or 0.0

        p.monthly_surplus = round(avg_credit - avg_debit, 2)
        p.savings_rate = round((credits - (t.get("total_debits") or 0.0)) / credits, 4) if credits else 0.0
        p.sip_ratio = round((t.get("sip_total") or 0.0) / credits, 4) if credits else 0.0
        p.emi_burden = round((t.get("emi_total") or 0.0) / credits, 4) if credits else 0.0
        debits = t.get("total_debits") or 1.0
        p.lifestyle_ratio = round((t.get("lifestyle_total") or 0.0) / debits, 4)
        p.emergency_buffer_months = round(
            p.savings_balance / avg_debit, 2) if avg_debit > 0 else 0.0

        equity_held = bool(set(p.existing_products) & INVESTMENT_CATEGORIES)
        sip_active = p.sip_ratio >= 0.05
        p.investing_activity_score = round(
            min(1.0, (p.sip_ratio * 3) + (len(p.existing_products) * 0.15) + (0.2 if equity_held else 0)),
            3)

        score = self._risk_score(p, equity_held, sip_active)
        p.computed_risk_capacity = ("aggressive" if score >= 2.5
                                    else "conservative" if score <= -1.0 else "moderate")

        if p.stated_risk_appetite != p.computed_risk_capacity:
            p.risk_alignment_note = (
                f"Stated appetite '{p.stated_risk_appetite}' differs from computed capacity "
                f"'{p.computed_risk_capacity}'; treating the more conservative of the two as binding.")
        else:
            p.risk_alignment_note = "Stated appetite matches computed capacity."

        p.life_stage = self._life_stage(p)
        insurance_held = any(h in INSURANCE_PRODUCTS for h in p.existing_products)
        p.protection_gap = (not insurance_held) and (p.dependents > 0 or p.has_loan or p.age < 60)
        p.first_time_investor = (not p.existing_products) and not sip_active

    def _risk_score(self, p: CustomerProfile, equity_held: bool, sip_active: bool) -> float:
        score = 0.0
        if p.age < 30:
            score += 1.5
        elif p.age <= 45:
            score += 0.5
        elif p.age > 60:
            score -= 1.5
        elif p.age > 50:
            score -= 0.5
        if p.emergency_buffer_months >= 6:
            score += 1.0
        elif p.emergency_buffer_months < 3:
            score -= 1.0
        if p.savings_rate >= 0.25:
            score += 1.0
        elif p.savings_rate < 0.10:
            score -= 1.0
        if p.emi_burden > 0.35:
            score -= 1.0
        if p.dependents >= 2:
            score -= 0.5
        if p.investment_horizon_months >= 84:
            score += 1.0
        elif p.investment_horizon_months < 24:
            score -= 1.0
        if equity_held:
            score += 1.0
        if sip_active:
            score += 0.5
        return score

    def _life_stage(self, p: CustomerProfile) -> str:
        if p.age >= 60:
            return "retirement"
        if p.age >= 50:
            return "pre_retirement"
        if p.marital_status == "married" or p.dependents > 0:
            return "family_formation"
        if p.age < 30:
            return "early_career"
        return "wealth_building"

    @staticmethod
    def _months_between(t: dict) -> int:
        from datetime import date
        first = str(t.get("first_date") or "")
        last = str(t.get("last_date") or "")
        try:
            d1 = date.fromisoformat(first[:10])
            d2 = date.fromisoformat(last[:10])
        except ValueError:
            return 12
        months = (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1
        return max(1, months)
