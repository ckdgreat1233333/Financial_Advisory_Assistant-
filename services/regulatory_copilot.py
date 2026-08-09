"""Regulatory & Compliance Copilot facade.

Combines the versioned knowledge store, confidence gating, grounded
citation checks, contradiction detection, and two response layers
(internal compliance vs customer transparency) with a full audit trail.
"""
from __future__ import annotations

from services.llm_service import LLMService
from services.prompt_service import PromptService
from services.audit_service import AuditService
from models.regulatory import Citation, RegulatoryAnswer, RetrievedChunk
from regulatory import confidence as conf
from regulatory.confidence import (
    NO_ANSWER_SIM_THRESHOLD,
    ESCALATE_CONFIDENCE_THRESHOLD,
    detect_conflicts,
)
from regulatory.embedder import RegulatoryEmbedder
from regulatory.parsing import extract_json, sanitize_ascii, to_bool, to_float
from regulatory.store import RegulatoryKnowledgeStore
from utils.enums import AuditSeverity

INTERNAL_NO_ANSWER = (
    "Information not found in the approved regulatory documents. "
    "Please refine the query or escalate to a compliance officer for manual research."
)
CUSTOMER_NO_ANSWER = (
    "I could not find this information in our published regulatory disclosures. "
    "Please contact your bank or visit a branch for assistance."
)
CUSTOMER_DISCLAIMER = (
    "This information is for general guidance only and is not legal advice. "
    "For help specific to your account, please contact your bank."
)
COMPLEX_REDIRECT = (
    "This question involves regulatory interpretation that requires a bank official. "
    "Please contact your relationship manager or the bank's grievance desk for assistance."
)


