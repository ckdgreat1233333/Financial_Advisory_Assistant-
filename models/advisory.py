"""Data models for the Personalized Financial Advisory Assistant."""
from dataclasses import dataclass, field


@dataclass
class KBChunk:
    """A clause-level chunk of a knowledge-base document with provenance."""
    chunk_id: str
    text: str
    clause_ref: str
    document_id: str
    title: str
    category: str = ""
    version: str = "v1.0"


@dataclass
class RetrievedChunk:
    """A retrieved chunk together with its similarity score."""
    chunk: KBChunk
    similarity: float


@dataclass
class CustomerProfile:
    """A customer's raw attributes enriched with derived behavioural features."""
    customer_id: str
    name: str
    age: int
    city: str = ""
    occupation: str = ""
    employment_type: str = ""
    annual_income: float = 0.0
    monthly_income: float = 0.0
    marital_status: str = ""
    dependents: int = 0
    kyc_status: str = "verified"
    stated_risk_appetite: str = ""
    investment_horizon_months: int = 0
    goals: list[str] = field(default_factory=list)
    has_loan: bool = False
    savings_balance: float = 0.0
    existing_products: list[str] = field(default_factory=list)

    savings_rate: float = 0.0
    monthly_surplus: float = 0.0
    sip_ratio: float = 0.0
    emi_burden: float = 0.0
    lifestyle_ratio: float = 0.0
    emergency_buffer_months: float = 0.0
    investing_activity_score: float = 0.0
    computed_risk_capacity: str = "moderate"
    risk_alignment_note: str = ""
    life_stage: str = ""
    protection_gap: bool = False
    first_time_investor: bool = False
    segment: str = ""

    def summary_text(self) -> str:
        """Natural-language profile used for embeddings and LLM context."""
        goals = ", ".join(self.goals) or "no stated goal"
        holdings = ", ".join(self.existing_products) if self.existing_products else "none"
        return (
            f"{self.name}, {self.age}, {self.occupation} in {self.city}. "
            f"Annual income Rs {self.annual_income:,.0f}; monthly surplus about "
            f"Rs {self.monthly_surplus:,.0f}; savings rate {self.savings_rate:.0%}. "
            f"{self.marital_status.capitalize()} with {self.dependents} dependent(s); "
            f"loan present: {'yes' if self.has_loan else 'no'}; KYC {self.kyc_status}. "
            f"Investment horizon {self.investment_horizon_months} months; stated risk appetite "
            f"'{self.stated_risk_appetite}'; computed risk capacity '{self.computed_risk_capacity}'. "
            f"Goals: {goals}. Emergency buffer covers {self.emergency_buffer_months:.1f} months of expenses. "
            f"Existing holdings: {holdings}. Life stage: {self.life_stage}."
        )

    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "age": self.age,
            "city": self.city,
            "occupation": self.occupation,
            "employment_type": self.employment_type,
            "annual_income": self.annual_income,
            "monthly_income": self.monthly_income,
            "marital_status": self.marital_status,
            "dependents": self.dependents,
            "kyc_status": self.kyc_status,
            "stated_risk_appetite": self.stated_risk_appetite,
            "investment_horizon_months": self.investment_horizon_months,
            "goals": self.goals,
            "has_loan": self.has_loan,
            "savings_balance": self.savings_balance,
            "existing_products": self.existing_products,
            "savings_rate": round(self.savings_rate, 4),
            "monthly_surplus": round(self.monthly_surplus, 2),
            "sip_ratio": round(self.sip_ratio, 4),
            "emi_burden": round(self.emi_burden, 4),
            "lifestyle_ratio": round(self.lifestyle_ratio, 4),
            "emergency_buffer_months": round(self.emergency_buffer_months, 2),
            "investing_activity_score": round(self.investing_activity_score, 3),
            "computed_risk_capacity": self.computed_risk_capacity,
            "risk_alignment_note": self.risk_alignment_note,
            "life_stage": self.life_stage,
            "protection_gap": self.protection_gap,
            "first_time_investor": self.first_time_investor,
            "segment": self.segment,
        }


@dataclass
class ProductCandidate:
    """A product evaluated by the suitability engine for one customer.
    verdict is one of: eligible | escalate | blocked."""
    product_id: str
    name: str
    category: str
    asset_class: str
    risk_level: str
    verdict: str
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    citation_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "category": self.category,
            "asset_class": self.asset_class,
            "risk_level": self.risk_level,
            "verdict": self.verdict,
            "score": round(self.score, 3),
            "reasons": self.reasons,
            "warnings": self.warnings,
            "citation_refs": self.citation_refs,
        }


@dataclass
class AdvisoryResponse:
    """A structured, traceable advisory answer for either track.
    track is 'rm' (internal decision support) or 'customer'."""
    track: str
    customer_id: str
    question: str
    answered: bool
    profile_summary: str = ""
    segment: str = ""
    recommendations: list[ProductCandidate] = field(default_factory=list)
    narrative: str = ""
    goal: str | None = None
    amount: float | None = None
    confidence: float = 0.0
    disclaimers: list[str] = field(default_factory=list)
    needs_human_override: bool = False
    escalation_reason: str | None = None
    compliance_notes: list[str] = field(default_factory=list)
    retrieved_refs: list[str] = field(default_factory=list)

    def to_dict(self, include_retrieved: bool = True) -> dict:
        return {
            "track": self.track,
            "customer_id": self.customer_id,
            "question": self.question,
            "goal": self.goal,
            "amount": self.amount,
            "answered": self.answered,
            "profile_summary": self.profile_summary,
            "segment": self.segment,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "narrative": self.narrative,
            "confidence": round(self.confidence, 3),
            "disclaimers": self.disclaimers,
            "needs_human_override": self.needs_human_override,
            "escalation_reason": self.escalation_reason,
            "compliance_notes": self.compliance_notes,
            "retrieved_refs": self.retrieved_refs if include_retrieved else [],
        }
