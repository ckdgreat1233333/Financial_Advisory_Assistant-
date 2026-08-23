# Architecture — Personalized Financial Advisory Assistant

## 1. End-to-End Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                                │
│                    static/index.html (Vanilla JS SPA)                      │
│                                                                            │
│   ┌───────────────────────────────┐   ┌────────────────────────────────┐   │
│   │ RM CONSOLE (Business Track)   │   │ CUSTOMER PORTAL (Customer      │   │
│   │                               │   │ Track)                         │   │
│   │ • Customer directory          │   │ • Goal picker (education,      │   │
│   │ • Profile card: segment,      │   │   retirement, wealth, safety,  │   │
│   │   life stage, feature chips   │   │   tax) + amount                │   │
│   │ • Advisory query box          │   │ • Plain-language guidance      │   │
│   │ • Verdict cards + risk flags  │   │ • Suitable-options only        │   │
│   │ • Escalation / override banner│   │ • Mandatory disclaimers        │   │
│   └───────────────┬───────────────┘   └───────────────┬────────────────┘   │
└───────────────────┼────────────────────────────────────┼───────────────────┘
                    │  POST /api/advisory/rm-query       │  POST /api/advisory/customer-goal
                    ▼                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       API LAYER — FastAPI (app.py)                         │
│   auth (role-based portals) · CORS · audit hooks · request validation      │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                  ADVISORY FACADE — services/advisory_service.py            │
│                                                                            │
│   ① PROFILE          ② SEGMENT           ③ EVALUATE        ④ GROUND       │
│   ┌─────────────┐    ┌──────────────┐     ┌───────────────┐  ┌───────────┐ │
│   │ profiling/  │    │ profiling/   │     │ guardrails/   │  │ advisory/ │ │
│   │ profile_    │───▶│ segmentation │────▶│ suitability.py│─▶│ product_  │ │
│   │ builder.py  │    │ MiniLM+KMeans│     │ verdicts+score│  │ store.py  │ │
│   └─────────────┘    └──────────────┘     └───────┬───────┘  └─────┬─────┘ │
│                                                   │                │       │
│            blocked ⇒ excluded from customer flow  │                │       │
│            escalate ⇒ human override required ◀───┘                │       │
│                                                    ▼               ▼       │
│                                          ⑤ VERBALIZE      clause-level   │
│                                          ┌──────────────┐ RAG context     │
│                                          │ agents/rec.  │◀────────────────│
│                                          │ _agent.py    │                 │
│                                          │ (LLM explains│                 │
│                                          │  NEVER decides)                │
│                                          └──────┬───────┘                 │
│                                                 ▼                         │
│                                          ⑥ SCRUB + DISCLOSE               │
│                                          ┌──────────────┐                 │
│                                          │ guardrails/  │  banned claims  │
│                                          │ compliance.py│  removed AFTER  │
│                                          └──────┬───────┘  generation    │
└─────────────────────────────────────────────────┼─────────────────────────┘
                                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            DATA & KNOWLEDGE LAYER                          │
