"""Compliance-aligned tone management.

Enforces non-promissory language on every customer-facing string AFTER the
LLM step, so a prompt-injected or drifted model output can never reach a
customer promising guaranteed outcomes. Violations are logged for audit.
"""
from __future__ import annotations

import re

BANNED_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\bguaranteed?\s+(?:returns?|profits?|income|growth)\b", re.I),
     "market-linked returns that are not guaranteed",
     "guaranteed returns claim"),
    (re.compile(r"\bassured\s+(?:returns?|profits?|payouts?)\b", re.I),
     "indicative returns that are not assured",
     "assured returns claim"),
    (re.compile(r"\brisks?[\s-]*free\b", re.I), "low-risk but never free of all risk", "risk-free claim"),
    (re.compile(r"\bno\s+risk\b", re.I), "limited risk rather than zero risk", "no-risk claim"),
    (re.compile(r"\bdefinitely\s+(?:will|shall|grow|double|earn)\b", re.I),
     "may, subject to market conditions", "definitive outcome claim"),
    (re.compile(r"\b(?:sure|certain)[\s-]*shot\b", re.I), "possible but uncertain", "sure-shot claim"),
    (re.compile(r"\bmultibagger\b", re.I), "a potentially higher-return product",
     "multibagger hype"),
    (re.compile(r"\bdouble[sd]?\s+your\s+money\b", re.I),
     "grow your money over time, subject to markets", "doubling promise"),
    (re.compile(r"\byou\s+must\s+(?:invest|buy|purchase)\b", re.I),
     "you may consider", "binding instruction"),
    (re.compile(r"\binvest\s+now\s+before\b", re.I), "you may evaluate in your own time",
     "urgency pressure"),
]

CUSTOMER_DISCLAIMERS = [
    "This is general financial guidance generated with AI assistance and does not "
    "constitute investment advice or a recommendation to buy any specific product.",
    "Market-linked products carry risk; past performance is not indicative of future "
    "results and returns are never guaranteed.",
    "Please consult a qualified relationship manager or SEBI-registered adviser before "
    "making investment decisions.",
]

RM_DISCLAIMER = ("Internal decision-support only. Suitability verdicts are system-generated "
                 "and require RM judgement; escalate-flagged items need documented supervisor "
                 "approval before customer presentation.")


def enforce_non_promissory(text: str) -> tuple[str, list[str]]:
    """Scrub banned claims. Returns (clean_text, violations)."""
    violations: list[str] = []
    if not text:
        return text, violations
    for pattern, replacement, label in BANNED_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            violations.append(f"{label} ({len(matches)}x)")
            text = pattern.sub(replacement, text)
    return text, violations


def compliance_notes_for_track(track: str) -> list[str]:
    return [RM_DISCLAIMER] if track == "rm" else list(CUSTOMER_DISCLAIMERS)
