# Lovable Prompt — GlobalReach frontend (conversational / chat UI)

> Paste everything inside the code fence below into Lovable as your first message.
> The app is a **ChatGPT/Claude-style chat interface** for your market-research agent team.
> It looks and works fully on **mock data**, but routes everything through one **typed service
> layer** (`src/services/api.ts`) so I can point it at the real FastAPI backend by flipping one
> flag. The structured market-entry brief renders as a **rich card inside an assistant message**,
> the way Claude/ChatGPT render rich content.

---

```
Build a polished, production-quality React web app called "GlobalReach" — a conversational
AI assistant for market-entry research. It should look and feel like ChatGPT / Claude: a
left sidebar with chat history and a user profile, a central conversation thread, and a
chat input field pinned to the bottom.

WHAT IT DOES
The user chats with a team of AI research agents. They ask things like "Should my fast-fashion
brand expand into Japan with a $20k budget?" The agents research the market and reply with a
market-entry brief: a verdict (GO / PROCEED WITH CAUTION / NOT YET), platform strategy, budget
allocation, risks, and citations. Follow-up questions continue the same conversation.

OVERALL LAYOUT (three regions)
1. LEFT SIDEBAR (collapsible, ~280px, like ChatGPT):
   - Top: a "＋ New chat" button and the "GlobalReach" wordmark/logo.
   - Middle: "Chat history" — a scrollable list of past conversations grouped by
     Today / Yesterday / Previous 7 days. Each item shows the conversation title (auto-generated
     from the first message, e.g. "Japan · fast fashion") and is clickable to open it. The active
     conversation is highlighted. Hovering a row reveals rename and delete icons.
   - Bottom: a USER PROFILE card, always visible:
       * Avatar + display name + email.
       * A "Token usage" mini-panel: total tokens used (in + out), estimated cost in USD, and
         number of analyses run. Show a small usage progress bar against a monthly quota
         (e.g. 2,000,000 tokens). Clicking it opens a Profile / Usage modal (see below).
   - The sidebar can collapse to a thin rail (icon-only) via a toggle, and is a slide-over
     drawer on mobile.

2. MAIN AREA — the conversation:
   - A top bar showing the current conversation title and, on the right, the THEME SLIDER
     (see below) plus a "usage" pill showing tokens used this session.
   - The message thread:
       * User messages: right-aligned bubbles (or ChatGPT-style full-width rows with an avatar).
       * Assistant messages: left-aligned with a small agent avatar. An assistant message can be:
           (a) plain markdown text (clarifying questions, follow-up answers), OR
           (b) a rich MARKET-ENTRY BRIEF card (see "brief card" below), OR
           (c) a live "thinking" state while the agents work.
   - EMPTY STATE (new chat): a centered welcome — product name, one-line description, and 3–4
     example prompt chips the user can click to autofill the input (e.g. "Expand a consumer app
     into Brazil ($15k)", "Is Germany good for B2B SaaS?", "Compare Japan vs. UK for fast fashion").

3. CHAT INPUT (pinned to bottom of the main area, like ChatGPT/Claude):
   - An auto-growing multiline textarea with placeholder "Ask about a market… (country, business
     type, budget)".
   - A send button (arrow icon), disabled while a response is streaming. Enter sends,
     Shift+Enter = newline.
   - A subtle helper row under it: a small note "Agents: Data · Platform · Strategy · Critic"
     and a token estimate. Keep it clean.

THEME SLIDER (explicit requirement)
- A sliding toggle switch (iOS-style pill that slides left↔right) in the top bar, with a sun
  icon on the light side and a moon icon on the dark side. Sliding it animates the whole app
  between light and dark mode. Persist the choice to localStorage and respect the OS preference
  on first load.
- Light mode: near-white background, deep ink text. Dark mode: deep slate/ink background
  (#0F172A family), soft off-white text. One accent color (indigo/violet) used consistently.
  Verdict colors are semantic in BOTH themes: GO = emerald, PROCEED WITH CAUTION = amber,
  NOT YET = red.

THE "THINKING" STATE (agentic transparency — make this feel alive)
- When the user sends a market question, immediately show an assistant message containing an
  animated AGENT STEPPER: DataAgent → PlatformAgent → StrategyAgent → CriticAgent.
- Each step shows status (queued / running / done / error) with a spinner→check, and a short
  live message (e.g. "Fetching World Bank data for Japan…", "Comparing 5 platforms…",
  "Checking claims against sources…"). Completed steps collapse to a green check with elapsed
  time. Use a subtle shimmer while running.
- When done, the stepper smoothly gives way to the rich brief card in the same message.

THE MARKET-ENTRY BRIEF CARD (assistant rich message)
Rendered inline inside the assistant bubble. Compact but rich, expandable:
- Header: a large color-coded VERDICT badge, a confidence meter (0–100 radial or bar), the
  target country + business type, and the executive summary paragraph.
- Collapsible sections (accordion or tabs) inside the card:
   * Market data: stat tiles (Population, GDP per capita, Internet penetration %, Mobile
     subscriptions) each with data year and a "World Bank" source chip.
   * Platforms: a horizontal bar chart of interest_score (0–100) per platform + rank + rationale.
   * Budget: a donut chart of budget_allocation by platform, plus a table (platform, %, $amount),
     with the total budget.
   * Risks: cards with a severity pill (low/med/high), title, description.
   * Next steps: a checklist.
   * Cost: tokens (in/out) + USD for this analysis, and a tiny per-agent bar chart.
- A "Citations" footer: numbered sources (World Bank, Google Trends) with detail text and
  external-link icons; claims may show superscript citation numbers.
- If report.verification.flags is non-empty, show an amber "Verification notes" strip listing
  what the Critic agent flagged.
- Card action buttons: "Export PDF", "Export Markdown", "Copy".

PROFILE / USAGE MODAL (opened from the sidebar profile card)
- Shows avatar, display name, email (editable form fields, local only for now).
- Usage dashboard: total tokens in/out, total USD cost, total analyses run, and a bar chart of
  tokens over the last several analyses. A monthly quota progress bar.
- A theme preference row (mirrors the slider). Close button.

GLOBAL BEHAVIOR
- Toasts for success/error. Skeleton loaders for async loads. Friendly empty states.
- Fully responsive: sidebar becomes a drawer on mobile; brief card sections stack.
- Accessible: keyboard navigable, ARIA labels, good contrast in both themes.
- Smooth, restrained motion (message fade/slide-in, streaming shimmer, theme cross-fade).
- Typography: Inter for UI, a monospace for numbers/metrics.

DATA LAYER — VERY IMPORTANT
Create ONE file `src/services/api.ts` that is the ONLY source of data. It must:
- Export `const API_BASE = import.meta.env.VITE_API_BASE ?? ""` and a `USE_MOCKS = true` flag.
- Export typed async functions:
    * `listConversations(): Promise<ConversationSummary[]>`
    * `getConversation(id): Promise<Conversation>`
    * `createConversation(): Promise<Conversation>`
    * `renameConversation(id, title)`, `deleteConversation(id)`
    * `sendMessage(conversationId, text, onEvent): Promise<Message>` — this is the core call.
      While running it should emit ProgressEvents to the onEvent callback (simulate a realistic
      streaming sequence over ~4–7s in mock mode) and finally resolve with the assistant Message
      (which for a market question contains a `report`).
    * `getProfile(): Promise<Profile>`
- When USE_MOCKS is true, all of the above return realistic mock data with delays and a simulated
  streaming sequence. When false, call `${API_BASE}/api/...` with fetch, and use EventSource for
  the streaming progress.
- Keep all TypeScript types in `src/services/types.ts` matching EXACTLY the shapes below.

TYPES (use these field names precisely):
- ResearchRequest: { target_country: string; business_type: string; home_country: string;
  budget: number; currency: string }
- MarketData: { population: number; gdp_per_capita: number; internet_penetration: number;
  mobile_subscriptions: number; data_year: string }
- PlatformRec: { platform: string; interest_score: number; rank: number; rationale: string }
- BudgetItem: { platform: string; percentage: number; amount: number }
- Risk: { title: string; severity: "low" | "medium" | "high"; description: string }
- Citation: { id: number; source: string; detail: string; url: string | null }
- CostAgent: { agent: string; tokens_in: number; tokens_out: number }
- Cost: { total_tokens_in: number; total_tokens_out: number; usd: number; per_agent: CostAgent[] }
- Verification: { checked: boolean; flags: string[]; note: string }
- Report: { id: string; request: ResearchRequest;
  verdict: "GO" | "PROCEED WITH CAUTION" | "NOT YET"; confidence: number;
  executive_summary: string; market_data: MarketData; platform_recommendations: PlatformRec[];
  budget_allocation: BudgetItem[]; risks: Risk[]; next_steps: string[]; citations: Citation[];
  cost: Cost; verification: Verification;
  agent_briefs: { data: string; platform: string; strategy: string } }
- ProgressEvent: { agent: string; status: "queued" | "running" | "done" | "error";
  message: string; timestamp: string }
- Message: { id: string; role: "user" | "assistant";
  kind: "text" | "report"; text?: string; report?: Report; created_at: string }
- ConversationSummary: { id: string; title: string; created_at: string; updated_at: string }
- Conversation: { id: string; title: string; created_at: string; updated_at: string;
  messages: Message[] }
- Profile: { name: string; email: string; avatar_url: string | null;
  usage: { total_tokens_in: number; total_tokens_out: number; total_usd: number;
  runs_count: number; monthly_quota_tokens: number } }

Seed mocks with 3 believable conversations, each with a user question and a full assistant
report (e.g. Japan / fast fashion → PROCEED WITH CAUTION; Brazil / consumer app → GO;
Germany / B2B SaaS → GO), plus a Profile with realistic token usage, so every screen looks real
on first load.

Use recharts for charts, react-router for routing (one route "/" plus "/c/:conversationId"),
and keep components small and reusable: Sidebar, ConversationList, ProfileCard, ChatThread,
MessageBubble, AgentStepper, BriefCard, VerdictBadge, ConfidenceMeter, StatTile, CitationPanel,
ThemeSlider, ChatInput, UsageModal.
```

---

## How this maps to the backend (for when I build it)

The chat model is a thin wrapper over the same research engine:
- `sendMessage` → backend classifies the message: a market question triggers a research run
  (`Data → Platform → Strategy → Critic`) and returns an assistant `Message` with `kind: "report"`;
  a follow-up/clarifying message returns `kind: "text"`.
- Conversations + messages persist in SQLite (adds a `conversations` and `messages` table to the
  plan in ARCHITECTURE.md; the `Report` shape is unchanged).
- Progress still streams over SSE; the frontend's `onEvent` maps directly to it.

## After Lovable generates the app
1. Export the files into a `frontend/` folder in this repo (or tell me where you put them).
2. I'll build the FastAPI backend to match these types, then set `USE_MOCKS = false` and point
   `VITE_API_BASE` at the backend.
3. We verify the happy path, the streaming "thinking" state, and error states together.
