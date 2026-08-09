# API Reference — Regulatory & Compliance Copilot

All endpoints return JSON. The complete OpenAPI schema is available at `/docs` (Swagger UI) when the server is running.

The copilot exposes **two response tracks**, both grounded in the approved regulatory corpus:

| Track | Endpoint | Audience | Returns |
|-------|----------|----------|---------|
| **Internal** | `POST /api/regulatory/query` | Compliance & audit teams | Grounded answer, verifiable citations, confidence scores, retrieval excerpts, escalation recommendation |
| **Customer** | `POST /api/regulatory/customer-query` | Bank customers | Plain-language answer + disclaimer; internal retrieval details are **never** exposed |

---

## Authentication

### `POST /api/auth/login`
Logs a user in.

**Request:**
```json
{ "username": "admin", "password": "admin123", "portalType": "officer" }
```
`portalType` may be `customer` or `officer`.

**Response 200:**
```json
{
  "user": { "username": "admin", "email": "admin@bankreg.com", "name": "Compliance Officer",
            "phone": "+91 9876543210", "role": "officer", "password": null },
  "token": "tok-<hex>"
}
```

### `POST /api/auth/register`
**Request:**
```json
{ "username": "cust1", "fullName": "Ravi Kumar", "email": "r@mail.com",
  "password": "pass123", "phone": "999", "portalType": "customer" }
```
Password must be at least 6 characters. **Response 200:** `{ "user": {...}, "token": "tok-..." }`

### `POST /api/auth/logout`
**Response 200:** `{ "success": true }`

### `GET /api/auth/me?username=<username>`
Returns the current user. **Response 200:** `{ "user": {...} }`. **401** if no such user.

### `GET /api/users`
Lists all users. **Response 200:** `{ "users": [ { "username", "email", "name", "phone", "role" }, ... ] }`

### `PATCH /api/users/profile`
**Request:** `{ "name": "...", "email": "...", "phone": "...", "username": "..." }`
**Response 200:** `{ "user": { "role", "email", "name", "phone" } }`

### `DELETE /api/users/{username}`
Removes a user. **Response 200:** `{ "success": true }`, **404** if not found.

---

## Regulatory Copilot — Internal Track (Compliance & Audit)

### `POST /api/regulatory/query`

Ask a grounded compliance question. The answer is generated **only** from retrieved, approved regulatory clauses.

**Request:**
```json
{ "question": "What documents are required for KYC verification of an individual customer?" }
```

**Response 200:**
```json
{
  "track": "internal",
  "question": "What documents are required for KYC verification of an individual customer?",
  "answered": true,
  "answer": "For an individual customer, KYC verification may be satisfied by presenting any one officially valid document, such as a passport, driving licence, Voter ID, Aadhaar card, or NREGA job card.",
  "citations": [
    {
      "chunk_id": "rbi_kyc_master_direction-1_1",
      "clause_ref": "1.1",
      "source": "Master Direction - Know Your Customer (KYC) Norms",
      "circular_no": "RBI/2025-26/09",
      "quote": "Identity shall be verified using an officially valid document.",
      "grounded": true
    }
  ],
  "retrieved": [
    {
      "chunk_id": "rbi_kyc_master_direction-1_1",
      "clause_ref": "1.1",
      "source": "Master Direction - Know Your Customer (KYC) Norms",
      "circular_no": "RBI/2025-26/09",
      "version": "v1.0",
      "similarity": 0.78,
      "text": "1.1 ..."
    }
  ],
  "retrieval_confidence": 0.78,
  "answer_confidence": 0.9,
  "confidence": 0.83,
  "confidence_level": "High",
  "needs_escalation": false,
  "escalation_reason": null,
  "contradiction_detected": false,
  "disclaimer": null
}
```

**Key fields:**

| Field | Meaning |
|-------|---------|
| `answered` | `true` when a grounded answer was produced, `false` for the "Information not found" response |
| `citations[].grounded` | Whether the citation references a clause that was actually retrieved |
| `confidence` | Combined confidence: `0.6 × retrieval + 0.4 × llm` |
| `confidence_level` | `High` (≥ 0.75), `Medium` (≥ 0.55), `Low` |
| `needs_escalation` | `true` when the answer requires human compliance review |
| `escalation_reason` | Why escalation is recommended (low confidence, ungrounded citations, contradiction, or no answer) |
| `contradiction_detected` | `true` when retrieved clauses from different documents conflict |
| `retrieved` | Full retrieval excerpts with similarity scores (internal-only) |

**Behavioural guarantees:**
- If retrieval similarity falls below the floor (0.45), the LLM is **never called** and the response is the "Information not found" message with `answered: false` and `needs_escalation: true`.
- If the LLM marks `not_supported`, or produces no usable answer, the same "Information not found" response is returned.
- If two retrieved clauses contradict each other, the query is escalated for human adjudication instead of the AI picking a side.

