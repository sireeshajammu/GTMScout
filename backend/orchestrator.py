"""Orchestrator: turns a chat message into an assistant Message.

Routes four intents from the IntakeAgent:
  new_report  -> Data -> Research -> Platform -> Strategy -> Critic -> DeepDive  (full brief)
  comparison  -> side-by-side of markets already analyzed this chat (+ recommendation)
  ranking     -> lightweight analyze + rank several candidate markets
  reply       -> grounded conversational text (follow-ups, greetings, clarifications)

Assembles objects matching the frontend TypeScript types and aggregates token cost.
"""
import operator
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

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
from safety import is_blocked, REFUSAL
from tools.worldbank import is_ambiguous, resolve_country, suggest_country
from config import usd_cost

# --- agent-loop tuning ---
MAX_STRATEGY_ATTEMPTS = 2   # 1 initial + up to 1 reflective revision
CONFIDENCE_FLOOR = 70       # below this, the loop tries to strengthen the answer

# --- input validation ---
MIN_BUDGET = 500
MAX_BUDGET = 100_000_000    # $100M — above this, almost certainly a typo


class ReportState(TypedDict, total=False):
    """LangGraph state for the report agent loop — the real 'agent memory' that flows
    node-to-node: the plan, tool observations, accumulated evidence, and a reasoning log.

    The three accumulating channels (evidence / log / agents) use an `operator.add`
    reducer, so each node RETURNS the items it adds and LangGraph concatenates them —
    no in-place mutation. Everything else uses the default (replace) reducer.
    """
    request: Dict
    plan: Dict
    # accumulating channels (reducer = list concat)
    evidence: Annotated[List, operator.add]     # findings gathered across the loop
    log: Annotated[List, operator.add]          # reasoning scratchpad (node transitions)
    agents: Annotated[List, operator.add]       # agent handles, for cost aggregation
    iterations: int
    # agent handles reused across nodes
    data_agent: Any
    platform_agent: Any
    research_agent: Any
    strategy_agent: Any
    critic_agent: Any
    # observations threaded between nodes
    data_out: Dict
    research_out: Dict
    platform_out: Dict
    strategy_out: Dict
    critic_out: Dict
    deep_out: Dict
    # terminal output (an assistant Message)
    result: Dict


def _log(node: str, msg: str) -> Dict:
    return {"node": node, "note": msg}


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


def _clarify(intake, text: str) -> Dict:
    msg = _text_message(text)
    msg["_cost"] = _cost_block([intake])
    return msg


