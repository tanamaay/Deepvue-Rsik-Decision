import pytest
from app.policies.engine import evaluate_policy, evaluate_clause
from app.policies.definitions import get_policy


SAMPLE_CONTEXT = {
    "applied_on": "2026-02-20",
    "business": {
        "legal_name": "Saraswati Traders Private Limited",
        "pan": "AAFCS4321K",
        "gstin": "29AAFCS4321K1ZP",
        "registered_address": "No. 42, 3rd Cross, Peenya Industrial Area, Bengaluru 560058",
        "declared_annual_turnover_inr": 14500000,
        "sector": "wholesale_distribution",
    },
    "loan": {"amount_inr": 2500000, "tenure_months": 12, "purpose": "working_capital"},
    "unstructured": {
        "field_agent_note": "Mentioned a second unit in Tumkur that isn't on the GST record.",
        "document_text": "Date of Incorporation: 11 August 2023",
    },
    "upstream_data": {
        "gstin_status": "ACTIVE",
        "incorporation_date": "2023-08-11",
        "registered_address": "No. 42, 3rd Cross, Peenya Industrial Area, Bengaluru 560058",
        "annual_turnover_inr": 10200000,
        "days_since_last_filing": 41,
    },
    "upstream_failed": False,
    "extraction": {
        "incorporation_date": {"value": "2023-08-11", "grounded": True},
        "concerns": [{"description": "second unit in Tumkur not on GST record", "type": "undisclosed_unit"}],
    },
    "extraction_failed": False,
}


class TestPolicyEngine:
    def test_kaveri_3_1_sample_is_review(self):
        decision = evaluate_policy("kaveri", "3.1", SAMPLE_CONTEXT)
        assert decision["outcome"] in ("REVIEW", "REJECTED")
        clause_ids = [r["clause_id"] for r in decision["clause_results"]]
        assert "A1" in clause_ids

    def test_kaveri_3_2_more_lenient_incorporation(self):
        decision_31 = evaluate_policy("kaveri", "3.1", SAMPLE_CONTEXT)
        decision_32 = evaluate_policy("kaveri", "3.2", SAMPLE_CONTEXT)
        a1_31 = next(r for r in decision_31["clause_results"] if r["clause_id"] == "A1")
        a1_32 = next(r for r in decision_32["clause_results"] if r["clause_id"] == "A1")
        assert a1_31["status"] == "failed"
        assert a1_32["status"] == "passed"

    def test_nexa_more_lenient(self):
        decision = evaluate_policy("nexa", "1.4", SAMPLE_CONTEXT)
        assert decision["outcome"] in ("APPROVED", "REVIEW")

    def test_upstream_failure_kaveri_review(self):
        ctx = {**SAMPLE_CONTEXT, "upstream_failed": True, "upstream_data": None}
        decision = evaluate_policy("kaveri", "3.1", ctx)
        a7 = next(r for r in decision["clause_results"] if r["clause_id"] == "A7")
        assert a7["status"] == "failed"
        assert decision["outcome"] == "REVIEW"

    def test_excluded_sector_crypto(self):
        ctx = {
            **SAMPLE_CONTEXT,
            "extraction": {
                **SAMPLE_CONTEXT["extraction"],
                "sectors": [{"value": "virtual_digital_assets", "grounded": True}],
            },
        }
        decision = evaluate_policy("kaveri", "3.1", ctx)
        a8 = next(r for r in decision["clause_results"] if r["clause_id"] == "A8")
        assert a8["status"] == "failed"
        assert decision["outcome"] == "REJECTED"

    def test_nexa_crypto_not_excluded(self):
        ctx = {
            **SAMPLE_CONTEXT,
            "extraction": {
                **SAMPLE_CONTEXT["extraction"],
                "sectors": [{"value": "virtual_digital_assets", "grounded": True}],
            },
        }
        decision = evaluate_policy("nexa", "1.4", ctx)
        b8 = next(r for r in decision["clause_results"] if r["clause_id"] == "B8")
        assert b8["status"] == "passed"

    def test_deterministic(self):
        d1 = evaluate_policy("kaveri", "3.1", SAMPLE_CONTEXT)
        d2 = evaluate_policy("kaveri", "3.1", SAMPLE_CONTEXT)
        assert d1["outcome"] == d2["outcome"]
        for r1, r2 in zip(d1["clause_results"], d2["clause_results"]):
            assert r1["status"] == r2["status"]

    def test_loan_to_turnover_kaveri_fails(self):
        ctx = {**SAMPLE_CONTEXT, "loan": {**SAMPLE_CONTEXT["loan"], "amount_inr": 3000000}}
        decision = evaluate_policy("kaveri", "3.1", ctx)
        a4 = next(r for r in decision["clause_results"] if r["clause_id"] == "A4")
        assert a4["status"] == "failed"
        assert "29." in a4["reason"] or "exceeds" in a4["reason"]

    def test_clean_application_approves_nexa(self):
        from app.sample_data import VARIANTS
        from app.services.extraction import _extract_with_regex

        p = VARIANTS["clean_approve"]
        ex = _extract_with_regex(
            p["unstructured"]["field_agent_note"],
            p["unstructured"]["document_text"],
        )
        upstream = {
            **SAMPLE_CONTEXT["upstream_data"],
            "incorporation_date": "2020-08-11",
            "gstin": p["business"]["gstin"],
        }
        ctx = {
            "applied_on": p["applied_on"],
            "business": p["business"],
            "loan": p["loan"],
            "unstructured": p["unstructured"],
            "upstream_data": upstream,
            "upstream_failed": False,
            "extraction": {**ex["fields"], "concerns": ex["concerns"]},
            "extraction_failed": False,
        }
        assert evaluate_policy("nexa", "1.4", ctx)["outcome"] == "APPROVED"

    def test_clean_application_approves_kaveri_31(self):
        from app.sample_data import VARIANTS
        from app.services.extraction import _extract_with_regex

        p = VARIANTS["clean_approve"]
        ex = _extract_with_regex(
            p["unstructured"]["field_agent_note"],
            p["unstructured"]["document_text"],
        )
        upstream = {
            **SAMPLE_CONTEXT["upstream_data"],
            "incorporation_date": "2020-08-11",
            "gstin": p["business"]["gstin"],
        }
        ctx = {
            "applied_on": p["applied_on"],
            "business": p["business"],
            "loan": p["loan"],
            "unstructured": p["unstructured"],
            "upstream_data": upstream,
            "upstream_failed": False,
            "extraction": {**ex["fields"], "concerns": ex["concerns"]},
            "extraction_failed": False,
        }
        assert evaluate_policy("kaveri", "3.1", ctx)["outcome"] == "APPROVED"
