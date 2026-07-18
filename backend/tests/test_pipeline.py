"""Smoke tests for the GTMScout pipeline.

Run from the backend/ directory:
    python -m tests.test_pipeline           # tools only (no OpenAI cost)
    python -m tests.test_pipeline --live     # full orchestrator (uses OpenAI)
"""
import sys
import json


def test_tools():
    print("=== tool: platform_data ===")
    from tools.platform_data import get_platform_interest
    r = get_platform_interest("Germany", "B2B SaaS")
    assert r["success"] and r["comparison"], "platform_data returned nothing"
    top = r["comparison"][0]
    print("top platform:", top, "| category:", r["category"])
    assert top["interest"] == 100, "top platform should normalize to 100"

    print("\n=== tool: worldbank (live or fallback) ===")
    from tools.worldbank import get_country_data
    wb = get_country_data("Japan")
    assert wb["success"], "worldbank failed"
    print("is_fallback:", wb["is_fallback"], "| population:",
          wb["data"]["population"]["value"])

    print("\n=== tool: worldbank (unknown country) ===")
    bad = get_country_data("Narnia")
    assert not bad["success"], "unknown country should fail cleanly"
    print("unknown-country handled:", bad["error"][:50])
    print("\nTOOL TESTS PASSED")


def test_orchestrator_live():
    print("\n=== orchestrator: market question (LIVE OpenAI) ===")
    from orchestrator import run_research
    msg = run_research("Is Germany good for a B2B SaaS with a $30k budget? US-based.")
    assert msg["kind"] == "report", f"expected report, got {msg['kind']}"
    r = msg["report"]
    for k in ["verdict", "confidence", "market_data", "platform_recommendations",
              "budget_allocation", "risks", "next_steps", "citations", "cost", "verification"]:
        assert k in r, f"missing key: {k}"
    assert abs(sum(b["amount"] for b in r["budget_allocation"]) - 30000) < 1, "budget must sum to total"
    print("verdict:", r["verdict"], "| confidence:", r["confidence"],
          "| cost $:", r["cost"]["usd"])

    print("\n=== orchestrator: clarification ===")
    msg2 = run_research("hello")
    assert msg2["kind"] == "text", "greeting should return a text clarification"
    print("clarify:", msg2["text"][:60])
    print("\nORCHESTRATOR TESTS PASSED")


if __name__ == "__main__":
    test_tools()
    if "--live" in sys.argv:
        test_orchestrator_live()
    else:
        print("\n(skipping live orchestrator tests — pass --live to run them)")
