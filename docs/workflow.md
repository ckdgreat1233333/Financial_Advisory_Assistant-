# Regulatory & Compliance Copilot — Workflow

## Internal Track (Compliance & Audit)

### Flow Diagram

```
Compliance Officer Question
      │  POST /api/regulatory/query
      ▼
Retrieve top-k clauses (FAISS) ──similarity < 0.45──► "Information not found" + escalate
      │  similarity ≥ 0.45
      ▼
Build prompt from retrieved clauses (approved context only)
      │
      ▼
LLM (strict JSON: answer, citations, confidence, not_supported, contradiction)
      │
      ▼
Validate: not_supported? / empty? / ungrounded citations? / contradiction?
      │
      ├── yes ──────────────► "Information not found" + escalate for review
      │
      ├── confidence < 0.55 ─► Answer delivered + escalate (compliance review)
      │
      └── otherwise ─────────► Grounded answer with citations + excerpts
      │
      ▼
Audit log (risk = high if escalated, else low)
```

### Step-by-Step

1. **Compliance Officer asks a question**
   - `POST /api/regulatory/query` with `{ "question": "..." }`.

2. **Retrieve (RegulatoryKnowledgeStore)**
   - The query is embedded with the same MiniLM model and searched against the FAISS index (`k=4`).
   - Top-1 cosine similarity becomes the retrieval confidence.

3. **Gate 1 — retrieval floor (0.45)**
   - Below the floor the LLM is **never called**. The response is the "Information not found" message with `needs_escalation: true` and reason `No relevant regulatory clause retrieved (similarity below threshold).`
   - This is the anti-hallucination guarantee: no clause, no LLM call.

4. **Generate (LLM)**
   - The prompt (`regulatory_compliance_prompt.txt`) includes only the retrieved clauses as approved context and demands a strict JSON response with `answer`, `citations`, `confidence`, `not_supported`, `contradiction`.
   - Each citation must carry `[ID:...]`, `clause`, `source`, and a `quote` that appears verbatim in the context.

5. **Validate (RegulatoryCopilot)**
   - **not_supported / empty answer** → "Information not found" + escalate.
   - **Citation grounding** — each citation is checked against the retrieved chunk set. Ungrounded citations → escalate (`One or more citations could not be grounded in retrieved clauses.`).
   - **Contradiction detection** — if retrieved clauses from *different* documents fall in the conflict similarity band (0.70–0.95), the query escalates for human adjudication (`Possible contradiction between retrieved clauses; requires human adjudication.`).
   - **Confidence gate** — combined confidence (`0.6 × retrieval + 0.4 × llm`) below 0.55 escalates (`Answer confidence below escalation threshold; requires compliance review.`).

6. **Deliver**
   - A grounded answer is returned with the citations block, confidence scores, and retrieval excerpts (`retrieved`) for full traceability.

7. **Audit**
   - Every query is written to the audit ledger; escalated queries are logged as `high` risk.

---

## Customer Track (Transparency)

### Flow Diagram

```
Customer Question
      │  POST /api/regulatory/customer-query
      ▼
Retrieve top-k clauses (FAISS) ──similarity < 0.45──► not-found message + disclaimer
      │
      ▼
LLM (plain-language, strict JSON: answer, confidence, not_supported, needs_human)
      │
      ▼
needs_human or cross-document conflict?
      │
      ├── yes ──────────────► Redirect to bank official + disclaimer
      │
      ├── not_supported ─────► not-found message + disclaimer
      │
      └── otherwise ─────────► Plain-language answer + disclaimer
      │
      ▼
Audit log (risk = low). Internal details never exposed.
```

### Step-by-Step

1. **Customer asks a question**
   - `POST /api/regulatory/customer-query` with `{ "question": "..." }`.

2. **Retrieve** — same retrieval as the internal track, but the customer-facing serialization **always** returns `retrieved: []` and `citations: []`.

3. **Gate 1 — retrieval floor (0.45)**
   - Below the floor the customer gets: *"I could not find this information in our published regulatory disclosures. Please contact your bank or visit a branch for assistance."* with the standard disclaimer.

4. **Generate (LLM, customer persona)**
   - `regulatory_customer_prompt.txt` instructs plain, non-legal language, no internal terminology or circular numbers, and flags `needs_human` for complex questions.

5. **Validate**
   - `not_supported` → not-found message + disclaimer.
   - `needs_human` **or** a cross-document conflict → redirect to a bank official: *"This question involves regulatory interpretation that requires a bank official..."* + disclaimer.
   - Otherwise → plain-language answer + disclaimer.

6. **Audit** — logged as `low` risk.

---

## Corpus Lifecycle (Officer)

### Ingest

```
POST /api/regulatory/documents (multipart: file + optional title/circular_no/issue_date)
      │
      ▼
Store file in data/regulatory/<doc_id>.<ext>   (.txt / .md / .pdf)
      │
      ▼
Rebuild index: scan corpus → hash compare → chunk → embed → FAISS + manifest + registry
      │
      ▼
New document is immediately retrievable by both tracks
```

**Document format** (clause-level chunking):

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

**Important:** the chunker splits on numbered clauses (`1.`, `1.1`, ...). A document with **no parseable numbered clauses is skipped** by the ingest pipeline and will not appear in the registry — the upload appears to "succeed" but the document is not indexed.

### Archive

```
DELETE /api/regulatory/documents/{doc_id}
      │
      ▼
Delete file → remove registry row → rebuild index
      │
      ▼
Document is no longer retrievable; audit entry logged as medium risk
```

---

## Key Design Decisions

### "Assist, Not Approve"

- The copilot **never** renders a binding regulatory decision.
- It provides grounded answers, citations, and confidence scores.
- Low-confidence, unsupported, or contradictory queries are escalated to a compliance officer — the final word is always human.

### "Silence is Better than Hallucination"

- The LLM is never invoked below the retrieval floor.
- The LLM is instructed to answer **only** from the approved context and to set `not_supported` when the context does not contain the answer.
- Ungrounded citations force escalation rather than being silently dropped.

### Audit-Friendly Explanation Trail

- Every query, ingest, and archive is logged with timestamp, actor, event type, risk level, and details.
- Internal answers carry retrieval excerpts and per-citation grounding status so a reviewer can verify the source.

### Two Tracks, One Source of Truth

- Both tracks answer from the same approved corpus, but with different personas and disclosure boundaries.
- The customer track strips internal provenance entirely — no circular numbers, no similarity scores, no retrieved excerpts.
- Complex or conflicting customer questions are redirected to a bank official instead of being answered speculatively.

### Rules Live in One Place

- Retrieval floor, escalation threshold, confidence bands, and conflict detection ranges are named constants in `regulatory/confidence.py` — never scattered across the codebase.
