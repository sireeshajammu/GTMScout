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
- "reply": use this when the message is a greeting, OR is a follow-up question about the previous
  report (e.g. "why LinkedIn?", "what are the risks?"), OR still lacks a country or business type.
  In these cases write a helpful, concise "reply". When answering a follow-up about the previous
  report, ground your answer in ITS SPECIFIC numbers from the transcript (the platform interest
  scores, the budget split percentages, the named risks, the verdict/confidence) — do not give
  generic advice. e.g. "Instagram leads at 100/100 and takes 45% ($6,750) of the budget because…".

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
- If the user asks to COMPARE two or more countries, pick the FIRST country mentioned for the
  report (we analyze one market per brief) — set intent "new_report" for that country if a
  business type is known; otherwise set intent "reply" and ask which single country to start with.
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
