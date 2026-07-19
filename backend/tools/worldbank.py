"""World Bank data tool.

Fetches live economic + demographic indicators. Fast (concurrent requests, no
sleeps) and resilient: if the API is slow or unreachable, falls back to curated
recent figures so the pipeline never hard-fails (important on serverless).
"""
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

# All ~249 countries, precomputed offline from ISO-3166 (see scripts/generate_country_codes.py).
# Loaded once at import — a single ~19KB module, no runtime API fetch, no cold-start cost.
from country_codes_data import COUNTRY_INDEX

WORLDBANK_API = "https://api.worldbank.org/v2/country"
REQUEST_TIMEOUT = 10  # seconds per indicator

# Colloquial shorthands the official ISO names don't cover. These win over COUNTRY_INDEX.
COUNTRY_ALIASES = {
    "usa": "USA", "us": "USA", "u.s.": "USA", "u.s.a.": "USA", "america": "USA",
    "uk": "GBR", "u.k.": "GBR", "britain": "GBR", "great britain": "GBR", "england": "GBR",
    "uae": "ARE", "emirates": "ARE",
    "russia": "RUS", "south korea": "KOR", "north korea": "PRK", "korea": "KOR",
    "turkey": "TUR", "vietnam": "VNM", "iran": "IRN", "syria": "SYR", "laos": "LAO",
    "brunei": "BRN", "bolivia": "BOL", "venezuela": "VEN", "tanzania": "TZA",
    "moldova": "MDA", "czech republic": "CZE", "czechia": "CZE", "ivory coast": "CIV",
    "cape verde": "CPV", "swaziland": "SWZ", "eswatini": "SWZ", "burma": "MMR", "myanmar": "MMR",
    "drc": "COD", "dr congo": "COD", "democratic republic of congo": "COD", "congo": "COG",
    "taiwan": "TWN", "palestine": "PSE", "hong kong": "HKG", "macau": "MAC", "macao": "MAC",
    "brasil": "BRA", "deutschland": "DEU",
}

INDICATORS = {
    "internet_users_percent": "IT.NET.USER.ZS",
    "mobile_subscriptions_percent": "IT.CEL.SETS.P2",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "population": "SP.POP.TOTL",
}

# Curated fallback (approx. recent values) used only if the live API fails.
FALLBACK = {
    "JPN": {"population": 124500000, "gdp_per_capita": 33800, "internet_users_percent": 93, "mobile_subscriptions_percent": 161},
    "USA": {"population": 334900000, "gdp_per_capita": 81600, "internet_users_percent": 97, "mobile_subscriptions_percent": 110},
    "BRA": {"population": 216400000, "gdp_per_capita": 9670, "internet_users_percent": 84, "mobile_subscriptions_percent": 113},
    "DEU": {"population": 84500000, "gdp_per_capita": 52700, "internet_users_percent": 96, "mobile_subscriptions_percent": 127},
    "IND": {"population": 1428600000, "gdp_per_capita": 2480, "internet_users_percent": 46, "mobile_subscriptions_percent": 82},
    "CHN": {"population": 1410700000, "gdp_per_capita": 12610, "internet_users_percent": 77, "mobile_subscriptions_percent": 121},
    "GBR": {"population": 68300000, "gdp_per_capita": 48900, "internet_users_percent": 96, "mobile_subscriptions_percent": 118},
    "FRA": {"population": 68200000, "gdp_per_capita": 44700, "internet_users_percent": 93, "mobile_subscriptions_percent": 111},
    "CAN": {"population": 40800000, "gdp_per_capita": 53400, "internet_users_percent": 93, "mobile_subscriptions_percent": 92},
    "MEX": {"population": 128500000, "gdp_per_capita": 11500, "internet_users_percent": 78, "mobile_subscriptions_percent": 100},
}


