"""Orchestrator: turns a chat message into an assistant Message.

Routes four intents from the IntakeAgent:
  new_report  -> Data -> Research -> Platform -> Strategy -> Critic -> DeepDive  (full brief)
  comparison  -> side-by-side of markets already analyzed this chat (+ recommendation)
  ranking     -> lightweight analyze + rank several candidate markets
  reply       -> grounded conversational text (follow-ups, greetings, clarifications)

Assembles objects matching the frontend TypeScript types and aggregates token cost.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from agents.intake_agent import IntakeAgent
from agents.planner_agent import PlannerAgent
from agents.data_agent import DataAgent
from agents.research_agent import ResearchAgent
from agents.platform_agent import PlatformAgent
from agents.strategy_agent import StrategyAgent
from agents.critic_agent import CriticAgent
from agents.deepdive_agent import DeepDiveAgent
from agents.comparison_agent import ComparisonAgent
from agents.ranking_agent import RankingAgent
from contracts import validate_report
from config import usd_cost

# --- agent-loop tuning ---
MAX_STRATEGY_ATTEMPTS = 2   # 1 initial + up to 1 reflective revision
CONFIDENCE_FLOOR = 70       # below this, the loop tries to strengthen the answer


@dataclass
class RunState:
    """Shared state that flows through the agent loop — the real 'agent memory':
    the plan, tool observations, accumulated evidence, and a reasoning log."""
    request: Dict
    plan: Dict = field(default_factory=dict)
    obs: Dict = field(default_factory=dict)        # tool/agent observations
    evidence: List = field(default_factory=list)   # accumulated findings
    log: List = field(default_factory=list)        # reasoning scratchpad (node transitions)
    agents: List = field(default_factory=list)     # for cost aggregation
    iterations: int = 0

    def note(self, node: str, msg: str):
        self.log.append({"node": node, "note": msg})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _text_message(text: str) -> Dict:
    return {"id": _uid("msg"), "role": "assistant", "kind": "text", "text": text, "created_at": _now()}


def _report_message(report: Dict) -> Dict:
    return {"id": _uid("msg"), "role": "assistant", "kind": "report", "report": report, "created_at": _now()}


def _comparison_message(comparison: Dict) -> Dict:
    return {"id": _uid("msg"), "role": "assistant", "kind": "comparison", "comparison": comparison, "created_at": _now()}


def _ranking_message(ranking: Dict) -> Dict:
    return {"id": _uid("msg"), "role": "assistant", "kind": "ranking", "ranking": ranking, "created_at": _now()}


def run_research(
    text: str,
    history: Optional[List[Dict]] = None,
    reports: Optional[List[Dict]] = None,
    home_country: Optional[str] = None,
    budget: Optional[float] = None,
    currency: Optional[str] = None,
) -> Dict:
    reports = reports or []
    analyzed = [r.get("request", {}).get("target_country") for r in reports if r.get("request")]
    analyzed = [c for c in analyzed if c]

    intake = IntakeAgent()
    parsed = intake.execute(text, history=history, analyzed_countries=analyzed)
    intent = parsed.get("intent", "reply")
    req = parsed.get("request", {}) or {}

    # ---------- REPLY ----------
    if intent == "reply":
        msg = _text_message(parsed.get("reply") or
                            "Tell me the target country, business type, and budget and I'll run the analysis.")
        msg["_cost"] = _cost_block([intake])
        return msg

    # ---------- RANKING ----------
    if intent == "ranking":
        countries = req.get("countries") or []
        business_type = req.get("business_type") or _infer_business(reports) or "general"
        b = float(budget or req.get("budget") or 20000)
        ccy = currency or req.get("currency") or "USD"
        if len(countries) < 2:
            # not really a ranking — fall through to a single report if possible
            if countries:
                req["target_country"] = countries[0]
                req["business_type"] = business_type
                return _run_report(intake, req, home_country, b, ccy)
            msg = _text_message("Which markets should I rank? Name a few countries (or a region) and the business type.")
            msg["_cost"] = _cost_block([intake])
            return msg
        ranking_agent = RankingAgent()
        out = ranking_agent.execute(countries, business_type, b, ccy)
        if not out.get("success"):
            msg = _text_message(out.get("error", "I couldn't rank those markets. Try naming specific countries."))
            msg["_cost"] = _cost_block([intake, ranking_agent])
            return msg
        out["cost"] = _cost_block([intake, ranking_agent])
        return _ranking_message(out)

    # ---------- COMPARISON ----------
    if intent == "comparison":
        wanted = set(c.lower() for c in (req.get("countries") or analyzed))
        matched = [r for r in reports if r.get("request", {}).get("target_country", "").lower() in wanted]
        if len(matched) < 2:
            matched = reports  # fall back to everything we have
        if len(matched) >= 2:
            comp_agent = ComparisonAgent()
            comp = comp_agent.build(matched)
            comp["cost"] = _cost_block([intake, comp_agent])
            return _comparison_message(comp)
        # Not enough analyzed markets yet -> rank the requested ones fresh.
        countries = req.get("countries") or analyzed
        if len(countries) >= 2:
            business_type = req.get("business_type") or _infer_business(reports) or "general"
            ranking_agent = RankingAgent()
            out = ranking_agent.execute(countries, business_type,
                                        float(budget or req.get("budget") or 20000),
                                        currency or req.get("currency") or "USD")
            if out.get("success"):
                out["cost"] = _cost_block([intake, ranking_agent])
                return _ranking_message(out)
        msg = _text_message("I need at least two analyzed markets to compare. Ask me to analyze each first.")
        msg["_cost"] = _cost_block([intake])
        return msg

    # ---------- NEW REPORT ----------
    request = {
        "target_country": req.get("target_country") or "",
        "business_type": req.get("business_type") or "general",
        "home_country": home_country or req.get("home_country") or "United States",
        "budget": float(budget or req.get("budget") or 20000),
        "currency": currency or req.get("currency") or "USD",
    }
    if not request["target_country"].strip():
        msg = _text_message("Which country should I analyze? Tell me the market and business type.")
        msg["_cost"] = _cost_block([intake])
        return msg
    return _run_report(intake, request, home_country, request["budget"], request["currency"])


def _run_report(intake, request: Dict, home_country, budget, currency) -> Dict:
    """Single-market brief produced by a hand-rolled, graph-shaped agent loop:

        plan ──► gather (parallel) ──► synthesize ──► critic ──┐
                                          ▲                     │ conditional edge
                                          └──── replan ◄────────┘  (unsupported claims OR confidence < floor)
                                                                 └──► deep_dive ──► assemble
    """
    request = {
        "target_country": request.get("target_country"),
        "business_type": request.get("business_type") or "general",
        "home_country": home_country or request.get("home_country") or "United States",
        "budget": float(budget or request.get("budget") or 20000),
        "currency": currency or request.get("currency") or "USD",
    }
    state = RunState(request=request)
    state.agents.append(intake)

    # ---- NODE: plan ----
    planner = PlannerAgent()
    state.agents.append(planner)
    state.plan = planner.plan(request)
    state.note("plan", f"gather {state.plan['gather']} in parallel; synthesize {state.plan['synthesize']}. "
                       f"{state.plan.get('reason', '')}")

    # ---- NODE: gather (independent tools run in parallel) ----
    data_agent = DataAgent()
    platform_agent = PlatformAgent()
    research_agent = ResearchAgent() if "web_research" in state.plan["gather"] else None
    state.agents += [a for a in (data_agent, platform_agent, research_agent) if a]

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_data = ex.submit(data_agent.execute, request["target_country"])
        f_plat = ex.submit(platform_agent.execute, request["target_country"], request["business_type"])
        f_res = ex.submit(research_agent.execute, request["target_country"], request["business_type"]) if research_agent else None
        data_out = f_data.result()
        platform_out = f_plat.result()
        research_out = f_res.result() if f_res else {"findings": [], "citations": [], "brief": "", "notable_risks": []}

    if not data_out.get("success"):
        m = _text_message(
            f"I couldn't pull reliable market data for “{request['target_country']}”. "
            f"{data_out.get('error', '')} Try a major market (e.g. Japan, Brazil, Germany, India)."
        )
        m["_cost"] = _cost_block(state.agents)
        return m
    if not platform_out.get("success"):
        platform_out = {"platform_recommendations": [], "citations": [], "brief": ""}

    state.obs.update(data=data_out, platform=platform_out, research=research_out)
    state.evidence += research_out.get("findings", [])
    state.note("gather", f"macro data ({'cached' if data_out.get('is_fallback') else 'live'}), "
                         f"{len(platform_out.get('platform_recommendations', []))} platforms, "
                         f"{len(research_out.get('findings', []))} web findings.")

    md = data_out["market_data"]
    platforms = platform_out.get("platform_recommendations", [])
    is_fallback = data_out.get("is_fallback", False)

    strategy_agent = StrategyAgent()
    critic_agent = CriticAgent()
    state.agents += [strategy_agent, critic_agent]

    # ---- NODE: synthesize + observe (critic) with a conditional replan edge ----
    strategy_out = strategy_agent.execute(request, md, platforms, research=research_out)
    if not strategy_out.get("success"):
        m = _text_message("The strategy step failed to produce a valid brief. Please try again.")
        m["_cost"] = _cost_block(state.agents)
        return m
    critic_out = critic_agent.execute(request, md, strategy_out, is_fallback)
    state.iterations = 1
    state.note("critic", f"verdict {strategy_out['verdict']} @ {strategy_out['confidence']}; "
                         f"{len(_actionable_flags(critic_out))} actionable flag(s), "
                         f"confidence_delta {critic_out.get('confidence_delta', 0)}.")

    while state.iterations < MAX_STRATEGY_ATTEMPTS and _needs_revision(critic_out, strategy_out):
        flags = _actionable_flags(critic_out)
        # observe -> replan: if the weakness is thin evidence, pull more before retrying.
        low_conf = _effective_confidence(strategy_out, critic_out) < CONFIDENCE_FLOOR
        if low_conf and research_agent is None:
            research_agent = ResearchAgent()
            state.agents.append(research_agent)
            research_out = research_agent.execute(request["target_country"], request["business_type"])
            state.obs["research"] = research_out
            state.evidence += research_out.get("findings", [])
            state.note("replan", "confidence low and web research was skipped — gathering live evidence, then revising.")
        else:
            state.note("replan", f"revising strategy to fix {len(flags)} flagged issue(s).")

        strategy_out = strategy_agent.execute(request, md, platforms, research=research_out, criticism=flags)
        critic_out = critic_agent.execute(request, md, strategy_out, is_fallback)
        state.iterations += 1
        state.note("critic", f"after revision: verdict {strategy_out['verdict']} @ {strategy_out['confidence']}, "
                             f"{len(_actionable_flags(critic_out))} remaining flag(s).")

    # ---- NODE: deep_dive (optional per plan) ----
    deep_out = {"competitors": [], "unit_economics": [], "regulatory": [], "gtm_timeline": []}
    if "deep_dive" in state.plan["synthesize"]:
        deepdive_agent = DeepDiveAgent()
        state.agents.append(deepdive_agent)
        deep_out = deepdive_agent.execute(request, md, platforms, research=research_out)
        state.note("deep_dive", f"{len(deep_out.get('competitors', []))} competitors, "
                                f"{len(deep_out.get('gtm_timeline', []))} GTM phases.")

    # ---- NODE: assemble ----
    confidence = _effective_confidence(strategy_out, critic_out)
    raw_citations = (
        data_out.get("citations", []) + platform_out.get("citations", []) + research_out.get("citations", [])
    )
    citations = [
        {"id": i, "source": c.get("source", ""), "detail": c.get("detail", ""), "url": c.get("url")}
        for i, c in enumerate(raw_citations, start=1)
    ]

    report = {
        "id": _uid("rep"),
        "request": request,
        "verdict": strategy_out["verdict"],
        "confidence": confidence,
        "executive_summary": strategy_out["executive_summary"],
        "market_data": md,
        "platform_recommendations": platforms,
        "budget_allocation": strategy_out["budget_allocation"],
        "risks": strategy_out["risks"],
        "next_steps": strategy_out["next_steps"],
        "competitors": deep_out.get("competitors", []),
        "unit_economics": deep_out.get("unit_economics", []),
        "regulatory": deep_out.get("regulatory", []),
        "gtm_timeline": deep_out.get("gtm_timeline", []),
        "research_findings": research_out.get("findings", []),
        "citations": citations,
        "cost": _cost_block(state.agents),
        "verification": critic_out["verification"],
        "plan": state.plan,
        "reasoning_log": state.log,
        "iterations": state.iterations,
        "agent_briefs": {
            "data": data_out.get("brief", ""),
            "platform": platform_out.get("brief", ""),
            "strategy": strategy_out.get("brief", ""),
            "research": _research_brief(research_out),
        },
    }
    # Contract boundary: validate the assembled brief. Non-fatal — log and still return
    # (we never want a schema nit to drop a real answer in production).
    try:
        validate_report(report)
    except Exception as e:  # noqa: BLE001
        print(f"WARN: report failed contract validation: {e}")
    return _report_message(report)


def _effective_confidence(strategy_out: Dict, critic_out: Dict) -> int:
    return int(max(0, min(100, strategy_out.get("confidence", 0) + critic_out.get("confidence_delta", 0))))


def _actionable_flags(critic_out: Dict) -> List[str]:
    """Critic flags the Strategy can actually fix — exclude the 'used cached data' note."""
    flags = critic_out.get("verification", {}).get("flags", []) or []
    return [f for f in flags if "cached fallback" not in f.lower()]


def _needs_revision(critic_out: Dict, strategy_out: Dict) -> bool:
    return bool(_actionable_flags(critic_out)) or _effective_confidence(strategy_out, critic_out) < CONFIDENCE_FLOOR


def _infer_business(reports: List[Dict]) -> Optional[str]:
    for r in reversed(reports):
        bt = r.get("request", {}).get("business_type")
        if bt:
            return bt
    return None


def _research_brief(research_out: Dict) -> str:
    findings = research_out.get("findings", [])
    if not findings:
        return research_out.get("brief", "")
    return research_out.get("brief", "") + " Key findings: " + " | ".join(findings[:4])


def _cost_block(agents) -> Dict:
    per_agent = []
    total_in = total_out = 0
    for a in agents:
        stats = a.get_token_stats()
        total_in += stats["tokens_in"]
        total_out += stats["tokens_out"]
        per_agent.append({"agent": stats["agent"], "tokens_in": stats["tokens_in"], "tokens_out": stats["tokens_out"]})
    return {
        "total_tokens_in": total_in,
        "total_tokens_out": total_out,
        "usd": usd_cost(total_in, total_out),
        "per_agent": per_agent,
    }
