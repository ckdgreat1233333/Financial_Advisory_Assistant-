"""Tests for the Personalized Financial Advisory Assistant.

Covers: profile builder features, segmentation determinism, product store
grounding, suitability guardrail paths (KYC gate, risk-grade blocks,
escalations, lock-in blocks, affordability), concentration cap,
non-promissory scrubbing, and advisory service track behavior.
"""
import os

os.environ.setdefault("GROQ_API_KEY", "dummy-test-key")

import pytest

import database.db as db
from models.advisory import CustomerProfile
from profiling.profile_builder import ProfileBuilder
from guardrails.suitability import SuitabilityEngine, apply_concentration_cap
from guardrails.compliance import enforce_non_promissory, CUSTOMER_DISCLAIMERS


@pytest.fixture(scope="module")
def products():
    conn = db.get_db()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@pytest.fixture(scope="module")
def engine():
    return SuitabilityEngine()


@pytest.fixture(scope="module")
def profiles():
    pb = ProfileBuilder()
    return pb.build_all()


def _profile_by_appetite(profiles, appetite):
    for p in profiles.values():
        if p.stated_risk_appetite == appetite and p.kyc_status == "verified":
            return p
    raise AssertionError(f"no verified {appetite} customer found")


def _product(products, pid):
    return next(p for p in products if p["product_id"] == pid)


# ── Profile builder ────────────────────────────────────────

def test_profile_builder_derives_features():
    pb = ProfileBuilder()
    p = pb.build("CUST0001")
    assert 0 <= p.savings_rate <= 1 or p.savings_rate < 0
    assert p.life_stage in ("early_career", "family_formation", "wealth_building",
                            "pre_retirement", "retirement")
    assert p.computed_risk_capacity in ("conservative", "moderate", "aggressive")
    assert isinstance(p.goals, list) and len(p.goals) > 0
    assert p.summary_text().startswith("Bhavna")


def test_profile_unknown_customer_raises():
    with pytest.raises(ValueError):
        ProfileBuilder().build("NOPE0000")


def test_binding_profile_is_more_conservative(profiles):
    eng = SuitabilityEngine()
    p = _profile_by_appetite(profiles, "aggressive")
    p.computed_risk_capacity = "conservative"
    assert eng.binding_profile(p) == "conservative"
    p.computed_risk_capacity = "aggressive"
    assert eng.binding_profile(p) == "aggressive"


def test_summary_mentions_holdings(profiles):
    p = next(iter(profiles.values()))
    text = p.summary_text().lower()
    assert "existing holdings" in text
    assert "life stage" in text


# ── Segmentation ───────────────────────────────────────────

def test_segmentation_assigns_every_customer(profiles):
    from profiling.segmentation import CustomerSegmenter
    seg = CustomerSegmenter(k=5).fit(profiles)
    assert len(seg.labels) == len(profiles)
    assert all(v for v in seg.labels.values())


def test_segmentation_deterministic_labels(profiles):
    from profiling.segmentation import CustomerSegmenter
    s1 = CustomerSegmenter(k=5).fit(profiles)
    labels1 = dict(s1.labels)
    s2 = CustomerSegmenter(k=5).fit(profiles)
    labels2 = dict(s2.labels)
    assert labels1 == labels2


def test_segment_labels_unique_across_clusters(profiles):
    from profiling.segmentation import CustomerSegmenter
    seg = CustomerSegmenter(k=5).fit(profiles)
    summary_labels = [c["label"] for c in seg.cluster_summaries]
    assert len(summary_labels) == len(set(summary_labels))


# ── Product knowledge store ────────────────────────────────

def test_product_store_grounding():
    from advisory.product_store import ProductKnowledgeStore
    store = ProductKnowledgeStore()
    assert len(store.chunks) >= 13 * 5
    results = store.retrieve_for_product("prod_ppf", "lock-in withdrawal rules", k=2)
    assert results
    assert all(r.chunk.document_id == "prod_ppf" for r in results)


def test_product_store_only_product_documents():
    from advisory.product_store import ProductKnowledgeStore
    store = ProductKnowledgeStore()
    doc_ids = {c.document_id for c in store.chunks}
    assert doc_ids and all(d.startswith("prod_") for d in doc_ids)


# ── Suitability engine / mis-selling guardrails ────────────

def test_kyc_gate_blocks_everything(profiles, products, engine):
    p = next(p for p in profiles.values() if p.kyc_status != "verified")
    cands = engine.evaluate(p, products, goal="wealth")
    assert all(c.verdict == "blocked" for c in cands)
    assert any("KYC" in (c.warnings[0] if c.warnings else "") for c in cands)


def test_conservative_high_risk_blocked_with_sebi_citation(profiles, products, engine):
    p = _profile_by_appetite(profiles, "conservative")
    p.computed_risk_capacity = "conservative"
    p.investment_horizon_months = max(p.investment_horizon_months, 60)
    cands = engine.evaluate(p, products, goal="wealth")
    equity = [c for c in cands if c.product_id == "prod_index_sip"][0]
    assert equity.verdict == "blocked"
    assert any("sebi" in ref for ref in equity.citation_refs)


def test_first_time_investor_high_risk_escalates(profiles, products, engine):
    p = _profile_by_appetite(profiles, "aggressive")
    p.first_time_investor = True
    cands = engine.evaluate(p, products, goal="wealth")
    equity = [c for c in cands if c.product_id == "prod_largecap"][0]
    assert equity.verdict == "escalate"


def test_lockin_exceeding_horizon_blocks(profiles, products, engine):
    p = _profile_by_appetite(profiles, "conservative")
    p.investment_horizon_months = 24
    cands = engine.evaluate(p, products)
    ppf = [c for c in cands if c.product_id == "prod_ppf"][0]
    assert ppf.verdict == "blocked"
    assert any("Lock-in" in r for r in ppf.reasons)


