# Insurance Claims Intelligence Platform (ClaimsGuard AI)

An enterprise-grade **Insurance Claims Intelligence Platform** that automates claim triage, coverage interpretation, fraud screening, and escalation — using Machine Learning, Retrieval-Augmented Generation (RAG), LLM-based explainability, and a four-agent orchestration pipeline with human-in-the-loop (HITL) checkpoints.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                   │
│                                                                        │
│              Vanilla JS SPA (static/index.html)                        │
│              ClaimsGuard AI — served at "/" by app.py                  │
│              - Customer Portal (My Claims, Submit Claim, AI Chat)      │
│              - Officer Queue (triage, accept/reject, doc review)       │
│              - Audit Ledger + Admin                                    │
└───────────────────────────────┬────────────────────────────────────────┘
                                │  HTTP REST (JSON)
┌───────────────────────────────┼────────────────────────────────────────┐
│                       ┌───────▼────────┐                              │
│                       │  FastAPI App   │                              │
│                       │   (app.py)     │                              │
│                       │   Port 8000    │                              │
│                       └───────┬────────┘                              │
│                               │                                        │
│                   ┌───────────┼───────────────┐                       │
│                   ▼           ▼               ▼                       │
│            ┌──────────┐  ┌──────────┐   ┌───────────┐                 │
│            │  Auth    │  │ Claims   │   │ Chat &    │                 │
│            │  Routes  │  │  CRUD    │   │ Analytics │                 │
│            └──────────┘  └────┬─────┘   └───────────┘                 │
│                               │                                        │
│                    ┌──────────▼──────────┐                            │
│                    │   Orchestrator      │                            │
│                    │  (Agent Flow)       │                            │
│                    └──────────┬──────────┘                            │
│                               │                                        │
│              ┌────────────────┼────────────────┐                      │
│              ▼                ▼                ▼                      │
│     ┌────────────────┐ ┌─────────────┐ ┌───────────────┐             │
│     │  Document      │ │   Policy    │ │   Fraud       │             │
│     │  Agent         │ │Interpretation│ │  Detection    │             │
│     └──────┬─────────┘ └──────┬──────┘ └──────┬────────┘             │
│            │                  │               │                       │
│            ▼                  ▼               ▼                       │
│     ┌────────────┐   ┌────────────┐   ┌─────────────────────┐         │
│     │  Document  │   │  Policy    │   │  FraudCaseService   │         │
│     │ Processor  │   │  Service   │   │ (historical case    │         │
│     │ (PDF/OCR/  │   │  (RAG)     │   │  similarity via FAISS)│       │
│     │  extract)  │   └──────┬─────┘   └──────────┬──────────┘         │
│     └──────┬─────┘          │                    │                    │
│            │                ▼                    ▼                    │
│            │        ┌───────────────────────────────┐                 │
│            │        │  Escalation Decision Agent   │                 │
│            │        │  (HITL checkpoint)           │                 │
│            │        └───────────────┬───────────────┘                 │
│            │                        │                                 │
│            ▼                        ▼                                 │
│     ┌───────────────────────────────────────────────┐                 │
│     │            LLM Service (Groq / OpenAI SDK)    │                 │
│     │       explanation + grounded customer chat    │                 │
│     └───────────────────────────────────────────────┘                 │
│                                                                        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
              ┌────────────────────┼─────────────────┐
              ▼                    ▼                 ▼
    ┌─────────────────┐   ┌────────────────┐  ┌────────────┐
    │    SQLite DB     │   │   FAISS Index  │  │ Prompts    │
    │  users           │   │  (vector DB)   │  │ (txt)      │
    │  claims          │   │  384-dim       │  │            │
    │  fraud_cases     │   │  all-MiniLM    │  │            │
    │  audit_logs      │   │  L2 v2         │  │            │
    │  policy_docs,faq │   └────────────────┘  └────────────┘
    └─────────────────┘
