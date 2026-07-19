from agents.base_agent import Agent
from typing import Dict, List


class StrategyAgent(Agent):
    """
    Synthesizes market data + platform research into a market-entry verdict:
    verdict, confidence, executive summary, budget allocation, risks, next steps.
    Returns fully structured output.
    """

    def __init__(self):
        system_prompt = """You are a market-entry strategy advisor. You synthesize research into a
clear, actionable brief. You are given: the business request, verified market data, and a ranked
platform list. Produce a professional recommendation.

Return ONLY JSON with this exact shape:
{
  "verdict": "GO" | "PROCEED WITH CAUTION" | "NOT YET",
  "confidence": <int 0-100>,
  "executive_summary": "<2-3 sentence recommendation>",
  "budget_allocation": [{"platform": "<name or 'Creative & Localization'>", "percentage": <number>, "amount": <number>}],
  "risks": [{"title": "<short>", "severity": "low"|"medium"|"high", "description": "<1 sentence>"}],
  "next_steps": ["<action>", ...]
}

Rules:
- budget_allocation percentages MUST sum to 100 and amounts MUST sum to the total budget.
- Allocate primarily across the top 3 recommended platforms; you may reserve 5-15% for creative/localization.
- Give 2-4 concrete risks. Flag low internet penetration (<70%), large GDP-per-capita gaps vs. home market, and platform mismatches.
- Give 3-5 concrete next steps. Be specific to the country and business type.
- LEGALITY: if the business is illegal or criminally restricted in the TARGET country (e.g. cannabis
  in Singapore, gambling where banned, alcohol where prohibited), the verdict MUST be "NOT YET",
  confidence must be low, and the FIRST risk must be the legal prohibition (severity "high"). Never
  return "GO" for something illegal in that market."""
        super().__init__(name="StrategyAgent", system_prompt=system_prompt)

    def execute(self, request: Dict, market_data: Dict, platform_recs: List[Dict],
                research: Dict = None, criticism: List[str] = None) -> Dict:
        budget = request.get("budget", 20000)
        currency = request.get("currency", "USD")
        top = platform_recs[:5]

        # Reflection: on a re-run, inject the critic's findings so the model fixes them.
        criticism_block = ""
        if criticism:
            criticism_block = (
                "\n\nA reviewer flagged these problems with your PREVIOUS attempt — fix each one, "
                "and do not repeat unsupported claims:\n" + "\n".join(f"- {c}" for c in criticism)
            )

        research = research or {}
        findings = research.get("findings", [])
        web_risks = research.get("notable_risks", [])
        research_block = ""
        if findings or web_risks:
            research_block = "\n\nLive web research (use this as evidence; prefer it over assumptions):\n"
            research_block += "\n".join(f"- {f}" for f in findings)
            if web_risks:
                research_block += "\nRisks surfaced by research:\n" + "\n".join(f"- {r}" for r in web_risks)

        prompt = f"""Business request:
- Target country: {request.get('target_country')}
- Business type: {request.get('business_type')}
- Home country: {request.get('home_country', 'United States')}
- Total budget: {budget} {currency}

Verified market data:
- Population: {market_data.get('population')}
- GDP per capita (USD): {market_data.get('gdp_per_capita')}
- Internet penetration: {market_data.get('internet_penetration')}%
- Mobile subscriptions (per 100): {market_data.get('mobile_subscriptions')}
- Data year: {market_data.get('data_year')}

Ranked platforms:
{chr(10).join(f"{p['rank']}. {p['platform']} ({p['interest_score']}/100) — {p['rationale']}" for p in top)}
{research_block}{criticism_block}

Return the JSON brief. Budget amounts are in {currency}, total = {budget}.
Ground the executive_summary and risks in the live research above when it is present."""

        res = self.call_json(prompt, max_tokens=900, temperature=0.4)
        if not res.get("success"):
            return {"success": False, "error": res.get("error"), "agent": self.name}

        data = res["data"]
        # Normalize budget allocation so amounts sum to the budget.
        alloc = data.get("budget_allocation") or []
        alloc = self._normalize_allocation(alloc, budget)

        verdict = data.get("verdict", "PROCEED WITH CAUTION")
        if verdict not in ("GO", "PROCEED WITH CAUTION", "NOT YET"):
            verdict = "PROCEED WITH CAUTION"

        return {
            "success": True,
            "agent": self.name,
            "verdict": verdict,
            "confidence": int(max(0, min(100, data.get("confidence", 60)))),
            "executive_summary": data.get("executive_summary", ""),
            "budget_allocation": alloc,
            "risks": data.get("risks", []),
            "next_steps": data.get("next_steps", []),
            "brief": "Synthesized verdict, budget split, risks and next steps.",
        }

    @staticmethod
    def _normalize_allocation(alloc: List[Dict], budget: float) -> List[Dict]:
        cleaned = []
        for a in alloc:
            try:
                pct = float(a.get("percentage", 0))
            except (TypeError, ValueError):
                pct = 0
            cleaned.append({"platform": a.get("platform", "Channel"), "percentage": pct})
        total_pct = sum(a["percentage"] for a in cleaned) or 100
        out = []
        for a in cleaned:
            pct = round(a["percentage"] / total_pct * 100, 1)
            out.append({
                "platform": a["platform"],
                "percentage": pct,
                "amount": round(budget * pct / 100, 2),
            })
        return out
