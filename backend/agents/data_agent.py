from agents.base_agent import Agent
from tools.worldbank import get_country_data
from typing import Dict


class DataAgent(Agent):
    """
    Gathers hard economic + demographic data for a country from the World Bank,
    returns it as structured market_data with citations, and writes a one-line brief.
    """

    def __init__(self):
        system_prompt = """You are a data analyst. You are handed verified World Bank figures for a country.
Write ONE concise, factual sentence (max 30 words) summarizing the market's size and digital readiness.
Do not invent numbers beyond those given. Return JSON: {"brief": "<sentence>"}."""
        super().__init__(name="DataAgent", system_prompt=system_prompt)

    def execute(self, country: str) -> Dict:
        wb = get_country_data(country)
        if not wb.get("success"):
            return {"success": False, "error": wb.get("error"), "agent": self.name, "country": country}

        d = wb["data"]
        def val(key):
            return d.get(key, {}).get("value")

        year = None
        for k in ("population", "gdp_per_capita", "internet_users_percent"):
            year = d.get(k, {}).get("year")
            if year:
                break

        market_data = {
            "population": val("population"),
            "gdp_per_capita": val("gdp_per_capita"),
            "internet_penetration": val("internet_users_percent"),
            "mobile_subscriptions": val("mobile_subscriptions_percent"),
            "data_year": str(year or "recent"),
        }

        # cheap grounded brief
        brief = f"{country} market data compiled from World Bank indicators."
        res = self.call_json(
            f"Country: {country}\nWorld Bank figures: {market_data}\nWrite the brief JSON.",
            max_tokens=120,
        )
        if res.get("success"):
            brief = res["data"].get("brief", brief)

        src_label = "World Bank (cached)" if wb.get("is_fallback") else "World Bank"
        citations = [
            {"source": src_label, "detail": f"{country} population, GDP per capita, internet & mobile penetration ({market_data['data_year']})",
             "url": "https://data.worldbank.org/country"},
        ]

        return {
            "success": True,
            "agent": self.name,
            "country": country,
            "market_data": market_data,
            "is_fallback": wb.get("is_fallback", False),
            "brief": brief,
            "citations": citations,
        }
