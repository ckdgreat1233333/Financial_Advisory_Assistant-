# API Reference — Insurance Claims Intelligence Platform

All endpoints return JSON. Auth-required endpoints accept the JWT issued by `POST /api/auth/login` (the SPA stores it and sends it as a bearer token). The complete OpenAPI schema is available at `/docs` (Swagger UI) when the server is running.

---

## Authentication

### `POST /api/auth/login`
Logs a user in and returns a JWT.

**Request:**
```json
{ "username": "admin", "password": "admin123", "portalType": "officer" }
```
`portalType` may be `customer`, `officer`, or `admin`.

**Response 200:**
```json
{
  "user": { "username": "admin", "email": "...", "name": "...", "phone": "...", "role": "officer" },
  "token": "<jwt>"
}
```

### `POST /api/auth/register`
```json
{ "username": "cust1", "fullName": "Ravi Kumar", "email": "r@mail.com",
  "password": "pass123", "phone": "999", "portalType": "customer" }
```
**Response 200:** `{ "user": {...}, "token": "<jwt>" }`

### `POST /api/auth/logout`
**Response 200:** `{ "status": "logged_out" }`

### `GET /api/auth/me`
Returns the current user. **Response:** `{ "user": {...} }`

---

## Claims

### `POST /api/claims`
Creates a new claim.

**Request:**
```json
{
  "claimantName": "Ravi Kumar",
  "claimantEmail": "ravi@mail.com",
  "claimantPhone": "999",
  "policyNumber": "P-AUTO-2026-0001",
  "type": "auto",
  "amount": 5000,
  "incidentDate": "2026-07-20",
  "lossDescription": "Collision damage on Highway 101",
  "documents": [
    { "name": "claim_form.txt", "docType": "claim_form" },
    { "name": "policy.txt", "docType": "policy_document" },
    { "name": "proof.txt", "docType": "proof_of_loss" }
  ]
}
```
`type` is one of: `auto`, `health`, `property`, `fire`, `theft`, `travel`, `liability`.

**Response 200:** `{ "claim": { ...claim object, "id": "CLM-XXXX", "status": "received" } }`

### `GET /api/claims?email=`
Lists claims. Customers pass their email to see only their own claims.

**Response 200:** `{ "claims": [ ...claim objects ] }`

### `GET /api/claims/{claim_id}`
Full claim detail, including document list and the agent consensus.

**Response 200:** a claim object (not wrapped):
```json
{
  "id": "CLM-XXXX", "claimantName": "...", "status": "received",
  "type": "auto", "amount": 5000.0, "progress": 25,
  "fraudScore": 30, "fraudLevel": "Unknown", "coverageStatus": "covered",
  "documents": [ { "id": "...", "name": "claim_form.txt", "type": "Claim Form",
                   "docType": "claim_form", "status": "pending" } ],
  "agentConsensus": {
    "documentValidation":   { "status": "pass", "score": 90, "details": "..." },
    "policyInterpretation": { "status": "pass", "score": 90, "details": "..." },
    "fraudScreening":       { "status": "pass", "score": 30, "details": "..." },
    "escalationDecision":   { "status": "pass", "score": 100, "details": "..." }
  }
}
```

**Status values:** `received | under_review | accepted | rejected`
**Coverage:** `covered | review_required | failed`
**Fraud levels:** `Low | Medium | High | Unknown`

### `POST /api/claims/{claim_id}/documents`
Uploads claim documents (multipart/form-data, field name `files`). When the three mandatory documents (Claim Form, Policy Document, Proof of Loss) are present, the orchestrator pipeline runs automatically.

**Response 200:** `{ "claim": { ...updated claim object } }`

### `POST /api/claims/{claim_id}/process`
Manually re-runs the agent pipeline on an existing claim.
**Response 200:** updated claim object.

### `PATCH /api/claims/{claim_id}/accept` | `PATCH /api/claims/{claim_id}/reject`
Officer decision (human-in-the-loop). Every action is written to the audit ledger.

**Request:**
```json
{ "actor": "Admin Officer", "reason": "All documents verified" }
```

**Response 200:**
```json
{ "claim": { "...": "..." }, "auditLog": { "eventType": "Claims Officer Acceptance", "..." } }
```

