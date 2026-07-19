import type {
  Conversation,
  ConversationSummary,
  Message,
  ProgressEvent,
  Profile,
  Report,
} from "./types";
import { japanReport, brazilReport, germanyReport } from "./mockReports";

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

// Mock mode:
//  - VITE_USE_MOCKS="true"  -> always mocks
//  - VITE_USE_MOCKS="false" -> always real backend
//  - unset                  -> mocks only when no API_BASE is configured
const _forceMocks = import.meta.env.VITE_USE_MOCKS as string | undefined;
export const USE_MOCKS =
  _forceMocks === "true" || (_forceMocks !== "false" && !API_BASE);

// -------- helpers --------

const uid = () => Math.random().toString(36).slice(2, 10);
const now = () => new Date().toISOString();
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function makeReportMessage(report: Report): Message {
  return { id: uid(), role: "assistant", kind: "report", report, created_at: now() };
}
function makeUserMessage(text: string): Message {
  return { id: uid(), role: "user", kind: "text", text, created_at: now() };
}
function makeTextMessage(text: string): Message {
  return { id: uid(), role: "assistant", kind: "text", text, created_at: now() };
}

// -------- seed data (first run only) --------

function seedConversations(): Conversation[] {
  return [
    {
      id: "conv_japan",
      title: "Japan · fast fashion",
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
      updated_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      messages: [
        makeUserMessage(
          "Should my fast-fashion brand expand into Japan with a $20k budget? We're based in the US.",
        ),
        makeReportMessage(japanReport),
      ],
    },
    {
      id: "conv_brazil",
      title: "Brazil · consumer app",
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 26).toISOString(),
      updated_at: new Date(Date.now() - 1000 * 60 * 60 * 25).toISOString(),
      messages: [
        makeUserMessage("Is Brazil a good market for a consumer mobile app? We have $15k to test."),
        makeReportMessage(brazilReport),
      ],
    },
    {
      id: "conv_germany",
      title: "Germany · B2B SaaS",
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
      updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4).toISOString(),
      messages: [
        makeUserMessage("How viable is Germany for a US-based B2B SaaS with a $30k GTM budget?"),
        makeReportMessage(germanyReport),
      ],
    },
  ];
}

function seedProfile(): Profile {
  return {
    name: "Alex Morgan",
    email: "alex@gtmscout.ai",
    avatar_url: null,
    usage: {
      total_tokens_in: 54420,
      total_tokens_out: 19210,
      total_usd: 0.553,
      runs_count: 3,
      monthly_quota_tokens: 2_000_000,
    },
  };
}

// -------- persistent store (localStorage-backed) --------

const STORAGE_KEY = "gtmscout_store_v1";

type StoreShape = { conversations: Conversation[]; profile: Profile };

function loadStore(): StoreShape {
  if (typeof window === "undefined") {
    return { conversations: seedConversations(), profile: seedProfile() };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as StoreShape;
  } catch {
    /* ignore corrupt storage */
  }
  return { conversations: seedConversations(), profile: seedProfile() };
}

const store: StoreShape & { listeners: Set<() => void> } = {
  ...loadStore(),
  listeners: new Set<() => void>(),
};

function persist() {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ conversations: store.conversations, profile: store.profile }),
    );
  } catch {
    /* quota / private mode — ignore */
  }
}

function emit() {
  persist();
  store.listeners.forEach((l) => l());
}

export function subscribe(fn: () => void) {
  store.listeners.add(fn);
  return () => store.listeners.delete(fn);
}

// -------- conversation + profile API (client-side in both modes) --------

export async function listConversations(): Promise<ConversationSummary[]> {
  return store.conversations
    .map(({ id, title, created_at, updated_at }) => ({ id, title, created_at, updated_at }))
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}

export async function getConversation(id: string): Promise<Conversation> {
  const c = store.conversations.find((c) => c.id === id);
  if (!c) throw new Error("Conversation not found");
  return structuredClone(c);
}

export async function createConversation(): Promise<Conversation> {
  const c: Conversation = {
    id: `conv_${uid()}`,
    title: "New chat",
    created_at: now(),
    updated_at: now(),
    messages: [],
  };
  store.conversations = [c, ...store.conversations];
  emit();
  return structuredClone(c);
}

export async function renameConversation(id: string, title: string): Promise<void> {
  const c = store.conversations.find((c) => c.id === id);
  if (c) {
    c.title = title;
    c.updated_at = now();
    emit();
  }
}

export async function deleteConversation(id: string): Promise<void> {
  store.conversations = store.conversations.filter((c) => c.id !== id);
  emit();
}

export async function getProfile(): Promise<Profile> {
  return structuredClone(store.profile);
}

// -------- agent progress choreography --------

const AGENT_STEPS: { agent: string; msgs: string[]; ms: number }[] = [
  {
    agent: "DataAgent",
    msgs: ["Fetching World Bank macro indicators…", "Normalizing GDP + internet penetration…"],
    ms: 1400,
  },
  {
    agent: "PlatformAgent",
    msgs: ["Scoring platform interest for the vertical…", "Ranking platforms + writing rationale…"],
    ms: 1500,
  },
  {
    agent: "StrategyAgent",
    msgs: ["Allocating budget across platforms…", "Drafting verdict, risks + next steps…"],
    ms: 1500,
  },
  {
    agent: "CriticAgent",
    msgs: ["Verifying claims against sources…"],
    ms: 900,
  },
];