def test_amount_below_minimum_blocks(profiles, products, engine):
    p = _profile_by_appetite(profiles, "conservative")
    cands = engine.evaluate(p, products, amount=100)
    fd = [c for c in cands if c.product_id == "prod_fd"][0]
    assert fd.verdict == "blocked"


def test_low_risk_products_eligible_for_conservative(profiles, products, engine):
    p = _profile_by_appetite(profiles, "conservative")
    p.investment_horizon_months = max(p.investment_horizon_months, 36)
    cands = engine.evaluate(p, products, goal="safety")
    fd = [c for c in cands if c.product_id == "prod_fd"][0]
    sweep = [c for c in cands if c.product_id == "prod_sweep"][0]
    assert fd.verdict == "eligible"
    assert sweep.verdict == "eligible"
    assert fd.score > 0


def test_senior_high_risk_escalation(profiles, products, engine):
    p = _profile_by_appetite(profiles, "aggressive")
    p.age = 67
    p.first_time_investor = False
    cands = engine.evaluate(p, products, goal="wealth")
    equity = [c for c in cands if c.risk_level == "high" and c.category == "equity_fund"]
    assert any(c.verdict == "escalate" for c in equity)
    assert any("Senior citizen" in w for c in equity for w in c.warnings)


def test_protection_gap_warning_added(profiles, products, engine):
    p = _profile_by_appetite(profiles, "conservative")
    p.protection_gap = True
    p.existing_products = []
    cands = engine.evaluate(p, products, goal="safety")
    fd = [c for c in cands if c.product_id == "prod_fd"][0]
    assert any("Protection gap" in w for w in fd.warnings)


def test_goal_mismatch_warns(profiles, products, engine):
    p = _profile_by_appetite(profiles, "conservative")
    cands = engine.evaluate(p, products, goal="retirement")
    rd = [c for c in cands if c.product_id == "prod_rd"][0]
    assert rd.verdict == "eligible"
    assert any("does not target" in w for w in rd.warnings)


def test_concentration_cap_limits_per_class():
    def mk(pid, cat, score):
        from models.advisory import ProductCandidate
        return ProductCandidate(product_id=pid, name=pid, category=cat, asset_class="x",
                                risk_level="low", verdict="eligible", score=score)
    cands = [mk(f"e{i}", "equity_fund", 0.9 - i * 0.01) for i in range(4)]
    picked = apply_concentration_cap(cands, cap_per_class=2, top_n=5)
    assert len(picked) == 2


# ── Non-promissory compliance scrubber ─────────────────────

def test_scrubber_removes_guaranteed_claims():
    text = "This fund gives guaranteed returns and is risk-free."
    clean, violations = enforce_non_promissory(text)
    assert "guaranteed returns" not in clean.lower()
    assert "risk-free" not in clean.lower()
    assert len(violations) >= 2


def test_scrubber_softens_definitive_instructions():
    clean, violations = enforce_non_promissory("You must invest now before the market rises.")
    assert "you must invest" not in clean.lower()
    assert violations


def test_clean_text_passes_through():
    clean, violations = enforce_non_promissory(
        "One option is a recurring deposit; it offers stable but modest growth.")
    assert clean == "One option is a recurring deposit; it offers stable but modest growth."
    assert violations == []


def test_customer_disclaimers_present():
    assert len(CUSTOMER_DISCLAIMERS) == 3
    joined = " ".join(CUSTOMER_DISCLAIMERS).lower()
    assert "not constitute investment advice" in joined
    assert "never guaranteed" in joined


# ── Advisory service tracks ────────────────────────────────

@pytest.fixture(scope="module")
def advisory():
    from services.advisory_service import AdvisoryService
    svc = AdvisoryService()
    yield svc
    import database.db as dbm
    conn = dbm.get_db()
    conn.execute("DELETE FROM advisory_sessions WHERE session_id LIKE 'ADV-%'")
    conn.execute("DELETE FROM audit_logs WHERE eventType IN "
                 "('RM Advisory Query','Customer Goal Guidance','Customer Profile View')")
    conn.commit()
    conn.close()


def test_rm_track_structure(advisory):
    res = advisory.rm_query("CUST0002", "Which products fit for wealth?", actor="pytest")
    d = res.to_dict()
    assert d["track"] == "rm"
    assert d["answered"]
    assert d["profile_summary"]
    assert d["segment"]
    assert isinstance(d["recommendations"], list)
    assert len(d["disclaimers"]) == 1


def test_rm_track_never_recommends_blocked(advisory):
    res = advisory.rm_query("CUST0004", "Any equity suggestions?", actor="pytest")
    for rec in res.recommendations:
        assert rec.verdict in ("eligible", "escalate")


def test_customer_track_hides_internal_data(advisory):
    res = advisory.customer_goal("CUST0004", "education", amount=25000)
    d = res.to_dict(include_retrieved=False)
    assert d["track"] == "customer"
    assert d["retrieved_refs"] == []
    assert len(d["disclaimers"]) == 3
    for rec in d["recommendations"]:
        assert rec["verdict"] == "eligible"
        assert rec["risk_level"] != "high" or any(
            "not guaranteed" in w for w in rec["warnings"])


def test_sessions_logged(advisory):
    advisory.rm_query("CUST0001", "log check", actor="pytest")
    sessions = db.list_advisory_sessions(limit=10)
    assert sessions
    assert any(s["actor"] == "pytest" for s in sessions)


def test_response_serializable(advisory):
    import json
    res = advisory.customer_goal("CUST0002", "retirement")
    payload = json.dumps(res.to_dict())
    assert '"track": "customer"' in payload
