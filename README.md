# GTMScout — an agentic market-entry research assistant

Ask a plain-English question — *"Should a fintech expand into Germany with a $30k budget?"* — and
GTMScout runs a **real agent loop**: it plans an approach, calls tools (in parallel), synthesizes a
verdict, **critiques and revises its own answer**, and returns a grounded, cited brief. The task
genuinely needs multiple steps and tools, so a single model call isn't enough.

**Live demo:** app → https://gtm-scout.vercel.app · API health → https://gtm-scout-api.vercel.app/api/health
**Model:** OpenAI `gpt-4o-mini` (cheap; ~$0.002 per full brief).

---

## What it does (the agent loop)

For a market question the flow is **plan → act → observe → decide-what's-next**:

```
Intake (route/parse/refuse) → Planner (pick tools) → gather: [DataAgent ∥ ResearchAgent] → PlatformAgent
        │                                                            │                          │
   LangGraph StateGraph carries plan + observations +                └─ (Platform prefers web-named platforms)
   evidence + reasoning-log through the loop                         → StrategyAgent → CriticAgent
        │                                                                   ▲             │  conditional edge:
        │                                                    revise ────────┘             │  unsupported claims
                                                       DeepDiveAgent → assemble ◄──────────┘  OR confidence < 70
```

It also routes non-report intents: **clarify** (under-specified), **refuse** (illegal business),
**comparison** (side-by-side of analyzed markets), and **ranking** (score several markets). The
graph itself is defined in `backend/orchestrator.py` (`_build_report_graph`).

## How it maps to the assignment's core requirements

| Requirement | Where |
|---|---|
| 1. Real agent loop (plan→act→observe→decide, multi-step) | `orchestrator.py` — LangGraph `StateGraph`: planner + concurrent gather + reflection cycle (critic → revise → critic) |
| 2. ≥2–3 tools, one can fail | World Bank (fails→fallback), Tavily web search (returns nothing→graceful), heuristic platform model, pgvector RAG |
| 3. Error handling & recovery | LLM retries, WB per-indicator retry+fallback, graceful tool degradation, Strategy re-planning |
| 4. State across steps | `RunState` (plan/observations/evidence/log) + client-side conversation memory + RAG cache |
| 5. Structured, grounded output + citations | pydantic-validated `Report` (`contracts.py`), real World Bank + Tavily source URLs |
| 6. Minimal evaluation (5–10 cases, defined correctness, pass/fail) | `backend/evals/` → `run_eval.py`, `eval_cases.py`, `RESULTS.md` (10/10 live) |
| 7. README | this file |

**Stretch goals done:** self-correction/reflection, ambiguity handling (clarifying questions),
guardrails (safety refusal + jurisdiction legality + indirect-prompt-injection defense),
fuzzy country/business matching, research-driven (cited) platform selection, cost/latency
awareness (tracking + a concurrency optimization), evaluation harness with metrics, and a
LangGraph `StateGraph` planner/executor multi-agent architecture.

---

