from agents.base_agent import Agent
from tools.platform_data import get_platform_interest
from typing import Dict


class PlatformAgent(Agent):
    """
    Ranks social/marketing platforms for a country + business type. Interest scores
    come from the platform-interest tool; the LLM writes a specific rationale per
    platform and returns a structured, ranked recommendation list.
    """

    def __init__(self):
        system_prompt = """You are a digital go-to-market strategist.
You receive relative platform interest scores (0-100) for a market and a business type.
For each platform, write a SPECIFIC one-line rationale (max 20 words) grounded in the business
type and audience — not generic filler. Keep the given interest scores and ranking order.

Return ONLY JSON:
{"platforms": [{"platform": "...", "interest_score": <int>, "rank": <int>, "rationale": "..."}]}"""
        super().__init__(name="PlatformAgent", system_prompt=system_prompt)

    def execute(self, country: str, business_type: str = "general") -> Dict:
        interest = get_platform_interest(country, business_type)
        if not interest.get("success"):
            return {"success": False, "error": interest.get("error"), "agent": self.name, "country": country}

        comparison = interest["comparison"]
        prompt = (
            f"Country: {country}\nBusiness type: {business_type}\n"
            f"Platform interest scores (already ranked):\n"
            + "\n".join(f"{i+1}. {c['platform']}: {c['interest']}/100" for i, c in enumerate(comparison))
            + "\n\nReturn the JSON with a rationale per platform."
        )
        res = self.call_json(prompt, max_tokens=600)

        recs = []
        if res.get("success") and isinstance(res["data"].get("platforms"), list):
            # Trust tool scores/order; take rationale from the model.
            rationale_by_name = {p.get("platform"): p.get("rationale", "") for p in res["data"]["platforms"]}
            for i, c in enumerate(comparison):
                recs.append({
                    "platform": c["platform"],
                    "interest_score": c["interest"],
                    "rank": i + 1,
                    "rationale": rationale_by_name.get(c["platform"], "Relevant channel for this audience."),
                })
        else:
            for i, c in enumerate(comparison):
                recs.append({
                    "platform": c["platform"], "interest_score": c["interest"],
                    "rank": i + 1, "rationale": "Ranked by relative interest for this market/segment.",
                })

        return {
            "success": True,
            "agent": self.name,
            "country": country,
            "business_type": business_type,
            "category": interest.get("category"),
            "platform_recommendations": recs,
            "brief": f"Ranked {len(recs)} platforms for {business_type} in {country} by relative interest.",
            "citations": [
                {"source": "GTMScout heuristic interest model", "detail": interest.get("source", ""), "url": None},
            ],
        }