│                                                                            │
│  SQLite (database/db.py)              Version-controlled corpus            │
│  ├ users, audit_logs                  ├ data/products/*.txt                │
│  ├ customers (150 synthetic)          │   (13 products × clauses)          │
│  ├ transactions (~13k rows, 12 mo)    └ manifest JSON sidecar + hashes     │
│  ├ products (13 structured rows)                                           │
│  └ advisory_sessions                  FAISS index: product_index.bin       │
│                                                                            │
│  data/customers/*.csv ← scripts/generate_data.py (seeded, deterministic)   │
│  data/goals/goal_definitions.json (horizons + risk guidance per goal)      │
└────────────────────────────────────────────────────────────────────────────┘
```

## 2. Customer Data Ingestion & Profiling Pipeline

```
customers.csv ──┐
                ├──► SQLite seed (auto on startup) ──► ProfileBuilder
transactions.csv┘                                            │
                                                             ▼
   raw attributes            derived behavioural features (traceable)
   ─ age, income             ─ savings_rate = (credits − debits)/credits
   ─ dependents, loan        ─ monthly_surplus, sip_ratio, emi_burden
   ─ KYC status              ─ emergency_buffer_months = balance / avg spend
   ─ stated appetite         ─ computed_risk_capacity (weighted rule score)
   ─ horizon, goals          ─ life_stage, protection_gap, first_time_investor
```

**Feature justification (deliverable 6.2A).** Every feature exists to satisfy a specific regulatory or suitability question:

| Feature | Why it is used |
|---|---|
| `computed_risk_capacity` | SEBI §1 requires assessment against *documented* capacity; we combine stated appetite with behaviour and let the **more conservative bind** |
| `emergency_buffer_months` | Illiquid products must not be recommended when the buffer is thin |
| `emi_burden` | High fixed obligations reduce genuine loss capacity |
| `life_stage` | Goal patterns (education fees vs retirement) drive goal-tag matching |
| `protection_gap` | Cover-first guidance prevents investment-before-insurance mis-selling |
| `first_time_investor` | Triggers mandatory escalation for high-risk products |

## 3. Embedding-Based Segmentation

- Each profile's natural-language summary (`summary_text()`) is embedded with **all-MiniLM-L6-v2** (384-dim, L2-normalized).
- **KMeans k=5**, `random_state=42`, `n_init=10` — fully reproducible.
- Cluster names are assigned by **ranking centroid statistics relative to other clusters** (age, savings rate, buffer, investing activity), producing stable explainable labels such as *Pre-Retirement Preservers*, *High-Saving Wealth Builders*, *Cash-Strapped Family Builders*.
- The segment appears on every RM profile card so the RM can sanity-check machine grouping against their own knowledge.

## 4. Product Knowledge RAG Layer

- Corpus: one narrative document per product (`data/products/prod_*.txt`) with metadata header + numbered clauses (Overview / Features / Suitability / Risks / Charges-Tax).
- Ingestion machinery: SHA-256 hash → clause chunker → embed → FAISS `IndexFlatL2` + JSON manifest; rebuilt only when file hashes change.
- `retrieve_for_product(product_id, query)` restricts retrieval to a single product's clauses, so each explanation quotes the right brochure section.
- Structured rule inputs (risk level, lock-in, minimums) come from the `products` table — rules never parse prose.

## 5. Agent-Driven Recommendation Logic (Hybrid)

```
deterministic engine ──► candidates[] ──► agent prompt (strict JSON contract)
                                              │
                     parsed JSON summary ◀────┘
                              │  else deterministic fallback template
                              ▼
                 scrubber → response payload → audit log
```

The LLM receives the engine verdict table as **authoritative input** and is instructed not to add, remove, or re-rank products. Failure modes are handled: JSON parse failure, empty generation, API errors → template narrative, `confidence` lowered, advice still delivered safely.

## 6. Guardrails Against Mis-Selling

See `guardrails/suitability.py`. Verdicts: **eligible / escalate / blocked**. Hard constraints run before any LLM call; escalations require documented supervisor approval in the RM console; blocked items are structurally absent from customer-track payloads (`to_dict(include_retrieved=False)` plus eligible-only filtering).

## 7. Separate Response Flows

| Aspect | RM track | Customer track |
|---|---|---|
| Payload | Full candidate list incl. escalate/blocked reasons | Eligible only; internal scores, segments and KYC never exposed |
| Language | Professional shorthand, JSON-derived flags | Plain language, empathy rules, <220 words |
| Disclaimers | Internal decision-support notice | Three-part advisory disclaimer set |
| Retrieval refs | Compliance citation IDs included | Hidden |

## 8. Key Design Decisions

1. **Rules decide, LLM explains** — inversion of naive "ask GPT for recommendations"; this is what makes every output auditable.
2. **Structured rules vs narrative RAG split** — the suitability engine reads structured attributes from SQLite; retrieval only supplies explanation context, so guardrails never depend on prose parsing.
3. **Post-generation language enforcement** — prompt rules alone are not controls; the scrubber runs after the model on every customer string.
4. **Graceful degradation** — no valid LLM key? Template narratives keep both tracks functional (verified by tests).
5. **Deterministic synthetic data** — seeded generator makes demos and tests reproducible end-to-end.
