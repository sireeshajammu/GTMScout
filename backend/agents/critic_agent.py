from agents.base_agent import Agent
from typing import Dict, List


class CriticAgent(Agent):
    """
    Reviews the assembled brief for claims not supported by the underlying data,
    internal inconsistencies, or overconfidence. Produces verification flags and a
    confidence adjustment. This is the app's self-correction / grounding check.
    """

    def __init__(self):
        system_prompt = """You are a skeptical research reviewer. You are given a market-entry brief
plus the verified data it was built from. Your job is to catch problems, not to praise.

Check for:
- claims or numbers in the summary/risks that are NOT supported by the provided data,
- a verdict that doesn't match the data (e.g. "GO" despite very low internet penetration),
- a "GO"/"CAUTION" verdict for a business that is ILLEGAL in the target country (that must be "NOT YET"),
- budget allocation that ignores the top platforms,
- overconfidence given data gaps or use of cached/fallback data.

Return ONLY JSON:
{
  "flags": ["<short issue>", ...],        // empty list if the brief is well-supported
  "note": "<one-sentence summary of your review>",
  "confidence_delta": <int between -25 and +10>  // how much to adjust confidence
}"""
        super().__init__(name="CriticAgent", system_prompt=system_prompt)

    def execute(self, request: Dict, market_data: Dict, strategy: Dict, is_fallback: bool) -> Dict:
        prompt = f"""Request: {request}
Market data (is_cached_fallback={is_fallback}): {market_data}
Verdict: {strategy.get('verdict')} (confidence {strategy.get('confidence')})
Executive summary: {strategy.get('executive_summary')}
Budget allocation: {strategy.get('budget_allocation')}
Risks: {strategy.get('risks')}

Review it and return the JSON."""
        res = self.call_json(prompt, max_tokens=400, temperature=0.3)

        if not res.get("success"):
            return {
                "success": True,  # non-fatal
                "verification": {"checked": False, "flags": [], "note": "Verification step unavailable."},
                "confidence_delta": 0,
            }

        data = res["data"]
        flags: List[str] = data.get("flags", []) or []
        if is_fallback:
            flags.append("Market data used cached fallback figures (live World Bank fetch unavailable).")
        note = data.get("note", "Review complete.")
        try:
            delta = int(data.get("confidence_delta", 0))
        except (TypeError, ValueError):
            delta = 0
        delta = max(-25, min(10, delta))

        return {
            "success": True,
            "agent": self.name,
            "verification": {
                "checked": True,
                "flags": flags,
                "note": f"Critic reviewed the brief; {len(flags)} flag(s). {note}",
            },
            "confidence_delta": delta,
        }
