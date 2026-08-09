# Architecture Documentation — Regulatory & Compliance Copilot

> Enterprise architecture for a hallucination-resistant, citation-enforced, human-in-the-loop regulatory Q&A system for banking, built on RAG with two response tracks (internal compliance vs customer transparency).

---

## 1. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                   │
│                                                                        │
│              Vanilla JS SPA — Regulatory & Compliance Copilot          │
│              (static/index.html, served at "/")                        │
│              - Compliance Officer: Compliance Query, Regulatory        │
│                Corpus, Audit Ledger, Admin                             │
│              - Customer: Regulatory Transparency Assistant             │
└───────────────────────────────┬────────────────────────────────────────┘
                                │  HTTP REST (JSON)
┌───────────────────────────────┼────────────────────────────────────────┐
│                       ┌───────▼────────┐                              │
│                       │  FastAPI App   │                              │
│                       │   (app.py)     │                              │
│                       │   Port 8000    │                              │
│                       └───────┬────────┘                              │
│                               │                                        │
│                 ┌─────────────┼──────────────┐                        │
│                 ▼             ▼              ▼                        │
│          ┌────────────┐ ┌───────────┐ ┌───────────────┐               │
│          │  Auth      │ │ Audit &   │ │ Regulatory    │               │
│          │  Routes    │ │ Admin     │ │ Copilot       │               │
│          │            │ │ Routes    │ │ (2 tracks)    │               │
│          └────────────┘ └───────────┘ └──────┬────────┘               │
│                                              │                        │
│                    ┌─────────────────────────┼─────────────────┐      │
│                    ▼                         ▼                 ▼      │
│        ┌──────────────────┐      ┌──────────────────┐  ┌────────────┐ │
│        │ RegulatoryCopilot│      │ agents/          │  │ LLMService │ │
│        │ (facade)         │      │ compliance_agent │  │ (Groq via  │ │
│        │ gating ·         │      │ customer_reg_    │  │ OpenAI SDK)│ │
│        │ grounding ·      │      │ agent            │  │            │ │
│        │ escalation       │      │                  │  │ gpt-oss-   │ │
│        └────────┬─────────┘      └──────────────────┘  │ 120b       │ │
│                 │                                       └────────────┘ │
│                 ▼                                                     │
│      ┌─────────────────────────────────────┐                         │
│      │  RegulatoryKnowledgeStore           │                         │
│      │  (regulatory/store.py)              │                         │
│      │  corpus → hash → clause-chunk →     │                         │
│      │  embed (MiniLM) → FAISS index       │                         │
│      │  + manifest JSON + SQLite registry  │                         │
│      └─────────────────────────────────────┘                         │
│                                                                        │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │
        ┌──────────────────────┼─────────────────────┐
        ▼                      ▼                     ▼
