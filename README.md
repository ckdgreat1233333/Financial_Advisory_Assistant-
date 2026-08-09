# Regulatory & Compliance Copilot

An enterprise-grade **Regulatory & Compliance Copilot** for banking. It answers compliance and customer questions **only** from an approved, version-controlled corpus of RBI circulars and internal policies — using Retrieval-Augmented Generation (RAG) with strict hallucination prevention, citation grounding, confidence scoring, contradiction detection, and human-in-the-loop escalation.

> In compliance systems, silence is better than hallucination.

---

## What it does

The copilot exposes **two deliberately separated response tracks**:

| Track | Audience | What you get |
|-------|----------|--------------|
| **Internal** | Compliance & audit teams | Grounded answer + verifiable citations, confidence score, retrieval excerpts, escalation recommendation |
| **Customer** | Bank customers | Plain-language answer + disclaimer, complex questions redirected to a bank official, **no internal details exposed** |

Both tracks answer exclusively from the approved corpus. If no relevant clause is retrieved, the copilot refuses to answer rather than guess — and flags the query for human review.

### Safety gates (single source of truth in `regulatory/confidence.py`)

| Gate | Threshold | Behaviour |
|------|-----------|-----------|
| Retrieval floor | top-1 similarity < 0.45 | LLM is **never called** → "Information not found" |
| Escalation | combined confidence < 0.55 | Answer flagged for compliance review |
| Confident | combined confidence ≥ 0.75 | Delivered with `High` confidence |
| Contradiction | cross-document similarity in 0.70–0.95 | Possible conflict → escalate for human adjudication |

Combined confidence blends retrieval and LLM self-assessment: `0.6 × retrieval + 0.4 × llm`. Every citation must reference a clause that was actually retrieved; ungrounded citations force escalation.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER (Vanilla JS SPA)                      │
│                 served at "/" by app.py (static/index.html)           │
│   ┌──────────────────────────────┐  ┌──────────────────────────────┐  │
│   │ Officer Portal               │  │ Customer Portal              │  │
│   │ - Internal Compliance Query  │  │ - Transparency Assistant     │  │
│   │ - Regulatory Corpus mgmt     │  │   (plain language + notice)  │  │
│   │ - Audit log + user admin     │  └──────────────────────────────┘  │
│   └───────────────┬──────────────┘                                     │
│                   │  HTTP REST (JSON)                                  │
└───────────────────┼───────────────────────────────────────────────────┘
                    ▼
            ┌────────────────┐
            │  FastAPI app   │  app.py  (port 8000)
            │  (app.py)      │
            └───────┬────────┘
                    │
         ┌──────────┴───────────┐
         ▼                      ▼
┌──────────────────┐   ┌──────────────────────┐
│ RegulatoryCopilot│   │ agents/              │
│ (facade)         │   │  compliance_agent    │  internal track
│                  │   │  customer_reg_agent  │  customer track
└────────┬─────────┘   └──────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────┐
│  RegulatoryKnowledgeStore (regulatory/store.py)   │
│  corpus → clause-chunk → embed → FAISS index      │
│  + manifest JSON sidecar + SQLite registry        │
└───────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────┐
│  LLM Service (Groq via OpenAI SDK)                │
│  openai/gpt-oss-120b @ api.groq.com/openai/v1     │
│  strict JSON output, citations, confidence        │
└───────────────────────────────────────────────────┘
```

### Data flow

1. **Ingest** — a document is placed in `data/regulatory/`; the store hashes it, parses its header metadata + numbered clauses, and embeds each clause.
2. **Index** — embeddings go into a FAISS `IndexFlatL2` (384-dim MiniLM vectors), with a JSON manifest sidecar mapping every chunk to its source document. The index is rebuilt **only** when a file's hash changes or new files appear → the store is always reproducible from the approved corpus.
3. **Retrieve** — a query is embedded and the top-k clauses are retrieved with similarity scores.
4. **Answer** — the copilot gates on retrieval confidence, then prompts the LLM with only the retrieved clauses as context, parses the structured JSON response, grounds every citation against what was actually retrieved, and decides whether to answer or escalate.
5. **Audit** — every query, ingest, and archive action is written to an immutable audit log.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Frontend** | Vanilla JS SPA (`static/index.html`) |
| **LLM** | Groq via the OpenAI SDK (`openai/gpt-oss-120b`, endpoint-configurable) |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`, 384-dim) |
| **Vector Store** | FAISS (`IndexFlatL2`) + JSON manifest sidecar |
| **Database** | SQLite (`database/data/regulatory_copilot.db`) |
| **Docs** | `.txt`, `.md`, `.pdf` (PyMuPDF) |
| **Auth** | Login/register with role-based portal selection |
| **Audit / Logging** | Audit log table, Python logging |

---

## Project Structure

