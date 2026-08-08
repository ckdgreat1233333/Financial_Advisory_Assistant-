# Architecture Documentation — Insurance Claims Intelligence Platform

> Enterprise architecture for a compliant, explainable, multi-agent insurance claims processing system using ML, RAG, and LLM orchestration.

---

## 1. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                   │
│                                                                        │
│              Vanilla JS SPA — ClaimsGuard AI                           │
│              (static/index.html, served at "/")                       │
│              - Customer Portal: My Claims, Submit Claim, AI Chat      │
│              - Officer Queue:  triage, doc review, accept/reject      │
│              - Audit Ledger + Admin                                   │
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

## 2. Data Flow

### Business Track — Claim Processing

```
Officer/Customer → POST /api/claims  (claimant, type, amount, incident, loss)
      │
      ▼
Customer Uploads Documents → POST /api/claims/{id}/documents
  (Claim Form, Policy Document, Proof of Loss, + type-specific)
      │
      ▼
Orchestrator.process_claim()
      │
   ┌──┼─────────────┬────────────────┐
   ▼  ▼             ▼                ▼
Document        Policy          Fraud
 Agent          Interpretation   Detection
   │   Agent          Agent            Agent
   ▼  │              │                │
Validate &      Check           Rules + semantic
Extract         coverage,      similarity to
fields          limits,        historical fraud
                exclusions,    cases (FAISS)
                reporting
      │              │                │
      └──────────────┼────────────────┘
                     ▼
         Escalation Decision Agent
         (HITL checkpoint decision)
                     │
   ┌─────────────────┼─────────────────┐
   ▼                 ▼                 ▼
Continue       Manual Review      Fraud Screen
processing     (officer decides)  (mandatory review)
                     │
                     ▼
         Officer Accept / Reject / Override
                     │
                     ▼
              Audit Log (immutable)
```

### Customer Track — Grounded Q&A

```
Customer Question → POST /api/chat
      │
      ▼
IntentClassifier → route (status / explanation / policy / next-steps)
      │
      ▼
PolicyService.retrieve_context()     → RAG (chunker → embed → FAISS search)
      │
      ├── matched policy rules        → rule-based answer (always available)
      └── LLM (Groq) with persona     → grounded conversational answer
      │
      ▼
Response { text, reasoning, intent, policyGrounding }
```

---

## 3. Agent Design

| Agent | Input | Processing | Output | Escalation |
|-------|-------|-----------|--------|-----------|
| **Document** | file_path, doc_type | PDF→text, OCR fallback, regex extraction, required-field validation | `ClaimExtractedData`, validation status/confidence | OCR fail / low confidence / missing fields |
| **Policy Interpretation** | claim, extracted_data, missing_docs | Coverage scope, mandatory docs, coverage limits, 30-day reporting window, exclusions | `PolicyResult` (Covered / Not Covered / Manual Review), policy sections, explanation | Missing docs, amount over limit, exclusions, late reporting |
| **Fraud Detection** | claim, extracted_data, policy_result | Policy-defined rules + semantic similarity to historical fraud cases | `FraudAssessment` (LOW/MEDIUM/HIGH, score, indicators, LLM explanation) | High risk or similarity ≥ 0.85 |
| **Escalation Decision** | claim, policy_result, fraud_assessment | Combines coverage + fraud signals into a single recommendation | `EscalationDecision` (Continue / Escalate), next_step, rationale | Any High fraud risk, uncertain coverage |

### Orchestrator Flow

```
process_claim(claim, file_paths, document_types):
  1. document_agent.process(each file)      → extracted data + validation
  2. Merge extracted data across documents  → ClaimExtractedData
  3. policy_agent.interpret_coverage(...)   → coverage status + policy sections
  4. fraud_agent.evaluate(...)              → fraud level + similarity score
  5. escalation_agent.decide(...)           → next_step + requires_human_review
  6. Store results in DB metadata
  7. If escalation.requires_human_review → status = MANUAL_REVIEW (HITL)
  8. Officer Accept / Reject → recorded in audit trail
```

---

## 4. RAG Pipeline

```
Policy Document (data/policies/insurance_policy.txt)
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
│  FAISS Index │  IndexFlatL2 (L2 distance ≈ cosine similarity)
│              │  Saved to data/indexes/faiss_index.bin
└──────┬───────┘
       │
  ┌────┴────┐
  │  Query  │
  └────┬────┘
       │
       ▼
┌──────────────┐
│  Retriever   │  embed_query → FAISS.search(k=5) → return chunks
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
TOP_K = 5                                                    # Retrieve top-5 chunks
INDEX_PATH = "data/indexes/faiss_index.bin"
```

