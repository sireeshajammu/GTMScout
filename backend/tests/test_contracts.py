"""Contract tests — run without any API keys:  python -m tests.test_contracts"""
from contracts import validate_report, StrategyAgentOut, PlatformRec


def _sample_report():
    return {
        "id": "rep_x", "request": {"target_country": "Brazil", "business_type": "consumer app"},
        "verdict": "GO", "confidence": 72, "executive_summary": "…",
        "market_data": {"population": 2.1e8, "gdp_per_capita": 10713, "internet_penetration": 84.5,
                        "mobile_subscriptions": 101.9, "data_year": "2025"},
        "platform_recommendations": [{"platform": "Instagram", "interest_score": 100, "rank": 1, "rationale": "x"}],
        "budget_allocation": [{"platform": "Instagram", "percentage": 50.0, "amount": 7500.0}],
        "risks": [{"title": "LGPD", "severity": "medium", "description": "…"}],
        "next_steps": ["localize"], "citations": [{"id": 1, "source": "World Bank", "detail": "…", "url": None}],
        "cost": {"total_tokens_in": 1, "total_tokens_out": 1, "usd": 0.0, "per_agent": []},
        "verification": {"checked": True, "flags": [], "note": "ok"},
    }


def test_valid_report_passes():
    r = validate_report(_sample_report())
    assert r.verdict == "GO" and r.market_data.internet_penetration == 84.5
    print("valid report passes ✔".replace("✔", "OK"))


def test_invalid_report_rejected():
    bad = _sample_report()
    del bad["verdict"]  # required field missing
    try:
        validate_report(bad)
        raise AssertionError("expected validation to fail")
    except Exception as e:
        assert "verdict" in str(e)
        print("invalid report rejected OK")


def test_agent_contract():
    out = StrategyAgentOut.model_validate({
        "verdict": "NOT YET", "confidence": 40, "executive_summary": "…",
        "budget_allocation": [], "risks": [], "next_steps": [], "junk_field": "ignored",
    })
    assert out.verdict == "NOT YET"
    PlatformRec.model_validate({"platform": "TikTok", "interest_score": 90, "rank": 2})
    print("agent contracts OK")


if __name__ == "__main__":
    test_valid_report_passes()
    test_invalid_report_rejected()
    test_agent_contract()
    print("\nALL CONTRACT TESTS PASSED")