### `PATCH /api/claims/{claim_id}/override`
Officer override of an agent recommendation.
**Request:** `{ "actor": "...", "decision": "...", "reason": "..." }`

### `PATCH /api/claims/{claim_id}/documents/{doc_id}`
Officer updates a document's review status.

**Request:**
```json
{ "status": "verified" }
```
**Response 200:** updated claim object (not wrapped).

### `GET /api/claims/{claim_id}/documents/{doc_name}/file`
Streams the uploaded document for in-browser viewing.
**Response 200:** the file body with its content type.

### `GET /api/claims/{claim_id}/fraud-analysis`
Detailed fraud screening for a claim.

**Response 200:**
```json
{
  "claim_id": "CLM-XXXX",
  "fraud_level": "Low",
  "fraud_score": 18.0,
  "confidence_score": 0.9,
  "similarity_score": null,
  "similar_cases": [],
  "reasons": ["No significant fraud indicators identified"],
  "fraud_indicators": [],
  "triggered_rules": [],
  "llm_explanation": "..."
}
```

### `GET /api/claims/{claim_id}/explanation`
Explainable decision in plain language (ethics-aware — never exposes internal scores, and uses "undergoing additional verification" phrasing for flagged claims).

**Response 200:**
```json
{
  "claim_id": "CLM-XXXX",
  "decision": "under review",
  "explanation": "...",
  "disclaimer": "..."
}
```

---

## Customer Chat

### `POST /api/chat`
Grounded customer assistant. Answers are backed by the policy document (RAG) or matched policy rules, never free-form LLM guesswork.

**Request:**
```json
{ "message": "What documents do I need?", "history": [], "claimsContext": [] }
```

**Response 200:**
```json
{
  "text": "To file a claim, you need: Claim Form, Policy Document, and Proof of Loss...",
  "reasoning": "Rule-based match",
  "intent": "POLICY_QUERY",
  "policyGrounding": { "documentName": "Insurance Claims Policy", "clause": "...", "extractedText": "..." }
}
```

### `POST /api/customer/chat`
Alternative customer-agent endpoint (`question` + `mode`).

---

## Audit & Administration

### `GET /api/audit-logs`
Immutable audit ledger.
**Response 200:** `{ "logs": [ { "timestamp": "...", "actor": "...", "eventType": "...", "riskLevel": "...", "details": "..." } ] }`

### `GET /api/fraud-cases`
Historical fraud case corpus used for similarity screening.
**Response 200:** `{ "fraudCases": [...] }`

### `GET /api/fraud-cases/thresholds`
**Response 200:** `{ "high": 0.7, "medium": 0.5 }`

### `GET /api/policy-documents`
**Response 200:** `{ "policyDocuments": [...] }`

### `POST /api/policy-documents` · `DELETE /api/policy-documents/{doc_id}`
Create / archive policy documents (admin).

### `GET /api/faq`
**Response 200:** `{ "faqs": [...] }`

### `GET /api/users`
**Response 200:** `{ "users": [...] }`

### `PATCH /api/users/profile`
**Request:** `{ "name": "...", "email": "...", "phone": "...", "username": "..." }`
**Response 200:** `{ "user": {...} }`

### `DELETE /api/users/{username}`
Removes a user (admin).

---

## Analytics

### `GET /api/analytics/claims-dashboard`
**Response:** `{ "avgFraudScore": ..., "highRiskPortfolio": ..., "highRiskDelta": ..., "automatedPassRate": ..., "fraudAlerts": ..., "commonFailurePoints": [...] }`

### `GET /api/analytics/fraud-dashboard`
Fraud-focused dashboard metrics.

### `GET /api/analytics/pipeline-health`
**Response:** `{ "ocrParseRate": "320 docs / min", "tokenLatencyMs": 132, "ragVectorCacheHitRate": 99.4 }`

---

## Utility

### `POST /api/uploads`
Generic multipart file upload (stores under `data/uploads/`).
**Request:** multipart field `files`, optional `claim_id` form field.
**Response 200:** `{ "results": [ { "id": "...", "name": "...", "type": "..." } ] }`

---

## Error Format

Errors follow FastAPI conventions:
```json
{ "detail": "Human-readable error message" }
```
Validation errors return `422` with a structured `detail` array.
