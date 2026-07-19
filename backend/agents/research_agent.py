from agents.base_agent import Agent
from tools.web_research import research_market, is_enabled
from tools import vector_store
from typing import Dict, List


class ResearchAgent(Agent):
    """
    Gathers LIVE market intelligence via web search (Tavily) AND retrieves related
    prior findings from the pgvector research cache (RAG), then synthesizes them into
    grounded findings with real source URLs. New findings are written back to the
    cache so future briefs reuse them. Degrades gracefully when Tavily / the vector
    store aren't configured.
    """

    def __init__(self):
        system_prompt = """You are a market research analyst. You are given raw web-search snippets
and possibly some prior research about a country and a business type. Extract only what is
supported by the snippets.

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
        # RAG: retrieve semantically-related prior findings from the vector cache.
        cached = vector_store.search(f"{business_type} market entry in {country}", k=4)
        web = research_market(country, business_type)
        web_snippets = web.get("snippets", [])

        if not web_snippets and not cached:
            return {
                "success": True, "agent": self.name, "enabled": is_enabled(),
                "findings": [], "notable_risks": [], "citations": [], "cached_used": 0,
                "brief": "Live web research unavailable this run." if not is_enabled() else "No usable web results found.",
            }

        lines = []
        for c in cached:
            lines.append(f"- (prior research on {c['country']}) {c['content']} (source: {c.get('url', '')})")
        for s in web_snippets:
            if s.get("answer"):
                lines.append(f"- {s['answer']}")
            else:
                lines.append(f"- {s.get('title', '')}: {s.get('content', '')} (source: {s.get('url', '')})")

        res = self.call_json(
            f"Country: {country}\nBusiness type: {business_type}\n\nEvidence:\n" + "\n".join(lines)
            + "\n\nReturn the findings JSON.",
            max_tokens=600,
        )
        findings: List[str] = []
        notable_risks: List[str] = []
        if res.get("success"):
            findings = res["data"].get("findings", []) or []
            notable_risks = res["data"].get("notable_risks", []) or []

        # Write new findings back to the cache for future reuse.
        stored = vector_store.upsert_findings(country, business_type, findings, web.get("sources", []))

        brief = f"Gathered {len(findings)} findings from {len(web.get('sources', []))} live web sources"
        if cached:
            brief += f" + {len(cached)} from the research cache"
        if stored:
            brief += f"; cached {stored} for reuse"

        return {
            "success": True,
            "agent": self.name,
            "enabled": True,
            "findings": findings,
            "notable_risks": notable_risks,
            "citations": web.get("sources", []),
            "cached_used": len(cached),
            "brief": brief + ".",
        }
