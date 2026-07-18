from agents.base_agent import Agent
from typing import Dict
import json


class IntakeAgent(Agent):
    """
    Parses a free-text chat message into a structured market-research request,
    or decides the message needs clarification. This is what makes the app feel
    conversational rather than form-driven.
    """

    def __init__(self):
        system_prompt = """You are the intake router for a market-entry research assistant.
Given a user's chat message, decide whether it is a concrete market-entry question
that names (or clearly implies) a TARGET COUNTRY and a BUSINESS TYPE.

Return ONLY a JSON object with this exact shape:
{
  "is_market_question": true | false,
  "request": {
    "target_country": "<country name or empty string>",
    "business_type": "<business type or empty string>",
    "home_country": "<home country if stated, else 'United States'>",
    "budget": <number, default 20000 if not stated>,
    "currency": "<3-letter code, default 'USD'>"
  },
  "clarification": "<if is_market_question is false, a short friendly question asking for the missing pieces; else empty string>"
}

Rules:
- A message is a market question only if you can identify BOTH a target country and a business type.
- Normalize country names to common English (e.g. 'brasil' -> 'Brazil').
- Parse budgets like '$15k', '20,000 USD', '30k euros' into a number + currency.
- If it's small talk, a greeting, or missing country/business, set is_market_question false and ask for the missing pieces in clarification.
"""
        super().__init__(name="IntakeAgent", system_prompt=system_prompt)

    def execute(self, text: str) -> Dict:
        result = self.call_json(
            f'User message: "{text}"\n\nReturn the JSON object.',
            max_tokens=300,
        )
        if not result.get("success"):
            # On parse failure, degrade gracefully to asking for details.
            return {
                "is_market_question": False,
                "request": {},
                "clarification": "Could you share the target country, business type, and budget? "
                "For example: \"Consumer app in Brazil, $15k USD.\"",
                "_error": result.get("error"),
            }
        data = result["data"]
        data.setdefault("is_market_question", False)
        data.setdefault("request", {})
        data.setdefault("clarification", "")
        return data