def _budget_issue(b: float) -> Optional[str]:
    """Return a clarifying message if the budget is implausible, else None."""
    if b < MIN_BUDGET:
        return (f"A market-entry test usually needs at least ~${MIN_BUDGET:,.0f} to be meaningful — "
                f"you entered ${b:,.0f}. Did you mean a larger amount (e.g. $5,000)?")
    if b > MAX_BUDGET:
        return (f"${b:,.0f} is an unusually large go-to-market budget — please confirm the amount "
                "(e.g. did you mean $50 million rather than $50 billion?).")
    return None


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

    # ---------- SAFETY GATE (deterministic, before any LLM call) ----------
    if is_blocked(text):
        return _text_message(REFUSAL)

    intake = IntakeAgent()
    parsed = intake.execute(text, history=history, analyzed_countries=analyzed)
    intent = parsed.get("intent", "reply")
    req = parsed.get("request", {}) or {}

    # ---------- REFUSE (semantic — intake caught a harmful/illegal ask) ----------
    if intent == "refuse":
        return _clarify(intake, parsed.get("reply") or REFUSAL)

    # ---------- REPLY ----------
    if intent == "reply":
        msg = _text_message(parsed.get("reply") or
                            "Tell me the target country, business type, and budget and I'll run the analysis.")
        msg["_cost"] = _cost_block([intake])
        return msg

    # ---------- RANKING ----------
    if intent == "ranking":
        countries = req.get("countries") or []
        business_type = (req.get("business_type") or _infer_business(reports) or "").strip()
        if not business_type:
            return _clarify(intake, "What type of business should I rank these markets for? "
                                    "(e.g. consumer app, B2B SaaS, fintech)")
        b = float(budget or req.get("budget") or 20000)
        issue = _budget_issue(b)
        if issue:
            return _clarify(intake, issue)
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
    target = (req.get("target_country") or "").strip()
    if not target:
        return _clarify(intake, "Which country should I analyze? Tell me the market and business type.")

    amb = is_ambiguous(target)
    if amb:
        return _clarify(intake, f"“{target}” is ambiguous — did you mean {amb}? Tell me which one.")

    # Resolve / fuzzy-correct the country. High-confidence typos ("Phillipines") auto-correct;
    # near-misses ask for confirmation; anything too far falls through to the data agent's
    # honest "not a country" failure.
    resolved = resolve_country(target)
    if resolved:
        target = resolved[1]  # canonical spelling (fixes typos in the displayed report)
    else:
        sugg = suggest_country(target)
        if sugg:
            return _clarify(intake, f"I don't recognize “{target}”. Did you mean {sugg[0]}? "
                                    "Reply with the correct country.")

    business_type = (req.get("business_type") or "").strip()
    if not business_type:
        return _clarify(intake, "What type of business is this for? "
                                "(e.g. consumer app, B2B SaaS, fintech, fast fashion, e-commerce)")

    b = float(budget or req.get("budget") or 20000)
    issue = _budget_issue(b)
    if issue:
        return _clarify(intake, issue)

    request = {
        "target_country": target,
        "business_type": business_type,
        "home_country": home_country or req.get("home_country") or "United States",
        "budget": b,
        "currency": currency or req.get("currency") or "USD",
    }
    return _run_report(intake, request, home_country, request["budget"], request["currency"])


# ===========================================================================
# The report agent loop as a LangGraph StateGraph.
#
#            ┌───────────────────────── revise ◄──┐  (conditional edge:
#   plan ► gather ► [data ok?] ► synthesize ► critic  unsupported claims OR
#             │         │ no          │ fail      │   confidence < floor)
#             │      fail_data     fail_strategy  └► deep_dive ► assemble ► END
#
# Each node is a plain function (state) -> partial-state-update. Agents and the
# OpenAI client are unchanged — LangGraph only owns the transitions/state.
# `gather` keeps a ThreadPoolExecutor internally so the two independent I/O tools
# (World Bank ∥ Tavily) still run CONCURRENTLY; LangGraph's sync executor would
# otherwise run same-superstep nodes serially and lose that measured speedup.
# ===========================================================================

def _node_plan(state: ReportState) -> Dict:
    request = state["request"]
    planner = PlannerAgent()
    plan = planner.plan(request)
    return {
        "plan": plan,
        "agents": [planner],
        "log": [_log("plan", f"gather {plan['gather']} in parallel; synthesize {plan['synthesize']}. "
                             f"{plan.get('reason', '')}")],
    }


def _node_gather(state: ReportState) -> Dict:
    request = state["request"]
    plan = state["plan"]
    data_agent = DataAgent()
    platform_agent = PlatformAgent()
    research_agent = ResearchAgent() if "web_research" in plan.get("gather", []) else None

    # Data and Research are independent -> run CONCURRENTLY. Platform depends on
    # Research (it prefers platforms the web says matter locally), so it runs after.
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_data = ex.submit(data_agent.execute, request["target_country"])
        f_res = ex.submit(research_agent.execute, request["target_country"], request["business_type"]) if research_agent else None
        data_out = f_data.result()
        research_out = f_res.result() if f_res else {"findings": [], "citations": [], "brief": "", "notable_risks": []}

    platform_out = platform_agent.execute(
        request["target_country"], request["business_type"], research=research_out
    )
    if not platform_out.get("success"):
        platform_out = {"platform_recommendations": [], "citations": [], "brief": "", "success": False}

    _rag = research_out.get("cached_used", 0)
    note = (f"macro data ({'cached' if data_out.get('is_fallback') else 'live'}), "
            f"{len(platform_out.get('platform_recommendations', []))} platforms"
            + (" (web-grounded)" if platform_out.get("research_driven") else " (heuristic)") + ", "
            f"{len(research_out.get('findings', []))} web findings"
            + (f" (+{_rag} from RAG cache)" if _rag else "") + ".")
    return {
        "data_agent": data_agent, "platform_agent": platform_agent, "research_agent": research_agent,
        "data_out": data_out, "research_out": research_out, "platform_out": platform_out,
        "agents": [a for a in (data_agent, platform_agent, research_agent) if a],
        "evidence": research_out.get("findings", []),
        "log": [_log("gather", note)],
    }