class RegulatoryCopilot:

    def __init__(self, llm=None, audit=None, store=None):
        self.store = store or RegulatoryKnowledgeStore(embedder=RegulatoryEmbedder())
        self.llm = llm or LLMService()
        self.prompts = PromptService()
        self.audit = audit or AuditService()

    # ── Retrieval ──────────────────────────────────────────────

    def retrieve_excerpts(self, question: str, top_k: int = 4) -> list[RetrievedChunk]:
        return self.store.retrieve(question, k=top_k)

    # ── Internal (Compliance & Audit) track ────────────────────

    def answer_internal(self, question: str, top_k: int = 4) -> RegulatoryAnswer:
        retrieved = self.store.retrieve(question, k=top_k)
        ret_conf = conf.retrieval_confidence(retrieved)
        conflicts = detect_conflicts(retrieved, self.store.embedder)

        # Gate 1 - no answer. Do not call the LLM below the retrieval floor.
        if ret_conf < NO_ANSWER_SIM_THRESHOLD:
            answer = self._build_answer(
                track="internal", question=question, retrieved=retrieved,
                ret_conf=ret_conf, answer_text=INTERNAL_NO_ANSWER,
                answered=False,
                escalation_reason="No relevant regulatory clause retrieved (similarity below threshold).",
            )
            self._audit(answer)
            return answer

        context = self._format_context(retrieved)
        prompt = self.prompts.load(
            "regulatory_compliance_prompt.txt", question=question, context=context
        )
        raw = self._safe_generate(prompt)
        parsed = extract_json(raw)

        answer_text = sanitize_ascii(str(parsed.get("answer", ""))).strip()
        llm_conf = to_float(parsed.get("confidence"), 0.0)
        not_supported = to_bool(parsed.get("not_supported"))
        contradiction = to_bool(parsed.get("contradiction")) or bool(conflicts)

        citations, grounding_ok = self._parse_and_ground_citations(parsed, retrieved)
        combined = conf.combined_confidence(ret_conf, llm_conf)

        # Gate 2 - not supported by any retrieved clause.
        if not answer_text or not_supported:
            answer = self._build_answer(
                track="internal", question=question, retrieved=retrieved,
                ret_conf=ret_conf, answer_text=INTERNAL_NO_ANSWER,
                answered=False, citations=citations, contradiction=contradiction,
                escalation_reason="The retrieved clauses do not support an answer.",
            )
            self._audit(answer)
            return answer

        escalation_reason = None
        if contradiction:
            escalation_reason = "Possible contradiction between retrieved clauses; requires human adjudication."
        elif not grounding_ok:
            escalation_reason = "One or more citations could not be grounded in retrieved clauses."
        elif combined < ESCALATE_CONFIDENCE_THRESHOLD:
            escalation_reason = "Answer confidence below escalation threshold; requires compliance review."
        elif not citations:
            escalation_reason = "No verifiable citations produced; requires compliance review."

        answer = self._build_answer(
            track="internal", question=question, retrieved=retrieved,
            ret_conf=ret_conf, answer_text=answer_text,
            answered=True, citations=citations, llm_conf=llm_conf,
            contradiction=contradiction, escalation_reason=escalation_reason,
        )
        self._audit(answer)
        return answer

    # ── Customer (Transparency) track ──────────────────────────

    def answer_customer(self, question: str, top_k: int = 4) -> RegulatoryAnswer:
        retrieved = self.store.retrieve(question, k=top_k)
        ret_conf = conf.retrieval_confidence(retrieved)
        conflicts = detect_conflicts(retrieved, self.store.embedder)

        if ret_conf < NO_ANSWER_SIM_THRESHOLD:
            answer = self._build_answer(
                track="customer", question=question, retrieved=retrieved,
                ret_conf=ret_conf, answer_text=CUSTOMER_NO_ANSWER,
                answered=False, disclaimer=CUSTOMER_DISCLAIMER,
                escalation_reason=None,
            )
            self._audit(answer)
            return answer

        context = self._format_context(retrieved)
        prompt = self.prompts.load(
            "regulatory_customer_prompt.txt", question=question, context=context
        )
        raw = self._safe_generate(prompt)
        parsed = extract_json(raw)

        answer_text = sanitize_ascii(str(parsed.get("answer", ""))).strip()
        llm_conf = to_float(parsed.get("confidence"), 0.0)
        not_supported = to_bool(parsed.get("not_supported"))
        needs_human = to_bool(parsed.get("needs_human"))

        if not answer_text or not_supported:
            answer = self._build_answer(
                track="customer", question=question, retrieved=retrieved,
                ret_conf=ret_conf, answer_text=CUSTOMER_NO_ANSWER,
                answered=False, disclaimer=CUSTOMER_DISCLAIMER,
            )
            self._audit(answer)
            return answer

        if needs_human or bool(conflicts):
            answer = self._build_answer(
                track="customer", question=question, retrieved=retrieved,
                ret_conf=ret_conf, answer_text=COMPLEX_REDIRECT,
                answered=False, llm_conf=llm_conf,
                contradiction=bool(conflicts),
                disclaimer=CUSTOMER_DISCLAIMER,
                escalation_reason="Query requires a human bank official (complex or conflicting sources).",
            )
            self._audit(answer)
            return answer

        answer = self._build_answer(
            track="customer", question=question, retrieved=retrieved,
            ret_conf=ret_conf, answer_text=answer_text,
            answered=True, llm_conf=llm_conf,
            disclaimer=CUSTOMER_DISCLAIMER,
        )
        self._audit(answer)
        return answer

    # ── Internal helpers ───────────────────────────────────────

    def _build_answer(
        self,
        track: str,
        question: str,
        retrieved: list[RetrievedChunk],
        ret_conf: float,
        answer_text: str,
        answered: bool,
        citations: list[Citation] | None = None,
        llm_conf: float | None = None,
        contradiction: bool = False,
        escalation_reason: str | None = None,
        disclaimer: str | None = None,
    ) -> RegulatoryAnswer:
        combined = conf.combined_confidence(ret_conf, llm_conf)
        needs_escalation = escalation_reason is not None or (
            answered and combined < conf.CONFIDENT_THRESHOLD and track == "internal"
        )
        return RegulatoryAnswer(
            track=track,
            question=question,
            answered=answered,
            answer=answer_text,
            citations=citations or [],
            retrieved=retrieved,
            retrieval_confidence=ret_conf,
            answer_confidence=llm_conf if llm_conf is not None else 0.0,
            confidence=combined,
            confidence_level=conf.confidence_level(combined),
            needs_escalation=needs_escalation,
            escalation_reason=escalation_reason,
            contradiction_detected=contradiction,
            disclaimer=disclaimer,
        )

    def _format_context(self, retrieved: list[RetrievedChunk]) -> str:
        blocks = []
        for item in retrieved:
            c = item.chunk
            blocks.append(
                f"[ID:{c.chunk_id}] | Document: {c.title} | Circular: {c.circular_no or 'N/A'} | "
                f"Date: {c.issue_date or 'N/A'} | Version: {c.version}\n"
                f"Clause {c.clause_ref}:\n{c.text}"
            )
        return "\n\n".join(blocks)

    def _parse_and_ground_citations(self, parsed: dict, retrieved: list[RetrievedChunk]) -> tuple[list[Citation], bool]:
        """Validate that every citation references a chunk that was actually retrieved."""
        allowed_ids = {r.chunk.chunk_id for r in retrieved}
        allowed_clauses = {(r.chunk.document_id, r.chunk.clause_ref) for r in retrieved}
        chunk_by_id = {r.chunk.chunk_id: r.chunk for r in retrieved}

        citations: list[Citation] = []
        grounding_ok = True
        for raw_cite in parsed.get("citations", []) or []:
            if not isinstance(raw_cite, dict):
                continue
            chunk_id = str(raw_cite.get("id", "")).replace("ID:", "").strip()
            clause = str(raw_cite.get("clause", "")).strip()
            source = sanitize_ascii(str(raw_cite.get("source", ""))).strip()
            quote = sanitize_ascii(str(raw_cite.get("quote", ""))).strip()

            chunk = chunk_by_id.get(chunk_id)
            grounded = chunk is not None
            if not grounded and chunk_id:
                # Fallback: match by (document, clause_ref) among retrieved chunks.
                for item in retrieved:
                    if item.chunk.clause_ref == clause and (item.chunk.document_id, item.chunk.clause_ref) in allowed_clauses:
                        chunk = item.chunk
                        chunk_id = item.chunk.chunk_id
                        grounded = True
                        break
            if not grounded:
                grounding_ok = False
            citations.append(
                Citation(
                    chunk_id=chunk_id,
                    clause_ref=clause,
                    source=source or (chunk.title if chunk else "Unknown"),
                    circular_no=chunk.circular_no if chunk else "",
                    quote=quote,
                    grounded=grounded,
                )
            )
        return citations, grounding_ok

    def _safe_generate(self, prompt: str) -> str:
        try:
            return self.llm.generate(prompt, temperature=0.1, max_tokens=1400)
        except Exception:
            return ""

    def _audit(self, answer: RegulatoryAnswer) -> None:
        severity = AuditSeverity.WARNING if answer.needs_escalation else AuditSeverity.INFO
        self.audit.log(
            actor=f"Regulatory Copilot ({answer.track})",
            action="Regulatory Query",
            details=(
                f"Q: {answer.question} | answered: {answer.answered} | "
                f"confidence: {answer.confidence} | escalated: {answer.needs_escalation} | "
                f"citations: {[c.chunk_id for c in answer.citations]}"
            ),
            severity=severity,
        )
