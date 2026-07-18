# GTMScout — Architecture (as built)

> An agentic AI application. A user asks, in plain English, about expanding a business into a
> foreign market; a team of specialist agents produces a grounded market-entry brief — a
> **GO / PROCEED WITH CAUTION / NOT YET** verdict, platform strategy, budget allocation, risks,
> next steps, and citations — rendered inside a chat interface.

---

## 1. High-level shape

```
Frontend (React · TanStack Start)                Backend (FastAPI · Python, stateless)
─────────────────────────────────────           ──────────────────────────────────────
Chat UI, sidebar history, profile,     POST      Orchestrator
token-usage, light/dark theme slider  ──────►      IntakeAgent   (free text → request | clarify)
                                     /api/research  DataAgent     (World Bank + fallback)
Conversations + history + profile      ◄──────      PlatformAgent (interest model + LLM rationale)
persist in localStorage (no DB)         Message      StrategyAgent (verdict, budget, risks, steps)
                                       (Report)      CriticAgent   (verify claims, adjust confidence)
                                                   OpenAI gpt-4o-mini
```

Two independent Vercel deployments (one repo): **backend** (Python serverless) and **frontend**
(TanStack Start). They connect via `VITE_API_BASE` + CORS.

## 2. Why stateless + client-side state
The backend does exactly one thing: `message text → assistant Message`. Conversation list,
message history, and the user profile (including cumulative token usage) live in the browser's
`localStorage`, surfaced through the frontend's single data module `src/services/api.ts`.

- No database, no session store → trivial to run on serverless (no cold-start DB, no migrations).
- The same `api.ts` runs on **mock data** (no backend) or the **real backend** via one env flag,
  so the UI is always demoable.

## 3. The agent pipeline (`backend/orchestrator.py`)
1. **IntakeAgent** — parses the chat message into `{target_country, business_type, home_country,
   budget, currency}` or returns a clarifying question if country/business is missing.
2. **DataAgent** — pulls World Bank indicators (population, GDP/capita, internet %, mobile subs);
   falls back to curated recent figures if the API is slow/unreachable. Emits structured
   `market_data` + a citation.
3. **PlatformAgent** — scores platforms for the country + business category
   (`tools/platform_data.py`), and the LLM writes a specific rationale per platform. Returns a
   ranked `platform_recommendations` list.
4. **StrategyAgent** — synthesizes verdict, confidence, executive summary, budget allocation
   (normalized to sum to the budget), risks, and next steps. Structured JSON.
5. **CriticAgent** — reviews the brief against the data, produces `verification.flags`, and
   returns a confidence delta (self-correction / grounding check).

The orchestrator aggregates token usage + USD cost across all five agents and assembles the
final `Report`.

## 4. Tools (`backend/tools/`)
- `worldbank.py` — live World Bank API (concurrent requests, per-indicator timeout) with a
  curated fallback so a run never hard-fails.
- `platform_data.py` — lean, category-weighted platform-interest model (0–100). Replaces the
  original `pytrends` tool on the deployed path — `pytrends` drags in `pandas` (heavy cold
  starts) and rate-limits constantly, which is fatal on serverless. `web_search.py` (the original
  pytrends implementation) is kept for reference/local use.
- `calculator.py` — deterministic budget/growth/comparison math.

## 5. API contract
**`POST /api/research`**
```json
{ "text": "Should my fast-fashion brand expand into Japan with a $20k budget?",
  "home_country": null, "budget": null, "currency": null }
```
`home_country` / `budget` / `currency` are optional overrides; if null they're parsed from `text`.

**Returns a `Message`:**
- `{ "kind": "text", "text": "...clarifying question..." }` — when the message isn't a complete
  market question, or a data/strategy step fails gracefully, or
- `{ "kind": "report", "report": Report }` — the full brief.

**`Report`** (mirrors `frontend/src/services/types.ts`): `id, request, verdict, confidence,
executive_summary, market_data, platform_recommendations[], budget_allocation[], risks[],
next_steps[], citations[], cost{total_tokens_in,total_tokens_out,usd,per_agent[]},
verification{checked,flags[],note}, agent_briefs{data,platform,strategy}`.

**`GET /api/health`** → `{ status, model, openai_key_present }`.

## 6. Frontend integration points
- `src/services/api.ts` — conversations/profile CRUD (localStorage) in both modes; `sendMessage`
  posts to `/api/research` in real mode and animates an optimistic agent stepper while awaiting
  the single response. Token usage updates from `report.cost` after each run.
- `src/services/types.ts` — the shared shapes; keep in sync with the backend Report.
- Mode switch: `VITE_API_BASE` set → real backend; empty → mocks (`VITE_USE_MOCKS` can force either).

## 7. Hosting
- **Backend**: Vercel project, Root Directory `backend`, Python 3.12 runtime, `maxDuration 60s`
  (`vercel.json`). Env: `OPENAI_API_KEY`, `FRONTEND_ORIGIN`.
- **Frontend**: Vercel project, Root Directory `frontend`, `NITRO_PRESET=vercel` so the TanStack
  Start/Nitro build emits Vercel Build Output. Env: `VITE_API_BASE`, `VITE_USE_MOCKS=false`.

See [README.md](README.md) for step-by-step deploy instructions.
