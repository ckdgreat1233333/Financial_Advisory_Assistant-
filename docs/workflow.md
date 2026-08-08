# Insurance Claim Processing Workflow

## Business Track (Internal)

### Flow Diagram

```
Customer submits claim → uploads documents → DocumentAgent → PolicyInterpretationAgent
    → FraudDetectionAgent → EscalationDecisionAgent → [Human Review] → Officer Decision
                                                           ↑
                                       High fraud risk / uncertain coverage
```

### Step-by-Step Workflow

1. **Create the Claim**
   - `POST /api/claims`
   - Captures claimant details, policy number, claim type, amount, incident date, and loss description.

2. **Upload Documents**
   - `POST /api/claims/{id}/documents` (multipart, field `files`)
   - Mandatory documents (Section 2 of the policy):
     - **Claim Form** (signed by the policyholder)
     - **Policy Document / Certificate**
     - **Proof of Loss** statement
   - Type-specific documents: Medical Report (health), Police Report (theft / accident), Invoice / Receipt (property / repair), Incident Report (fire / property damage).
   - When all three mandatory documents are present, the orchestrator pipeline runs automatically.

3. **Document Processing** (Document Agent)
   - PDF text extraction (searchable PDFs) with OCR fallback for scanned documents
   - Per-type field extraction into `ClaimExtractedData`
     - Claim Form: claimant name, policy number, claim amount, incident date/location, loss description
     - Policy Document: policy number, coverage limit, inception date, prior claims
     - Proof of Loss: reported amount, loss description, witnesses, third party
   - Required-field completeness check and OCR confidence threshold check

4. **Coverage Interpretation** (Policy Interpretation Agent)
   - Claim type must be in the covered scope (Auto, Health, Property, Fire, Theft, Travel, Liability)
   - All mandatory documents must be present
   - Claim amount must be within the coverage limit (Section 3)
   - Incident must be reported within the **30-day reporting window**
   - Loss cause must not match a policy exclusion (Section 4)
   - Result: `Covered` / `Not Covered` / `Manual Review` (missing docs)

5. **Fraud Screening** (Fraud Detection Agent)
   - Rule-based signals (Section 5 of the policy):
     - Claim amount exceeds coverage limit
     - Claim filed within 14 days of policy inception (heightened scrutiny window)
     - Missing supporting documents
     - High prior-claim count (≥ 3)
     - Claimed amount differing from reported loss by more than 20%
   - Semantic similarity: claim narrative embedded and compared against historical fraud cases (FAISS)
   - Produces `Low` / `Medium` / `High` fraud level with reasons, indicators, and an LLM-generated explanation

6. **Escalation Decision** (Escalation Decision Agent)
   - **Any High fraud risk → mandatory manual review**
   - Medium fraud + uncertain coverage → escalated
   - Coverage marked Manual Review → escalated
   - Otherwise → continue processing

7. **Human-in-the-Loop Checkpoint**
   - Officer reviews the claim, documents, and agent consensus
   - Officer accepts, rejects, or overrides (`PATCH /api/claims/{id}/accept|reject|override`)
   - Every action is recorded in the immutable audit ledger

8. **Final Decision**
   - `ACCEPTED`: claim approved by officer
   - `REJECTED`: claim declined by officer
   - `MANUAL_REVIEW`: awaiting officer decision

---

## Customer Track (External)

### Flow Diagram

```
Customer Query → IntentClassifier → Policy RAG (retrieve policy context) → LLM (persona) → Response
                    ↓
              Route to appropriate handler
```

### Intent Classes

| Intent | Example |
|--------|---------|
| `CLAIM_STATUS` | "Where is my claim status?" |
| `CLAIM_EXPLANATION` | "Why was my claim rejected?" |
| `POLICY_QUERY` | "What is the coverage for fire damage?" |
| `NEXT_STEPS` | "How do I appeal the decision?" |
| `DOCUMENT_PROCESSING` | "Upload my proof of loss" |
| `GENERAL_QUERY` | "Hello" |

### Persona Modes

| Mode | When to Use | Tone |
|------|-------------|------|
| `customer_advisory` / `friendly` | Default customer queries | Polite, simple language, disclaimers |
| `compliance` | Sensitive / regulatory queries | Formal, strict policy-only responses |

### Customer Query Examples

**Coverage Guidance Example:**
> Customer: "What documents do I need to file a claim?"
> Assistant: "To file a claim, you need: Claim Form (signed), Policy Document, and Proof of Loss. Additional documents may include Medical Reports, Police Reports..."

**Decision Explanation Example:**
> Customer: "Why is my claim under review?"
> Assistant: "Your claim is currently undergoing additional verification. We are taking a closer look at the information you provided to be sure everything is correct. A claim officer will update you shortly."

**Tone Difference (vs Internal System):**
> Internal: "FRAUD SCREENING: HIGH — semantic similarity 0.82 to case FC-104. Mandatory manual review (Section 5)."
> Customer: "Your claim is undergoing additional verification. Please allow 1–2 business days for a claim officer to review."

---

## RAG Pipeline

### Architecture

```
Policy Documents → Chunker (split by Section) → Embedder (SentenceTransformer)
                                                      ↓
                                                FAISS Index
                                                      ↓
Customer Query → Embedder (same model) → FAISS Search (top-k) → Retrieved Chunks
                                                                      ↓
                                                              LLM Prompt (context + question)
                                                                      ↓
                                                              Generated Response
```

### Chunking Strategy
- Splits on the `Section N - Title` pattern
- Each chunk = one policy section, preserving complete rule context

### Embedding Model
- `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional embeddings
- Optimized for semantic similarity

### Why FAISS?
- Industry-standard vector search library
- Efficient similarity over the fraud-case corpus and policy sections
- L2 distance on normalized vectors ≈ cosine similarity

### Graceful Degradation
If `faiss-cpu` / `sentence-transformers` are not installed, the platform falls back to **rule-based** coverage and fraud logic plus policy keyword matching, so claims and chat remain fully functional without embeddings.

---

## Key Design Decisions

### "Assist, Not Approve" Principle
- The system **never** makes final approval decisions.
- It provides coverage interpretation, fraud screening, and explanations.
- All high-fraud-risk cases require human claim officer review.
- The customer agent never promises a payout and never accuses a customer of fraud.

### Audit-Friendly Explanation Trail
- Every agent decision and officer action is logged to the audit ledger.
- Logs include: timestamp, actor, event type, risk level, and structured details.
- LLM-generated explanations reference policy sections and reasons.

### Compliance Controls
- Strict prompt guardrails ("Use ONLY supplied policy context").
- "I cannot determine" fallback for unsupported queries.
- No external knowledge injection.
- Human-in-the-loop for every escalated claim.

### Rules Come From The Policy Document
Coverage scope, mandatory documents, reporting window (30 days), inception scrutiny (14 days), exclusions, and fraud rules are all **parsed from `data/policies/insurance_policy.txt`** — they are never hardcoded in Python.