def _node_fail_data(state: ReportState) -> Dict:
    request = state["request"]
    out = state["data_out"]
    m = _text_message(
        f"I couldn't pull reliable market data for “{request['target_country']}”. "
        f"{out.get('error', '')} Try a major market (e.g. Japan, Brazil, Germany, India)."
    )
    m["_cost"] = _cost_block(state["agents"])
    return {"result": m}


def _node_synthesize(state: ReportState) -> Dict:
    request = state["request"]
    md = state["data_out"]["market_data"]
    platforms = state["platform_out"].get("platform_recommendations", [])
    strategy_agent = StrategyAgent()
    critic_agent = CriticAgent()
    strategy_out = strategy_agent.execute(request, md, platforms, research=state["research_out"])
    return {
        "strategy_agent": strategy_agent, "critic_agent": critic_agent,
        "strategy_out": strategy_out, "agents": [strategy_agent, critic_agent], "iterations": 1,
    }


def _node_fail_strategy(state: ReportState) -> Dict:
    m = _text_message("The strategy step failed to produce a valid brief. Please try again.")
    m["_cost"] = _cost_block(state["agents"])
    return {"result": m}


def _node_critic(state: ReportState) -> Dict:
    request = state["request"]
    md = state["data_out"]["market_data"]
    is_fallback = state["data_out"].get("is_fallback", False)
    strategy_out = state["strategy_out"]
    critic_out = state["critic_agent"].execute(request, md, strategy_out, is_fallback)
    prefix = "after revision: " if state.get("iterations", 1) > 1 else ""
    note = (f"{prefix}verdict {strategy_out['verdict']} @ {strategy_out['confidence']}; "
            f"{len(_actionable_flags(critic_out))} actionable flag(s), "
            f"confidence_delta {critic_out.get('confidence_delta', 0)}.")
    return {"critic_out": critic_out, "log": [_log("critic", note)]}


def _node_revise(state: ReportState) -> Dict:
    request = state["request"]
    md = state["data_out"]["market_data"]
    flags = _actionable_flags(state["critic_out"])
    research_out = state["research_out"]
    platform_out = state["platform_out"]
    updates: Dict = {}
    # observe -> replan: if the weakness is thin evidence, pull more before retrying.
    low_conf = _effective_confidence(state["strategy_out"], state["critic_out"]) < CONFIDENCE_FLOOR
    if low_conf and state.get("research_agent") is None:
        research_agent = ResearchAgent()
        research_out = research_agent.execute(request["target_country"], request["business_type"])
        # Now that we have live research, re-derive platforms so they're web-grounded too.
        platform_out = state["platform_agent"].execute(
            request["target_country"], request["business_type"], research=research_out
        )
        updates.update({
            "research_agent": research_agent, "research_out": research_out, "platform_out": platform_out,
            "agents": [research_agent], "evidence": research_out.get("findings", []),
            "log": [_log("replan", "confidence low and web research was skipped — gathering live evidence "
                                   "(and re-grounding platforms), then revising.")],
        })
    else:
        updates["log"] = [_log("replan", f"revising strategy to fix {len(flags)} flagged issue(s).")]

    platforms = platform_out.get("platform_recommendations", [])
    strategy_out = state["strategy_agent"].execute(request, md, platforms, research=research_out, criticism=flags)
    updates["strategy_out"] = strategy_out
    updates["iterations"] = state.get("iterations", 1) + 1
    return updates


