# GTMScout — Architecture (as built)

> An agentic market-entry research assistant. A user asks, in plain English, whether/how to
> expand a business into a country; a **hand-rolled agent loop** plans, calls tools in parallel,
> synthesizes a verdict, **critiques and revises itself**, and returns a grounded, cited brief.

---

## 1. The agent loop (the core)

`backend/orchestrator.py` is a **hand-rolled, graph-shaped state machine** — not a linear
pipeline. For a market question the flow is:

```
IntakeAgent ─ routes intent ─┬─ reply / refuse / clarify        (fast, no pipeline)
                             ├─ comparison  (from prior reports)
                             ├─ ranking     (score N markets)
                             └─ new_report ▼

   PlannerAgent ─► gather (PARALLEL) ─► StrategyAgent ─► CriticAgent ──┐
                    DataAgent ∥                              ▲          │ conditional edge:
                    ResearchAgent ∥                          │          │ unsupported claims
                    PlatformAgent                            └─ replan ─┘ OR confidence < 70
                         │                                   (re-run Strategy with the
                    (RunState: plan +                         criticism; gather more evidence
                     observations +                           if research was skipped)
                     evidence + log)                              │
                                                             DeepDiveAgent ─► assemble Report
```

- **plan → act → observe → decide.** The Planner decides which tools to run; the Critic is the
  "observe"; the conditional edge back to Strategy is "decide-what's-next."
- **`RunState`** (a dataclass) is the agent memory that flows through the loop: the plan, each
  tool's observations, accumulated evidence, and a `reasoning_log` (surfaced in the UI's
  "Agent reasoning" panel and in the `Report`).
- **Bounded**, not open-ended: max 2 Strategy attempts. This trades some adaptivity for
  predictable latency/cost and no infinite loops.

**Why hand-rolled, not LangGraph:** the graph is small and I wanted to explain every transition
and keep serverless cold-starts lean (no `langchain-core` weight). The nodes/edges map 1:1 to a
`StateGraph`, so porting later is contained. (See README → Design decisions.)

## 2. Agents (each = a distinct reasoning domain + explicit contract)

| Agent | Job | Output contract (`contracts.py`) |
|-------|-----|----------------------------------|
| Intake | route intent, parse country/business/budget, refuse harmful | — |
| Planner | choose tools + what runs in parallel | plan dict |
| Data | World Bank macro data (+ fallback) | `DataAgentOut` |
| Research | Tavily web search + RAG cache | `ResearchAgentOut` |
| Platform | rank platforms (heuristic model + LLM rationale) | `PlatformAgentOut` |
| Strategy | verdict, budget, risks, next steps | `StrategyAgentOut` |
| Critic | verify claims vs data, adjust confidence | `CriticAgentOut` |
| DeepDive | competitors, unit economics, regulatory, GTM timeline | `DeepDiveAgentOut` |
| Comparison / Ranking | side-by-side / multi-market rank | — |

Every agent extends `base_agent.Agent` (OpenAI `gpt-4o-mini`, retries, token+USD tracking,
JSON-mode). The orchestrator validates the assembled `Report` against the pydantic contract at
the boundary (non-fatal).

## 3. Tools (`backend/tools/`) — with deliberate failure handling
- **`worldbank.py`** — live World Bank API, **per-indicator resilient** (each indicator retries
  independently; only the ones that fail use curated fallback). Country resolution is
  data-driven: a precomputed ISO-3166 index (`country_codes_data.py`, 249 countries) + alias &
  city maps, so there is no runtime country-list fetch.
- **`web_research.py`** — Tavily web search; returns nothing gracefully (no key / no results).
- **`platform_data.py`** — a **transparent heuristic** interest model (hand-tuned category
  weights, *not* learned). Replaced `pytrends` (kept in `web_search.py` for reference) because
  pandas bloats serverless cold starts.
- **`vector_store.py`** — pgvector RAG cache (embeds findings, HNSW index); no-ops without
  `DATABASE_URL`.

## 4. Safety & validation
- `safety.py` — a **deterministic gate that runs before any LLM call** and refuses clearly
  illegal/harmful businesses; the Intake agent adds a semantic `refuse` intent. Jurisdiction
  legality (e.g. cannabis in Singapore) is enforced in the Strategy/Critic prompts → NOT YET.
- Input validation in the orchestrator: budget floor/ceiling, required business type, ambiguous
  country ("Congo → which one?"), major-city → country.

## 5. State model (why no server DB for chat)
The backend is **stateless per request**. Conversations, history, and profile/token-usage live
**client-side in `localStorage`** (frontend `src/services/api.ts`), which is ideal for serverless.
The only server-side persistence is the **optional** pgvector research cache. The frontend sends
recent `history` (and prior `reports`) with each message so the backend can accumulate context,
answer follow-ups, and build comparisons without re-analysis.

## 6. Frontend
React + TanStack Start. Chat UI with a sidebar (history + profile/token usage), a light/dark
theme slider, and inline rich cards: `BriefCard` (report + Agent-reasoning trace),
`ComparisonCard`, `RankingCard`. `src/services/types.ts` mirrors the backend contracts.

## 7. Deployment
Two Vercel projects from one repo: **backend** (Python 3.12, `api/index.py`, `maxDuration 60s`)
and **frontend** (TanStack Start, `NITRO_PRESET=vercel`). Same repo, connected by `VITE_API_BASE`
+ CORS. See README → Deploy.

## 8. Evaluation
`backend/evals/` — 10 cases with deterministic "correct" definitions + a harness that prints
pass/fail and metrics (pass rate, tool-call success, self-correction rate, latency, cost). See
`evals/RESULTS.md`.
