"""GenAI layer of the advisory assistant.

The agent NEVER decides suitability - that is done deterministically by
guardrails.suitability.SuitabilityEngine. The agent only verbalizes engine
output into track-appropriate language, grounded in retrieved product
literature. If the LLM fails or returns unparseable output, deterministic
template narratives are used so the system degrades safely.
"""
from __future__ import annotations

import json
import logging

from models.advisory import CustomerProfile, ProductCandidate

logger = logging.getLogger("advisory_agent")

MAX_CANDIDATE_LINES = 5


class RecommendationAgent:

    def __init__(self, llm, prompts):
        self.llm = llm
        self.prompts = prompts

    def _candidates_block(self, candidates: list[ProductCandidate], include_blocked: bool) -> str:
        lines = []
        shown = 0
        for c in candidates:
            if not include_blocked and c.verdict == "blocked":
                continue
            if shown >= MAX_CANDIDATE_LINES * (3 if include_blocked else 1):
                break
            parts = [f"- {c.name} [{c.product_id}] verdict={c.verdict} score={c.score}"]
            if c.reasons:
                parts.append(f"  constraints: {'; '.join(c.reasons)}")
            if c.warnings:
                parts.append(f"  warnings: {'; '.join(c.warnings[:2])}")
            lines.append("\n".join(parts))
            shown += 1
        return "\n".join(lines)

    def verbalize_for_rm(self, profile: CustomerProfile, question: str,
                         candidates: list[ProductCandidate], context: str) -> tuple[str, dict]:
        prompt = self.prompts.load(
            "rm_advisory_prompt.txt",
            profile_summary=profile.summary_text(),
            segment=profile.segment,
            question=question,
            candidates_block=self._candidates_block(candidates, include_blocked=True),
            context=context,
        )
        raw = self._safe_generate(prompt)
        parsed = self._extract_json(raw)
        if parsed and "summary" in parsed:
            return str(parsed.get("summary", "")).strip(), parsed
        return self._rm_fallback(profile, question, candidates), {}

    def narrate_for_customer(self, profile: CustomerProfile, goal: str, amount_line: str,
                             eligible: list[ProductCandidate], context: str) -> str:
        prompt = self.prompts.load(
            "customer_guidance_prompt.txt",
            profile_summary=profile.summary_text(),
            goal=goal,
            amount_line=amount_line,
            candidates_block=self._candidates_block(eligible[:MAX_CANDIDATE_LINES],
                                                    include_blocked=False),
            context=context,
        )
        text = self._safe_generate(prompt)
        if not text:
            return self._customer_fallback(goal)
        return text

    def _safe_generate(self, prompt: str) -> str:
        try:
            return self.llm.generate(prompt, temperature=0.2, max_tokens=900)
        except Exception as exc:
            logger.warning("LLM generation failed: %s", exc)
            return ""

    @staticmethod
    def _extract_json(raw: str) -> dict | None:
        if not raw:
            return None
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None

    def _rm_fallback(self, profile: CustomerProfile, question: str,
                     candidates: list[ProductCandidate]) -> str:
        eligible = [c for c in candidates if c.verdict == "eligible"][:3]
        names = ", ".join(c.name for c in eligible) or "no eligible products"
        return (
            f"{profile.name}: {profile.life_stage.replace('_', ' ')} stage, savings rate "
            f"{profile.savings_rate:.0%}, emergency buffer {profile.emergency_buffer_months:.1f} months, "
            f"binding risk capacity '{profile.computed_risk_capacity}'. "
            f"Regarding '{question}', the strongest engine-approved options are {names}."
        )

    def _customer_fallback(self, goal: str) -> str:
        return (
            f"Based on your {goal} goal, a few options may be worth exploring with your "
            "relationship manager. Deposit-style options offer stability but modest growth; "
            "market-linked options offer higher potential growth but their value can also fall, "
            "and returns are never guaranteed. A human advisor can help you weigh these trade-offs "
            "before you decide."
        )
