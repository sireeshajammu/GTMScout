from agents.base_agent import Agent
from typing import Dict, List, Optional


class IntakeAgent(Agent):
    """
    Conversational router. Reads the whole recent conversation (not just the last
    message) and decides one of two things:
      - intent "new_report": we now have enough to run a market-entry analysis, so
        it returns the accumulated {target_country, business_type, home_country,
        budget, currency}.
      - intent "reply": the message is a greeting, a follow-up question about the
        previous report, or is still missing a country/business — so it returns a
        short conversational reply instead.

    Reading the transcript is what makes the app feel like a chat rather than a
    one-shot form: "software development" + an earlier "India" now combine.
    """

    def __init__(self):
        system_prompt = """You are the conversational router for a market-entry research assistant.
You read the ENTIRE recent conversation plus the newest user message, then respond with JSON.

Decide the intent:
- "new_report": the conversation now identifies BOTH a target country and a business type.
  Accumulate details across ALL turns (a country mentioned earlier + a business type mentioned
  later together count). Carry over the budget/home country/currency from earlier turns if the
  newest message doesn't restate them.
- "reply": use this when the message is a greeting, a follow-up question about a previous report,
  OR a request to compare/recommend between markets already analyzed in the conversation.
  Write a helpful, concise "reply" grounded in the SPECIFIC numbers from the transcript (platform
  interest scores, budget split %, named risks, verdict/confidence, market data, research findings)
  — never give generic advice. e.g. "Instagram leads at 100/100 and takes 45% ($6,750) because…".
  BE DECISIVE: if the user asks which market is better or what you recommend (e.g. "USA or Brazil?",
  "which is the better bet?"), and reports for those markets are in the conversation, PICK ONE and
  justify it with 2-4 concrete reasons drawn from the reports (market size/growth from research
  findings, internet penetration, GDP per capita, competition, budget efficiency, verdict &
  confidence). Do NOT deflect with "which would you like to explore?" — commit to a recommendation.

Return ONLY this JSON:
{
  "intent": "new_report" | "reply",
  "request": {
    "target_country": "<country or empty>",
    "business_type": "<business type or empty>",
    "home_country": "<home country if known, else 'United States'>",
    "budget": <number, default 20000>,
    "currency": "<3-letter code, default 'USD'>"
  },
  "reply": "<text to show the user when intent is 'reply'; else empty string>"
}

Rules:
- Normalize country names to common English (e.g. 'brasil' -> 'Brazil').
- Parse budgets like '$15k', '20,000 USD', '30k euros' into a number + currency.
- PIVOT (important): if the newest message asks to analyze ONE (possibly different) country —
  e.g. "now do Mexico", "what about France?", "same analysis for Vietnam", "try India instead" —
  set intent "new_report" for THAT country and INHERIT the business_type, budget, home_country and
  currency from the most recent report in the conversation. A pivot to a new country is NOT a
  comparison — never ask the user to choose between the old country and the new one.
- PARAMETER CHANGE: if the newest message only changes the budget, business type, or home country
  for a market already in the conversation (e.g. "what if I cut the budget to $5k?", "make it $50k",
  "same but for a fintech"), set intent "new_report" for that SAME country, inherit the unchanged
  details, and apply the new value — so a real re-computed brief is produced. Do NOT just estimate
  a new budget split in text; re-run the analysis.
- COMPARE: only when the NEWEST message itself names two or more countries to compare AND none is
  singled out (e.g. "compare Brazil vs India"), set intent "reply" and ask which single country to
  start with (we analyze one market per brief).
- Only set intent "new_report" when target_country AND business_type are both non-empty.
"""
        super().__init__(name="IntakeAgent", system_prompt=system_prompt)

    def execute(self, text: str, history: Optional[List[Dict]] = None) -> Dict:
        transcript = self._format_history(history)
        prompt = (
            (f"Conversation so far:\n{transcript}\n\n" if transcript else "")
            + f'Newest user message: "{text}"\n\nReturn the JSON object.'
        )
        result = self.call_json(prompt, max_tokens=400)

        if not result.get("success"):
            return {
                "intent": "reply",
                "request": {},
                "reply": "Could you share the target country, business type, and budget? "
                'For example: "Consumer app in Brazil, $15k USD."',
                "_error": result.get("error"),
            }

        data = result["data"]
        data.setdefault("intent", "reply")
        data.setdefault("request", {})
        data.setdefault("reply", "")
        return data

    @staticmethod
    def _format_history(history: Optional[List[Dict]]) -> str:
        if not history:
            return ""
        lines = []
        for m in history[-10:]:
            role = m.get("role", "user")
            speaker = "User" if role == "user" else "Assistant"
            txt = (m.get("text") or "").strip()
            if txt:
                lines.append(f"{speaker}: {txt}")
        return "\n".join(lines)
