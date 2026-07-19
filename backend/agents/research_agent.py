from agents.base_agent import Agent
from tools.web_research import research_market, is_enabled
from typing import Dict, List


class ResearchAgent(Agent):
    """
    Gathers LIVE market intelligence via web search (Tavily) and synthesizes it into
    a few grounded findings with real source URLs. These findings feed the
    StrategyAgent so the verdict/risks/summary are based on current evidence, not
    just static indicators. Degrades gracefully when Tavily isn't configured.
    """

    def __init__(self):
        system_prompt = """You are a market research analyst. You are given raw web-search snippets
about a country and a business type. Extract only what is supported by the snippets.

Return ONLY JSON:
{
  "findings": ["<concise, specific fact grounded in the snippets (competitors, market size, regulation, platform/usage stat, recent trend)>", ...],
  "notable_risks": ["<risk implied by the evidence>", ...]
}
Rules:
- 3-6 findings, each one sentence, specific (names, numbers, dates when present).
- Do NOT invent facts not present in the snippets. If snippets are thin, return fewer findings."""
        super().__init__(name="ResearchAgent", system_prompt=system_prompt)

    def execute(self, country: str, business_type: str) -> Dict:
        web = research_market(country, business_type)

        # No key / no results -> return an empty-but-successful result; pipeline continues.
        if not web.get("snippets"):
            return {
                "success": True,
                "agent": self.name,
                "enabled": is_enabled(),
                "findings": [],
                "notable_risks": [],
                "citations": [],
                "brief": "Live web research unavailable this run." if not is_enabled()
                else "No usable web results found.",
            }

        snippet_text = "\n".join(
            (f"- {s.get('answer')}" if s.get("answer")
             else f"- {s.get('title','')}: {s.get('content','')} (source: {s.get('url','')})")
            for s in web["snippets"]
        )
        res = self.call_json(
            f"Country: {country}\nBusiness type: {business_type}\n\nWeb snippets:\n{snippet_text}\n\n"
            "Return the findings JSON.",
            max_tokens=600,
        )

        findings: List[str] = []
        notable_risks: List[str] = []
        if res.get("success"):
            findings = res["data"].get("findings", []) or []
            notable_risks = res["data"].get("notable_risks", []) or []

        return {
            "success": True,
            "agent": self.name,
            "enabled": True,
            "findings": findings,
            "notable_risks": notable_risks,
            "citations": web.get("sources", []),
            "brief": f"Gathered {len(findings)} live findings from {len(web.get('sources', []))} web sources.",
        }
