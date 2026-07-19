from agents.base_agent import Agent
from tools.worldbank import get_country_data
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List


class RankingAgent(Agent):
    """
    Evaluates and ranks several candidate markets for a business. Runs a LIGHTWEIGHT
    analysis (live World Bank data per country, fetched concurrently) then a single
    LLM call to score + rank them — much cheaper than a full brief per country.
    """

    def __init__(self):
        system_prompt = """You are a market-entry analyst ranking candidate countries for a business.
You are given each country's macro data. Score each 0-100 for attractiveness for THIS business,
weighing market size (population), spending power (GDP per capita), digital readiness (internet
penetration), and fit with the business type. Rank best-first.

Return ONLY JSON:
{ "items": [ {"country": "...", "score": <0-100>, "verdict": "GO"|"PROCEED WITH CAUTION"|"NOT YET",
              "rationale": "<1 line grounded in the data>"} ],
  "note": "<1 line on the overall picture>" }
Order items best-first. Every provided country must appear exactly once."""
        super().__init__(name="RankingAgent", system_prompt=system_prompt)

    def execute(self, countries: List[str], business_type: str, budget: float, currency: str) -> Dict:
        countries = [c for c in dict.fromkeys([c.strip() for c in countries if c and c.strip()])][:6]
        if not countries:
            return {"success": False, "error": "No candidate countries."}

        # Fetch macro data concurrently.
        data_by_country: Dict[str, Dict] = {}
        with ThreadPoolExecutor(max_workers=min(6, len(countries))) as ex:
            futures = {c: ex.submit(get_country_data, c) for c in countries}
            for c, fut in futures.items():
                try:
                    data_by_country[c] = fut.result()
                except Exception:
                    data_by_country[c] = {"success": False}

        rows = []
        macros = {}
        for c in countries:
            d = data_by_country.get(c, {})
            if not d.get("success"):
                continue
            md = d["data"]
            macros[c] = {
                "population": md.get("population", {}).get("value"),
                "gdp_per_capita": md.get("gdp_per_capita", {}).get("value"),
                "internet_penetration": md.get("internet_users_percent", {}).get("value"),
            }
            rows.append(
                f"- {c}: population {macros[c]['population']}, GDP/capita ${macros[c]['gdp_per_capita']}, "
                f"internet {macros[c]['internet_penetration']}%"
            )

        if not rows:
            return {"success": False, "error": "Could not fetch data for the candidate countries."}

        res = self.call_json(
            f"Business type: {business_type}\nBudget: {budget} {currency}\n\nCandidates:\n"
            + "\n".join(rows) + "\n\nRank them and return the JSON.",
            max_tokens=700,
        )
        items = []
        note = ""
        if res.get("success"):
            note = res["data"].get("note", "")
            for i, it in enumerate(res["data"].get("items", []), start=1):
                c = it.get("country", "")
                m = macros.get(c, {})
                items.append({
                    "rank": i,
                    "country": c,
                    "score": int(max(0, min(100, it.get("score", 0)))),
                    "verdict": it.get("verdict", "PROCEED WITH CAUTION"),
                    "rationale": it.get("rationale", ""),
                    "population": m.get("population"),
                    "gdp_per_capita": m.get("gdp_per_capita"),
                    "internet_penetration": m.get("internet_penetration"),
                })

        return {
            "success": True,
            "business_type": business_type,
            "budget": budget,
            "currency": currency,
            "items": items,
            "note": note,
        }
