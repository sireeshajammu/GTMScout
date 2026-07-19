"""Orchestrator: turns a chat message into an assistant Message.

Pipeline:  IntakeAgent -> (clarify | DataAgent -> PlatformAgent -> StrategyAgent -> CriticAgent)
Assembles a Report that matches the frontend's TypeScript `Report`/`Message` types,
aggregates token cost across all agents, and attaches structured citations.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from agents.intake_agent import IntakeAgent
from agents.data_agent import DataAgent
from agents.research_agent import ResearchAgent
from agents.platform_agent import PlatformAgent
from agents.strategy_agent import StrategyAgent
from agents.critic_agent import CriticAgent
from config import usd_cost


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _text_message(text: str) -> Dict:
    return {"id": _uid("msg"), "role": "assistant", "kind": "text", "text": text, "created_at": _now()}


def _report_message(report: Dict) -> Dict:
    return {"id": _uid("msg"), "role": "assistant", "kind": "report", "report": report, "created_at": _now()}


def run_research(
    text: str,
    history: Optional[List[Dict]] = None,
    home_country: Optional[str] = None,
    budget: Optional[float] = None,
    currency: Optional[str] = None,
) -> Dict:
    """Main entry point. Returns an assistant Message dict (text or report).

    `history` is the recent conversation ([{role, text}, ...]) so the intake agent
    can accumulate context across turns and answer follow-up questions.
    """

    intake = IntakeAgent()
    parsed = intake.execute(text, history=history)

    # Not enough info yet, a greeting, or a follow-up question -> conversational reply.
    if parsed.get("intent") != "new_report":
        msg = _text_message(
            parsed.get("reply")
            or "Tell me the target country, business type, and budget and I'll run the analysis."
        )
        # attach the tiny intake cost so usage still tracks
        msg["_cost"] = _cost_block([intake])
        return msg

    req = parsed.get("request", {})
    # Allow explicit overrides from the client, else use parsed values.
    request = {
        "target_country": req.get("target_country") or "",
        "business_type": req.get("business_type") or "general",
        "home_country": home_country or req.get("home_country") or "United States",
        "budget": float(budget or req.get("budget") or 20000),
        "currency": currency or req.get("currency") or "USD",
    }

    # Safety net: if the router mislabeled intent without a country, ask instead of erroring.
    if not request["target_country"].strip():
        msg = _text_message("Which country should I analyze? Tell me the market and business type.")
        msg["_cost"] = _cost_block([intake])
        return msg

    # --- Agent pipeline ---
    data_agent = DataAgent()
    research_agent = ResearchAgent()
    platform_agent = PlatformAgent()
    strategy_agent = StrategyAgent()
    critic_agent = CriticAgent()

    data_out = data_agent.execute(request["target_country"])
    if not data_out.get("success"):
        m = _text_message(
            f"I couldn't pull reliable market data for “{request['target_country']}”. "
            f"{data_out.get('error', '')} Try a major market (e.g. Japan, Brazil, Germany, India)."
        )
        m["_cost"] = _cost_block([intake, data_agent])
        return m

    # Live web research (Tavily) — grounds the strategy in current evidence.
    research_out = research_agent.execute(request["target_country"], request["business_type"])

    platform_out = platform_agent.execute(request["target_country"], request["business_type"])
    if not platform_out.get("success"):
        platform_out = {"platform_recommendations": [], "citations": [], "brief": ""}

    strategy_out = strategy_agent.execute(
        request, data_out["market_data"], platform_out.get("platform_recommendations", []),
        research=research_out,
    )
    if not strategy_out.get("success"):
        m = _text_message("The strategy step failed to produce a valid brief. Please try again.")
        m["_cost"] = _cost_block([intake, data_agent, research_agent, platform_agent, strategy_agent])
        return m

    critic_out = critic_agent.execute(
        request, data_out["market_data"], strategy_out, data_out.get("is_fallback", False)
    )

    # Apply critic confidence adjustment
    confidence = strategy_out["confidence"] + critic_out.get("confidence_delta", 0)
    confidence = int(max(0, min(100, confidence)))

    # --- Assemble citations with ids (World Bank + interest model + live web sources) ---
    raw_citations = (
        data_out.get("citations", [])
        + platform_out.get("citations", [])
        + research_out.get("citations", [])
    )
    citations = []
    for i, c in enumerate(raw_citations, start=1):
        citations.append({"id": i, "source": c.get("source", ""), "detail": c.get("detail", ""), "url": c.get("url")})

    agents = [intake, data_agent, research_agent, platform_agent, strategy_agent, critic_agent]

    report = {
        "id": _uid("rep"),
        "request": request,
        "verdict": strategy_out["verdict"],
        "confidence": confidence,
        "executive_summary": strategy_out["executive_summary"],
        "market_data": data_out["market_data"],
        "platform_recommendations": platform_out.get("platform_recommendations", []),
        "budget_allocation": strategy_out["budget_allocation"],
        "risks": strategy_out["risks"],
        "next_steps": strategy_out["next_steps"],
        "research_findings": research_out.get("findings", []),
        "citations": citations,
        "cost": _cost_block(agents),
        "verification": critic_out["verification"],
        "agent_briefs": {
            "data": data_out.get("brief", ""),
            "platform": platform_out.get("brief", ""),
            "strategy": strategy_out.get("brief", ""),
            "research": _research_brief(research_out),
        },
    }
    return _report_message(report)


def _research_brief(research_out: Dict) -> str:
    findings = research_out.get("findings", [])
    if not findings:
        return research_out.get("brief", "")
    return research_out.get("brief", "") + " Key findings: " + " | ".join(findings[:4])


def _cost_block(agents) -> Dict:
    """Aggregate token usage + USD cost across a list of agents."""
    per_agent = []
    total_in = total_out = 0
    for a in agents:
        stats = a.get_token_stats()
        total_in += stats["tokens_in"]
        total_out += stats["tokens_out"]
        per_agent.append({
            "agent": stats["agent"],
            "tokens_in": stats["tokens_in"],
            "tokens_out": stats["tokens_out"],
        })
    return {
        "total_tokens_in": total_in,
        "total_tokens_out": total_out,
        "usd": usd_cost(total_in, total_out),
        "per_agent": per_agent,
    }
