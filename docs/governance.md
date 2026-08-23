# Ethics, Risk & Governance Controls

This document maps the assistant's controls to the governance expectations of
the capstone brief: bias, over-personalization, regulatory compliance, and
human-in-the-loop checkpoints.

---

## 1. Bias in Recommendations

| Risk | Mitigation | Where |
|---|---|---|
| Demographic proxying (gender/city influencing advice) | Gender is stored but **never used** by the risk score or suitability rules; city only sets cost-of-living context in raw data, not verdicts | `profiling/profile_builder.py`, `guardrails/suitability.py` |
| Segment stereotyping | Segments are descriptive labels for RMs, never rule inputs — no product verdict reads `segment` | `suitability.py` (no reference) |
| Wealth bias toward high-revenue products | The engine has **no revenue field**; scoring rewards goal fit, horizon fit and risk alignment only. Cross-sell pressure is structurally impossible | `evaluate()` scoring weights |
| Label drift across clusters | Rank-based cluster naming avoids absolute thresholds that could encode majority norms | `segmentation.py` |

**Fairness test:** `test_conservative_high_risk_blocked_with_sebi_citation` proves protection applies by *capacity*, not by wealth or identity.

## 2. Over-Personalization Risks

| Risk | Mitigation |
|---|---|
| Customers boxed into past behaviour | Stated appetite can raise capacity up to computed level; only downward binding is automatic, and mismatches are surfaced to the RM (`risk_alignment_note`) rather than silently enforced |
| Filter bubbles (only "safe" suggestions forever) | RM track shows escalated candidates too — the human decides whether to proceed with documented acknowledgement |
| Creepy use of transaction detail in customer chat | Customer track prompt forbids quoting raw profile internals ("Do not reveal internal scores, KYC details, segment names"); payload strips `profile_summary` entirely (`profile_summary=""`) |

## 3. Regulatory Compliance Mapping (SEBI / RBI)

| Requirement | Source clause | Implementation |
|---|---|---|
| Suitability obligation — product grade vs client capacity | SEBI/HO/OIAE/2025-26/07 §1 | Gap-1 ⇒ escalate; gap ≥ 2 ⇒ block; citation attached to candidate |
| Documented risk profiling beyond stated willingness | SEBI §1.1 | Behavioural features feed `computed_risk_capacity`; conservative value binds |
| Retained rationale per recommendation | SEBI §1.2 | Reasons/warnings persisted in `advisory_sessions` + audit ledger |
| Non-promissory language | SEBI §2.1 | Banned-pattern scrubber runs post-generation; violations logged |
| Escalation before execution for vulnerable cases | SEBI §3, RBI §2.1 | Senior-citizen & first-time-investor escalations with mandatory override banner |
| KYC prerequisite for recommendations | RBI/2025-26/21 §2 | Global gate: any non-verified status blocks every recommendation |
| Guidance-vs-advice distinction | RBI §1.1 | Customer track labelled guidance; three-part disclaimer states it is not investment advice |
| Human access to review/override system output | RBI §3 | RM console escalation banners + `needs_human_override` flag on every response |

## 4. Human-in-the-Loop Checkpoints

```
① Profile build      ── deterministic, auditable features (no human needed)
② Engine verdicts    ── deterministic
③ ESCALATION GATE    ── HUMAN: supervisor approval required for escalated items
④ LLM verbalization  ── machine output, but…
⑤ SCRUBBER           ── machine control on language
⑥ CUSTOMER DECISION  ── HUMAN: customer explicitly nudged to consult an advisor
                        before acting; assistant never executes anything
```

Escalations are visible in the RM console with a red banner and cannot be
"dismissed" in the UI — the flag travels with the payload until an approved
human acts outside the system.

## 5. Audit Trail

Every interaction writes two records:

- `advisory_sessions` — track, customer, question, answered, override flag, escalation reason.
- `audit_logs` — actor-level ledger entries (`RM Advisory Query`, `Customer Goal Guidance`, profile views), with elevated risk level when overrides are pending.

## 6. Out-of-Scope Guarantees

The system contains **no execution path**: it cannot place orders, move money,
or generate predictions of guaranteed performance. Expected-return figures are
labelled indicative and never guaranteed — in structured data, corpus prose,
prompts, and scrubber patterns simultaneously.

## 7. Known Limitations (honest disclosure)

1. Synthetic data may under-represent irregular-income volatility patterns.
2. KMeans segments are descriptive; they are not validated against business KPIs.
3. The banned-language list covers common mis-selling phrases but not all possible phrasings; it is a control layer, not proof of compliance.
4. Compliance documents are synthetic summaries written for this capstone, not verbatim regulation text.
