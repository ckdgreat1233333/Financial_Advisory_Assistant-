"""Deterministic suitability engine and mis-selling prevention controls.

Every recommendation passes through this rules layer BEFORE any LLM is
involved. The engine produces one of three verdicts per product:

    eligible  - passes all hard constraints; may carry warnings
    escalate  - allowed only with human (RM/supervisor) approval
    blocked   - fails a hard constraint; must never be recommended

Rules are grounded in the compliance corpus:
    SEBI/HO/OIAE/2025-26/07  suitability obligation, escalation, language
    RBI/2025-26/21           KYC prerequisite, vulnerable customers, override
"""
from __future__ import annotations

import json
from pathlib import Path

from models.advisory import CustomerProfile, ProductCandidate

BASE = Path(__file__).resolve().parent.parent
GOAL_DEFS_PATH = BASE / "data" / "goals" / "goal_definitions.json"

RISK_RANK = {"low": 0, "moderate": 1, "high": 2}
PROFILE_RANK = {"conservative": 0, "moderate": 1, "aggressive": 2}

SEBI_DOC = "sebi_miselling_advisory_standards"
RBI_DOC = "rbi_fair_practices_customer_advisory"

CITE_SUITABILITY = f"{SEBI_DOC}-1"
CITE_RISK_PROFILING = f"{SEBI_DOC}-1_1"
CITE_ESCALATION = f"{SEBI_DOC}-3"
CITE_LANGUAGE = f"{SEBI_DOC}-2_1"
CITE_KYC = f"{RBI_DOC}-2"
CITE_VULNERABLE = f"{RBI_DOC}-2_1"
CITE_OVERRIDE = f"{RBI_DOC}-3"


