import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { ChatThread } from "@/components/ChatThread";
import { createConversation, sendMessage } from "@/services/api";
import { useState } from "react";
import type { Conversation, Message, ProgressEvent } from "@/services/types";
import { ChatInput } from "@/components/ChatInput";
import { MessageBubble, ThinkingMessage } from "@/components/MessageBubble";
import { Globe2 } from "lucide-react";

export const Route = createFileRoute("/")({
  component: HomePage,
});

const EXAMPLES = [
  "Expand a consumer app into Brazil ($15k)",
  "Is Germany good for B2B SaaS with a $30k budget?",
  "Compare Japan vs. UK for fast fashion",
  "Should we launch a DTC skincare brand in Mexico?",
];

function HomePage() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [startedAt, setStartedAt] = useState(0);
  const [pendingUser, setPendingUser] = useState<Message | null>(null);
  const [autoFill, setAutoFill] = useState<string | undefined>(undefined);

  const handleSend = async (text: string) => {
    if (busy) return;
    setBusy(true);
    const conv: Conversation = await createConversation();
    setPendingUser({
      id: "temp",
      role: "user",
      kind: "text",
      text,
      created_at: new Date().toISOString(),
    });
    setEvents([]);
    setStartedAt(Date.now());
    try {
      await sendMessage(conv.id, text, (e) => setEvents((prev) => [...prev, e]));
      navigate({ to: "/c/$conversationId", params: { conversationId: conv.id } });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell title="New chat">
      <div className="flex h-full flex-col min-h-0">
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-4 py-6 space-y-6">
            {!pendingUser && !busy ? (
              <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                  <Globe2 className="h-7 w-7" />
                </div>
                <h1 className="text-2xl font-semibold tracking-tight">GTMScout</h1>
                <p className="mt-2 max-w-lg text-sm text-muted-foreground">
                  A team of research agents that decides where — and how — to expand your business.
                  Ask about a market and get a verdict, platform strategy, budget, and risks.
                </p>
                <div className="mt-6 grid w-full max-w-2xl gap-2 sm:grid-cols-2">
                  {EXAMPLES.map((e) => (
                    <button
                      key={e}
                      onClick={() => setAutoFill(e)}
                      className="rounded-xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground/90 transition-colors hover:border-primary/60 hover:bg-muted/60"
                    >
                      {e}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {pendingUser && <MessageBubble msg={pendingUser} />}
                {busy && <ThinkingMessage events={events} startedAt={startedAt} />}
              </>
            )}
          </div>
        </div>
        <ChatInput onSend={handleSend} disabled={busy} autoFillText={autoFill} />
      </div>
    </AppShell>
  );
}

// avoid unused import warning
void ChatThread;
