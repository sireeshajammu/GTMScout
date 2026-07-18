import { cn } from "@/lib/utils";
import type { Verdict } from "@/services/types";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

export function VerdictBadge({ verdict, size = "md" }: { verdict: Verdict; size?: "sm" | "md" | "lg" }) {
  const map = {
    GO: {
      label: "GO",
      icon: CheckCircle2,
      cls: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
    },
    "PROCEED WITH CAUTION": {
      label: "PROCEED WITH CAUTION",
      icon: AlertTriangle,
      cls: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
    },
    "NOT YET": {
      label: "NOT YET",
      icon: XCircle,
      cls: "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30",
    },
  } as const;
  const { label, icon: Icon, cls } = map[verdict];
  const sizeCls = {
    sm: "text-xs px-2 py-1",
    md: "text-sm px-3 py-1.5",
    lg: "text-base px-4 py-2",
  }[size];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-semibold tracking-wide",
        cls,
        sizeCls,
      )}
    >
      <Icon className="h-4 w-4" />
      {label}
    </span>
  );
}
