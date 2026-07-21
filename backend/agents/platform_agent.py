from agents.base_agent import Agent
from tools.platform_data import get_platform_interest
from typing import Dict, List, Optional


class PlatformAgent(Agent):
    """
    Ranks social/marketing platforms for a country + business type.

    Two modes:
      • Research-driven (preferred): when live web research is available, the LLM
        selects and scores the platforms actually named as relevant in that market
        — including local ones (KakaoTalk, Naver, LINE, VK) the heuristic can't know
        — and the recommendation is grounded in cited web sources.
      • Heuristic fallback: with no research (Tavily off / thin results), it uses the
        hand-tuned interest model (tools/platform_data.py) as before.

    The heuristic still seeds a sensible global baseline so the LLM always has a floor.
    """

    def __init__(self):
        system_prompt = """You are a digital go-to-market strategist. Pick the marketing platforms
that matter for a specific business entering a specific country, and score each 0-100.

You get a HEURISTIC BASELINE (generic global platform scores) and, when available, LIVE RESEARCH
(cited web findings about this market). Rules:
- If LIVE RESEARCH names platforms that matter locally — including country-specific ones like
  KakaoTalk/Naver (Korea), LINE (Japan), VK (Russia), WeChat/Douyin (China), WhatsApp (LATAM/India)
  — PREFER them. Add them and drop baseline platforms that aren't relevant in this market.
- Use the baseline only as a starting point when research is silent on platforms.
- interest_score = how important the platform is for THIS business in THIS country (0-100).
- Set from_research=true ONLY when the live research supports the platform's relevance.
- Write a SPECIFIC one-line rationale (max 20 words), grounded in the business + audience.

Return ONLY JSON:
{"platforms": [{"platform": "...", "interest_score": <int 0-100>, "rationale": "...", "from_research": <bool>}]}
Return 5-6 platforms, most relevant first."""
        super().__init__(name="PlatformAgent", system_prompt=system_prompt)

    def execute(self, country: str, business_type: str = "general",
                research: Optional[Dict] = None) -> Dict:
        interest = get_platform_interest(country, business_type)
        if not interest.get("success"):
            return {"success": False, "error": interest.get("error"), "agent": self.name, "country": country}

        comparison = interest["comparison"]
        findings: List[str] = (research or {}).get("findings", []) or []

        baseline_lines = "\n".join(f"- {c['platform']}: {c['interest']}/100" for c in comparison)
        research_lines = ("\n".join(f"- {f}" for f in findings)
                          if findings else "(none — use the heuristic baseline)")
        prompt = (
            f"Country: {country}\nBusiness type: {business_type}\n\n"
            f"HEURISTIC BASELINE (generic global scores):\n{baseline_lines}\n\n"
            f"LIVE RESEARCH (cited findings about this market):\n{research_lines}\n\n"
            "Return the platforms JSON."
        )
        res = self.call_json(prompt, max_tokens=700)

        recs: List[Dict] = []
        if res.get("success") and isinstance(res["data"].get("platforms"), list):
            picked = [p for p in res["data"]["platforms"] if p.get("platform")]
            picked.sort(key=lambda p: p.get("interest_score", 0), reverse=True)
            for i, p in enumerate(picked[:6]):
                recs.append({
                    "platform": p["platform"],
                    "interest_score": max(1, min(100, int(p.get("interest_score", 50)))),
                    "rank": i + 1,
                    "rationale": p.get("rationale") or "Relevant channel for this audience.",
                    "from_research": bool(p.get("from_research")),
                })
        if not recs:
            # Fallback: trust the heuristic tool scores/order verbatim.
            for i, c in enumerate(comparison):
                recs.append({
                    "platform": c["platform"], "interest_score": c["interest"], "rank": i + 1,
                    "rationale": "Ranked by relative interest for this market/segment.",
                    "from_research": False,
                })

        research_driven = any(r.get("from_research") for r in recs)
        if research_driven:
            citations = [{"source": "Live web research", "url": None,
                          "detail": "Platform relevance grounded in cited web findings"}]
            for c in ((research or {}).get("citations") or [])[:3]:
                citations.append({"source": c.get("title", "web source"),
                                  "detail": "market platform landscape", "url": c.get("url")})
            src_note = "research-driven (web-grounded) with heuristic baseline"
        else:
            citations = [{"source": "GTMScout heuristic interest model",
                          "detail": interest.get("source", ""), "url": None}]
            src_note = "heuristic interest model"

        return {
            "success": True,
            "agent": self.name,
            "country": country,
            "business_type": business_type,
            "category": interest.get("category"),
            "platform_recommendations": recs,
            "research_driven": research_driven,
            "brief": f"Ranked {len(recs)} platforms for {business_type} in {country} ({src_note}).",
            "citations": citations,
        }
