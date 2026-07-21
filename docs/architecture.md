# Intelligent Loan Processing Assistant

## ML & NLP Concepts Usage

This document explicitly maps where ML and NLP concepts are used in the system,
as required by the capstone evaluation criteria.

---

### 1. Intent Classification (Classification - Section 8)

**File:** `ml/intent_classifier.py`, `ml/model.py`

**Where:** Customer queries and internal routing are classified into 5 intent types:
`POLICY_QUERY`, `DOCUMENT_PROCESSING`, `APPLICATION_STATUS`, `RISK_QUERY`, `GENERAL_QUERY`

**Model:** TF-IDF Vectorizer + Logistic Regression (scikit-learn Pipeline)

**Why this approach:**
- Lightweight and fast for intent routing (no GPU needed)
- Easy to train and update with new examples
- Works well with limited training data (400+ labeled examples in `data/intents/intents.csv`)

**Metrics:** Precision, recall, F1-score computed via `sklearn.metrics.classification_report`

---

### 2. Semantic Similarity Search (Similarity Search - Section 8)

**File:** `rag/embedder.py`, `database/faiss_db.py`

**Where:** RAG pipeline retrieves relevant policy sections for a given query

**Model:** SentenceTransformer `all-MiniLM-L6-v2` (384-dim embeddings)

**Why Transformers instead of classical NLP:**
- Captures semantic meaning of entire sentences (e.g., "monthly income" ≈ "salary per month")
- Understands context and synonyms
- Classical keyword matching would miss semantic relationships
- Handles paraphrased queries naturally

**Similarity calculation:** FAISS IndexFlatL2 (L2 distance on normalized vectors = cosine similarity)

---

### 3. Retrieval-Augmented Generation (RAG - Section 6.2C)

**File:** `rag/pipeline.py`, `rag/retriever.py`, `rag/chunker.py`

**Pipeline:**
1. **Chunking:** Policy documents split by section headers using regex
2. **Embedding:** Each chunk embedded into 384-dim vector
3. **Indexing:** Vectors stored in FAISS index
4. **Retrieval:** Top-k most semantically similar chunks retrieved
5. **Grounding:** Retrieved chunks fed as context to LLM prompt

---

### 4. Document Extraction (Named Entity Recognition via Regex)

**File:** `document_processing/extractor.py`

**Approach:** Regex pattern matching for structured field extraction from banking documents.

**Document types and extracted fields:**
| Document Type | Fields Extracted |
|---|---|
| Salary Slip | monthly_salary, employer, employee_name, employment_duration |
| Bank Statement | account_number, average_monthly_balance, bank_name |
| Employment Letter | employer, employee_name, designation, employment_duration |
| PAN Card | pan_number, name_on_pan |
| Aadhaar Card | aadhaar_number, name_on_aadhaar, date_of_birth, address |

**Production note:** Would be enhanced with LayoutLM (transformer-based document AI) for
layout-aware extraction. The current regex approach provides high precision for
structured Indian banking documents.

---

### 5. Agent-Based Decision Flow

**File:** `agents/orchestrator.py`, `agents/document_agent.py`, `agents/policy_agent.py`,
`agents/risk_agent.py`, `agents/customer_agent.py`

**Agents:**
| Agent | Input | Decision | Escalation |
|---|---|---|---|
| Document Agent | File path, doc type | Extract & validate text | Invalid docs → manual review |
| Policy Agent | Application + extracted data | Check compliance against policy rules | Policy violations → manual review |
| Risk Agent | Application + policy result | Compute risk level (Low/Med/High) | High risk → manual review |
| Customer Agent | Customer question + policy context | Answer using RAG + prompts | Cannot determine → contact loan officer |

---

### 6. Prompt Engineering (GenAI Personas - Section 7.2B)

**File:** `prompts/*.txt`

| Persona | File | Tone | Behavior |
|---|---|---|---|
| Strict Compliance | `compliance_prompt.txt` | Formal, regulatory | ONLY policy-based answers, never guesses |
| Customer Advisory | `customer_prompt.txt` | Polite, simple language | Explains policies conversationally, never promises approval |
| Risk Explainer | `risk_prompt.txt` | Analytical | Explains risk factors without changing calculated risk |
| Policy Checker | `policy_prompt.txt` | Precise | Checks compliance using ONLY retrieved policy context |
| Document Validator | `document_prompt.txt` | Factual | Extracts only explicitly present information |

---

### 7. Risk Flagging Logic (Section 6.2E)

**File:** `services/risk_service.py`, `models/risk.py`

| Risk Level | Criteria | Action |
|---|---|---|
| LOW | All documents submitted, income verified, employment >12mo, loan within limits | Continue processing |
| MEDIUM | Minor salary/statement mismatch, employment 6-12mo, missing optional info | Request additional documents |
| HIGH | Missing mandatory docs, income below ₹30k, loan >20x salary, inconsistencies | Manual review required |

**Sample scenarios** are defined in `models/risk.py` → `RISK_SCENARIOS` dict.

---

### 8. Compliance & Ethics (Section 9)

| Concern | Mitigation |
|---|---|
| Bias risk | Rule-based checks with consistent thresholds; LLM only explains, never decides |
| Hallucination risk | Strict "policy-only" guardrails; "I cannot determine" fallback |
| Over-reliance on AI | Human-in-the-loop checkpoint for all high-risk and manual-review cases |
| Human approval | Orchestrator's `submit_human_decision()` method for manual review workflow |
| Audit trail | Every decision logged via `AuditService` with actor, action, timestamp, and severity |