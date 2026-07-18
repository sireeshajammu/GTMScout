"""World Bank data tool.

Fetches live economic + demographic indicators. Fast (concurrent requests, no
sleeps) and resilient: if the API is slow or unreachable, falls back to curated
recent figures so the pipeline never hard-fails (important on serverless).
"""
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

WORLDBANK_API = "https://api.worldbank.org/v2/country"
REQUEST_TIMEOUT = 10  # seconds per indicator

# Name -> World Bank ISO3 code
COUNTRY_CODES = {
    "japan": "JPN", "usa": "USA", "united states": "USA", "us": "USA",
    "brazil": "BRA", "brasil": "BRA", "germany": "DEU", "deutschland": "DEU",
    "india": "IND", "china": "CHN", "uk": "GBR", "united kingdom": "GBR",
    "france": "FRA", "canada": "CAN", "mexico": "MEX", "australia": "AUS",
    "indonesia": "IDN", "nigeria": "NGA", "south korea": "KOR", "korea": "KOR",
    "italy": "ITA", "spain": "ESP", "netherlands": "NLD", "sweden": "SWE",
    "singapore": "SGP", "uae": "ARE", "united arab emirates": "ARE",
    "saudi arabia": "SAU", "south africa": "ZAF", "argentina": "ARG",
    "vietnam": "VNM", "thailand": "THA", "philippines": "PHL", "poland": "POL",
    "turkey": "TUR", "egypt": "EGY", "colombia": "COL", "chile": "CHL",
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


def get_country_code(country_name: str) -> Optional[str]:
    return COUNTRY_CODES.get(country_name.lower().strip())


def _fetch_indicator(country_code: str, indicator_code: str) -> Dict:
    """Fetch the most recent non-null value for one indicator."""
    url = (
        f"{WORLDBANK_API}/{country_code}/indicator/{indicator_code}"
        f"?format=json&per_page=5&mrnev=1"
    )
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    result = resp.json()
    if len(result) > 1 and result[1]:
        for row in result[1]:
            if row.get("value") is not None:
                return {"value": float(row["value"]), "year": row.get("date"), "source": "World Bank"}
    return {"value": None, "source": "World Bank", "note": "No data available"}


def get_country_data(country_name: str) -> Dict:
    """
    Fetch economic and demographic data for a country from the World Bank API.
    Falls back to curated figures if the live API is unavailable.
    """
    country_code = get_country_code(country_name)
    if not country_code:
        return {
            "success": False,
            "error": f"Country '{country_name}' is not supported yet.",
            "country": country_name,
        }

    data = {
        "country": country_name,
        "country_code": country_code,
        "success": True,
        "data": {},
        "is_fallback": False,
    }

    try:
        # Fetch all indicators concurrently to stay well within serverless limits.
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {
                name: ex.submit(_fetch_indicator, country_code, code)
                for name, code in INDICATORS.items()
            }
            for name, fut in futures.items():
                data["data"][name] = fut.result()

        # If the API returned no usable numbers, fall back.
        if all(v.get("value") is None for v in data["data"].values()):
            raise ValueError("empty result set")
        return data

    except Exception:
        fb = FALLBACK.get(country_code)
        if not fb:
            return {
                "success": False,
                "error": "World Bank API unavailable and no fallback data for this country.",
                "country": country_name,
            }
        data["is_fallback"] = True
        for name, value in fb.items():
            data["data"][name] = {"value": float(value), "year": "recent", "source": "World Bank (cached)"}
        return data
