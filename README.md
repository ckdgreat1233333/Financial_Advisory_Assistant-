# Personalized Financial Advisory Assistant

An enterprise-grade **Personalized Financial Advisory Assistant** for banking. It supports **relationship managers (RM decision support)** and **customers (goal-based guidance)** with responsible, explainable, compliance-aligned GenAI — every recommendation is decided by a deterministic suitability engine, grounded in an approved product-knowledge RAG layer, and verbalized (never invented) by the LLM.

> In financial advisory, explainability is more important than intelligence.

---

## What it does

The assistant exposes **two deliberately separated response flows**:

| Track | Audience | What you get |
|-------|----------|--------------|
| **Business track** | Relationship managers | Customer profile summary, segment, engine-scored product recommendations with reasoning, risk flags, mis-selling guardrails, human-override/escalation status |
| **Customer track** | Bank customers | Goal-based guidance in plain language, suitable options only, honest trade-offs, mandatory advisory disclaimers, human-advisor nudge |

Blocked products are never shown to customers. Escalated products require documented supervisor approval before customer presentation. Every advisory interaction is written to an immutable audit trail.

### Core principle: the rules decide, the LLM explains

```
SuitabilityEngine (deterministic)  →  verdict per product
        │  eligible / escalate / blocked
        ▼
ProductKnowledgeStore (RAG)        →  approved narrative context
        ▼
RecommendationAgent (GenAI)        →  phrasing ONLY, strict JSON / guided prose
        ▼
Compliance scrubber                →  non-promissory language enforced AFTER the LLM
```