> Graceful degradation: if `faiss` / `sentence-transformers` are not installed, the policy and fraud services fall back to rule-based logic so the platform remains fully functional; semantic similarity is simply omitted.

---

## 5. Security & Compliance

### Authentication & Authorization

```
┌────────────────────────────────────────────────────────────────┐
│  AUTH FLOW                                                     │
│                                                                │
│  1. POST /api/auth/register → user created in SQLite           │
│  2. POST /api/auth/login    → JWT issued                       │
│  3. Protected /api/* routes → JWT verified                     │
│  4. Role-based access:                                         │
│     - customer: own claims, submit claim, chat                 │
│     - officer:  claims queue, document review, accept/reject   │
│     - admin:    audit logs, user management, policy documents  │
└────────────────────────────────────────────────────────────────┘
```

### Audit Trail

Every state-changing action is logged via `AuditService`:

| Field       | Description                                     |
|-------------|-------------------------------------------------|
| timestamp   | When the action occurred                        |
| actor       | Who performed the action                        |
| eventType   | e.g., "Claims Officer Acceptance", "Fraud Screening" |
| riskLevel   | INFO / WARNING / ERROR                          |
| details     | Structured payload with full context            |

### Ethical Controls

- **Never accuse** — flagged claims are described as "undergoing additional verification", never as fraud.
- **Explain without exposing internals** — customer/officer explanations reference policy sections and reasons, not raw fraud scores or agent internals.
- **HITL** — the escalation agent can only *recommend*; the final decision is always a human claim officer's.
- **Rules from the policy document** — all thresholds are parsed from `insurance_policy.txt`, keeping behavior auditable and consistent.

---

## 6. ML & NLP Concepts

| Concept                | Implementation                                               |
|------------------------|--------------------------------------------------------------|
| **Supervised ML**      | Intent classification (joblib model + insurance keyword fallback) |
| **Embeddings**         | SentenceTransformer (all-MiniLM-L6-v2) → 384-dim vectors     |
| **Vector Search**      | FAISS IndexFlatL2 (L2 distance ≈ cosine similarity)          |
| **RAG Pipeline**       | Chunk → Embed → Index → Retrieve → Augment → Generate        |
| **Agent Workflow**     | 4 specialized agents coordinated by the orchestrator         |
| **HITL**               | Human decision required for high fraud risk / uncertain coverage |
| **Prompt Personas**    | Customer advisory, compliance, fraud explainer, policy checker, document validator |
| **Similarity Search**  | Historical fraud case corpus scored per claim (0–1 similarity) |

### Embedding Details

```python
# rag/embedder.py
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
# Output: 384-dimensional dense vector
# Model: 6-layer transformer, 22M parameters
# Distance: IndexFlatL2 (L2 distance ≈ cosine for unit vectors)
```

---

## 7. Fraud Classification

```
                    FRAUD LEVELS
                    ────────────

    LOW                    MEDIUM                    HIGH
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Consistent   │    │ Claim amount │    │ 3+ indicators│
│ details      │    │ exceeds      │    │ triggered    │
│              │    │ coverage     │    │              │
│ No pattern   │    │ limit        │    │ Semantic     │
│ similarity   │    │              │    │ similarity   │
│              │    │ Recent       │    │ ≥ 0.85       │
│ Amount within│    │ inception    │    │              │
│ coverage     │    │ (≤ 14 days)  │    │              │
│              │    │ Missing docs │    │              │
│              │    │              │    │              │
│              │    │ Similarity   │    │              │
│              │    │ 0.70–0.85    │    │              │
├──────────────┤    ├──────────────┤    ├──────────────┤
│ Continue     │    │ Review /     │    │ Mandatory    │
│ processing   │    │ request docs │    │ Manual       │
│              │    │              │    │ Review       │
└──────────────┘    └──────────────┘    └──────────────┘
```

| Similarity | Classification | Action |
|-----------|----------------|--------|
| ≥ 0.85     | High           | Always escalated to human review |
| ≥ 0.70     | Medium         | Review recommended |
| < 0.70     | Low            | Continue normal processing |

---

## 8. Prompt Personas

| Persona              | Tone              | Behavior                                   |
|----------------------|-------------------|--------------------------------------------|
| **Customer Advisory** | Polite, simple    | Explains claims in plain language, never promises payouts |
| **Strict Compliance** | Formal, regulatory | Policy-only answers, never guesses         |
| **Fraud Explainer**   | Analytical        | Explains risk factors, never changes score |
| **Policy Checker**    | Precise, strict   | Checks coverage using only policy context  |
| **Document Validator**| Factual, concise  | Extracts only explicitly present info      |