# Major business cities -> their country (so "Dubai"/"Mumbai" resolve instead of failing).
CITY_TO_COUNTRY = {
    "dubai": "ARE", "abu dhabi": "ARE", "mumbai": "IND", "delhi": "IND", "new delhi": "IND",
    "bangalore": "IND", "bengaluru": "IND", "shanghai": "CHN", "beijing": "CHN", "shenzhen": "CHN",
    "sao paulo": "BRA", "são paulo": "BRA", "rio de janeiro": "BRA", "tokyo": "JPN", "osaka": "JPN",
    "lagos": "NGA", "nairobi": "KEN", "istanbul": "TUR", "moscow": "RUS", "paris": "FRA",
    "berlin": "DEU", "london": "GBR", "madrid": "ESP", "milan": "ITA", "toronto": "CAN",
    "new york": "USA", "los angeles": "USA", "san francisco": "USA", "mexico city": "MEX",
    "buenos aires": "ARG", "jakarta": "IDN", "bangkok": "THA", "seoul": "KOR", "sydney": "AUS",
}

# Names that map to more than one country — ask instead of guessing.
AMBIGUOUS = {
    "congo": "the Democratic Republic of the Congo or the Republic of the Congo",
    "korea": "South Korea or North Korea",
    "georgia": "the country Georgia or the US state",
    "guinea": "Guinea, Guinea-Bissau, or Equatorial Guinea",
}


def is_ambiguous(country_name: str) -> Optional[str]:
    """If the name is ambiguous, return a clarifying hint; else None."""
    return AMBIGUOUS.get((country_name or "").lower().strip())


def is_city(country_name: str) -> Optional[str]:
    """If the name is a known city, return its country code; else None."""
    return CITY_TO_COUNTRY.get((country_name or "").lower().strip())


def get_country_code(country_name: str) -> Optional[str]:
    """Resolve a country name / ISO-2 / ISO-3 / major city to a World Bank ISO-3 code.
    Aliases first (colloquial shorthands), then the ISO-3166 index, then major cities."""
    n = (country_name or "").lower().strip()
    return COUNTRY_ALIASES.get(n) or COUNTRY_INDEX.get(n) or CITY_TO_COUNTRY.get(n)


def _fetch_indicator(country_code: str, indicator_code: str) -> Dict:
    """Fetch the most recent non-null value for one indicator, with one retry."""
    url = (
        f"{WORLDBANK_API}/{country_code}/indicator/{indicator_code}"
        f"?format=json&per_page=5&mrnev=1"
    )
    last_err = None
    for attempt in range(2):  # one retry — WB can be transiently slow
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "GTMScout/1.0"})
            resp.raise_for_status()
            result = resp.json()
            if len(result) > 1 and result[1]:
                for row in result[1]:
                    if row.get("value") is not None:
                        return {"value": float(row["value"]), "year": row.get("date"), "source": "World Bank"}
            return {"value": None, "source": "World Bank", "note": "No data available"}
        except Exception as e:  # noqa: BLE001
            last_err = e
    return {"value": None, "error": str(last_err)}


def get_country_data(country_name: str) -> Dict:
    """
    Fetch economic and demographic data for a country from the World Bank API.

    Resilient per-indicator: each indicator is fetched independently, and only the
    ones that fail fall back to curated values (previously a single failed request
    dumped ALL indicators to fallback — that was why production kept showing cached
    data). `is_fallback` is True only if at least one indicator used a fallback value.
    """
    country_code = get_country_code(country_name)
    if not country_code:
        return {
            "success": False,
            "error": f"I couldn't recognize '{country_name}' as a country. "
            "If it's a city, tell me the country instead; otherwise check the spelling.",
            "country": country_name,
        }

    data = {
        "country": country_name,
        "country_code": country_code,
        "success": True,
        "data": {},
        "is_fallback": False,
    }
    fb = FALLBACK.get(country_code, {})

    # Fetch all indicators concurrently.
    live: Dict[str, Dict] = {}
    try:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {
                name: ex.submit(_fetch_indicator, country_code, code)
                for name, code in INDICATORS.items()
            }
            for name, fut in futures.items():
                live[name] = fut.result()
    except Exception:
        live = {}

    for name in INDICATORS:
        got = live.get(name) or {}
        if got.get("value") is not None:
            data["data"][name] = got
        elif name in fb:
            data["data"][name] = {"value": float(fb[name]), "year": "recent", "source": "World Bank (cached)"}
            data["is_fallback"] = True
        else:
            data["data"][name] = {"value": None, "source": "World Bank", "note": "No data available"}

    # If we have no numbers at all and no fallback, report failure.
    if all(v.get("value") is None for v in data["data"].values()):
        return {
            "success": False,
            "error": "World Bank API unavailable and no fallback data for this country.",
            "country": country_name,
        }
    return data
