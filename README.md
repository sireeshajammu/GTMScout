# GTMScout

An agentic market-entry research assistant. Tell it a country, a business type, and a budget —
*"a fintech app in Brazil with $20k"* — and it comes back with a go/no-go call: real population and
GDP figures, which marketing platforms to spend on, how to split the budget, the risks, and what to
do first. Every fact carries a citation.

It's not one model answering a prompt. It's about ten small agents, each doing one job, run by a
LangGraph state machine that decides what to call and checks the result before it ships.

**Live app:** https://gtm-scout.vercel.app · **API health:** https://gtm-scout-api.vercel.app/api/health
**Model:** OpenAI `gpt-4o-mini` (~$0.002 per full brief).

## How it works

A report question runs through a plan-act-observe-decide loop:

```
Intake (route + parse)               ← is this a report, a comparison, a ranking, or small talk?
   │  new_report
   ▼
Planner            → picks which tools are worth running
Gather             → World Bank data ∥ web research (concurrent), then platform ranking
Strategy           → writes the verdict: GO / PROCEED WITH CAUTION / NOT YET
Critic             → checks it against the data ─┐  if flags or confidence < 70 (max 2x)
   ▲                                             │
   └──────── Strategy (revise with criticism) ◄──┘
   ▼  critic satisfied
Deep-dive          → competitors, unit economics, regulatory, GTM timeline
Assemble           → validate schema, attach citations + cost, return
```

The intake router also handles three other intents: a clarifying question when the ask is
incomplete, a refusal for illegal businesses, a side-by-side comparison of markets already analyzed,
and a ranking across several candidate markets. The report graph itself is in
`backend/orchestrator.py` (`_build_report_graph`).

## Run it locally

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY (TAVILY_API_KEY & DATABASE_URL are optional)
python run_local.py         # http://localhost:8000  → /api/health
```

**Frontend**
```bash
cd frontend && npm install
printf "VITE_API_BASE=http://localhost:8000\nVITE_USE_MOCKS=false\n" > .env.local
npm run dev                 # http://localhost:8080
```
With no `.env.local`, the UI runs on built-in mock data, so you can see it without a backend.

**Deploy:** two Vercel projects from one repo — backend root `backend/` (env `OPENAI_API_KEY`;
`TAVILY_API_KEY` and `DATABASE_URL` optional), frontend root `frontend/` (env `VITE_API_BASE`,
`VITE_USE_MOCKS=false`, `NITRO_PRESET=vercel`).

## Configuration

| Variable | Where | Needed? |
|---|---|---|
| `OPENAI_API_KEY` | backend | Yes |
| `TAVILY_API_KEY` | backend | Optional — enables live web research; without it you get fewer findings |
| `DATABASE_URL` | backend | Optional — Postgres + pgvector for the research cache; no-ops if unset |
| `VITE_API_BASE` | frontend | Points the UI at the backend |

## Evaluation and tests

The eval harness runs 10 cases with deterministic pass/fail checks — structure, routing, directional
verdict, tool-call success, self-correction rate, latency, and dollar cost. Last run: 10/10, ~8.8s
and ~$0.002 per report.

```bash
GTMSCOUT_API_BASE=http://localhost:8000 python -m evals.run_eval
```

Offline unit and contract tests (no API keys):
```bash
python -m tests.test_units       # safety, fuzzy matching, injection scanner, budget/country logic
python -m tests.test_contracts   # pydantic I/O contracts
```

## Design decisions and tradeoffs

These are the five calls I'd defend in a review.

1. **Ten small agents, not one big prompt.** Each agent has a fixed pydantic input/output contract,
   so structured data flows between them and I can test, swap, or cost-track any one in isolation. I
   started with a single mega-prompt and threw it out — you can't tell a fact from a guess in that
   output, and you can't fix one part without risking another. The cost is more LLM calls, so more
   latency and spend than one call would take.

2. **A planner that picks tools, instead of a fixed pipeline.** For a well-known market the planner
   can skip live web search or the deep-dive, so cheap questions stay cheap. The tradeoff: it's an
   extra LLM call, and today it really only controls web research and the deep-dive — the data fetch
   and platform ranking always run.

3. **LangGraph state graph for the loop.** The report path is a compiled `StateGraph` with typed
   shared state, conditional edges, and a critic → revise cycle. I get a standard, inspectable
   structure I can draw and reason about instead of a tangle of `if` statements. The cost is that
   `langchain-core` adds weight to serverless cold starts.

4. **Facts come from APIs, the model only reasons.** Population and GDP come from the World Bank;
   competitors and market signals from live web search; the budget math is recomputed in Python after
   the model answers. The model never invents a number. The limit is that I'm bounded by what those
   sources cover, and one model does every reasoning step.

5. **Parallel tools with a fallback for everything.** The two independent I/O tools run concurrently,
   and nothing hard-fails: World Bank falls back per indicator, web search returns empty, platforms
   fall back to a hand-tuned table, the cache no-ops without a database. The tradeoff is that the
   concurrency lives inside one graph node rather than as separate graph branches, and the pgvector
   cache currently runs *alongside* web search rather than in front of it, so it doesn't cut API
   calls yet.

## Known limitations

- Streaming is faked: the "reasoning" stepper in the UI is a client-side animation; the backend
  returns one response.
- The critic is strict — it revises almost every report, which adds a call each time. Its confidence
  floor should be calibrated against labeled data.
- Prompt-injection defense on web content is layered (a scanner, spotlighting, no side effects), not
  a proof; a novel phrasing could still slip through the scanner.
- The two web searches run sequentially, so a slow run can approach the serverless timeout.
- The eval checks structure and routing, not the factuality of the prose.

## Future work

- **Multi-model routing.** Use a stronger model for the critic than for drafting, and cheaper models
  for narrow steps, instead of running `gpt-4o-mini` everywhere. Match the model to the task.
- **Cache-first retrieval.** Query the pgvector cache before calling Tavily, and only hit the web on
  a weak or stale cache miss, with rules for when a live call is even warranted. That turns the cache
  into a real cost saver rather than extra context.
- **Broader evaluation.** Add faithfulness/factuality scoring (for example with DeepEval) on top of
  the current structural checks, alongside the latency, cost, and task-success metrics already
  tracked.
- **Auth and rate limiting.** Add authentication and per-user authorization, plus rate limiting so
  100 users can't turn into 1000 Tavily calls: a request queue, concurrency limits, retries with
  exponential backoff, and a per-account spend cap.
- **Scale and observability.** Move past a single serverless function to horizontal scaling with
  caching and background processing, and add request tracing plus token/cost metrics so a bad report
  can be traced and reproduced.

## A note on process

I used an AI assistant to help with background research and to move faster on boilerplate. The
architecture, the tradeoffs above, and the decisions behind them are mine.