class SuitabilityEngine:

    def __init__(self):
        self.goal_defs = json.loads(GOAL_DEFS_PATH.read_text(encoding="utf-8")) \
            if GOAL_DEFS_PATH.exists() else {}

    def binding_profile(self, profile: CustomerProfile) -> str:
        """The more conservative of stated appetite and computed capacity binds."""
        stated, computed = profile.stated_risk_appetite, profile.computed_risk_capacity
        return stated if PROFILE_RANK.get(stated, 1) <= PROFILE_RANK.get(computed, 1) else computed

    def evaluate(self, profile: CustomerProfile, products: list[dict],
                 goal: str | None = None, amount: float | None = None,
                 horizon_months: int | None = None) -> list[ProductCandidate]:
        candidates: list[ProductCandidate] = []
        kyc_ok = profile.kyc_status == "verified"
        binding = self.binding_profile(profile)
        effective_horizon = horizon_months or profile.investment_horizon_months
        affordability_cap = max(profile.savings_balance * 0.25, max(profile.monthly_surplus, 0) * 6)

        for prod in products:
            c = ProductCandidate(
                product_id=prod["product_id"], name=prod["name"],
                category=prod["category"], asset_class=prod["asset_class"],
                risk_level=prod["risk_level"], verdict="eligible",
            )
            score = 0.0

            if not kyc_ok:
                c.verdict = "blocked"
                c.warnings.append(
                    f"KYC status is '{profile.kyc_status}'. Recommendations are withheld "
                    f"until KYC updation completes.")
                c.citation_refs.append(CITE_KYC)
                candidates.append(c)
                continue

            allowed = [a.strip() for a in str(prod.get("allowed_risk_profiles", "")).split("|") if a.strip()]
            if binding not in allowed:
                gap = RISK_RANK.get(prod["risk_level"], 0) - PROFILE_RANK.get(binding, 1)
                if gap >= 2:
                    c.verdict = "blocked"
                    c.reasons.append(
                        f"Risk grade '{prod['risk_level']}' far exceeds assessed capacity '{binding}'.")
                    c.citation_refs.append(CITE_SUITABILITY)
                else:
                    c.verdict = "escalate"
                    c.warnings.append(
                        f"Product risk exceeds the binding risk capacity '{binding}' by one grade. "
                        f"Proceeds only with documented client acknowledgement and supervisor approval.")
                    c.citation_refs.extend([CITE_SUITABILITY, CITE_ESCALATION])

            lock_exceeds_horizon = (
                (effective_horizon > 0 and prod["lock_in_months"] > effective_horizon)
                or (effective_horizon <= 0 and prod["lock_in_months"] > 0)
            )
            if lock_exceeds_horizon:
                c.verdict = "blocked"
                c.reasons.append(
                    f"Lock-in of {prod['lock_in_months']} months exceeds the customer's "
                    f"{'unknown' if effective_horizon <= 0 else effective_horizon}-month horizon.")
            elif effective_horizon > 0 and prod["min_horizon_months"] > effective_horizon:
                c.warnings.append(
                    f"Designed for horizons of {prod['min_horizon_months']}+ months; customer "
                    f"horizon is {effective_horizon} months. Liquidity risk applies.")

            min_inv = float(prod.get("min_investment") or 0)
            if amount is not None and amount < min_inv:
                c.verdict = "blocked"
                c.reasons.append(
                    f"Requested Rs {amount:,.0f} is below the minimum ticket of Rs {min_inv:,.0f}.")
            elif min_inv > affordability_cap and amount is None:
                c.warnings.append(
                    f"Minimum ticket Rs {min_inv:,.0f} exceeds the estimated comfortable "
                    f"commitment of Rs {affordability_cap:,.0f}. Affordability review advised.")

            tags = [t for t in str(prod.get("goal_tags", "")).split("|") if t]
            goal_matched = False
            if goal:
                goal_matched = goal in tags
                if not goal_matched:
                    c.warnings.append(
                        f"Product does not target the '{goal}' goal directly "
                        f"(targets: {', '.join(tags)}).")
                elif c.verdict == "eligible":
                    score += 2.0
            else:
                overlap = set(tags) & set(profile.goals)
                goal_matched = bool(overlap)
                if goal_matched and c.verdict == "eligible":
                    score += 1.5 * (len(overlap) / max(1, len(tags)))

            if profile.age >= 65 and prod["risk_level"] == "high" and c.verdict == "eligible":
                c.verdict = "escalate"
                c.warnings.append(
                    "Senior citizen presenting a high-risk product: mandatory human review "
                    "before it may be shown as suitable.")
                c.citation_refs.append(CITE_VULNERABLE)

            if profile.first_time_investor and prod["risk_level"] == "high" and c.verdict == "eligible":
                c.verdict = "escalate"
                c.warnings.append(
                    "First-time investor considering a high-risk product: supervised "
                    "acknowledgement of loss capacity required first.")
                c.citation_refs.extend([CITE_RISK_PROFILING, CITE_ESCALATION])

            if prod["risk_level"] == "high" and c.verdict == "eligible":
                c.warnings.append(
                    "Market-linked: returns are NOT guaranteed and drawdowns are possible.")

            if profile.protection_gap and prod["category"] != "protection":
                c.warnings.append(
                    "Protection gap detected (no life/health cover on record). Consider "
                    "term and health cover before growth investments.")

            if profile.emergency_buffer_months < 3 and \
                    prod["liquidity"] in ("none", "low") and prod["category"] != "protection":
                c.warnings.append(
                    f"Emergency buffer covers only {profile.emergency_buffer_months:.1f} months "
                    f"of expenses while this product locks funds.")

            if prod["product_id"] in profile.existing_products:
                score -= 0.25
                c.warnings.append("Already held by the customer; adding more concentrates exposure.")

            if c.verdict == "eligible":
                if binding == prod["risk_level"]:
                    score += 1.5
                if "tax" in (profile.goals + ([goal] if goal else [])) and \
                        str(prod.get("tax_benefit")) == "yes":
                    score += 0.5
                if profile.emergency_buffer_months < 3 and prod["liquidity"] in ("high", "medium"):
                    score += 0.75
                if profile.age >= 60 and str(prod.get("senior_citizen_friendly")) == "yes":
                    score += 0.25
                if effective_horizon >= prod["min_horizon_months"] and prod["min_horizon_months"] > 0:
                    score += 0.5
                c.score = round(min(1.0, max(0.05, score / 4.5)), 3)

            if c.verdict == "escalate":
                c.score = round(max(c.score, 0.30), 3)
                c.citation_refs.append(CITE_OVERRIDE)

            candidates.append(c)

        return candidates


def apply_concentration_cap(eligible: list[ProductCandidate], cap_per_class: int = 2,
                            top_n: int = 5) -> list[ProductCandidate]:
    """Limits same-category concentration in what the assistant surfaces."""
    picked, counts = [], {}
    for c in sorted(eligible, key=lambda x: (-x.score, x.product_id)):
        counts[c.category] = counts.get(c.category, 0)
        if counts[c.category] >= cap_per_class:
            continue
        picked.append(c)
        counts[c.category] += 1
        if len(picked) >= top_n:
            break
    return picked