## Run it locally

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY (TAVILY_API_KEY & DATABASE_URL optional)
python run_local.py         # http://localhost:8000  → /api/health
```

**Evaluation** (the deliverable — runs the 10 cases, prints pass/fail + metrics)
```bash
# against local backend (above), or a deployed one:
GTMSCOUT_API_BASE=http://localhost:8000 python -m evals.run_eval
```

**Tests** (offline, no keys): `python -m tests.test_units` · `python -m tests.test_contracts`

**Frontend**
```bash
cd frontend && npm install
printf "VITE_API_BASE=http://localhost:8000\nVITE_USE_MOCKS=false\n" > .env.local
npm run dev                 # http://localhost:8080
```
> With no `.env.local`, the UI runs on built-in **mock data** (no backend needed).

**Deploy:** two Vercel projects (backend + frontend) from one repo — backend root `backend/`
(env `OPENAI_API_KEY`; `TAVILY_API_KEY` + `DATABASE_URL` optional), frontend root `frontend/`
(env `VITE_API_BASE`, `VITE_USE_MOCKS=false`, `NITRO_PRESET=vercel`).

---

## Key design decisions & tradeoffs

- **LangGraph `StateGraph` for the agent loop.** The report loop
  (plan → gather → synthesize → critic → *revise* → deep_dive → assemble) is a compiled
  `StateGraph` with a typed state channel, conditional edges, and a real reflection **cycle**
  (critic → revise → critic). Nodes are plain functions and the agents/OpenAI client are unchanged,
  so LangGraph only owns the state transitions. The intake **router** (reply/refuse/comparison/
  ranking/new_report) stays plain Python — a graph would add nothing there. Tradeoff: `langchain-core`
  adds some serverless cold-start weight, accepted for the standard, inspectable structure
  (`_REPORT_GRAPH.get_graph()` renders the diagram). One deliberate detail: the `gather` node keeps
  a `ThreadPoolExecutor` internally so World Bank ∥ Tavily still run concurrently — LangGraph's sync
  executor would otherwise run same-superstep nodes serially and lose that speedup.
- **Agents, not functions.** Each agent owns a distinct reasoning domain with an explicit pydantic
  I/O contract (`contracts.py`), so they're independently testable/replaceable and individually
  cost-tracked. Tradeoff: more LLM calls (higher latency/cost) than one mega-prompt.
- **Bounded reflection (max 2 Strategy passes).** Real self-correction without infinite loops.
  Tradeoff: caps how much it can recover in one turn.
- **Research-driven platform selection, heuristic as fallback.** When live web research is available,
  the PlatformAgent picks and scores the platforms the research names as locally relevant — including
  country-specific ones a static table can't know (KakaoTalk/Naver in Korea, VK in Russia) — and the
  choice is cited. With no research (Tavily off/thin), it falls back to the hand-tuned heuristic model
  (`tools/platform_data.py`, *not* learned). This replaced `pytrends`, which pulled in `pandas` (heavy
  cold starts) and rate-limited constantly. Tradeoff: PlatformAgent now depends on ResearchAgent, so
  it runs after it rather than fully in parallel.
- **Stateless backend + client-side chat state.** Conversations/history/profile live in
  `localStorage`; no server DB for chat → trivial serverless hosting. Only the RAG cache is
  server-side (and optional).
- **Precomputed country data, not a runtime fetch.** ~249 countries are bundled offline
  (`country_codes_data.py`, generated from ISO-3166) → no runtime World Bank list call, no
  cold-start cost. Static data belongs at build time.
- **pgvector over a dedicated vector DB.** At this corpus size, vector search is just an index on
  Postgres I already have — no extra vendor/sync surface. Behind an interface, so swapping to
  Qdrant/Pinecone at scale is contained.
- **One optimization, measured:** the three independent gather tools run in **parallel**
  (`ThreadPoolExecutor`), and cold-start latency was cut by dropping `pandas`.

## Known limitations (honest)

- **Streaming is faked.** The UI's "Agent reasoning" stepper is an *optimistic client-side*
  animation; the backend returns a single POST, it does not stream tokens/steps. Real SSE is TODO.
- **Indirect prompt injection is defended in layers, not solved.** `ResearchAgent` now (1) drops web
  snippets containing injection markers via a deterministic scanner (`safety.scan_injection`),
  (2) wraps the remaining content in `<untrusted_web>` tags the system prompt marks as data-not-
  instructions (spotlighting), and (3) returns schema-constrained JSON. Backstop: that agent has no
  tools/side effects, so a bypass can only skew *text*, never *act*. Residual risk: a novel phrasing
  the scanner misses could still influence the wording — full immunity would need a dedicated
  guardrail model.
- **The Critic is strict.** In eval, it revised **3/3** report cases — it almost always triggers
  one revision, adding an LLM call. The `CONFIDENCE_FLOOR = 70` should be calibrated against a
  labelled quality set so it revises when it *helps*, not reflexively.
- **The platform model's *fallback* is a heuristic, not learned** — when web research is
  unavailable, platform scores are a relative signal, not empirical demand.
- **Eval checks structure/routing/directional verdicts, not prose factuality.** Judging the
  free-text analysis would need an LLM-as-judge or human rubric.
- **Guardrail on insufficient evidence is soft** — sparse-data markets get a low-confidence NOT YET
  with flags rather than an explicit "I don't have enough data to answer."
- **Fuzzy country/business matching is bounded.** Misspellings now auto-correct via `rapidfuzz`
  ("Phillipines" → Philippines), with a safety rail that refuses to silently guess between close
  neighbours (Iran/Iraq, Austria/Australia) and asks "did you mean X?" instead. Residual: a confident
  typo toward one clear neighbour (e.g. "Nigeer" → Niger) auto-resolves without asking.

## Scope & time-box (where I stopped, and why)

The brief suggests ~4–6 hours and prefers "a smaller thing done well." I went well beyond that — I
treated this as a learning project and kept iterating, adding depth on several stretch goals (RAG,
comparison/ranking modes, a full chat UI, deployment, safety hardening). A tight 4–6h version would
be: **the agent loop + 3 tools + error handling + the eval harness + this README** — the core
requirements. Everything past that is optional depth, and I've tried to keep each addition honestly
scoped, tested, and documented rather than half-finished. If I were resubmitting to spec, I'd cut
the comparison/ranking UI and the deployment polish and spend that time on the eval and tests
instead.

## How I used AI assistants

Built with  use of an AI coding assistant (Claude Code). I directed the architecture and made
the engineering-judgment calls — LangGraph `StateGraph` for the loop, agents vs functions, pgvector
vs a dedicated DB, precompute vs runtime fetch, research-driven vs heuristic platforms, the
injection-defense and safety approach — and reviewed,
ran, and tested the output (the eval harness and unit tests exist partly to keep the assistant
honest). The assistant accelerated implementation; the decisions and their justifications are mine.

## What I'd do with more time

1. **Real streaming** (SSE) so the reasoning trace is genuine, not optimistic.
2. **A dedicated guardrail model** for prompt injection (beyond the current scanner + spotlighting)
   + an LLM-as-judge eval for prose factuality.
3. **Calibrate the Critic** (confidence floor) against a labelled set; add a calculator/code tool
   so numeric claims are computed, not generated.
4. **Harden for scale** (the interview prompt): cache by (country, business), a request queue, a
   provider fallback for when OpenAI is down, and structured tracing/observability.
