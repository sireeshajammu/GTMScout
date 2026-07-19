from agents.base_agent import Agent
from typing import Dict, List


# The tools the planner may schedule. data + platform + strategy are required for a
# valid structured brief; web_research and deep_dive are optional and query-driven.
KNOWN_TOOLS = ["macro_data", "web_research", "platform_ranking", "strategy", "critic", "deep_dive"]


class PlannerAgent(Agent):
    """
    Decides HOW to answer an analysis request: which tools to run and which can run
    in parallel. This is what turns the fixed pipeline into a plan -> act -> observe
    loop. The plan is data-driven (it can skip web_research or deep_dive for a narrow
    question), but always keeps the tools needed to produce a valid brief.
    """

    def __init__(self):
        system_prompt = """You are the planner for a market-entry research agent. Given the user's
request, decide which tools to run to answer it well, and which can run in parallel.

Tools:
- macro_data: World Bank population/GDP/internet for the country (REQUIRED for a brief).
- web_research: live web search for competitors/market size/regulation (skip for purely generic asks).
- platform_ranking: rank marketing platforms for the business (REQUIRED for a brief).
- strategy: synthesize verdict/budget/risks (REQUIRED for a brief).
- critic: verify the strategy against the data (recommended).
- deep_dive: competitor teardown + unit economics + regulatory + GTM timeline (skip if the user only wants a quick read).

Return ONLY JSON:
{
  "goal": "<one line: what the user wants>",
  "gather": ["macro_data", "web_research", "platform_ranking"],   // subset to run in PARALLEL first
  "synthesize": ["strategy", "critic", "deep_dive"],              // run in order after gather
  "reason": "<one line: why this plan>"
}
Rules:
- 'gather' must include macro_data and platform_ranking. Include web_research unless the ask is generic.
- 'synthesize' must include strategy. Include critic. Include deep_dive unless the user wants only a quick answer."""
        super().__init__(name="PlannerAgent", system_prompt=system_prompt)

    def plan(self, request: Dict) -> Dict:
        prompt = (
            f"Request: analyze {request.get('business_type')} entering "
            f"{request.get('target_country')} with budget {request.get('budget')} "
            f"{request.get('currency')}.\nReturn the plan JSON."
        )
        res = self.call_json(prompt, max_tokens=250, temperature=0.2)
        gather = ["macro_data", "web_research", "platform_ranking"]
        synth = ["strategy", "critic", "deep_dive"]
        goal = reason = ""
        if res.get("success"):
            d = res["data"]
            goal = d.get("goal", "")
            reason = d.get("reason", "")
            gather = [t for t in d.get("gather", gather) if t in KNOWN_TOOLS] or gather
            synth = [t for t in d.get("synthesize", synth) if t in KNOWN_TOOLS] or synth
        # Enforce the invariants for a valid brief.
        for req in ("macro_data", "platform_ranking"):
            if req not in gather:
                gather.append(req)
        if "strategy" not in synth:
            synth.insert(0, "strategy")
        return {"goal": goal, "gather": gather, "synthesize": synth, "reason": reason}
