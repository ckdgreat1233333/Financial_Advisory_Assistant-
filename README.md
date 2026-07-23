# Intelligent Loan Processing Assistant

An enterprise-grade Intelligent Loan Processing Assistant for the Banking domain, leveraging Machine Learning, Retrieval-Augmented Generation (RAG), and agent-based reasoning to automate and enhance loan application processing.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                       │
│                                                                            │
│   ┌──────────────────────────┐    ┌──────────────────────────────────┐    │
│   │   Vanilla JS SPA         │    │   React 19 + Tailwind SPA        │    │
│   │   (static/index.html)    │    │   (loan-lifecycle UI)            │    │
│   │   - Customer Portal      │    │   - Customer Dashboard           │    │
│   │   - Officer Queue        │    │   - Officer Ops Center           │    │
│   │   - AI Chat              │    │   - AI Assistant with Grounding  │    │
│   └──────────┬───────────────┘    └──────────────┬───────────────────┘    │
│              │                                    │                        │
└──────────────┼────────────────────────────────────┼────────────────────────┘
               │           HTTP REST (JSON)         │
               └────────────────┬───────────────────┘
                                │
┌───────────────────────────────┼───────────────────────────────────────────┐
│                      ┌───────▼────────┐                                  │
│                      │  FastAPI App   │                                  │
│                      │   (app.py)     │                                  │
│                      │   Port 8000    │                                  │
│                      └───────┬────────┘                                  │
│                              │                                            │
│         ┌────────────────────┼────────────────────┐                      │
│         ▼                    ▼                    ▼                      │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐                │
│   │  Auth    │         │  Loan    │         │ Chat &   │                │
│   │  Routes  │         │  CRUD    │         │Analytics │                │
│   └──────────┘         └────┬─────┘         └────┬─────┘                │
│                             │                    │                        │
│                    ┌────────▼────────┐           │                        │
│                    │   Orchestrator  │           │                        │
│                    │  (Agent Flow)   │           │                        │
│                    └────────┬────────┘           │                        │
│                             │                    │                        │
│              ┌──────────────┼──────────────┐     │                        │
│              ▼              ▼              ▼     │                        │
│      ┌────────────┐ ┌────────────┐ ┌──────────┐ │                        │
│      │ Document   │ │  Policy    │ │   Risk   │ │                        │
│      │   Agent    │ │   Agent    │ │   Agent  │ │                        │
│      └──────┬─────┘ └──────┬─────┘ └────┬─────┘ │                        │
│             │              │            │        │                        │
│             ▼              ▼            ▼        │                        │
│      ┌────────────┐ ┌────────────┐ ┌──────────┐ │                        │
│      │  Document  │ │  Policy    │ │   Risk   │ │                        │
│      │ Processor  │ │  Service   │ │  Service │ │                        │
│      └──────┬─────┘ │  (RAG)     │ └────┬─────┘ │                        │
│             │       └──────┬─────┘      │       │                        │
│             ▼              │            │       │                        │
│      ┌────────────┐       │            │       │                        │
│      │   PDF      │       │            │       │                        │
│      │   Reader   │       │            │       │                        │
│      │   OCR      │       │            │       │                        │
│      │  Extractor │       │            │       │                        │
│      │ Validator  │       │            │       │                        │
│      └────────────┘       │            │       │                        │
│                           ▼            ▼       │                        │
│                    ┌──────────────────────┐    │                        │
│                    │    LLM Service       │    │                        │
│                    │  (Ollama / Gemini)   │    │                        │
│                    └──────────────────────┘    │                        │
│                                                │                        │
└────────────────────────────────────────────────┼────────────────────────┘
                                                 │
                    ┌────────────────────────────┼──────────────┐
                    │                            │              │
                    ▼                            ▼              ▼
          ┌─────────────────┐         ┌────────────────┐ ┌──────────┐
          │    SQLite DB     │         │   FAISS Index  │ │Prompts   │
          │  - users         │         │  (vector DB)   │ │ (txt)    │
          │  - applications  │         │  384-dim       │ │          │
          │  - audit_logs    │         │  all-MiniLM    │ │          │
          │  - policy_docs   │         │  L2 v2         │ │          │
          │  - faq           │         └────────────────┘ └──────────┘
          └─────────────────┘