```

---

## Agent Pipeline

Each claim moves through a four-agent pipeline coordinated by `ClaimsProcessingOrchestrator`:

| Stage | Agent | What it does | Escalation trigger |
|-------|-------|--------------|--------------------|
| 1 | **Document Agent** | Extracts text (PDF/OCR), validates required fields, produces `ClaimExtractedData` | OCR failure / low confidence |
| 2 | **Policy Interpretation Agent** | Checks coverage scope, mandatory documents, coverage limits, 30-day reporting window, and exclusions parsed from `insurance_policy.txt` | Missing docs, amount over limit, exclusions |
| 3 | **Fraud Detection Agent** | Applies policy-defined fraud rules plus **semantic similarity to historical fraud cases** (FAISS) | High fraud level / similarity ≥ 0.85 |
| 4 | **Escalation Decision Agent** | Combines the above into a single decision; final authority always rests with a human claim officer | Any High fraud risk or uncertain coverage |

Human-in-the-loop is enforced by the escalation agent: **any claim flagged High fraud risk is ALWAYS escalated** for manual review. Officer accept/reject/override actions are recorded in the immutable audit ledger.

---

## Tech Stack

| Component               | Technology                                 |
|-------------------------|--------------------------------------------|
| **Backend**             | Python 3.12, FastAPI, Uvicorn              |
| **Frontend**            | Vanilla JS SPA (`static/index.html`)       |
| **LLM**                 | Groq via the OpenAI SDK (`openai/gpt-oss-120b`) |
| **Embeddings**          | Sentence Transformers (all-MiniLM-L6-v2)   |
| **Vector Store**        | FAISS (CPU, IndexFlatL2)                   |
| **Database**            | SQLite (`database/data/loan_assistant.db`) |
| **Document Processing** | PyMuPDF (pdf→text), pytesseract (OCR)      |
| **Auth**                | JWT tokens, role-based access              |
| **Audit / Logging**     | AuditService, Python logging               |

---

## Project Structure

```
LoanProcessingAssistant/
├── app.py                        # FastAPI entry point (serves static/index.html)
├── agents/                       # Agent-based orchestration
│   ├── orchestrator.py           # ClaimsProcessingOrchestrator
│   ├── document_agent.py         # Extraction & validation agent
│   ├── policy_agent.py           # Coverage interpretation agent
│   ├── fraud_agent.py            # Fraud screening agent
│   ├── escalation_agent.py       # HITL escalation decision agent
│   └── customer_agent.py         # Customer-facing chat agent
├── models/                       # Dataclass models
│   ├── claim.py, document.py, extracted_data.py
│   ├── policy.py, fraud.py, fraud_case.py
│   ├── escalation.py, audit.py
├── services/                     # Business logic services
│   ├── policy_service.py         # Coverage rules (parsed from policy) + RAG
│   ├── fraud_service.py          # Rule-based fraud screening
│   ├── fraud_case_service.py     # Historical fraud case similarity (FAISS)
│   ├── llm_service.py            # Groq LLM integration
│   ├── customer_service.py       # Customer advisory / compliance modes
│   ├── audit_service.py          # Audit trail
│   └── prompt_service.py         # Prompt template management
├── document_processing/          # PDF parsing, OCR, extraction, validation
├── rag/                          # RAG pipeline (chunker, embedder, retriever)
├── database/                     # SQLite + FAISS wrappers
├── data/
│   ├── policies/insurance_policy.txt   # Source of all coverage rules
│   └── intents/intents.csv              # Intent classification dataset
├── static/index.html            # ClaimsGuard AI SPA (served at "/")
├── prompts/                     # LLM prompt personas
├── docs/                        # Architecture / API / workflow docs
├── tests/                       # Pytest suite (55+ tests)
└── requirements.txt
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Tesseract OCR (optional, for scanned-document OCR)
- A Groq API key (for LLM explanations and chat)

### Setup

```bash
# 1. Python virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure the LLM key in .env
# GROQ_API_KEY=your-groq-api-key

# 4. Run the server
uvicorn app:app --reload --port 8000
```

The database schema, seed users, FAQ, policy documents, and historical fraud corpus are all initialized automatically on first run.

### Demo Login

Open `http://localhost:8000` and log in with the seeded officer account:

| Role | Username | Password |
|------|----------|----------|
| Officer / Admin / Customer | `admin` | `admin123` |

---

## API Endpoints

See [docs/api.md](docs/api.md) for the full reference.

| Method | Endpoint                                            | Description                              |
|--------|-----------------------------------------------------|------------------------------------------|
| POST   | `/api/auth/login` / `/register` / `/logout`         | Authentication                           |
| POST   | `/api/claims`                                        | Create a claim                           |
| GET    | `/api/claims?email=`                                 | List claims (filter by claimant)         |
| GET    | `/api/claims/{id}`                                   | Claim detail with agent consensus        |
| POST   | `/api/claims/{id}/documents`                         | Upload claim documents                   |
| PATCH  | `/api/claims/{id}/accept` / `/reject`                | Officer decision (HITL)                  |
| PATCH  | `/api/claims/{id}/documents/{doc_id}`                | Officer document status override         |
| GET    | `/api/claims/{id}/fraud-analysis`                    | Fraud screening detail                   |
| GET    | `/api/claims/{id}/explanation`                       | Explainable decision                     |
| POST   | `/api/chat`                                          | Customer AI assistant (grounded)         |
| GET    | `/api/audit-logs`                                    | Immutable audit ledger                   |
| GET    | `/api/fraud-cases`, `/api/fraud-cases/thresholds`    | Historical fraud corpus + thresholds     |
| GET    | `/api/analytics/*`                                   | Claims / fraud / pipeline dashboards     |
| GET    | `/api/policy-documents`, `/api/faq`, `/api/users`    | Reference data                          |

---

## Fraud Detection

Fraud screening combines two complementary signals:

1. **Policy-defined rules** — parsed from Section 5 of `insurance_policy.txt`:
   - Claim amount exceeds the coverage limit
   - Claim filed within 14 days of policy inception
   - Missing mandatory documents
   - High prior-claim count
   - Claimed amount differing from the reported loss by more than 20%

2. **Semantic similarity** — the claim narrative and uploaded document text (excluding the shared policy document) are embedded with `all-MiniLM-L6-v2` and compared against a corpus of historical fraud cases stored in the FAISS index. Each content source is scored independently and the best match is used.

| Similarity | Classification |
|-----------|----------------|
| ≥ 0.85     | High (mandatory manual review) |
| ≥ 0.70     | Medium (review recommended) |
| < 0.70     | Low |

---

## Design Principles

1. **Human-in-the-loop** — High fraud risk always requires a claim officer's decision; the system never auto-approves.
2. **Explainable AI** — Every coverage and fraud decision includes reasons, policy section references, and an LLM-generated explanation.
3. **Grounded responses** — Customer chat answers are backed by the actual policy document via RAG.
4. **Ethical safeguards** — The system never accuses a customer of fraud; flagged claims are described as "undergoing additional verification", and explanations never expose internal scores or agent details.
5. **Rules from documents** — Coverage and fraud thresholds are parsed from `insurance_policy.txt`, never hardcoded in Python.
6. **Compliance-by-design** — Every officer decision is recorded in an immutable audit ledger.
