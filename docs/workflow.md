# Loan Processing Workflow

## Business Track (Internal)

### Flow Diagram

```
Customer → Upload Documents → DocumentAgent → PolicyAgent → RiskAgent → [Human Review] → Decision
                                                                         ↑
                                                                    High Risk / Policy Violation
```

### Step-by-Step Workflow

1. **Create Loan Application**
   - `POST /api/business/loan-application`
   - Captures customer info, loan amount, salary, employment type

2. **Upload Documents** (5 mandatory document types)
   - Salary Slip (last 3 months)
   - Bank Statement (last 6 months)
   - Employment Letter
   - PAN Card
   - Aadhaar Card

3. **Document Processing** (DocumentAgent)
   - PDF text extraction (searchable PDFs)
   - OCR fallback for scanned documents
   - Document type validation
   - Field extraction (salary, employer, bank account, PAN, Aadhaar)
   - Required field completeness check
   - OCR confidence threshold check

4. **Policy Compliance Check** (PolicyAgent)
   - Minimum salary: ₹30,000/month
   - Maximum loan: 20x monthly salary
   - Required documents: all 5 mandatory
   - Employment duration: min 12 months
   - Result: ELIGIBLE / NOT_ELIGIBLE / MANUAL_REVIEW

5. **Risk Assessment** (RiskAgent)
   - Combines policy violations with extracted data
   - Computes Loan-to-Income ratio
   - Checks bank balance vs declared income
   - Produces RiskLevel: LOW / MEDIUM / HIGH
   - Generates LLM explanation for audit
   - Recommendation: CONTINUE / REQUEST_DOCUMENTS / MANUAL_REVIEW

6. **Human-in-the-Loop Checkpoint**
   - HIGH risk → mandatory manual review
   - Policy violations → manual review recommended
   - Loan officer reviews and decides

7. **Final Decision**
   - APPROVED: Low risk, all compliant
   - REJECTED: Policy violations
   - MANUAL_REVIEW: Needs human approval

---

## Customer Track (External)

### Flow Diagram

```
Customer Query → IntentClassifier → Policy RAG (retrieve policy context) → LLM (with persona) → Response
                    ↓
              Route to appropriate handler
```

### Persona Modes

| Mode | When to Use | Tone |
|---|---|---|
| `friendly` | Default customer queries | Polite, simple language, disclaimers |
| `compliance` | Sensitive/regulatory queries | Formal, strict policy-only responses |

### Customer Query Examples

**Eligibility Guidance Example:**
> Customer: "What is the minimum salary for a home loan?"
> Assistant: "Based on our banking policy, the minimum monthly salary required for a home loan is ₹30,000. Please note that the final decision is made by the bank after reviewing your complete application."

**Approval Explanation Example:**
> Customer: "My loan was approved. Why?"
> Assistant: "Your loan was approved because your application met all policy requirements: your monthly income of ₹50,000 exceeds the minimum requirement, you submitted all required documents, and your requested loan amount is within policy limits."

**Rejection Explanation Example:**
> Customer: "Why was my loan rejected?"
> Assistant: "Unfortunately, your loan application was not approved because the monthly salary mentioned in your application (₹25,000) is below the minimum requirement of ₹30,000 per month as per our home loan policy. You may consider increasing your income or applying with a co-applicant."

**Tone Difference (vs Internal System):**
> Internal: "HIGH RISK: Violation Section 3 - Income below ₹30,000 minimum. Recommend MANUAL_REVIEW."
> Customer: "We were unable to process your application at this time because your monthly income is below the required minimum. For more details, please contact our loan officer who can discuss your options."

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
- Splits on `Section N - Title` pattern
- Each chunk = one policy section
- Ensures complete rule context per section

### Embedding Model
- `sentence-transformers/all-MiniLM-L6-v2`
- 384-dimensional embeddings
- Optimized for semantic similarity
- ~10x faster than larger models like BERT

### Why FAISS?
- Industry-standard vector search library
- Handles millions of vectors efficiently
- L2 distance on normalized vectors = cosine similarity
- Suitable for banking compliance (deterministic/controllable)

---

## Key Design Decisions

### "Assist, Not Approve" Principle
- The system **never** makes final approval decisions
- Provides risk assessment, policy compliance checks, and explanations
- All high-risk cases require human loan officer review
- Customer agent never promises loan approval

### Audit-Friendly Explanation Trail
- Every agent decision logged to `AuditService`
- Logs include: actor, action, timestamp, details
- LLM-generated explanations stored in risk assessment
- Policy violations include section references

### Compliance Controls
- Strict prompt guardrails ("Use ONLY supplied policy context")
- "I cannot determine" fallback for unsupported queries
- No external knowledge injection
- Human-in-the-loop for escalation