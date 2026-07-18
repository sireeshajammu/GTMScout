# GTMScout — AI Market-Entry Advisor

GTMScout is a conversational, multi-agent AI app. You ask a plain-English question like
*"Should my fast-fashion brand expand into Japan with a $20k budget?"* and a team of
specialist agents researches the market and replies with a full **market-entry brief**:
a verdict (GO / PROCEED WITH CAUTION / NOT YET), platform strategy, budget allocation,
risks, next steps, citations, and token cost — all inside a ChatGPT/Claude-style chat UI.

```
┌────────────────────────────────────────────┐        ┌───────────────────────────────┐
│  Frontend  (React · TanStack Start)          │        │  Backend  (FastAPI · Python)   │
│  • chat UI, sidebar history, profile,        │  POST  │  Orchestrator                  │
│    token usage, light/dark theme slider      │ ─────► │   Intake → Data → Platform     │
│  • conversations + history + profile persist │ /api/  │        → Strategy → Critic      │
│    in localStorage (no DB needed)            │research│  OpenAI gpt-4o-mini            │
│  • VITE_API_BASE points at the backend       │ ◄───── │  World Bank API · interest     │
│                                              │  JSON  │  model · budget calculator     │
└────────────────────────────────────────────┘ (Report)└───────────────────────────────┘
```

The backend is **stateless** — its one job is to turn a message into a report. All
conversation/history/profile state lives client-side, which keeps hosting simple.

---

## Repository layout

```
market-research-agent/            (GTMScout)
├── backend/                      Python FastAPI service (deploy as Vercel project #1)
│   ├── api/index.py              Vercel serverless entry (exposes the ASGI app)
│   ├── main.py                   FastAPI app: /api/research, /api/health
│   ├── orchestrator.py           Chains the agents → assembles the Report
│   ├── agents/                   base, intake, data, platform, strategy, critic
│   ├── tools/                    worldbank (live+fallback), platform_data, calculator
│   │                             (web_search.py = original pytrends tool, kept for reference)
│   ├── config.py                 model + pricing config
│   ├── requirements.txt
│   ├── vercel.json               maxDuration + routing
│   ├── .env.example              → copy to .env with your OPENAI_API_KEY
│   └── tests/                    test_pipeline.py, test_worldbank.py, test_calculator.py
├── frontend/                     TanStack Start app from Lovable (deploy as Vercel project #2)
│   ├── src/services/api.ts       the ONLY data layer (mock ⇄ real backend switch)
│   ├── src/services/types.ts     shared TypeScript shapes (mirror of the backend Report)
│   └── .env.example              → VITE_API_BASE
├── ARCHITECTURE.md               design + rationale
└── README.md                     you are here
```

---

## Run it locally

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate       macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env and add your OPENAI_API_KEY
python run_local.py           # serves http://localhost:8000
```
Sanity check: open http://localhost:8000/api/health → `{"status":"ok", ...}`.
Optional: `python -m tests.test_pipeline --live` runs the full pipeline once.

### 2. Frontend
```bash
cd frontend
npm install
# point the UI at the backend:
echo "VITE_API_BASE=http://localhost:8000" > .env.local
echo "VITE_USE_MOCKS=false"                >> .env.local
npm run dev                   # serves http://localhost:8080
```
> Leave `.env.local` out entirely and the UI runs on built-in **mock data** (no backend
> needed) — handy for frontend-only work.

---

## Deploy to Vercel (two projects, one repo)

Push this repo to GitHub, then create **two** Vercel projects from it.

### Project #1 — Backend (Python)
1. **New Project** → import the repo → set **Root Directory = `backend`**.
2. Framework preset: **Other** (Vercel auto-detects the Python function in `api/`).
3. **Environment Variables**:
   - `OPENAI_API_KEY` = your key
   - `FRONTEND_ORIGIN` = your frontend URL once you have it (e.g. `https://gtmscout.vercel.app`) — or `*` to start.
4. Deploy. Note the URL, e.g. `https://gtmscout-api.vercel.app`.
   Verify: `https://gtmscout-api.vercel.app/api/health`.

> Vercel runs Python **3.12** for functions (wheels for all deps exist there — no build step needed).
> `vercel.json` already sets `maxDuration: 60s`, comfortably above a normal ~10–25s run.

### Project #2 — Frontend (TanStack Start)
1. **New Project** → import the same repo → set **Root Directory = `frontend`**.
2. Framework preset: **Vite** (or "Other" — the build command is `npm run build`).
3. **Environment Variables**:
   - `VITE_API_BASE` = the backend URL from step #1 (e.g. `https://gtmscout-api.vercel.app`)
   - `VITE_USE_MOCKS` = `false`
   - `NITRO_PRESET` = `vercel`  ← ensures the server build targets Vercel's Build Output API
4. Deploy. Open the URL and ask a question.
5. Go back to the **backend** project and set `FRONTEND_ORIGIN` to this frontend URL, then redeploy
   the backend (tightens CORS from `*` to just your site).

That's it — the frontend calls `${VITE_API_BASE}/api/research`, CORS is handled, and history/profile
persist in the browser.

### Environment variables at a glance
| Where | Variable | Value |
|-------|----------|-------|
| Backend | `OPENAI_API_KEY` | your OpenAI key |
| Backend | `FRONTEND_ORIGIN` | frontend URL (or `*`) |
| Frontend | `VITE_API_BASE` | backend URL |
| Frontend | `VITE_USE_MOCKS` | `false` |
| Frontend | `NITRO_PRESET` | `vercel` |

---

## Design notes
- **OpenAI `gpt-4o-mini`** is the model throughout (your integration, preserved). Cost is
  estimated from live token counts in `config.py`.
- **World Bank** is a live API call with a curated fallback, so a slow/blocked API never breaks a run.
- **Google Trends / `pytrends` was intentionally dropped from the deployed path** — it pulls in
  `pandas` (heavy cold starts) and rate-limits constantly, which is fatal on serverless. It's
  replaced by a lean, category-weighted interest model (`tools/platform_data.py`) that the
  PlatformAgent reasons over. The original `tools/web_search.py` remains for reference/local use.
- **CriticAgent** re-checks the brief against the data and adjusts confidence — the app's
  self-verification step, and its most distinctive "agentic" feature.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and the API contract.