```

---

## Tech Stack

| Component              | Technology                                |
|------------------------|-------------------------------------------|
| **Backend**            | Python 3.10+, FastAPI, Uvicorn            |
| **Frontend**           | React 19 (TS), Tailwind CSS, Vite         |
| **Classic Frontend**   | Vanilla JS SPA (static/index.html)        |
| **ML / Embeddings**    | Sentence Transformers (all-MiniLM-L6-v2)  |
| **Vector Store**       | FAISS (CPU, IndexFlatL2)                  |
| **LLM**                | Ollama (local) / Gemini API (cloud)       |
| **Database**           | SQLite (via aiosqlite + raw sql)          |
| **Document Processing**| PyMuPDF (pdf→text), pytesseract (OCR)     |
| **Auth**               | JWT tokens (python-jose)                  |
| **Audit / Logging**    | Custom AuditService, Python logging       |

---

## Project Structure

```
LoanProcessingAssistant/
├── app.py                        # FastAPI application entry point
├── models/                       # Pydantic models / SQL schemas
├── routes/                       # API route handlers
│   ├── auth.py                   # Auth routes (login/register)
│   ├── loans.py                  # Loan CRUD routes
│   └── chat.py                   # Chat/Analytics routes
├── agents/                       # Agent-based orchestration
│   ├── orchestrator.py           # Central orchestrator coordinating agents
│   ├── document_agent.py         # Document extraction & validation agent
│   ├── policy_agent.py           # Policy compliance checking agent
│   └── risk_agent.py             # Risk scoring & classification agent
├── rag/                          # Retrieval-Augmented Generation
│   └── pipeline.py               # RAG pipeline (embed, index, retrieve)
├── services/                     # Business logic services
│   ├── document_processor.py     # PDF parsing, OCR, field extraction
│   ├── policy_service.py         # Policy context retrieval via RAG
│   ├── risk_service.py           # Risk scoring & classification
│   ├── prompt_service.py         # Prompt template management
│   ├── llm_service.py            # LLM interaction (Ollama / Gemini)
│   ├── audit_service.py          # Audit trail and logging
│   └── auth_service.py           # JWT auth & user management
├── prompts/                      # LLM prompt templates (persona-based)
│   ├── customer_prompt.txt       # Customer advisory persona
│   ├── risk_prompt.txt           # Risk explainer persona
│   ├── policy_prompt.txt         # Policy checker persona
│   ├── compliance_prompt.txt     # Strict compliance persona
│   └── document_prompt.txt       # Document validator persona
├── data/                         # Application data
│   ├── schema.sql                # SQLite schema definitions
│   ├── seed.sql                  # Seed data for development
│   ├── documents/                # Uploaded loan documents (PDFs)
│   └── indexes/                  # FAISS vector index files
├── static/                       # Vanilla JS SPA frontend
│   └── index.html                # Customer portal + officer queue
├── public/                       # React build output
│   ├── loan-lifecycle/           # React SPA build
│   └── index.html                # React entry point
├── docs/                         # Documentation
│   └── architecture.md           # Architecture documentation
├── tests/                        # Test suite
│   ├── test_agents.py            # LLM service smoke test
│   ├── test_documents.py         # Document extraction & validation tests
│   ├── test_embedder.py          # Embedding smoke test
│   ├── test_integration.py       # Full workflow integration tests
│   ├── test_ml.py                # ML intent classification & preprocessing tests
│   └── test_rag.py               # RAG pipeline (chunker, embedder, FAISS) tests
├── requirements.txt              # Python dependencies
└── package.json                  # React SPA dependencies
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Tesseract OCR (for document OCR)
- Ollama (optional, for local LLM)

### Setup

```bash
# 1. Python virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Node dependencies (React frontend)
npm install

# 4. Initialize database
python -c "from services.audit_service import AuditService; AuditService.init_db()"

# 5. Build FAISS index
python -c "from rag.pipeline import RAGPipeline; RAGPipeline().build_index('data/home_loan_policy.txt')"

# 6. Run the server
uvicorn app:app --reload --port 8000
```

### LLM Configuration

Edit `app.py` to configure your LLM provider:

```python
# app.py - LLM Configuration
USE_OLLAMA = True           # Set False for Gemini API
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"
GEMINI_API_KEY = "your-gemini-api-key"
```

---

## API Endpoints

| Method | Endpoint                                          | Description                    |
|--------|---------------------------------------------------|--------------------------------|
| POST   | `/api/auth/register`                              | Register new user              |
| POST   | `/api/auth/login`                                 | Login, returns JWT             |
| GET    | `/api/applications`                               | List loan applications         |
| POST   | `/api/applications`                               | Create loan application        |
| GET    | `/api/applications/{id}`                          | Get application details        |
| POST   | `/api/applications/{id}/documents`                | Upload document                |
| POST   | `/api/applications/{id}/process`                  | Run agent orchestration        |
| POST   | `/api/applications/{id}/decision`                 | Human decision (HITL)          |
| POST   | `/api/chat`                                       | Ask a question (RAG)           |
| POST   | `/api/chat/history`                               | Get chat history               |
| GET    | `/api/analytics/summary`                          | Dashboard summary              |
| GET    | `/api/analytics/trends`                           | Trend data                     |
| GET    | `/api/admin/audit-log`                            | Audit log (admin)              |
| GET    | `/api/admin/hallucination-log`                    | Hallucination detection log    |

---

## ML / NLP Concepts Demonstrated

| Concept                | Implementation                                               |
|------------------------|--------------------------------------------------------------|
| **Supervised ML**      | Rule-based risk classification (Low / Medium / High)         |
| **Feature Engineering**| Salary, loan amount, employment months as engineered signals |
| **Embeddings**         | SentenceTransformer (all-MiniLM-L6-v2) → 384-dim vectors     |
| **Vector Search**      | FAISS IndexFlatL2 for cosine-style similarity search         |
| **RAG Pipeline**       | Chunk → Embed → Index → Retrieve → Augment → Generate        |
| **Agent Workflow**     | 3 specialized agents coordinated by an orchestrator          |
| **HITL Checkpoints**   | Human decision required for high-risk / policy-violation     |
| **Prompt Personas**    | 5 distinct personas with tone, role, and constraint guides   |
| **Guardrails**         | Policy-only responses, "cannot determine" fallback           |
| **Audit Trail**        | Every action logged with actor, action, timestamp, severity  |

---

## Design Principles

1. **Security-first** — JWT auth, role-based access (customer vs. officer vs. admin)
2. **Compliance-by-design** — Audit trail on every decision, hallucination logging
3. **Human-in-the-loop** — High-risk decisions require officer approval
4. **Explainable** — Every risk score includes reasons and LLM-generated explanation
5. **Grounded responses** — RAG ensures answers are backed by policy documents
6. **Open-source stack** — Sentence Transformers, FAISS, Ollama — no paid services required
