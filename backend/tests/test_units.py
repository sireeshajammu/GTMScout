"""Offline unit tests — no API keys needed.  Run: python -m tests.test_units

Covers the deterministic logic the eval harness can't isolate: the safety gate,
country resolution (aliases/cities/ambiguity), and budget validation.
"""
from safety import is_blocked
from tools.worldbank import get_country_code, is_ambiguous, is_city
from orchestrator import _budget_issue, MIN_BUDGET, MAX_BUDGET


def test_safety_blocks_harmful():
    harmful = [
        "illegal weapons market in Brazil", "arms trafficking ring", "gun smuggling business",
        "sell illegal drugs in Mexico", "a drug cartel app", "human trafficking operation",
        "counterfeit goods store", "a ponzi scheme", "money laundering service",
    ]
    for t in harmful:
        assert is_blocked(t), f"should block: {t}"
    print(f"safety blocks {len(harmful)}/{len(harmful)} harmful inputs OK")


def test_safety_allows_legit():
    legit = [
        "a firearms retail store in Texas", "a cannabis dispensary in Singapore",
        "a consumer app in Brazil", "a fintech in Germany", "a pharmacy chain in India",
        "a defense contractor consultancy",
    ]
    for t in legit:
        assert not is_blocked(t), f"should NOT block: {t}"
    print(f"safety allows {len(legit)}/{len(legit)} legitimate inputs OK")


def test_country_resolution():
    cases = {
        "Ecuador": "ECU", "Russia": "RUS", "north korea": "PRK", "USA": "USA",
        "uk": "GBR", "Turkey": "TUR", "Vietnam": "VNM", "Dubai": "ARE",  # city -> country
        "Mumbai": "IND", "jp": "JPN", "Narnia": None, "": None,
    }
    for name, expected in cases.items():
        got = get_country_code(name)
        assert got == expected, f"{name!r} -> {got}, expected {expected}"
    print(f"country resolution {len(cases)}/{len(cases)} correct OK")


def test_ambiguity_and_cities():
    assert is_ambiguous("Congo"), "Congo should be ambiguous"
    assert is_ambiguous("Korea"), "Korea should be ambiguous"
    assert not is_ambiguous("Japan"), "Japan is unambiguous"
    assert is_city("Dubai") == "ARE"
    assert is_city("Japan") is None
    print("ambiguity + city detection OK")


def test_budget_validation():
    assert _budget_issue(5) and "at least" in _budget_issue(5)
    assert _budget_issue(MIN_BUDGET - 1) is not None
    assert _budget_issue(20000) is None
    assert _budget_issue(MAX_BUDGET + 1) is not None and "unusually large" in _budget_issue(MAX_BUDGET + 1)
    print("budget validation OK")


if __name__ == "__main__":
    test_safety_blocks_harmful()
    test_safety_allows_legit()
    test_country_resolution()
    test_ambiguity_and_cities()
    test_budget_validation()
    print("\nALL UNIT TESTS PASSED")
