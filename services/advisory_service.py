"""Advisory service facade.

Wires the full pipeline for both tracks:
    profile -> segmentation -> suitability engine -> product RAG -> agent -> compliance scrub
and records every session in the advisory audit trail.
"""
from __future__ import annotations

import logging
import uuid

import database.db as db
from agents.recommendation_agent import RecommendationAgent
from guardrails.compliance import (
    CUSTOMER_DISCLAIMERS,
    RM_DISCLAIMER,
    enforce_non_promissory,
)
from guardrails.suitability import SuitabilityEngine, apply_concentration_cap
from models.advisory import AdvisoryResponse, ProductCandidate
from profiling.profile_builder import ProfileBuilder
from profiling.segmentation import get_segmenter
from advisory.product_store import ProductKnowledgeStore
from services.llm_service import LLMService
from services.prompt_service import PromptService

logger = logging.getLogger("advisory_service")

GOAL_LABELS = {"education": "Children's Education", "retirement": "Retirement Corpus",
               "wealth": "Wealth Creation", "safety": "Emergency & Safety Buffer",
               "tax": "Tax Saving"}


class AdvisoryService:

    def __init__(self):
        self.store = ProductKnowledgeStore()
        self.engine = SuitabilityEngine()
        self.llm = LLMService()
        self.prompts = PromptService()
        self.agent = RecommendationAgent(self.llm, self.prompts)
        self._products = self._load_products()

    def _load_products(self) -> list[dict]:
        conn = db.get_db()
        rows = conn.execute("SELECT * FROM products").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_profile(self, customer_id: str):
        profile = ProfileBuilder().build(customer_id)
        segmenter = get_segmenter()
        profile.segment = segmenter.labels.get(customer_id, "")
        return profile

    # ── Business track (RM decision support) ───────────────────

    def rm_query(self, customer_id: str, question: str, actor: str = "") -> AdvisoryResponse:
        profile = self.get_profile(customer_id)
        candidates = self.engine.evaluate(profile, self._products)

        eligible = apply_concentration_cap([c for c in candidates if c.verdict == "eligible"])
        escalate = [c for c in candidates if c.verdict == "escalate"]
        blocked_count = sum(1 for c in candidates if c.verdict == "blocked")

        context = self._context_for(eligible[:3] + escalate[:1], question)
        summary, extra = self.agent.verbalize_for_rm(profile, question, candidates, context)

        response = AdvisoryResponse(
            track="rm", customer_id=customer_id, question=question,
            answered=bool(summary), profile_summary=profile.summary_text(),
            segment=profile.segment, recommendations=eligible + escalate,
            narrative=summary, confidence=0.8 if summary else 0.3,
            disclaimers=[RM_DISCLAIMER],
            needs_human_override=bool(escalate),
            escalation_reason=(f"{len(escalate)} recommendation(s) require supervisor approval; "
                               f"{blocked_count} blocked by hard constraints.") if escalate or blocked_count else None,
            retrieved_refs=sorted({ref for c in eligible + escalate for ref in c.citation_refs}),
        )
        if isinstance(extra, dict):
            flags = extra.get("risk_flags") or []
            if isinstance(flags, list):
                response.compliance_notes.extend(str(f) for f in flags[:5])
        self._log(response, actor)
        return response

    # ── Customer track (personalized guidance) ─────────────────

    def customer_goal(self, customer_id: str, goal: str, amount: float | None = None,
                      horizon_months: int | None = None, actor: str = "") -> AdvisoryResponse:
        goal = goal if goal in GOAL_LABELS else "wealth"
        profile = self.get_profile(customer_id)
        candidates = self.engine.evaluate(profile, self._products, goal=goal,
                                          amount=amount, horizon_months=horizon_months)

        eligible = apply_concentration_cap(
            [c for c in candidates if c.verdict == "eligible"], top_n=3)
        escalated_hidden = any(c.verdict == "escalate" for c in candidates)

        amount_line = f"about Rs {amount:,.0f}" if amount else "not specified"
        context = self._context_for(eligible, goal)
        narrative = self.agent.narrate_for_customer(profile, GOAL_LABELS[goal],
                                                    amount_line, eligible, context)
        narrative, violations = enforce_non_promissory(narrative)

        response = AdvisoryResponse(
            track="customer", customer_id=customer_id,
            question=f"Guidance for {goal} goal", answered=True,
            profile_summary="", segment="",
            recommendations=eligible, narrative=narrative,
            goal=goal, amount=amount,
            confidence=0.75 if not violations else 0.65,
            disclaimers=list(CUSTOMER_DISCLAIMERS),
            needs_human_override=False,
            compliance_notes=(
                [f"non-promissory scrub applied: {', '.join(violations)}"] if violations else []),
            retrieved_refs=sorted({ref for c in eligible for ref in c.citation_refs}),
        )
        self._log(response, actor)
        return response

    # ── Helpers ────────────────────────────────────────────────

    def _context_for(self, candidates: list[ProductCandidate], query: str) -> str:
        parts = []
        seen = set()
        for c in candidates:
            if c.product_id in seen:
                continue
            seen.add(c.product_id)
            try:
                chunks = self.store.retrieve_for_product(c.product_id, query or c.name, k=2)
            except Exception as exc:
                logger.warning("Retrieval failed for %s: %s", c.product_id, exc)
                continue
            for r in chunks:
                parts.append(f"[{c.product_id} | {r.chunk.clause_ref}] {r.chunk.text}")
        return "\n\n".join(parts[:8])

    def _log(self, response: AdvisoryResponse, actor: str) -> None:
        try:
            db.create_advisory_session(
                session_id=f"ADV-{uuid.uuid4().hex[:10]}", track=response.track,
                customer_id=response.customer_id, actor=actor,
                question=response.question[:200], answered=response.answered,
                needs_human_override=response.needs_human_override,
                escalation_reason=response.escalation_reason or "",
                payload=str(len(response.recommendations)),
            )
        except Exception as exc:
            logger.warning("Advisory session log failed: %s", exc)


_default_advisory: AdvisoryService | None = None


def get_advisory_service() -> AdvisoryService:
    global _default_advisory
    if _default_advisory is None:
        _default_advisory = AdvisoryService()
    return _default_advisory