If the LLM fails or drifts, the system degrades to deterministic template narratives — it never blocks advice delivery and never invents products.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (Vanilla JS SPA)                     │
│                       served at "/" by app.py                            │
│   ┌──────────────────────────────┐    ┌─────────────────────────────┐    │
│   │ RM CONSOLE                   │    │ CUSTOMER PORTAL             │    │
│   │ - customer list + profiles   │    │ - goal guidance (education, │    │
│   │ - advisory queries           │    │   retirement, wealth…)      │    │
│   │ - verdicts, flags, override  │    │ - plain language + disclaimers │
│   └──────────────┬───────────────┘    └──────────────┬──────────────┘    │
└──────────────────┼────────────────────────────────────┼──────────────────┘
                   ▼                                    ▼
            ┌──────────────────────── FastAPI (app.py) ─────────────────┐
            │  /api/advisory/rm-query      /api/advisory/customer-goal  │
            │  /api/advisory/customers/:id/profile                      │
            │  + auth (role portals) · audit ledger · sessions          │
            └───────────────────────────┬───────────────────────────────┘
                                        ▼
                    ┌───────────────────────────────────────┐
                    │  AdvisoryService (facade)             │
                    │  services/advisory_service.py         │
                    └───┬───────────┬──────────────┬────────┘
                        ▼           ▼              ▼
     ┌────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
     │ profiling/         │ │ guardrails/      │ │ agents/              │
     │ profile_builder    │ │ suitability.py   │ │ recommendation_agent │
     │ (features, risk    │ │ hard constraints │ │ LLM verbalization    │
     │  score, life stage)│ │ escalation rules │ │ strict JSON fallback │
     │ segmentation.py    │ │ compliance.py    │ └──────────┬───────────┘
     │ MiniLM + KMeans    │ │ non-promissory   │            │
     └─────────┬──────────┘ └────────┬─────────┘            │
               ▼                     ▼                      ▼
     ┌─────────────────────────────────────────────────────────────────┐
     │  KNOWLEDGE LAYER (version-controlled, hash-verified corpus)     │
     │  data/products/*.txt → ProductKnowledgeStore (FAISS)            │
     └─────────────────────────────────────────────────────────────────┘
               ▼
     SQLite: users · customers · transactions · products ·
             advisory_sessions · audit_logs
```

### Data flow

1. **Ingest** — synthetic customers + 12 months of transactions (`scripts/generate_data.py`) are seeded into SQLite; product catalog lives as structured attributes (`products.csv` → `products` table) plus narrative clause documents in `data/products/`.
2. **Profile** — `ProfileBuilder` aggregates demographics + transactions into traceable features: savings rate, monthly surplus, EMI burden, emergency buffer, life stage, computed risk capacity.
3. **Segment** — profile summaries are embedded (MiniLM) and clustered (KMeans k=5); clusters get explainable rank-based names ("Pre-Retirement Preservers", "High-Saving Wealth Builders", …).
4. **Evaluate** — the suitability engine runs hard-constraint checks per product (KYC gate, risk-grade vs binding capacity, lock-in vs horizon, affordability, senior-citizen & first-time-investor protections).
5. **Ground** — for each surviving candidate, clause-level retrieval pulls approved product literature; guardrail decisions cite SEBI/RBI clause IDs from the regulatory corpus.
6. **Verbalize** — the agent phrases results within a strict output contract; the compliance scrubber enforces non-promissory language on every customer-facing string after generation.
7. **Audit** — every query is logged to `advisory_sessions` and the audit ledger.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Frontend | Vanilla JS SPA (`static/index.html`) |
| LLM | Groq via OpenAI SDK (`openai/gpt-oss-120b`, endpoint-configurable) |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`, shared instance) |
| Vector store | FAISS (`IndexFlatL2`) over the product corpus |
| Segmentation | scikit-learn KMeans over normalized embeddings |
| Database | SQLite (`database/data/advisory.db`) |
| Auth/Audit | Role-based portals, immutable audit ledger |

---

## Project Structure

```
├── app.py                          # FastAPI entry point + advisory endpoints
├── config.py                       # LLM provider / model / key
├── scripts/
│   └── generate_data.py            # Deterministic synthetic banking data
├── profiling/                      # Customer pipeline
│   ├── profile_builder.py          # Features + computed risk capacity
│   └── segmentation.py             # Embedding + KMeans segments
├── advisory/                       # Product knowledge RAG + shared infra
│   ├── knowledge_base.py           # Versioned corpus store (hash → chunk → FAISS)
│   ├── product_store.py            # Product catalog retrieval
│   ├── embedder.py                 # Shared MiniLM wrapper
│   └── chunker.py                  # Header + clause chunking
├── guardrails/                     # Mis-selling prevention
│   ├── suitability.py              # Deterministic verdicts + scoring
│   └── compliance.py               # Non-promissory scrubber + disclaimers
├── agents/
│   └── recommendation_agent.py     # GenAI explanation layer (never decides)
├── services/
│   ├── advisory_service.py         # Facade wiring both tracks
│   └── llm_service.py, prompt_service.py
├── models/advisory.py              # Profile, candidates, chunks, responses
├── prompts/
│   ├── rm_advisory_prompt.txt
│   └── customer_guidance_prompt.txt
├── data/
│   ├── customers/                  # customers.csv + transactions.csv (synthetic)
│   ├── products/                   # products.csv + 13 narrative corpus docs
│   ├── goals/goal_definitions.json
│   └── indexes/                    # product_index.bin + product_chunks.json
├── static/index.html               # RM console + customer portal SPA
├── tests/test_advisory.py          # 28 tests
└── docs/architecture.md, governance.md, api.md
```

---

## Quick Start

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# .env
# GROQ_API_KEY=your-groq-api-key

python scripts\generate_data.py      # regenerate synthetic data (optional)
uvicorn app:app --reload --port 8000
```

Open `http://localhost:8000`. Seeded login:

| Portal | Username | Password |
|--------|----------|----------|
| Relationship Manager / Customer | `admin` | `admin123` |

---

## API Endpoints (advisory)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/advisory/customers?search=` | Searchable customer directory |
| GET | `/api/advisory/customers/{id}/profile` | Full profile + derived features + summary |
| POST | `/api/advisory/rm-query` | **Business track**: `{customer_id, question}` → recommendations, verdicts, flags, override status |
| POST | `/api/advisory/customer-goal` | **Customer track**: `{customer_id, goal, amount?, horizon_months?}` → plain-language guidance + disclaimers |
| GET | `/api/advisory/products` | Product catalog (structured attributes) |
| GET | `/api/advisory/segments` | Segment summaries (cluster stats + labels) |
| GET | `/api/advisory/sessions` | Advisory audit trail |

---

## Guardrails Summary

| Control | Behavior |
|---------|----------|
| KYC gate | Non-verified KYC ⇒ all recommendations blocked (RBI fair-practices §2) |
| Risk-grade fit | Product grade > capacity by 2+ steps ⇒ **blocked**; 1 step ⇒ **escalate** w/ supervisor approval (SEBI suitability §1, §3) |
| Lock-in vs horizon | Lock-in beyond stated horizon ⇒ blocked |
| Affordability | Amount below minimum ticket ⇒ blocked; above comfortable commitment ⇒ warning |
| Vulnerable customers | Senior citizens (65+) & first-time investors + high-risk product ⇒ mandatory escalation (RBI §2.1) |
| Concentration cap | Max 2 products per category surfaced; allocation caps respected |
| Non-promissory language | Banned claims scrubbed from LLM output post-generation; violations logged |
| Human-in-the-loop | Escalations surface in RM console with explicit override requirement |

Guardrail verdicts carry provenance tags referencing the SEBI/RBI principles they enforce; the full regulatory mapping lives in `docs/governance.md`.

---

## Tests

```bash
pytest tests/ -q
```

28 tests: profile features, segmentation determinism/uniqueness, product-store grounding, every guardrail path (KYC/risk-grade/lock-in/affordability/senior/first-time/protection-gap), concentration cap, non-promissory scrubbing, both response tracks, and session logging.
