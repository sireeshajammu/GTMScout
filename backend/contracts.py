"""Explicit I/O contracts for every agent.

This is what makes "why agents, not functions?" a real answer: each agent owns a
distinct reasoning domain and returns a structured output validated against the
pydantic model below, so agents are independently testable and replaceable. The
orchestrator validates the assembled Report against `Report` at the boundary.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    # Lenient: ignore unexpected keys so a slightly-verbose LLM response still validates.
    model_config = ConfigDict(extra="ignore")


# ---- shared value objects ----
class MarketData(_Base):
    population: Optional[float] = None
    gdp_per_capita: Optional[float] = None
    internet_penetration: Optional[float] = None
    mobile_subscriptions: Optional[float] = None
    data_year: str = "recent"


class PlatformRec(_Base):
    platform: str
    interest_score: int
    rank: int
    rationale: str = ""


class BudgetItem(_Base):
    platform: str
    percentage: float
    amount: float


class Risk(_Base):
    title: str
    severity: str
    description: str = ""


class Citation(_Base):
    id: int
    source: str
    detail: str = ""
    url: Optional[str] = None


class Verification(_Base):
    checked: bool
    flags: List[str] = []
    note: str = ""


# ---- per-agent output contracts ----
class DataAgentOut(_Base):
    market_data: MarketData
    is_fallback: bool = False
    citations: List[dict] = []


class PlatformAgentOut(_Base):
    platform_recommendations: List[PlatformRec]
    citations: List[dict] = []


class ResearchAgentOut(_Base):
    findings: List[str] = []
    notable_risks: List[str] = []
    citations: List[dict] = []


class StrategyAgentOut(_Base):
    verdict: str
    confidence: int
    executive_summary: str
    budget_allocation: List[BudgetItem]
    risks: List[Risk]
    next_steps: List[str]


class CriticAgentOut(_Base):
    verification: Verification
    confidence_delta: int = 0


class DeepDiveAgentOut(_Base):
    competitors: List[dict] = []
    unit_economics: List[dict] = []
    regulatory: List[dict] = []
    gtm_timeline: List[dict] = []


class RankingItem(_Base):
    rank: int
    country: str
    score: int
    verdict: str
    rationale: str = ""


# ---- the assembled brief the frontend consumes ----
class Report(_Base):
    id: str
    request: dict
    verdict: str
    confidence: int
    executive_summary: str
    market_data: MarketData
    platform_recommendations: List[PlatformRec]
    budget_allocation: List[BudgetItem]
    risks: List[Risk]
    next_steps: List[str]
    citations: List[Citation]
    cost: dict
    verification: Verification
    # deep-dive + agent-loop fields (optional)
    competitors: List[dict] = []
    unit_economics: List[dict] = []
    regulatory: List[dict] = []
    gtm_timeline: List[dict] = []
    research_findings: List[str] = []
    plan: Optional[dict] = None
    reasoning_log: List[dict] = []
    iterations: Optional[int] = None
    agent_briefs: dict = {}


def validate_report(report: dict) -> Report:
    """Validate an assembled report against the contract. Raises on violation."""
    return Report.model_validate(report)
