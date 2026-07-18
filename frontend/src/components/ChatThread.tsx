import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { MessageBubble, ThinkingMessage } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import type { Conversation, ProgressEvent } from "@/services/types";
import { sendMessage } from "@/services/api";
import { Globe2 } from "lucide-react";

const EXAMPLES = [
  "Expand a consumer app into Brazil ($15k)",
  "Is Germany good for B2B SaaS with a $30k budget?",
  "Compare Japan vs. UK for fast fashion",
  "Should we launch a DTC skincare brand in Mexico?",
];

export function ChatThread({
  conversation,
  onTitleChanged,
}: {
  conversation: Conversation;
  onTitleChanged?: (title: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [startedAt, setStartedAt] = useState<number>(0);
  const [autoFill, setAutoFill] = useState<string | undefined>(undefined);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [conversation.messages.length, events.length]);

  const handleSend = async (text: string) => {
    if (busy) return;
    setBusy(true);
    setEvents([]);
    setStartedAt(Date.now());
    try {
      await sendMessage(conversation.id, text, (e) => {
        setEvents((prev) => [...prev, e]);
      });
      onTitleChanged?.(conversation.title);
    } catch (err) {
      console.error(err);
      toast.error("Something went wrong. Try again.");
    } finally {
      setBusy(false);
      setEvents([]);
    }
  };

  const empty = conversation.messages.length === 0;

  return (
    <div className="flex h-full flex-col min-h-0">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6 space-y-6">
          {empty ? (
            <EmptyState onPick={(t) => setAutoFill(t)} />
          ) : (
            conversation.messages.map((m) => (
              <div key={m.id} className="animate-in fade-in slide-in-from-bottom-1 duration-300">
                <MessageBubble msg={m} />
              </div>
            ))
          )}
          {busy && <ThinkingMessage events={events} startedAt={startedAt} />}
        </div>
      </div>
      <ChatInput onSend={handleSend} disabled={busy} autoFillText={autoFill} />
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (t: string) => void }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary">
        <Globe2 className="h-7 w-7" />
      </div>
      <h1 className="text-2xl font-semibold tracking-tight">GTMScout</h1>
      <p className="mt-2 max-w-lg text-sm text-muted-foreground">
        A team of research agents that decides where — and how — to expand your business. Ask about a
        market and get a verdict, platform strategy, budget, and risks.
      </p>
      <div className="mt-6 grid w-full max-w-2xl gap-2 sm:grid-cols-2">
        {EXAMPLES.map((e) => (
          <button
            key={e}
            onClick={() => onPick(e)}
            className="rounded-xl border border-border bg-card px-4 py-3 text-left text-sm text-foreground/90 transition-colors hover:border-primary/60 hover:bg-muted/60"
          >
            {e}
          </button>
        ))}
      </div>
    </div>
  );
}
