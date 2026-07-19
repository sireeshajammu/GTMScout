from agents.base_agent import Agent
from typing import Dict, List, Optional


class IntakeAgent(Agent):
    """
    Conversational router. Reads the whole recent conversation + the newest message
    and picks one of four intents:
      - "new_report": run a single-market brief (accumulates country/business/budget).
      - "comparison": build a side-by-side of markets ALREADY analyzed in this chat.
      - "ranking": analyze and rank several candidate markets (may be new).
      - "reply": greeting, follow-up question, or missing info -> a grounded text reply.
    """

    def __init__(self):
        system_prompt = """You are the router for a market-entry research assistant. You read the
recent conversation and the newest user message, then respond with JSON.

Intents:
- "new_report": the conversation identifies BOTH a target country and a business type. Accumulate
  details across turns; carry over budget/home/currency from earlier turns if not restated.
- "comparison": the user wants to compare or decide between markets that have ALREADY been analyzed
  in this conversation (their countries appear in ANALYZED_MARKETS). Put those countries in
  request.countries. Examples: "compare Brazil and USA", "show them side by side", "which is better".
- "ranking": the user wants several markets evaluated/ranked, and at least one is NOT already
  analyzed, OR they use ranking language ("rank", "best N markets", "top markets in LATAM").
  Put the candidate countries in request.countries (expand a region like "LATAM" or "Europe" into
  3-6 real countries yourself). Include business_type + budget.
- "reply": greeting, a follow-up question about a prior report, or still missing a country/business.
  Write a concise "reply" grounded in the SPECIFIC numbers from the transcript. Never generic.

Return ONLY this JSON:
{
  "intent": "new_report" | "comparison" | "ranking" | "reply",
  "request": {
    "target_country": "<country or empty>",
    "business_type": "<business type or empty>",
    "home_country": "<home country if known, else 'United States'>",
    "budget": <number, default 20000>,
    "currency": "<3-letter code, default 'USD'>",
    "countries": ["<for comparison/ranking>", ...]
  },
  "reply": "<text when intent is 'reply'; else empty string>"
}

Rules:
- Normalize country names to common English ('brasil' -> 'Brazil').
- Parse budgets like '$15k', '20,000 USD', '30k euros' into a number + currency.
- PIVOT: "now do Mexico", "what about France?", "try India instead" -> new_report for THAT country,
  inheriting business_type/budget/home/currency from the most recent report. A pivot is NOT a
  comparison.
- PARAMETER CHANGE: "cut the budget to $5k", "make it $50k", "same but a fintech" -> new_report for
  the SAME country with the new value, inheriting the rest. Re-run; do not estimate in text.
- COMPARISON vs REPLY: if the user asks "which is better?" about already-analyzed markets, prefer
  intent "comparison" (a structured side-by-side) over a plain reply.
- Only set new_report when target_country AND business_type are both non-empty.
- For comparison/ranking, business_type must be known (from the request or the transcript)."""
        super().__init__(name="IntakeAgent", system_prompt=system_prompt)

    def execute(self, text: str, history: Optional[List[Dict]] = None,
                analyzed_countries: Optional[List[str]] = None) -> Dict:
        transcript = self._format_history(history)
        analyzed = ", ".join(analyzed_countries or []) or "(none yet)"
        prompt = (
            (f"Conversation so far:\n{transcript}\n\n" if transcript else "")
            + f"ANALYZED_MARKETS (already have a report this chat): {analyzed}\n\n"
            + f'Newest user message: "{text}"\n\nReturn the JSON object.'
        )
        result = self.call_json(prompt, max_tokens=450)

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
