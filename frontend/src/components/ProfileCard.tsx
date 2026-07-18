import { useProfile } from "@/lib/store";
import { Progress } from "@/components/ui/progress";

export function ProfileCard({ onOpen }: { onOpen: () => void }) {
  const profile = useProfile();
  if (!profile) return null;
  const totalTokens = profile.usage.total_tokens_in + profile.usage.total_tokens_out;
  const pct = Math.min(100, (totalTokens / profile.usage.monthly_quota_tokens) * 100);
  const initials = profile.name
    .split(/\s+/)
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <button
      onClick={onOpen}
      className="m-2 flex flex-col gap-2 rounded-xl border border-border bg-card p-3 text-left hover:bg-sidebar-accent"
    >
      <div className="flex items-center gap-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold text-sm">
          {initials}
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold">{profile.name}</div>
          <div className="truncate text-[11px] text-muted-foreground">{profile.email}</div>
        </div>
      </div>
      <div className="rounded-lg bg-muted/40 p-2">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span>Token usage</span>
          <span className="font-mono">
            {formatK(totalTokens)} / {formatK(profile.usage.monthly_quota_tokens)}
          </span>
        </div>
        <Progress value={pct} className="mt-1.5 h-1.5" />
        <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
          <span className="font-mono">${profile.usage.total_usd.toFixed(2)}</span>
          <span>{profile.usage.runs_count} analyses</span>
        </div>
      </div>
    </button>
  );
}

function formatK(n: number) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "k";
  return String(n);
}
