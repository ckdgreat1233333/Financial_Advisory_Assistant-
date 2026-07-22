# Architecture Documentation — Intelligent Loan Processing Assistant

> Enterprise architecture for a compliant, explainable, multi-agent loan processing system using ML, RAG, and LLM orchestration.

---

## 1. System Architecture

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

## 2. Data Flow

### Business Track — Loan Application Processing

```
Officer → POST /api/business/loan-application
              │
Customer → Upload Documents → POST /api/applications/{id}/documents
              │
              ▼
    Orchestrator.process_application()
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
Document   Policy    Risk
 Agent     Agent     Agent
    │         │         │
    ▼         ▼         ▼
 Validate  Check     Evaluate
 & Extract Compliance Risk Level
              │
              ▼
         SQLite Store
   (status + metadata + audit)
              │
              ▼
    Officer Reviews → Approve/Reject
              │
              ▼
         Audit Log
```

### Customer Track — Q&A with RAG

```
Customer Question → POST /api/chat
              │
              ▼
    PolicyService.retrieve_context()
              │
    ┌─────────┴─────────┐
    ▼                   ▼
 Chunker           Embedder
(split policy   (SentenceTransformer
 by sections)    all-MiniLM-L6-v2)
    │                   │
    └─────────┬─────────┘
              ▼
      FAISS Search (top-3)
              │
              ▼
    PromptService.load(template,
       context, question)
              │
              ▼
    LLMService.generate()
              │
              ▼
    Grounded Response
  (text + policyGrounding)
```

---

## 3. Agent Design

| Agent         | Input                          | Processing                                    | Output                                          | Escalation               |
|---------------|--------------------------------|-----------------------------------------------|-------------------------------------------------|--------------------------|
| **Document**  | file_path, doc_type            | PDF→text, OCR fallback, regex extract, validate| extracted_text, ocr_confidence, validation_status, extracted_fields | OCR fail / low confidence → Manual Review |
| **Policy**    | application, extracted_data, missing_docs | min salary check, loan multiplier check, missing doc check, employment duration | eligibility_status, violations[], explanation, confidence | Policy violations → Manual Review |
| **Risk**      | application, extracted_data, policy_result | Match violations to risk rules, compute score, LLM explain | risk_level, risk_score, reasons[], llm_explain, triggered_rules[] | High risk → Manual Review |

### Orchestrator Flow

```
process_application(application_id):
  1. Load application + associated documents from DB
  2. document_agent.process(documents)       → extracted fields + validation
  3. policy_agent.check(application, fields) → violations + eligibility
  4. risk_agent.evaluate(application, fields, violations) → risk level + score
  5. Store results in DB
  6. If High Risk or Policy Violation → status = "manual_review"
  7. Else → status = "pending_officer" (ready for final decision)
  8. Audit every step
```

---

## 4. RAG Pipeline

```
Policy Document (home_loan_policy.txt)
        │
        ▼
┌──────────────┐
│   Chunker    │  Split by "Section N - Title" pattern
│  (regex)     │  Each section = 1 chunk
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Embedder   │  SentenceTransformer('all-MiniLM-L6-v2')
│              │  384-dimensional embeddings
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  FAISS Index │  IndexFlatL2 (L2 distance = cosine similarity)
│              │  Saved to data/indexes/faiss_index.bin
└──────┬───────┘
       │
  ┌────┴────┐
  │  Query  │
  └────┬────┘
       │
       ▼
┌──────────────┐
│  Retriever   │  embed_query → FAISS.search(k=3) → return chunks
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  LLM Prompt  │  Template {context} + {question} → LLM → Response
└──────────────┘
```

### RAG Configuration

```python
# rag/pipeline.py
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim
INDEX_TYPE = "IndexFlatL2"                                   # L2 distance
CHUNK_PATTERN = r"(Section \d+ - .+)"                       # Split by section
TOP_K = 3                                                    # Retrieve top-3 chunks
INDEX_PATH = "data/indexes/faiss_index.bin"
```

---

## 5. Security & Compliance

### Authentication & Authorization

```
┌────────────────────────────────────────────────────────────────┐
│  AUTH FLOW                                                     │
│                                                                │
│  1. POST /api/auth/register → user created in SQLite           │
│  2. POST /api/auth/login    → JWT issued (1h expiry)           │
│  3. All /api/* routes       → JWT verified via middleware      │
│  4. Role-based access:                                         │
│     - customer: own applications, chat                         │
│     - officer:  all applications, process, decide              │
│     - admin:    audit logs, hallucination logs                 │
└────────────────────────────────────────────────────────────────┘
```

### Audit Trail

Every state-changing action is logged via `AuditService.log()`:

| Field      | Description                                 |
|------------|---------------------------------------------|
| actor_id   | User who performed the action               |
| action     | e.g., "create_application", "agent_decision"|
| resource   | Affected resource (application_id, etc.)    |
| details    | JSON payload with full context              |
| severity   | INFO, WARNING, ERROR, CRITICAL              |
| timestamp  | ISO-8601 UTC timestamp                      |
| ip_address | Request origin (for compliance)             |

