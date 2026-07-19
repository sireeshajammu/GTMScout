from agents.base_agent import Agent
from typing import Dict, List


class ComparisonAgent(Agent):
    """
    Builds a side-by-side comparison of markets already analyzed in the conversation.
    The per-market metrics come straight from the existing reports (no re-analysis);
    this agent only produces the decisive recommendation (a pick + reasons).
    """

    def __init__(self):
        system_prompt = """You compare market-entry options and make a decisive recommendation.
Given several already-computed market briefs, pick the SINGLE best market for the business and
justify it with 3-4 concrete reasons drawn from the numbers (market size/growth, internet
penetration, GDP per capita, competition, platform fit, verdict & confidence, budget efficiency).

Return ONLY JSON:
{ "pick": "<country>", "reasons": ["<reason grounded in the data>", ...] }
Be decisive. Do not hedge or ask the user to choose."""
        super().__init__(name="ComparisonAgent", system_prompt=system_prompt)

    def build(self, reports: List[Dict]) -> Dict:
        """reports: list of full Report dicts already produced this conversation."""
        markets = []
        for r in reports:
            md = r.get("market_data", {})
            plats = r.get("platform_recommendations", [])
            markets.append({
                "country": r.get("request", {}).get("target_country", "?"),
                "business_type": r.get("request", {}).get("business_type", ""),
                "verdict": r.get("verdict"),
                "confidence": r.get("confidence"),
                "population": md.get("population"),
                "gdp_per_capita": md.get("gdp_per_capita"),
                "internet_penetration": md.get("internet_penetration"),
                "top_platform": plats[0]["platform"] if plats else None,
                "budget": r.get("request", {}).get("budget"),
                "currency": r.get("request", {}).get("currency", "USD"),
                "market_note": (r.get("research_findings") or [""])[0][:140],
            })

        summary = "\n".join(
            f"- {m['country']}: verdict {m['verdict']} ({m['confidence']}), "
            f"pop {m['population']}, GDP/cap ${m['gdp_per_capita']}, internet {m['internet_penetration']}%, "
            f"top {m['top_platform']}. {m['market_note']}"
            for m in markets
        )
        res = self.call_json(
            f"Business: {markets[0]['business_type'] if markets else ''}\nMarkets:\n{summary}\n\nReturn the JSON.",
            max_tokens=500,
        )
        rec = {"pick": markets[0]["country"] if markets else "", "reasons": []}
        if res.get("success"):
            rec["pick"] = res["data"].get("pick", rec["pick"])
            rec["reasons"] = res["data"].get("reasons", []) or []
        return {"markets": markets, "recommendation": rec}
