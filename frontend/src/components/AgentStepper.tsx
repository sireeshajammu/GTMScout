import type { AgentStatus, ProgressEvent } from "@/services/types";
import { Check, Loader2, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

const AGENTS = ["DataAgent", "PlatformAgent", "StrategyAgent", "CriticAgent"];

export function AgentStepper({ events, startedAt }: { events: ProgressEvent[]; startedAt: number }) {
  const latestByAgent = new Map<string, ProgressEvent>();
  for (const e of events) latestByAgent.set(e.agent, e);

  return (
    <div className="space-y-2 rounded-xl border border-border bg-muted/20 p-4">
      <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Research agents working…
      </div>
      {AGENTS.map((a, i) => {
        const ev = latestByAgent.get(a);
        const status: AgentStatus = ev?.status ?? "queued";
        return (
          <div key={a} className="flex items-center gap-3">
            <StatusIcon status={status} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{a}</span>
                {status === "running" && (
                  <span className="text-[10px] font-mono text-muted-foreground">
                    · {Math.max(0, Math.round((Date.now() - startedAt) / 1000))}s
                  </span>
                )}
              </div>
              <div
                className={cn(
                  "truncate text-xs text-muted-foreground",
                  status === "running" && "animate-pulse",
                )}
              >
                {ev?.message ?? "Queued"}
              </div>
            </div>
            {i < AGENTS.length - 1 && (
              <div className="hidden h-px w-6 bg-border md:block" aria-hidden />
            )}
          </div>
        );
      })}
    </div>
  );
}

function StatusIcon({ status }: { status: AgentStatus }) {
  if (status === "done")
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-500">
        <Check className="h-3.5 w-3.5" />
      </span>
    );
  if (status === "running")
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      </span>
    );
  if (status === "error")
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-500/20 text-red-500">
        !
      </span>
    );
  return (
    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
      <Circle className="h-3 w-3" />
    </span>
  );
}
