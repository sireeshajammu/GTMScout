"""Platform interest tool (serverless-friendly).

Returns a relative interest score (0-100) per social/marketing platform, weighted
by business category. Scores are a hand-tuned heuristic (not learned) informed by
public platform-usage and ad-spend patterns.

ROLE: this is now the BASELINE/FALLBACK. When live web research is available, the
PlatformAgent prefers platforms the research names as locally relevant (incl. ones
this table can't know — KakaoTalk, Naver, VK). This heuristic seeds a sensible
global floor and is the sole source only when research is off/thin. See
agents/platform_agent.py.

This deliberately replaced a pytrends-based tool, which pulled in pandas (heavy
serverless cold starts) and rate-limited constantly.
"""
import re
from typing import Dict, List

# Fuzzy matching for misspelled business types ("fintch" -> fintech). Optional dependency.
try:
    from rapidfuzz import process, fuzz
except Exception:  # noqa: BLE001
    process = None
    fuzz = None

# Base relative interest per platform (rough, generic baseline, 0-100).
_BASE = {
    "Instagram": 78, "TikTok": 72, "YouTube": 70, "Facebook": 68,
    "LinkedIn": 55, "WhatsApp": 66, "X (Twitter)": 50, "Google Search": 80,
    "Snapchat": 40, "Pinterest": 42, "Reddit": 38,
}

# Category multipliers — how well each platform fits a business type.
_CATEGORY_WEIGHTS = {
    "fast fashion":      {"Instagram": 1.30, "TikTok": 1.28, "Pinterest": 1.25, "YouTube": 1.05, "LinkedIn": 0.35},
    "consumer app":      {"Instagram": 1.25, "TikTok": 1.30, "YouTube": 1.10, "Facebook": 1.05, "LinkedIn": 0.40},
    "e-commerce":        {"Instagram": 1.22, "Facebook": 1.18, "Google Search": 1.25, "TikTok": 1.15, "LinkedIn": 0.45},
    "b2b saas":          {"LinkedIn": 1.55, "Google Search": 1.30, "YouTube": 1.05, "X (Twitter)": 1.10, "Instagram": 0.55, "TikTok": 0.35},
    "fintech":           {"LinkedIn": 1.30, "Google Search": 1.25, "YouTube": 1.10, "X (Twitter)": 1.15, "Instagram": 0.85},
    "food & beverage":   {"Instagram": 1.28, "TikTok": 1.25, "Facebook": 1.10, "Pinterest": 1.10, "LinkedIn": 0.35},
    "gaming":            {"YouTube": 1.35, "TikTok": 1.25, "X (Twitter)": 1.20, "Reddit": 1.20, "LinkedIn": 0.30},
    "skincare":          {"Instagram": 1.32, "TikTok": 1.28, "YouTube": 1.12, "Pinterest": 1.15, "LinkedIn": 0.35},
    "general":           {},
}

# Country nudges for platforms with notably different local footprints.
_COUNTRY_NUDGES = {
    "japan": {"LINE": 90, "X (Twitter)": 68, "YouTube": 74},
    "brazil": {"WhatsApp": 85, "Instagram": 88, "TikTok": 84},
    "germany": {"XING": 55, "LinkedIn": 78, "WhatsApp": 72},
    "china": {"WeChat": 95, "Douyin": 92, "Instagram": 10, "Facebook": 8},
    "india": {"WhatsApp": 88, "YouTube": 85, "Instagram": 80},
    "usa": {"Instagram": 82, "TikTok": 78, "X (Twitter)": 60},
}


# Keyword -> category anchors, reused for exact synonym hits and fuzzy fallback.
_BUSINESS_ANCHORS = {
    "saas": "b2b saas", "software": "b2b saas", "b2b": "b2b saas", "enterprise": "b2b saas",
    "app": "consumer app", "mobile": "consumer app",
    "shop": "e-commerce", "store": "e-commerce", "commerce": "e-commerce",
    "ecommerce": "e-commerce", "retail": "e-commerce", "dtc": "e-commerce", "d2c": "e-commerce",
    "fashion": "fast fashion", "apparel": "fast fashion", "clothing": "fast fashion",
    "fintech": "fintech", "finance": "fintech", "banking": "fintech", "payments": "fintech",
    "food": "food & beverage", "restaurant": "food & beverage",
    "beverage": "food & beverage", "drink": "food & beverage",
    "game": "gaming", "gaming": "gaming",
    "skincare": "skincare", "beauty": "skincare", "cosmetic": "skincare", "cosmetics": "skincare",
}
_ANCHOR_KEYS = list(_BUSINESS_ANCHORS.keys())


def _match_category(business_type: str) -> str:
    bt = (business_type or "").lower()
    for key in _CATEGORY_WEIGHTS:
        if key != "general" and key in bt:
            return key
    # exact synonym hit
    for anchor, category in _BUSINESS_ANCHORS.items():
        if anchor in bt:
            return category
    # fuzzy fallback for misspellings ("fintch", "gamng", "skincre")
    if process is not None:
        for word in re.findall(r"[a-z]{4,}", bt):
            match = process.extractOne(word, _ANCHOR_KEYS, scorer=fuzz.ratio)
            if match and match[1] >= 82:
                return _BUSINESS_ANCHORS[match[0]]
    return "general"


def get_platform_interest(country: str, business_type: str, top_n: int = 6) -> Dict:
    """
    Return a ranked comparison of platform interest for a country + business type.

    Returns:
        {"success": True, "category": str, "comparison": [{"platform","interest"}...],
         "source": "GTMScout interest model"}
    """
    category = _match_category(business_type)
    weights = _CATEGORY_WEIGHTS.get(category, {})
    nudges = _COUNTRY_NUDGES.get((country or "").lower().strip(), {})

    scores: Dict[str, float] = {}
    for platform, base in _BASE.items():
        w = weights.get(platform, 1.0)
        scores[platform] = base * w
    # country-specific platforms / overrides
    for platform, val in nudges.items():
        w = weights.get(platform, 1.0)
        scores[platform] = val * w

    # normalize so the top platform reads ~ its raw score capped at 100
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    if not ranked:
        return {"success": False, "error": "No platform data", "country": country}
    top = ranked[0][1]
    comparison = [
        {"platform": p, "interest": max(1, min(100, round(v / top * 100)))}
        for p, v in ranked
    ]
    return {
        "success": True,
        "country": country,
        "business_type": business_type,
        "category": category,
        "comparison": comparison,
        "source": "GTMScout heuristic interest model (hand-tuned weights, relative signal 0-100 — not learned)",
    }