async function playSteps(
  onEvent: ((e: ProgressEvent) => void) | undefined,
  control: { cancelled: boolean },
) {
  for (const step of AGENT_STEPS) {
    if (control.cancelled) return;
    onEvent?.({ agent: step.agent, status: "queued", message: "Queued", timestamp: now() });
    await delay(120);
    for (const m of step.msgs) {
      if (control.cancelled) return;
      onEvent?.({ agent: step.agent, status: "running", message: m, timestamp: now() });
      await delay(step.ms / step.msgs.length);
    }
    if (control.cancelled) return;
    onEvent?.({ agent: step.agent, status: "done", message: "Complete", timestamp: now() });
  }
}

// Simple heuristic used only in mock mode.
function detectMarketQuestion(text: string): Report | null {
  const t = text.toLowerCase();
  const pick = (r: Report) => structuredClone(r);
  if (/japan/.test(t)) return pick(japanReport);
  if (/brazil|brasil/.test(t)) return pick(brazilReport);
  if (/germany|deutschland/.test(t)) return pick(germanyReport);
  if (/\$\s?\d|budget|expand|market|launch|enter/.test(t)) return pick(japanReport);
  return null;
}

// Rich summary of a prior report so the backend can answer follow-up questions
// ("why Instagram?", "what were the risks?") using THIS report's real numbers.
function summarizeReport(r: Report): string {
  const platforms = r.platform_recommendations
    .map((p) => `${p.platform} ${p.interest_score}/100`)
    .join(", ");
  const budget = r.budget_allocation.map((b) => `${b.platform} ${b.percentage}%`).join(", ");
  const risks = r.risks.map((x) => x.title).join("; ");
  return (
    `[previous report] ${r.verdict} (confidence ${r.confidence}) for ` +
    `${r.request.target_country} · ${r.request.business_type}, ` +
    `budget ${r.request.budget} ${r.request.currency}.\n` +
    `Executive summary: ${r.executive_summary}\n` +
    `Platform interest: ${platforms}.\n` +
    `Budget split: ${budget}.\n` +
    `Risks: ${risks}.`
  );
}

function applyUsage(report: Report) {
  store.profile.usage.total_tokens_in += report.cost.total_tokens_in;
  store.profile.usage.total_tokens_out += report.cost.total_tokens_out;
  store.profile.usage.total_usd = Number(
    (store.profile.usage.total_usd + report.cost.usd).toFixed(4),
  );
  store.profile.usage.runs_count += 1;
}

// -------- send message --------

export async function sendMessage(
  conversationId: string,
  text: string,
  onEvent?: (e: ProgressEvent) => void,
): Promise<Message> {
  const conv = store.conversations.find((c) => c.id === conversationId);
  if (!conv) throw new Error("Conversation not found");

  // Capture recent conversation context BEFORE appending the new message, so the
  // backend can accumulate details across turns and answer follow-up questions.
  const history = conv.messages.slice(-10).map((m) => ({
    role: m.role,
    text: m.kind === "report" && m.report ? summarizeReport(m.report) : m.text ?? "",
  }));

  // Append the user message + set the title from the first message.
  const userMsg = makeUserMessage(text);
  conv.messages = [...conv.messages, userMsg];
  conv.updated_at = now();
  if (conv.title === "New chat" || conv.messages.length === 1) {
    conv.title = text.slice(0, 48).replace(/\s+/g, " ").trim() || "New chat";
  }
  emit();

  // ---- MOCK MODE ----
  if (USE_MOCKS) {
    const report = detectMarketQuestion(text);
    if (!report) {
      await delay(700);
      const reply = makeTextMessage(
        'Happy to help — could you share the **target country**, **business type**, and an approximate **budget** (with currency)? For example: _"Consumer app in Brazil, $15k USD."_',
      );
      conv.messages = [...conv.messages, reply];
      conv.updated_at = now();
      emit();
      return reply;
    }
    const control = { cancelled: false };
    await playSteps(onEvent, control);
    const assistantMsg = makeReportMessage(report);
    conv.messages = [...conv.messages, assistantMsg];
    conv.updated_at = now();
    applyUsage(report);
    emit();
    return assistantMsg;
  }

  // ---- REAL BACKEND ----
  const control = { cancelled: false };
  // Optimistic stepper runs while the backend works (backend is a single POST).
  const steps = playSteps(onEvent, control);

  let assistantMsg: Message;
  try {
    const resp = await fetch(`${API_BASE}/api/research`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, history }),
    });
    if (!resp.ok) throw new Error(`Backend error ${resp.status}`);
    assistantMsg = (await resp.json()) as Message;
  } catch {
    control.cancelled = true;
    await steps.catch(() => {});
    const failMsg = makeTextMessage(
      "I couldn't reach the research backend just now. Please check your connection and try again.",
    );
    conv.messages = [...conv.messages, failMsg];
    conv.updated_at = now();
    emit();
    return failMsg;
  }

  control.cancelled = true;
  await steps.catch(() => {});

  // Ensure a stable id/timestamp even if the backend omitted them.
  if (!assistantMsg.id) assistantMsg.id = uid();
  if (!assistantMsg.created_at) assistantMsg.created_at = now();

  conv.messages = [...conv.messages, assistantMsg];
  conv.updated_at = now();
  if (assistantMsg.kind === "report" && assistantMsg.report) {
    applyUsage(assistantMsg.report);
  }
  emit();
  return assistantMsg;
}