def _node_deep_dive(state: ReportState) -> Dict:
    request = state["request"]
    md = state["data_out"]["market_data"]
    platforms = state["platform_out"].get("platform_recommendations", [])
    deep_out = {"competitors": [], "unit_economics": [], "regulatory": [], "gtm_timeline": []}
    updates: Dict = {}
    if "deep_dive" in state["plan"].get("synthesize", []):
        deepdive_agent = DeepDiveAgent()
        deep_out = deepdive_agent.execute(request, md, platforms, research=state["research_out"])
        updates["agents"] = [deepdive_agent]
        updates["log"] = [_log("deep_dive", f"{len(deep_out.get('competitors', []))} competitors, "
                                            f"{len(deep_out.get('gtm_timeline', []))} GTM phases.")]
    updates["deep_out"] = deep_out
    return updates


def _node_assemble(state: ReportState) -> Dict:
    request = state["request"]
    data_out = state["data_out"]
    platform_out = state["platform_out"]
    research_out = state["research_out"]
    strategy_out = state["strategy_out"]
    critic_out = state["critic_out"]
    deep_out = state["deep_out"]
    md = data_out["market_data"]
    platforms = platform_out.get("platform_recommendations", [])

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
        "cost": _cost_block(state["agents"]),
        "verification": critic_out["verification"],
        "plan": state["plan"],
        "reasoning_log": state["log"],
        "iterations": state.get("iterations", 1),
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
    return {"result": _report_message(report)}


# ---- conditional edges ----
def _after_gather(state: ReportState) -> str:
    return "synthesize" if state["data_out"].get("success") else "fail_data"


def _after_synthesize(state: ReportState) -> str:
    return "critic" if state["strategy_out"].get("success") else "fail_strategy"


def _after_critic(state: ReportState) -> str:
    if state.get("iterations", 1) < MAX_STRATEGY_ATTEMPTS and _needs_revision(state["critic_out"], state["strategy_out"]):
        return "revise"
    return "deep_dive"


def _build_report_graph():
    g = StateGraph(ReportState)
    for name, fn in [
        ("plan", _node_plan), ("gather", _node_gather), ("fail_data", _node_fail_data),
        ("synthesize", _node_synthesize), ("fail_strategy", _node_fail_strategy),
        ("critic", _node_critic), ("revise", _node_revise),
        ("deep_dive", _node_deep_dive), ("assemble", _node_assemble),
    ]:
        g.add_node(name, fn)

    g.set_entry_point("plan")
    g.add_edge("plan", "gather")
    g.add_conditional_edges("gather", _after_gather, {"synthesize": "synthesize", "fail_data": "fail_data"})
    g.add_conditional_edges("synthesize", _after_synthesize, {"critic": "critic", "fail_strategy": "fail_strategy"})
    g.add_conditional_edges("critic", _after_critic, {"revise": "revise", "deep_dive": "deep_dive"})
    g.add_edge("revise", "critic")            # reflection cycle
    g.add_edge("deep_dive", "assemble")
    g.add_edge("assemble", END)
    g.add_edge("fail_data", END)
    g.add_edge("fail_strategy", END)
    return g.compile()


# Compiled once at import (no agent calls happen until .invoke()).
_REPORT_GRAPH = _build_report_graph()


def _run_report(intake, request: Dict, home_country, budget, currency) -> Dict:
    """Single-market brief produced by a LangGraph agent loop (see _build_report_graph)."""
    request = {
        "target_country": request.get("target_country"),
        "business_type": request.get("business_type") or "general",
        "home_country": home_country or request.get("home_country") or "United States",
        "budget": float(budget or request.get("budget") or 20000),
        "currency": currency or request.get("currency") or "USD",
    }
    initial: ReportState = {
        "request": request,
        "agents": [intake],  # seed cost aggregation with the intake agent
        "evidence": [], "log": [], "iterations": 0,
        "research_out": {"findings": [], "citations": [], "brief": "", "notable_risks": []},
    }
    final = _REPORT_GRAPH.invoke(initial)
    return final["result"]


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
