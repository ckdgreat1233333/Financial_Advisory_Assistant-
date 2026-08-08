import re
import json
import logging
from datetime import datetime

from services.policy_service import PolicyService
from services.prompt_service import PromptService
from services.llm_service import LLMService
from services.audit_service import AuditService
from services.fraud_case_service import (
    FraudCaseService,
    HIGH_SIM_THRESHOLD,
    MEDIUM_SIM_THRESHOLD,
)
from models.fraud import FraudAssessment
from models.claim import Claim
from models.extracted_data import ClaimExtractedData
from models.policy import PolicyResult
from utils.enums import FraudLevel, Recommendation, FraudIndicator

logger = logging.getLogger("claims_assistant")


class FraudService:
    """
    Fraud detection combining policy-defined risk rules with semantic
    similarity to historical fraud cases.

    All fraud rules and thresholds come from the policy document,
    never hardcoded in Python.
    """

    def __init__(self):
        self.policy = PolicyService()
        self.prompts = PromptService()
        self.llm = LLMService()
        self.audit = AuditService()
        self.case_service = FraudCaseService()

    def _get_policy_rules(self):
        self.policy._ensure_rules()
        return self.policy._rules

    def _get_fraud_rules(self) -> dict[FraudLevel, list[str]]:
        rules = self._get_policy_rules()
        if rules.fraud_rules:
            return rules.fraud_rules
        return {level: [] for level in FraudLevel}

    def evaluate(self, claim: Claim, extracted_data: ClaimExtractedData,
                 policy_result: PolicyResult, documents: list | None = None,
                 cross_document_issues: list[str] | None = None) -> FraudAssessment:
        """Legacy method name kept for orchestrator parity."""
        return self.detect_fraud(claim, extracted_data, policy_result,
                                 documents=documents, cross_document_issues=cross_document_issues)

    def detect_fraud(self, claim: Claim, extracted_data: ClaimExtractedData,
                     policy_result: PolicyResult, documents: list | None = None,
                     cross_document_issues: list[str] | None = None) -> FraudAssessment:
        risk_factors = []
        indicators = []
        triggered_rules = []
        fraud_level = FraudLevel.LOW
        confidence = 0.9
        fraud_rules = self._get_fraud_rules()

        amount = extracted_data.claimed_amount or claim.claim_amount or 0
        limit = extracted_data.coverage_limit

        # ---- Rule 1: Amount exceeds coverage ----
        if limit is not None and amount > limit:
            risk_factors.append(
                f"Claim amount ₹{amount:,.0f} exceeds coverage limit ₹{limit:,.0f} "
                "(Section 3 - Coverage Limits)"
            )
            indicators.append(FraudIndicator.AMOUNT_EXCEEDS_COVERAGE.value)

        # ---- Rule 2: Recent policy inception ----
        # The signal is the gap between policy inception and the incident:
        # a loss occurring within the scrutiny window of policy start is the
        # "bought insurance, then lost shortly after" pattern. When the
        # incident date is unavailable, fall back to days since inception.
        scrutiny_days = self._get_policy_rules().inception_scrutiny_days
        if scrutiny_days and extracted_data.policy_inception_date:
            days = self._days_between(
                extracted_data.policy_inception_date, extracted_data.incident_date)
            if days is None:
                days = self._days_since(extracted_data.policy_inception_date)
            if days is not None and days <= scrutiny_days:
                risk_factors.append(
                    f"Loss occurred {days} days after policy inception; within the {scrutiny_days}-day "
                    f"scrutiny window (Section 1 - Coverage Scope)"
                )
                indicators.append(FraudIndicator.RECENT_POLICY_INCEPTION.value)

        # ---- Rule 3: Missing documents ----
        if hasattr(policy_result, 'policy_sections') and any("Required Documents" in s for s in policy_result.policy_sections):
            risk_factors.append("Critical supporting documents missing (Section 2 - Required Documents)")
            indicators.append(FraudIndicator.MISSING_DOCUMENTS.value)

        # ---- Rule 4: Prior claim history ----
        if extracted_data.prior_claims is not None and extracted_data.prior_claims >= 3:
            risk_factors.append(
                f"High prior claim count ({extracted_data.prior_claims}) in recent history "
                "(Section 5 - Fraud Screening Rules)"
            )
            indicators.append(FraudIndicator.PRIOR_CLAIM_HISTORY.value)

        # ---- Rule 5: Inconsistent details (loss description vs claimed amount) ----
        if extracted_data.reported_amount and amount and extracted_data.reported_amount > 0:
            if abs(extracted_data.reported_amount - amount) / extracted_data.reported_amount > 0.2:
                risk_factors.append(
                    f"Claimed amount (₹{amount:,.0f}) differs from reported loss (₹{extracted_data.reported_amount:,.0f}) "
                    "by more than 20% (Section 5 - Fraud Screening Rules)"
                )
                indicators.append(FraudIndicator.INCONSISTENT_DETAILS.value)

        # ---- Rule 6: Cross-document inconsistency ----
        # Documents that reference different claim numbers, policy numbers or
        # insured persons indicate a mixed or mismatched upload rather than a
        # single coherent claim, and must not be merged silently.
        for issue in (cross_document_issues or []):
            risk_factors.append(issue)
        if cross_document_issues:
            indicators.append(FraudIndicator.INCONSISTENT_DETAILS.value)
            triggered_rules.append("Conflicting information across submitted documents")
            if fraud_level == FraudLevel.LOW:
                fraud_level = FraudLevel.MEDIUM
                confidence = 0.8

        # ---- Semantic similarity to historical fraud cases ----
        # Only meaningful when the claim carries real content. Boilerplate
        # fields (claim type / amount) are identical across claims and would
        # dominate the embedding, inflating similarity for every claim.
        # The full extracted text of the uploaded documents (excluding the
        # shared policy document) is used so that fraud narratives inside
        # the documents themselves are actually compared. Each candidate
        # text is embedded and scored separately; the best match across
        # blocks is used. Concatenating a short structured loss description
        # with a long document narrative would dilute the mean-pooled
        # embedding and hide fraud that only appears in one of the blocks.
        claim_type_label = claim.claim_type.value if hasattr(claim.claim_type, "value") else str(claim.claim_type)
        similarity_blocks = self._build_similarity_blocks(claim, extracted_data, documents)
        similar_cases = []
        best_similarity = 0.0
        if similarity_blocks:
            try:
                merged: dict[str, dict] = {}
                for block in similarity_blocks:
                    for scored in self.case_service.score_claim(
                        block, top_k=3, claim_type=claim_type_label
                    ):
                        existing = merged.get(scored["case_id"])
                        if existing is None or scored["similarity"] > existing["similarity"]:
                            merged[scored["case_id"]] = scored
                similar_cases = sorted(
                    merged.values(), key=lambda r: r["similarity"], reverse=True
                )[:3]
            except Exception as e:
                logger.warning(f"Fraud case similarity unavailable, skipping semantic screening: {e}")
                similar_cases = []

        if similar_cases:
            best_similarity = similar_cases[0]["similarity"]
            sim_level = self.case_service.classify_similarity(best_similarity)
            risk_factors.append(
                f"Semantic similarity {best_similarity:.0%} to historical fraud case "
                f"{similar_cases[0]['case_id']} ({sim_level})"
            )
            indicators.append(FraudIndicator.SEMANTIC_CASE_SIMILARITY.value)
            if sim_level == "High":
                triggered_rules.append(f"Strong semantic similarity to {similar_cases[0]['case_id']}")
            elif sim_level == "Medium":
                triggered_rules.append(f"Moderate similarity to historical fraud cases")

        # ---- Rule 7: LLM document analysis (dynamic) ----
        # The LLM reads the actual uploaded documents and reports
        # cross-document inconsistencies and fraud indicators that the
        # static rules and regex patterns cannot anticipate. This is the
        # primary layer for catching mixed/mismatched document sets and
        # narratives that only an analyst would notice. It never lowers a
        # risk level; rule findings are always additive.
        llm_findings = self._analyze_documents_with_llm(
            claim, extracted_data, documents, similar_cases
        )

        for issue in llm_findings.get("inconsistencies", []):
            if issue and issue not in risk_factors:
                risk_factors.append(f"Cross-document inconsistency: {issue}")
        if llm_findings.get("inconsistencies"):
            if FraudIndicator.INCONSISTENT_DETAILS.value not in indicators:
                indicators.append(FraudIndicator.INCONSISTENT_DETAILS.value)
            triggered_rules.append("Conflicting information across submitted documents (AI analysis)")
            if fraud_level == FraudLevel.LOW:
                fraud_level = FraudLevel.MEDIUM
                confidence = 0.8

        for indicator in llm_findings.get("fraud_indicators", []):
            if indicator and indicator not in risk_factors:
                risk_factors.append(f"AI analysis: {indicator}")
        if llm_findings.get("fraud_indicators"):
            indicators.append(FraudIndicator.AI_DETECTED_PATTERNS.value)
            triggered_rules.append("Suspicious patterns identified by AI document analysis")

        ai_summary = llm_findings.get("summary")
        if ai_summary:
            risk_factors.append(f"AI document analysis: {ai_summary}")

        ai_risk = llm_findings.get("overall_risk")
        if ai_risk == "High":
            fraud_level = FraudLevel.HIGH
            confidence = min(confidence, 0.8)
        elif ai_risk == "Medium" and fraud_level == FraudLevel.LOW:
            fraud_level = FraudLevel.MEDIUM
            confidence = min(confidence, 0.75)

        # ---- Determine fraud level ----
        if policy_result.policy_sections and any("Coverage Limits" in s for s in policy_result.policy_sections):
            fraud_level = FraudLevel.MEDIUM
        if FraudIndicator.SEMANTIC_CASE_SIMILARITY.value in indicators:
            if best_similarity >= HIGH_SIM_THRESHOLD:
                fraud_level = FraudLevel.HIGH
                confidence = 0.85
            elif best_similarity >= MEDIUM_SIM_THRESHOLD:
                fraud_level = FraudLevel.MEDIUM if fraud_level != FraudLevel.HIGH else fraud_level
                confidence = 0.8
        if len(indicators) >= 3:
            fraud_level = FraudLevel.HIGH
            confidence = 0.85
        if not risk_factors:
            risk_factors = ["No significant fraud indicators identified"]
            triggered_rules = fraud_rules.get(FraudLevel.LOW, [])

        recommendation = self._get_recommendation(fraud_level, indicators)

        assessment = FraudAssessment(
            fraud_level=fraud_level,
            fraud_score=self._get_fraud_score(fraud_level, risk_factors),
            confidence_score=confidence,
            reasons=risk_factors,
            recommendation=recommendation,
            similarity_score=best_similarity if similar_cases else None,
            similar_cases=similar_cases,
            fraud_indicators=indicators,
            triggered_rules=triggered_rules,
            generated_at=datetime.now(),
            requires_manual_review=fraud_level == FraudLevel.HIGH,
            manual_review_reason=(
                "High fraud risk detected; mandatory human review required" if fraud_level == FraudLevel.HIGH else None
            ),
            metadata={"ai_document_analysis": llm_findings},
        )

        self.audit.log(
            actor="Fraud Detection Agent",
            action="Fraud Screening",
            details=f"Fraud Level: {fraud_level.value}, Score: {assessment.fraud_score}, Similarity: {best_similarity:.2f}, Indicators: {len(indicators)}"
        )

        self._explain_with_llm(assessment, claim, extracted_data)

        return assessment

    def _analyze_documents_with_llm(
        self,
        claim: Claim,
        extracted_data: ClaimExtractedData,
        documents: list | None,
        similar_cases: list[dict],
    ) -> dict:
        """Dynamically analyze the full document set with the LLM.

        The LLM compares every identifier across documents and reads each
        document's narrative to surface inconsistencies and fraud indicators
        that hardcoded rules cannot anticipate. Returns a dict with
        ``inconsistencies``, ``fraud_indicators``, ``overall_risk`` and
        ``summary``. Any failure degrades gracefully to an empty result so
        the deterministic rules still apply.
        """
        empty = {"inconsistencies": [], "fraud_indicators": [], "overall_risk": None, "summary": ""}
        docs = [d for d in (documents or []) if getattr(d, "extracted_text", "")]
        if not docs:
            return empty

        try:
            sections = []
            for i, doc in enumerate(docs, 1):
                doc_type = getattr(doc, "document_type", None)
                type_label = doc_type.value if hasattr(doc_type, "value") else str(doc_type)
                text = (getattr(doc, "extracted_text", "") or "").strip()
                sections.append(f"[{i}] {type_label} - {getattr(doc, 'document_name', 'document')}\nExtracted text:\n{text[:1800]}")

            if similar_cases:
                case_lines = []
                for c in similar_cases:
                    case_lines.append(
                        f"- {c['case_id']} (similarity {c['similarity']:.0%}): "
                        f"indicators: {', '.join(c.get('matched_indicators', []) or [])}; "
                        f"narrative: {c.get('narrative', '')[:250]}"
                    )
                similar_text = "\n".join(case_lines)
            else:
                similar_text = "None"

            claim_type_label = claim.claim_type.value if hasattr(claim.claim_type, "value") else str(claim.claim_type)
            prompt = self.prompts.load(
                "document_analysis_prompt.txt",
                claim_id=claim.claim_id,
                claimant=claim.claimant_name or "Unknown",
                claim_type=claim_type_label,
                claim_amount=f"{claim.claim_amount:,.0f}",
                incident_date=claim.incident_date or "Unknown",
                documents="\n\n".join(sections),
                similar_cases=similar_text,
            )

            raw = self.llm.generate(prompt, temperature=0.1, max_tokens=2000)
            parsed = self._parse_llm_json(raw)

            def clean(value: object) -> str:
                return self._sanitize_ascii(str(value))

            inconsistencies = [clean(i) for i in parsed.get("inconsistencies", []) if str(i).strip()]
            indicators = [clean(i) for i in parsed.get("fraud_indicators", []) if str(i).strip()]
            risk = clean(parsed.get("overall_risk", "")).title()
            if risk not in ("Low", "Medium", "High"):
                risk = None
            return {
                "inconsistencies": inconsistencies,
                "fraud_indicators": indicators,
                "overall_risk": risk,
                "summary": clean(parsed.get("summary", "")).strip(),
            }
        except Exception as e:
            logger.warning(f"LLM document analysis unavailable, falling back to rule engine: {e}")
            return empty

    def _sanitize_ascii(self, text: str) -> str:
        """Replace non-ASCII punctuation with ASCII equivalents so LLM text
        is safe for consoles and logs that use legacy encodings."""
        if not text:
            return text
        replacements = {
            "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
            "\u2014": "-", "\u00a0": " ", "\u202f": " ", "\u2009": " ",
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
            "\u2026": "...", "\u20b9": "Rs", "\u20bf": "Rs",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return text

    def _parse_llm_json(self, raw: str) -> dict:
        """Extract and parse a JSON object from an LLM response."""
        if not raw:
            return {}
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return {}

    def _get_recommendation(self, fraud_level: FraudLevel, indicators: list[str]) -> Recommendation:
        if fraud_level == FraudLevel.HIGH:
            return Recommendation.MANUAL_REVIEW
        elif fraud_level == FraudLevel.MEDIUM:
            if FraudIndicator.INCONSISTENT_DETAILS.value in indicators:
                return Recommendation.MANUAL_REVIEW
            if FraudIndicator.MISSING_DOCUMENTS.value in indicators:
                return Recommendation.REQUEST_DOCUMENTS
            return Recommendation.MANUAL_REVIEW
        return Recommendation.CONTINUE

    def _get_fraud_score(self, fraud_level: FraudLevel, risk_factors: list[str]) -> float:
        base_scores = {FraudLevel.LOW: 15, FraudLevel.MEDIUM: 50, FraudLevel.HIGH: 80}
        score = base_scores.get(fraud_level, 30)
        adjustment = min(len(risk_factors) * 3, 15)
        return float(min(score + adjustment, 100))

    def _build_similarity_blocks(self, claim: Claim, extracted_data: ClaimExtractedData,
                                 documents: list | None = None) -> list[str]:
        """Candidate texts for semantic matching, one block per content source.

        Blocks are embedded and scored independently (the best match across
        blocks wins) because mean-pooled embeddings dilute when a short
        structured loss description is concatenated with a long document
        narrative. Boilerplate fields (claim type/amount) are excluded, and
        the shared policy document is skipped so the policy does not add
        identical text to every claim."""
        blocks = []
        loss_parts = []
        if extracted_data.loss_description:
            loss_parts.append(f"Loss description: {extracted_data.loss_description}")
        elif claim.loss_description:
            loss_parts.append(f"Loss description: {claim.loss_description}")
        if extracted_data.cause_of_loss:
            loss_parts.append(f"Cause of loss: {extracted_data.cause_of_loss}")
        if loss_parts:
            blocks.append("\n".join(loss_parts))
        for doc in (documents or []):
            doc_type = getattr(doc, "document_type", None)
            doc_type_value = doc_type.value if hasattr(doc_type, "value") else str(doc_type)
            if doc_type_value == "Policy Document":
                continue
            text = getattr(doc, "extracted_text", "") or ""
            if text.strip():
                blocks.append(text.strip()[:2000])
        return blocks

    def _days_since(self, date_str: str) -> int | None:
        if not date_str:
            return None
        d = self._parse_date(date_str)
        if d is None:
            return None
        return max(0, (datetime.now() - d).days)

    def _days_between(self, start_str: str, end_str: str | None) -> int | None:
        """Days from a start date to an end date (loss/incident), else None."""
        start = self._parse_date(start_str)
        if start is None:
            return None
        end = self._parse_date(end_str) if end_str else None
        if end is None:
            return None
        return max(0, (end - start).days)

    def _parse_date(self, date_str: str):
        if not date_str:
            return None
        text = date_str.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d/%b/%Y", "%d %B %Y"):
            try:
                return datetime.strptime(text, fmt)
            except (ValueError, TypeError):
                continue
        return None

    def _explain_with_llm(self, assessment: FraudAssessment, claim: Claim, extracted_data: ClaimExtractedData):
        try:
            claim_info = (
                f"Claim: {claim.claim_id}, Type: {claim.claim_type.value if hasattr(claim.claim_type, 'value') else claim.claim_type}, "
                f"Amount: ₹{claim.claim_amount:,.0f}"
            )
            risk_factors_text = "; ".join(assessment.reasons)
            similar_text = "; ".join(
                f"{c['case_id']} (sim {c['similarity']:.0%})" for c in assessment.similar_cases
            ) or "None"
            triggered_text = "; ".join(assessment.triggered_rules) if assessment.triggered_rules else "None"
            prompt = self.prompts.load(
                "fraud_prompt.txt",
                claim_information=claim_info,
                fraud_level=assessment.fraud_level.value,
                fraud_factors=risk_factors_text,
                similar_cases=similar_text,
                triggered_rules=triggered_text,
                recommendation=assessment.recommendation.value,
                fraud_score=str(assessment.fraud_score),
            )
            llm_explanation = self.llm.generate(prompt)
            assessment.llm_explanation = llm_explanation
        except Exception as e:
            assessment.llm_explanation = (
                f"Fraud Screening Summary:\n"
                f"Fraud Level: {assessment.fraud_level.value} (Score: {assessment.fraud_score:.0f})\n"
                f"Confidence: {assessment.confidence_score:.0%}\n"
                f"Similarity to Historical Fraud Cases: {assessment.similarity_score:.0% if assessment.similarity_score else 'N/A'}\n"
                f"Triggered Rules: {'; '.join(assessment.triggered_rules) if assessment.triggered_rules else 'None'}\n"
                f"Fraud Factors: {'; '.join(assessment.reasons)}\n"
                f"Recommendation: {assessment.recommendation.value}\n"
                f"LLM explanation unavailable: {str(e)}"
            )