┌──────────────┐   ┌───────────────────────┐  ┌─────────────┐
│  SQLite DB    │   │  FAISS Index (L2)     │  │  Prompts    │
│  users        │   │  data/indexes/        │  │  (txt)      │
│  audit_logs   │   │  regulatory_index.bin │  │  compliance │
│  faq          │   │  + regulatory_chunks  │  │  customer   │
│  regulatory_  │   │  .json (manifest)     │  └─────────────┘
│  docs         │   └───────────────────────┘
└──────────────┘
```

---

## 2. Data Flow

### Version-Controlled Knowledge Store

```
Approved corpus (data/regulatory/*.txt|.md|.pdf)
      │
      ▼
File hash (sha256) ──────┬── compared against manifest sidecar
                         ▼
              Has anything changed?
              ├── No  → load cached FAISS index + chunks (fast start)
              └── Yes ──► re-ingest changed/new documents
                         │
                         ▼
              Parse header metadata (Circular No / Date / Subject / Version / Category)
                         │
                         ▼
              Split into numbered clauses ("1.", "1.1", "2.4", ...)
                         │
                         ▼
              Embed each clause (SentenceTransformer all-MiniLM-L6-v2, 384-dim, L2-normalized)
                         │
                         ▼
              Build FAISS IndexFlatL2 → save regulatory_index.bin
              Write manifest (regulatory_chunks.json) → upsert SQLite registry
```

**Key invariant:** the index is *always reproducible from the approved corpus*. Re-ingestion happens only when a file's hash changes or new files appear, so the store is cheap to restart and tamper-evident.

### Internal Track (Compliance & Audit)

```
Compliance Officer Question → POST /api/regulatory/query
      │
      ▼
RegulatoryKnowledgeStore.retrieve()  → embed query → FAISS search → top-k clauses + similarities
      │
      ▼
retrieval_confidence = top-1 similarity
      │
      ├── < 0.45 (NO_ANSWER_SIM_THRESHOLD)
      │       └──► "Information not found" + escalate. LLM never called.
      │
      ▼
Format context from retrieved clauses → load regulatory_compliance_prompt.txt
      │
      ▼
LLM (strict JSON): { answer, citations[], confidence, not_supported, contradiction }
      │
      ▼
Parse + sanitize → ground every citation against the retrieved chunks
      │
      ▼
Confidence = 0.6 × retrieval + 0.4 × llm
      │
      ├── not_supported / empty answer      → "Information not found"
      ├── cross-document conflict           → escalate (human adjudication)
      ├── ungrounded citation               → escalate
      ├── confidence < 0.55                 → escalate (compliance review)
      └── otherwise                         → answer delivered with citations + excerpts
      │
      ▼
Audit entry written (risk = high if escalated, else low)
```

### Customer Track (Transparency)

```
Customer Question → POST /api/regulatory/customer-query
      │
      ▼
RegulatoryKnowledgeStore.retrieve()  → top-k clauses
      │
      ├── < 0.45 ──► "I could not find this information..." + disclaimer
      │
      ▼
Load regulatory_customer_prompt.txt (plain-language, non-legal tone)
      │
      ▼
LLM (strict JSON): { answer, confidence, not_supported, needs_human }
      │
      ├── not_supported                    → not-found message + disclaimer
      ├── needs_human OR conflict detected → redirect to bank official + disclaimer
      └── otherwise                        → plain-language answer + disclaimer
      │
      ▼
Audit entry (risk = low). Internal retrieval details are never serialized.
```

---

## 3. Copilot Design

### Safety Gates (`regulatory/confidence.py` — single source of truth)

| Constant | Value | Meaning |
|----------|-------|---------|
| `NO_ANSWER_SIM_THRESHOLD` | 0.45 | Below this top-1 similarity the LLM is **never called** — "Information not found" |
| `ESCALATE_CONFIDENCE_THRESHOLD` | 0.55 | Below this combined confidence, answers are escalated to a human reviewer |
| `CONFIDENT_THRESHOLD` | 0.75 | At/above this combined confidence the answer is delivered as `High` |
| `CONFLICT_LOW` / `CONFLICT_HIGH` | 0.70 / 0.95 | Cross-document pairwise-similarity band treated as a possible contradiction |

**Confidence model:**
```
retrieval_confidence = top-1 cosine similarity
combined_confidence  = 0.6 × retrieval_confidence + 0.4 × llm_confidence
confidence_level     = High (≥0.75) | Medium (≥0.55) | Low
```

### Escalation logic (internal track)

`needs_escalation = true` when any of the following holds:

| Condition | Escalation reason |
|-----------|-------------------|
| Retrieval below floor | No relevant regulatory clause retrieved (similarity below threshold) |
| `not_supported` / empty answer | The retrieved clauses do not support an answer |
| Cross-document contradiction | Possible contradiction between retrieved clauses; requires human adjudication |
| Ungrounded citation(s) | One or more citations could not be grounded in retrieved clauses |
| Combined confidence < 0.55 | Answer confidence below escalation threshold; requires compliance review |
| No citations produced | No verifiable citations produced; requires compliance review |

### Citation grounding

The LLM is instructed to cite each clause with its `[ID:...]` token and a verbatim `quote`. The copilot validates that **every** citation references a chunk that was actually retrieved:

- If the ID matches a retrieved chunk → `grounded: true`.
- If the ID is unknown but a retrieved chunk matches `(document, clause_ref)` → the citation is corrected to that chunk.
- If neither matches → `grounded: false` and the answer is escalated.

### Two-track separation

- The **internal** track returns `retrieved` (full excerpts + similarities) for traceability.
- The **customer** track always serializes `retrieved: []` and adds a standard disclaimer; complex/conflicting questions are redirected to a bank official. Internal terminology, circular numbers, and scores never reach the customer.

---

## 4. RAG Pipeline

```
Approved Regulatory Documents
        │
        ▼
┌──────────────────┐
│  Chunker         │  Header metadata + clause-level split
│  (regulatory/    │  "1.", "1.1", "2.4" → 1 chunk per clause
│   chunker.py)    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Embedder        │  SentenceTransformer('all-MiniLM-L6-v2')
│  (regulatory/    │  384-dim, L2-normalized (cosine ≈ L2)
│   embedder.py)   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  FAISS Index     │  IndexFlatL2 → data/indexes/regulatory_index.bin
│  (store.py)      │  + manifest sidecar regulatory_chunks.json
└──────┬───────────┘
       │
  ┌────┴────┐
  │  Query  │
  └────┬────┘
       │
       ▼
┌──────────────────┐
│  Retriever       │  embed_query → FAISS.search(k=4)
│  (store.py)      │  similarity = 1 - distance²/2  (normalized vectors)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  LLM Prompt      │  {context} + {question} → strict JSON answer
│  (prompts/)      │  with citations + confidence
└──────────────────┘
```

### Chunking strategy

A regulatory document starts with a `Key: Value` header and is followed by numbered clauses:

```
Circular No: RBI/2025-26/09
Date: 01-Aug-2025
Subject: Master Direction - Know Your Customer (KYC)
Version: v1.0
Category: circular

1. Applicability
These directions apply to all banks.

1.1 Customer Due Diligence
Identity shall be verified using an officially valid document.
```

Each clause (`1.`, `1.1`, ...) becomes one chunk carrying full traceability metadata: `chunk_id`, `clause_ref`, `document_id`, `title`, `circular_no`, `issue_date`, `version`. Prose lines like `5 years` are never treated as clauses (clause detection requires an uppercase heading word).

### Embedding details

```python
# regulatory/embedder.py
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")   # 384-dim, 22M params
# embeddings are L2-normalized → FAISS L2 distance maps to cosine similarity:
#   cosine ≈ 1 - distance² / 2
```

---

## 5. Security, Audit & Compliance

### Authentication

```
1. POST /api/auth/register → user created in SQLite (password SHA-256)
2. POST /api/auth/login    → opaque token issued, role set by portalType
3. Portal selection drives UI:
   - officer  → Compliance Query / Regulatory Corpus / Audit Ledger / Admin
   - customer → Regulatory Transparency Assistant
```

### Audit trail

Every query, ingest, and archive action is written to the immutable `audit_logs` table:

| Field | Description |
|-------|-------------|
| `id` | Unique log id (`LOG-<hex>`) |
| `timestamp` | When the action occurred |
| `actor` | Who/what performed the action |
| `eventType` | e.g. `Regulatory Query`, `Regulatory Document Ingest` |
| `riskLevel` | `low` / `medium` / `high` (escalated queries are `high`) |
| `details` | Structured payload with the question/action context |

Risk leveling: internal queries that need escalation are logged as `high`; customer queries and routine operations are `low`; document archive is `medium`.

### Compliance controls

- **Silence over hallucination** — below the retrieval floor the LLM is never invoked; unsupported questions return an explicit not-found message.
- **Grounded citations only** — every citation must point to a clause actually retrieved; ungrounded citations force escalation.
- **Contradiction detection** — cross-document conflicts are surfaced for human adjudication instead of the AI picking a side.
- **Human-in-the-loop** — the copilot can only recommend escalation; low-confidence, conflicting, or unsupported answers always reach a compliance officer.
- **Approved-corpus-only** — the LLM is constrained to the retrieved context and must not use outside knowledge or add legal interpretation.
- **Customer redaction** — internal retrieval details and circular numbers are never exposed on the customer track.

---

## 6. ML & NLP Concepts

| Concept | Implementation |
|---------|----------------|
| **Embeddings** | SentenceTransformer (all-MiniLM-L6-v2) → 384-dim L2-normalized vectors |
| **Vector Search** | FAISS IndexFlatL2 (cosine ≈ L2 on normalized vectors) |
| **RAG Pipeline** | Clause-chunk → embed → index → retrieve → augment → generate |
| **Versioned Store** | sha256 file hashes + manifest sidecar; rebuilds only on change |
| **Confidence Gating** | Retrieval floor + combined confidence + escalation thresholds |
| **Citation Grounding** | Every citation validated against the retrieved chunk set |
| **Contradiction Detection** | Cross-document pairwise similarity in a conflict band |
| **Two-track generation** | Compliance persona vs plain-language transparency persona |
| **HITL** | Low-confidence / conflicting / unsupported answers → compliance review |

---

## 7. Key Design Decisions

### "Silence is better than hallucination"

The copilot is designed for a domain where a confident-but-wrong answer is worse than no answer. It refuses below the retrieval floor, refuses when clauses don't support an answer, and escalates whenever it cannot fully verify its output.

### Rules live in one place

All thresholds live in `regulatory/confidence.py` as named constants — the behaviour ("no answer" vs answer vs escalate) is explicit, explainable, and auditable.

### The index is a derived artifact

The FAISS index and chunk manifest are always reproducible from `data/regulatory/`. There is no manually maintained vector store; ingestion, registry, and indexing are one pipeline.
