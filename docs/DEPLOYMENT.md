# GTMScout — Step-by-step Vercel deployment

Two Vercel projects from **one** GitHub repo:
- **Backend** (Python/FastAPI) → its own Vercel project, Root Directory = `backend`
- **Frontend** (TanStack Start) → its own Vercel project, Root Directory = `frontend`

Total time: ~15 minutes.

---

## Prerequisites
- A **GitHub** account.
- A **Vercel** account (sign up at vercel.com with "Continue with GitHub" — easiest).
- Your **OpenAI API key** (you already have it in `backend/.env`).

---

## Part 1 — Put the code on GitHub

Your project isn't a git repo yet. `node_modules/`, `.venv/`, and `.env` are already gitignored,
so secrets and huge folders won't be uploaded.

### 1a. Create the repo on GitHub (web)
1. Go to https://github.com/new
2. **Repository name**: `gtmscout` (anything is fine).
3. Choose **Private** (recommended) or Public.
4. **Do NOT** check "Add a README / .gitignore / license" — the repo already has them.
5. Click **Create repository**. Leave the page open — you'll need the URL it shows, which looks
   like `https://github.com/<you>/gtmscout.git`.

### 1b. Push your local code (run in the project folder)
Open a terminal in `C:\Users\srisi\Desktop\market-research-agent` and run:
```bash
git init
git add .
git commit -m "GTMScout: multi-agent market-entry advisor (backend + frontend)"
git branch -M main
git remote add origin https://github.com/<you>/gtmscout.git   # <-- use YOUR url from 1a
git push -u origin main
```
If Git asks you to sign in, use the browser prompt (GitHub Credential Manager) — no password typing.

Refresh the GitHub page; you should see `backend/`, `frontend/`, `README.md`, etc.

---

## Part 2 — Deploy the Backend (Vercel project #1)

1. Go to https://vercel.com/dashboard → **Add New… → Project**.
2. Under **Import Git Repository**, find `gtmscout` and click **Import**.
   - First time only: Vercel asks to install its GitHub app / grant repo access. Allow it for this repo.
3. On the **Configure Project** screen:
   - **Project Name**: `gtmscout-api` (this becomes your URL, e.g. `gtmscout-api.vercel.app`).
   - **Framework Preset**: **Other**.
   - **Root Directory**: click **Edit** → select the **`backend`** folder → **Continue**.
   - **Build and Output Settings**: leave everything empty (Python functions need no build step).
4. Expand **Environment Variables** and add:
   | Key | Value |
   |-----|-------|
   | `OPENAI_API_KEY` | your OpenAI key |
   | `FRONTEND_ORIGIN` | `*`  (tighten this in Part 4) |
5. Click **Deploy** and wait for it to finish.
6. **Verify**: open `https://<your-backend>.vercel.app/api/health`
   → you should see `{"status":"ok","model":"gpt-4o-mini","openai_key_present":true}`.
   - If `openai_key_present` is `false`, the env var didn't save — re-add it and redeploy.

**Copy the backend URL** — you need it next.

> Notes: Vercel runs **Python 3.12** for functions (all dependencies have prebuilt wheels there —
> the local Python 3.14 wheel issue does not apply). `backend/vercel.json` already routes all
> requests to the FastAPI app and sets `maxDuration: 60s`.

---

## Part 3 — Deploy the Frontend (Vercel project #2)

1. Dashboard → **Add New… → Project** → import the **same** `gtmscout` repo again.
   (Yes, you import the same repo a second time — that's how one repo becomes two projects.)
2. On **Configure Project**:
   - **Project Name**: `gtmscout` (→ `gtmscout.vercel.app`).
   - **Framework Preset**: **Vite**.
   - **Root Directory**: click **Edit** → select the **`frontend`** folder → **Continue**.
   - Leave Build/Output settings at their defaults (build command `npm run build`).
3. Add **Environment Variables**:
   | Key | Value |
   |-----|-------|
   | `VITE_API_BASE` | your backend URL from Part 2 (e.g. `https://gtmscout-api.vercel.app`) — no trailing slash |
   | `VITE_USE_MOCKS` | `false` |
   | `NITRO_PRESET` | `vercel` |
4. Click **Deploy**.
5. Open the frontend URL, type a question (e.g. *"Is Brazil good for a consumer app with $15k?"*),
   and you should see the agent stepper run and a report appear.

> If the build errors with something about an **output directory** (e.g. expecting `dist`):
> go to the frontend project → **Settings → General → Framework Preset = Other**, set
> **Build Command = `npm run build`**, leave **Output Directory blank**, and redeploy. This forces
> Vercel to use the Nitro build output (`.vercel/output`) that `NITRO_PRESET=vercel` produces.

---

## Part 4 — Lock down CORS (recommended)

Right now the backend accepts requests from anywhere (`FRONTEND_ORIGIN=*`). Restrict it:
1. Go to the **backend** project → **Settings → Environment Variables**.
2. Edit `FRONTEND_ORIGIN` → set it to your exact frontend URL, e.g. `https://gtmscout.vercel.app`
   (no trailing slash; no path).
3. **Redeploy** the backend: **Deployments** tab → the latest one → **⋯ → Redeploy**.

---

## Part 5 — Final check
- `https://<backend>/api/health` → ok, key present.
- Frontend loads, you can send a question, the report renders, and the sidebar token usage ticks up.
- Reload the page → your conversation is still there (it's saved in the browser's localStorage).

---

## Troubleshooting
| Symptom | Fix |
|---------|-----|
| Frontend shows "couldn't reach the research backend" | `VITE_API_BASE` is wrong/empty, or CORS. Confirm it's the exact backend URL with no trailing slash; make sure `FRONTEND_ORIGIN` includes your frontend origin (or `*`). Re-check in browser devtools → Network → `research` request. |
| `/api/health` shows `openai_key_present: false` | `OPENAI_API_KEY` not set on the **backend** project. Add it, redeploy. |
| Backend 500 on a question | Check the backend project → **Logs**. Usually an invalid/again-limited OpenAI key. |
| Frontend build fails on output directory | Switch its Framework Preset to **Other**, Build Command `npm run build`, Output Directory blank (see Part 3 note). |
| Function timeout | A run is normally 10–25s; `maxDuration` is 60s. If OpenAI is slow, just retry. |
| Changes don't show | Each `git push` to `main` auto-redeploys both projects. Confirm the push succeeded. |

## Updating later
Any `git push` to `main` triggers a redeploy of **both** projects automatically. Environment
variable changes require a manual **Redeploy** from the Deployments tab.