**Response when no answer (200, `answered: false`):**
```json
{
  "track": "internal",
  "answered": false,
  "answer": "Information not found in the approved regulatory documents. Please refine the query or escalate to a compliance officer for manual research.",
  "confidence": 0.0,
  "confidence_level": "Low",
  "needs_escalation": true,
  "escalation_reason": "No relevant regulatory clause retrieved (similarity below threshold).",
  "citations": [], "retrieved": [], "contradiction_detected": false, "disclaimer": null
}
```

---

## Regulatory Copilot — Customer Track (Transparency)

### `POST /api/regulatory/customer-query`

Ask a plain-language question about bank regulations. The customer track never exposes internal retrieval details, circular numbers, or confidence internals.

**Request:**
```json
{ "question": "What do I need to open a bank account?" }
```

**Response 200:**
```json
{
  "track": "customer",
  "question": "What do I need to open a bank account?",
  "answered": true,
  "answer": "To open a regular bank account you will need to show one government-issued identity document, such as a passport, driving licence, Voter ID, Aadhaar card or NREGA job card.",
  "citations": [],
  "retrieved": [],
  "retrieval_confidence": 0.72,
  "answer_confidence": 0.65,
  "confidence": 0.69,
  "confidence_level": "Medium",
  "needs_escalation": false,
  "escalation_reason": null,
  "contradiction_detected": false,
  "disclaimer": "This information is for general guidance only and is not legal advice. For help specific to your account, please contact your bank."
}
```

**Behavioural guarantees:**
- `retrieved` is always an empty array on the customer track — internal excerpts are never exposed.
- Answers carry the standard `disclaimer`.
- If no approved disclosure supports the question, the customer receives the "I could not find this information..." message with `answered: false`.
- If the question requires a bank official (`needs_human`) or retrieved clauses conflict, the response redirects the customer to the bank with a complex-question notice and `answered: false`.

---

## Regulatory Corpus Management

### `GET /api/regulatory/documents`
Lists the version-controlled approved corpus (from the SQLite registry).

**Response 200:**
```json
{
  "documents": [
    {
      "doc_id": "rbi_kyc_master_direction",
      "title": "Master Direction - Know Your Customer (KYC) Norms",
      "circular_no": "RBI/2025-26/09",
      "issue_date": "01-Aug-2025",
      "version": "v1.0",
      "category": "circular",
      "file_path": "...\\data\\regulatory\\rbi_kyc_master_direction.txt",
      "file_hash": "<sha256>",
      "status": "active",
      "ingested_at": "2026-08-08 00:00:00"
    }
  ]
}
```

### `POST /api/regulatory/documents`
Ingest a new approved regulatory document (multipart/form-data). Supported extensions: `.txt`, `.md`, `.pdf`. The file is stored in the approved corpus directory and the vector index is **rebuilt immediately** so the copilot answers from it right away.

**Form fields:**
| Field | Type | Notes |
|-------|------|-------|
| `file` | file | Required. The document (`.txt` / `.md` / `.pdf`) |
| `title` | string | Optional. Falls back to the parsed document header or filename |
| `circular_no` | string | Optional |
| `issue_date` | string | Optional |
| `version` | string | Optional (default `v1.0`) |
| `category` | string | Optional (default `circular`) |

**Response 200:** `{ "document": { ...registry row }, "ingested": true }`

> **Note on document format:** documents are chunked at **clause level** (`1.`, `1.1`, `2.4`, ...). A document with no parseable numbered clauses is skipped by the ingest pipeline. See `docs/workflow.md` for the expected format.

### `DELETE /api/regulatory/documents/{doc_id}`
Archives a document: removes the file, deletes the registry row, and rebuilds the index. **Response 200:** `{ "success": true }`, **404** if the document is not in the registry.

---

## Reference & Administration

### `GET /api/audit-logs?riskLevel=`
Immutable audit ledger. `riskLevel` may be `low`, `medium`, or `high`.

**Response 200:**
```json
{
  "logs": [
    { "id": "LOG-<hex>", "timestamp": "2026-08-08 12:00:00", "actor": "Regulatory Query",
      "eventType": "Regulatory Query", "riskLevel": "low",
      "details": "Internal query: What documents are required for KYC..." }
  ]
}
```

### `GET /api/faq?search=`
FAQ list, optionally filtered by search text.
**Response 200:** `{ "faqs": [ { "id", "question", "answer" }, ... ] }`

### `GET /`
Serves the SPA (`static/index.html`). **Response:** HTML.

---

## Error Format

Errors follow FastAPI conventions:
```json
{ "detail": "Human-readable error message" }
```

Common status codes:

| Code | Meaning |
|------|---------|
| `400` | Bad request (e.g. unsupported file extension, password too short) |
| `401` | Invalid credentials / not authenticated |
| `404` | Resource not found (e.g. document to archive, user to delete) |
| `422` | Validation error (structured `detail` array) |
| `503` | Copilot unavailable (e.g. store failed to initialize) |