```
LoanProcessingAssistant/
├── app.py                        # FastAPI entry point (serves static/index.html)
├── config.py                     # LLM provider / endpoint / model / key
├── agents/                       # Track-specific agents
│   ├── compliance_agent.py       # Internal (compliance & audit) track
│   └── customer_reg_agent.py     # Customer transparency track
├── services/                     # Business logic
│   ├── regulatory_copilot.py     # Facade: retrieval, gating, grounding, escalation
│   ├── llm_service.py            # Groq/OpenAI SDK communication
│   ├── prompt_service.py         # Prompt template loading
│   └── audit_service.py          # Audit trail
├── regulatory/                   # RAG core (banking domain)
│   ├── store.py                  # Version-controlled knowledge store (FAISS + manifest)
│   ├── chunker.py                # Header metadata + clause-level chunking
│   ├── embedder.py               # MiniLM embeddings
│   ├── confidence.py             # Thresholds + confidence scoring + conflict detection
│   └── parsing.py                # JSON extraction + sanitization helpers
├── models/
│   ├── regulatory.py             # RegulatoryDocument / Chunk / Citation / Answer
│   └── audit.py
├── database/                     # SQLite (db.py) + FAISS wrapper (faiss_db.py)
├── data/
│   ├── regulatory/               # APPROVED corpus (RBI circulars, internal policies)
│   └── indexes/                  # regulatory_index.bin + regulatory_chunks.json
├── prompts/
│   ├── regulatory_compliance_prompt.txt
│   └── regulatory_customer_prompt.txt
├── static/index.html             # SPA (served at "/")
├── tests/test_regulatory.py      # 21 tests (chunker, gating, tracks, store)
├── utils/enums.py                # AuditSeverity, AgentType
└── requirements.txt
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- A Groq API key (or any OpenAI-compatible endpoint)

### Setup

```bash
# 1. Python virtual environment
python -m venv .venv
.\.venv\Scripts\activate        # Windows
# source .venv/bin/activate     # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure the LLM key in .env
# GROQ_API_KEY=your-groq-api-key

# 4. Run the server
uvicorn app:app --reload --port 8000
```

The database schema, seed users, FAQ, and regulatory registry are initialized automatically on first run. The vector index builds itself from `data/regulatory/` and is cached for subsequent startups.

### Demo Login

Open `http://localhost:8000` and log in with the seeded officer account:

| Portal | Username | Password |
|--------|----------|----------|
| Compliance Officer / Customer | `admin` | `admin123` |

---

## Regulatory Corpus

The approved corpus lives in `data/regulatory/`. Each file is a plain-text document with a metadata header and numbered clauses:

```
Circular No: RBI/2025-26/09
Date: 01-Aug-2025
Subject: Master Direction - Know Your Customer (KYC)
Version: v1.0
Category: circular

1. Applicability
These directions apply to all banks.

1.1 Customer Due Diligence
...
```

Corpus documents (startup):

| Doc | Type |
|-----|------|
| `rbi_kyc_master_direction` | RBI circular |
| `rbi_kyc_updation_amendment` | RBI circular |
| `rbi_charges_disclosure_circular` | RBI circular |
| `rbi_customer_grievance_circular` | RBI circular |
| `internal_policy_kyc` | Internal policy |
| `audit_checklist_kyc` | Audit checklist |

New documents can be added through the **Regulatory Corpus** screen (upload `.txt` / `.md` / `.pdf`), which stores the file and rebuilds the index immediately, or archived from the same screen. Every ingest/archive is audit-logged.

---

## API Endpoints

See `docs/api.md` for details.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login (portal: `officer` / `customer`) |
| POST | `/api/auth/register` | Register a user |
| POST | `/api/auth/logout` | Logout |
| GET  | `/api/auth/me` | Current user |
| GET/PATCH/DELETE | `/api/users...` | User management |
| GET  | `/api/audit-logs` | Immutable audit ledger |
| GET  | `/api/faq` | FAQ list |
| POST | `/api/regulatory/query` | **Internal** track — citations + confidence + escalation |
| POST | `/api/regulatory/customer-query` | **Customer** track — plain language + disclaimer |
| GET  | `/api/regulatory/documents` | List the approved regulatory corpus |
| POST | `/api/regulatory/documents` | Ingest a new approved document (multipart upload) |
| DELETE | `/api/regulatory/documents/{doc_id}` | Archive a document + rebuild index |

---

## Design Principles

1. **Silence over hallucination** — if no approved clause supports an answer, the copilot says "Information not found" and escalates; it never guesses.
2. **Grounded citations** — every citation must point to a clause that was actually retrieved; ungrounded citations force escalation.
3. **Human-in-the-loop** — low confidence, contradictions, and ungrounded answers always reach a compliance officer.
4. **Two response tracks** — customers get plain language and a disclaimer; internal teams get provenance and escalation. Internal retrieval details are never exposed to customers.
5. **Version-controlled knowledge** — the index is always reproducible from the approved corpus; any change re-validates the store.
6. **Rules in one place** — confidence thresholds and conflict bands live in `regulatory/confidence.py` as explicit constants.
7. **Compliance-by-design** — every query, ingest, and archive is recorded in the audit ledger.

---

## Tests

```bash
pytest tests/test_regulatory.py -q
```

The suite covers the chunker, JSON parsing, confidence gating, both response tracks, citation grounding, contradiction escalation, model serialization, and a real ingest→retrieve round-trip with FAISS. **21 tests.**