### Hallucination Detection

```python
# services/llm_service.py
HALLUCINATION_PHRASES = [
    "I don't have information about",
    "I cannot determine",
    "Based on the policy provided",
    "The policy does not specify",
    # ... additional guardrail phrases
]

def check_hallucination(response: str) -> bool:
    """Check if response contains guardrail phrases."""
    # If policy grounding is absent but response makes
    # a definitive claim → potential hallucination
    # Logged to hallucination_log table for review
```

---

## 6. ML & NLP Concepts

| Concept                | Implementation                                               |
|------------------------|--------------------------------------------------------------|
| **Supervised ML**      | Rule-based risk classification (Low / Medium / High)         |
| **Feature Engineering**| Salary, loan amount, employment months as engineered signals |
| **Embeddings**         | SentenceTransformer (all-MiniLM-L6-v2) → 384-dim vectors     |
| **Vector Search**      | FAISS IndexFlatL2 (L2 distance approximates cosine)          |
| **RAG Pipeline**       | Chunk → Embed → Index → Retrieve → Augment → Generate        |
| **Agent Workflow**     | 3 specialized agents coordinated by orchestrator             |
| **HITL**               | Human decision required for high-risk / policy-violation     |
| **Prompt Personas**    | 5 distinct personas (customer, risk, policy, compliance, doc)|

### Embedding Details

```python
# rag/pipeline.py
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
# Output: 384-dimensional dense vector
# Model: 6-layer transformer, 22M parameters
# Distance: IndexFlatL2 (L2 distance ~ cosine for unit vectors)
# Performance: ~10K docs/sec on CPU
```

---

## 7. Risk Classification

```
                    RISK LEVELS
                    ────────────

    LOW                    MEDIUM                    HIGH
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ All docs     │    │ Minor salary │    │ Missing      │
│ submitted    │    │ / statement  │    │ mandatory    │
│              │    │ mismatch     │    │ docs         │
│ Income ≥     │    │              │    │              │
│ ₹30,000      │    │ Employment   │    │ Income <     │
│              │    │ 6-12 months  │    │ ₹30,000      │
│ Loan ≤ 20x   │    │              │    │              │
│ salary       │    │ Missing      │    │ Loan > 20x   │
│              │    │ optional     │    │ salary       │
│ Employment   │    │ info         │    │              │
│ ≥ 12 months  │    │              │    │ Inconsistent │
│              │    │              │    │ financial    │
│              │    │              │    │ information  │
├──────────────┤    ├──────────────┤    ├──────────────┤
│ Auto-        │    │ Request      │    │ Manual       │
│ continue     │    │ additional   │    │ Review       │
│              │    │ documents    │    │ Required     │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 8. Prompt Personas

| Persona            | File                     | Tone              | Behavior                                  |
|--------------------|--------------------------|-------------------|-------------------------------------------|
| **Strict Compliance** | compliance_prompt.txt   | Formal, regulatory| Policy-only answers, never guesses        |
| **Customer Advisory** | customer_prompt.txt     | Polite, simple    | Explains policies, never promises loan    |
| **Risk Explainer**    | risk_prompt.txt         | Analytical        | Explains risk factors, doesn't change score|
| **Policy Checker**    | policy_prompt.txt       | Precise, strict   | Checks compliance using only policy context|
| **Document Validator**| document_prompt.txt     | Factual, concise  | Extracts only explicitly present info     |

---

## 9. Ethical Controls

```
┌────────────────────────────────────────────────────────────────┐
│                    ETHICAL & COMPLIANCE CONTROLS                │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────────┐  ┌─────────────────────┐             │
│  │     Bias Risk       │  │  Hallucination Risk │             │
│  │  ───────────────    │  │  ─────────────────   │             │
│  │  Rule-based checks  │  │  "I cannot           │             │
│  │  with consistent    │  │  determine"          │             │
│  │  thresholds         │  │  fallback            │             │
│  │  LLM only explains, │  │  Policy-only         │             │
│  │  never decides      │  │  guardrails          │             │
│  └─────────────────────┘  └─────────────────────┘             │
│                                                                │
│  ┌─────────────────────┐  ┌─────────────────────┐             │
│  │  Over-reliance on   │  │  Human Approval     │             │
│  │  AI                 │  │  Checkpoints        │             │
│  │  ───────────────    │  │  ────────────────   │             │
│  │  HITL checkpoint    │  │  submit_human_      │             │
│  │  for all high-risk  │  │  decision() method  │             │
│  │  and manual-review  │  │  for manual review  │             │
│  │  cases              │  │  workflow           │             │
│  └─────────────────────┘  └─────────────────────┘             │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Audit Trail                                             │  │
│  │  ────────────                                            │  │
│  │  Every decision logged via AuditService                  │  │
│  │  with actor, action, timestamp, and severity             │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```
