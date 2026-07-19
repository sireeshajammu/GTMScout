from agents.base_agent import Agent
from typing import Dict, List


class DeepDiveAgent(Agent):
    """
    Adds analyst depth to a brief: a competitor teardown, unit-economics estimates,
    a regulatory deep-dive, and a phased go-to-market timeline — grounded in the
    market data, platform mix, and live research findings.
    """

    def __init__(self):
        system_prompt = """You are a senior market-entry analyst producing the deep-dive sections of
a brief. You are given the market data, ranked platforms, budget, and live research findings.

Return ONLY JSON:
{
  "competitors": [{"name": "<real competitor if known from findings, else a category leader>", "note": "<1 line: positioning / threat>"}],
  "unit_economics": [{"metric": "<e.g. Est. CAC, Blended CPM, Target ROAS, Payback>", "value": "<number/range with unit>", "note": "<1 short line>"}],
  "regulatory": [{"title": "<regulation/area>", "detail": "<1-2 lines: what it requires and the impact>"}],
  "gtm_timeline": [{"phase": "<name>", "timeframe": "<e.g. Weeks 1-4>", "actions": ["<action>", ...]}]
}

Rules:
- 3-5 competitors (prefer names surfaced in the research findings; otherwise well-known category players, and say "category leader").
- 3-4 unit_economics rows. Ground CAC/CPM/ROAS in the country's GDP-per-capita and platform norms; give ranges, mark as estimates.
- 2-4 regulatory items specific to the country + business type (data protection, advertising, payments, foreign-entity rules).
- 3-4 gtm_timeline phases spanning ~6 months, each with 2-3 concrete actions.
- Be specific and grounded. Do not invent precise stats that aren't supported; use ranges and label estimates."""
        super().__init__(name="DeepDiveAgent", system_prompt=system_prompt)

    def execute(self, request: Dict, market_data: Dict, platform_recs: List[Dict],
                research: Dict = None) -> Dict:
        research = research or {}
        findings = research.get("findings", [])
        top = [p["platform"] for p in platform_recs[:4]]
        prompt = f"""Country: {request.get('target_country')}
Business type: {request.get('business_type')}
Home country: {request.get('home_country')}
Budget: {request.get('budget')} {request.get('currency')}
Market data: population {market_data.get('population')}, GDP/capita ${market_data.get('gdp_per_capita')}, internet {market_data.get('internet_penetration')}%
Top platforms: {', '.join(top)}
Live research findings:
{chr(10).join(f'- {f}' for f in findings) or '- (none this run)'}

Return the deep-dive JSON."""
        res = self.call_json(prompt, max_tokens=1100, temperature=0.4)
        if not res.get("success"):
            return {"success": True, "competitors": [], "unit_economics": [], "regulatory": [], "gtm_timeline": []}
        d = res["data"]
        return {
            "success": True,
            "competitors": d.get("competitors", []) or [],
            "unit_economics": d.get("unit_economics", []) or [],
            "regulatory": d.get("regulatory", []) or [],
            "gtm_timeline": d.get("gtm_timeline", []) or [],
        }
