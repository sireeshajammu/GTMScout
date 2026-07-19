import type { Message, ProgressEvent } from "@/services/types";
import { BriefCard } from "./BriefCard";
import { ComparisonCard } from "./ComparisonCard";
import { RankingCard } from "./RankingCard";
import { AgentStepper } from "./AgentStepper";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";

export function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-3 w-full", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-muted/60 text-foreground rounded-bl-sm",
          msg.kind !== "text" && !isUser && "!bg-transparent !p-0 !max-w-full flex-1",
        )}
      >
        {msg.kind === "text" && <TextContent text={msg.text ?? ""} />}
        {msg.kind === "report" && msg.report && <BriefCard report={msg.report} />}
        {msg.kind === "comparison" && msg.comparison && <ComparisonCard comparison={msg.comparison} />}
        {msg.kind === "ranking" && msg.ranking && <RankingCard ranking={msg.ranking} />}
      </div>
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-foreground">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}

// Very small markdown-ish renderer for bold + italics + code
function TextContent({ text }: { text: string }) {
  const html = escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, '<code class="rounded bg-background/60 px-1 py-0.5 font-mono text-[0.85em]">$1</code>')
    .replace(/\n/g, "<br/>");
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}

export function ThinkingMessage({ events, startedAt }: { events: ProgressEvent[]; startedAt: number }) {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Bot className="h-4 w-4" />
      </div>
      <div className="flex-1 max-w-2xl">
        <AgentStepper events={events} startedAt={startedAt} />
      </div>
    </div>
  );
}
