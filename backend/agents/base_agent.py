from openai import OpenAI
import os
from dotenv import load_dotenv
import time
from typing import Dict, List, Optional
import json
from config import (
    MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    MAX_RETRIES,
    RETRY_DELAY,
    TRACK_TOKENS,
    usd_cost,
)

load_dotenv()


class Agent:
    """
    Base class for all specialist agents.
    Handles LLM interactions, retries, token tracking, cost, and structured output.
    """

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = MODEL
        self.token_count = {"input": 0, "output": 0}
        self.call_history = []

    def call_llm(
        self,
        messages: List[Dict],
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
        json_mode: bool = False,
    ) -> Optional[Dict]:
        """
        Make a call to the LLM with built-in retry logic and error handling.

        Args:
            messages: List of message dicts with "role" and "content"
            temperature: Creativity level (0-1)
            max_tokens: Max response length
            json_mode: If True, force a JSON object response (structured output)

        Returns:
            Response dict with success flag, content, tokens used, or error.
        """

        kwargs = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt}] + messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    wait_time = RETRY_DELAY ** attempt
                    time.sleep(wait_time)

                response = self.client.chat.completions.create(**kwargs)

                content = response.choices[0].message.content
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

                if TRACK_TOKENS:
                    self.token_count["input"] += input_tokens
                    self.token_count["output"] += output_tokens

                self.call_history.append(
                    {
                        "agent": self.name,
                        "attempt": attempt + 1,
                        "tokens_in": input_tokens,
                        "tokens_out": output_tokens,
                        "success": True,
                    }
                )

                return {
                    "success": True,
                    "content": content,
                    "tokens": {"input": input_tokens, "output": output_tokens},
                }

            except Exception as e:
                error_msg = str(e)
                # Retry on transient / rate-limit errors
                if ("429" in error_msg or "timeout" in error_msg.lower()) and attempt < MAX_RETRIES - 1:
                    continue

                self.call_history.append(
                    {
                        "agent": self.name,
                        "attempt": attempt + 1,
                        "success": False,
                        "error": error_msg,
                    }
                )
                return {
                    "success": False,
                    "error": f"LLM call failed: {error_msg}",
                    "attempt": attempt + 1,
                }

        return {
            "success": False,
            "error": f"Failed after {MAX_RETRIES} attempts",
            "agent": self.name,
        }

    def call_json(
        self,
        user_content: str,
        temperature: float = TEMPERATURE,
        max_tokens: int = MAX_TOKENS,
    ) -> Dict:
        """
        Convenience wrapper: ask the LLM for a JSON object and parse it.

        Returns:
            {"success": True, "data": <parsed dict>, "tokens": {...}} or
            {"success": False, "error": "..."}
        """
        result = self.call_llm(
            [{"role": "user", "content": user_content}],
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )
        if not result.get("success"):
            return result
        try:
            data = json.loads(result["content"])
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Model returned invalid JSON: {e}"}
        return {"success": True, "data": data, "tokens": result["tokens"]}

    def execute(self, input_data: Dict) -> Dict:
        raise NotImplementedError("Subclasses must implement execute()")

    def get_token_stats(self) -> Dict:
        """Get token usage + cost for this agent."""
        tin = self.token_count["input"]
        tout = self.token_count["output"]
        return {
            "agent": self.name,
            "tokens_in": tin,
            "tokens_out": tout,
            "usd": usd_cost(tin, tout),
            "total_calls": len(self.call_history),
            "successful_calls": sum(1 for c in self.call_history if c["success"]),
        }
