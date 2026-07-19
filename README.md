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
Intake (route/parse/refuse) → Planner (pick tools) → gather in PARALLEL
   [DataAgent · ResearchAgent · PlatformAgent]  → StrategyAgent → CriticAgent
        │                                              ▲             │  conditional edge:
   RunState carries plan + observations +              └── replan ───┘  unsupported claims
   evidence + reasoning-log through the loop           (re-run Strategy)  OR confidence < 70
        │                                                    │
                                                       DeepDiveAgent → assemble + validate Report
```

It also routes non-report intents: **clarify** (under-specified), **refuse** (illegal business),
**comparison** (side-by-side of analyzed markets), and **ranking** (score several markets). Full
design in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## How it maps to the assignment's core requirements

| Requirement | Where |
|---|---|
| 1. Real agent loop (plan→act→observe→decide, multi-step) | `orchestrator.py` — planner + parallel gather + reflection/replan edge (`RunState`) |
| 2. ≥2–3 tools, one can fail | World Bank (fails→fallback), Tavily web search (returns nothing→graceful), heuristic platform model, pgvector RAG |
| 3. Error handling & recovery | LLM retries, WB per-indicator retry+fallback, graceful tool degradation, Strategy re-planning |
| 4. State across steps | `RunState` (plan/observations/evidence/log) + client-side conversation memory + RAG cache |
| 5. Structured, grounded output + citations | pydantic-validated `Report` (`contracts.py`), real World Bank + Tavily source URLs |
| 6. Minimal evaluation (5–10 cases, defined correctness, pass/fail) | `backend/evals/` → `run_eval.py`, `eval_cases.py`, `RESULTS.md` (10/10 live) |
| 7. README | this file |

**Stretch goals done:** self-correction/reflection, ambiguity handling (clarifying questions),
guardrails (safety refusal + jurisdiction legality), cost/latency awareness (tracking + a
parallelization optimization), evaluation harness with metrics, and a planner/executor
multi-agent state-graph architecture.

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

**Deploy:** two Vercel projects (backend + frontend) from one repo — full click-by-click in
**[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## Key design decisions & tradeoffs

- **Hand-rolled state machine, not LangGraph.** The graph is small; I wanted to explain every
  transition and keep serverless cold-starts lean (no `langchain-core`). The nodes/edges map 1:1
  to a `StateGraph`, so porting is contained. Tradeoff: I reimplement a little plumbing LangGraph
  gives for free.
- **Agents, not functions.** Each agent owns a distinct reasoning domain with an explicit pydantic
  I/O contract (`contracts.py`), so they're independently testable/replaceable and individually
  cost-tracked. Tradeoff: more LLM calls (higher latency/cost) than one mega-prompt.
- **Bounded reflection (max 2 Strategy passes).** Real self-correction without infinite loops.
  Tradeoff: caps how much it can recover in one turn.
- **Dropped `pytrends` for a transparent heuristic platform model.** `pytrends` pulls in `pandas`
  (heavy serverless cold starts) and rate-limits constantly. The heuristic is honest (hand-tuned
  weights, *not* learned) and the LLM reasons on top.
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
- **Indirect prompt injection is unhandled.** `ResearchAgent` feeds raw Tavily web content to the
  LLM; a malicious page could try to inject instructions. The safety gate only screens *user*
  input, not *tool* output.
- **The Critic is strict.** In eval, it revised **3/3** report cases — it almost always triggers
  one revision, adding an LLM call. The `CONFIDENCE_FLOOR = 70` should be calibrated against a
  labelled quality set so it revises when it *helps*, not reflexively.
- **The platform model is a heuristic, not learned** — a relative signal, not empirical demand.
- **Eval checks structure/routing/directional verdicts, not prose factuality.** Judging the
  free-text analysis would need an LLM-as-judge or human rubric.
- **Guardrail on insufficient evidence is soft** — sparse-data markets get a low-confidence NOT YET
  with flags rather than an explicit "I don't have enough data to answer."
- **Country matching isn't fuzzy** — "Phillipines" (misspelled) still fails.

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

Built with heavy use of an AI coding assistant (Claude Code). I directed the architecture and made
the engineering-judgment calls — hand-rolled loop vs LangGraph, agents vs functions, pgvector vs a
dedicated DB, precompute vs runtime fetch, dropping `pytrends`, the safety approach — and reviewed,
ran, and tested the output (the eval harness and unit tests exist partly to keep the assistant
honest). The assistant accelerated implementation; the decisions and their justifications are mine.

## What I'd do with more time

1. **Real streaming** (SSE) so the reasoning trace is genuine, not optimistic.
2. **Tool-output sanitization** against indirect prompt injection + an LLM-as-judge eval for prose.
3. **Calibrate the Critic** (confidence floor) against a labelled set; add a calculator/code tool
   so numeric claims are computed, not generated.
4. **Harden for scale** (the interview prompt): cache by (country, business), a request queue, a
   provider fallback for when OpenAI is down, and structured tracing/observability.
