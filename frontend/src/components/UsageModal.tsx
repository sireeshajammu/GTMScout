import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { useProfile } from "@/lib/store";
import { ThemeSlider } from "./ThemeSlider";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function UsageModal({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const profile = useProfile();
  if (!profile) return null;
  const totalTokens = profile.usage.total_tokens_in + profile.usage.total_tokens_out;
  const pct = Math.min(100, (totalTokens / profile.usage.monthly_quota_tokens) * 100);

  // synthesize a mini history for the chart based on runs
  const history = Array.from({ length: Math.max(profile.usage.runs_count, 1) }, (_, i) => ({
    run: `#${i + 1}`,
    tokens: Math.round(totalTokens / Math.max(profile.usage.runs_count, 1)) * (0.7 + Math.random() * 0.6),
  }));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Profile & usage</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold">
              {profile.name.split(" ").map((s) => s[0]).join("").toUpperCase()}
            </span>
            <div className="flex-1 space-y-2">
              <div>
                <Label htmlFor="name">Name</Label>
                <Input id="name" defaultValue={profile.name} />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" defaultValue={profile.email} />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border p-3">
            <div className="flex items-center justify-between text-sm">
              <span>Monthly token quota</span>
              <span className="font-mono text-muted-foreground">
                {new Intl.NumberFormat().format(totalTokens)} / {new Intl.NumberFormat().format(profile.usage.monthly_quota_tokens)}
              </span>
            </div>
            <Progress value={pct} className="mt-2 h-2" />
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded bg-muted/50 p-2">
                <div className="text-muted-foreground">Tokens in</div>
                <div className="font-mono text-sm">{new Intl.NumberFormat().format(profile.usage.total_tokens_in)}</div>
              </div>
              <div className="rounded bg-muted/50 p-2">
                <div className="text-muted-foreground">Tokens out</div>
                <div className="font-mono text-sm">{new Intl.NumberFormat().format(profile.usage.total_tokens_out)}</div>
              </div>
              <div className="rounded bg-muted/50 p-2">
                <div className="text-muted-foreground">Cost</div>
                <div className="font-mono text-sm">${profile.usage.total_usd.toFixed(3)}</div>
              </div>
            </div>
            <div className="mt-3 h-32">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={history}>
                  <XAxis dataKey="run" stroke="currentColor" fontSize={10} />
                  <YAxis stroke="currentColor" fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-popover)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="tokens" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-border p-3">
            <div>
              <div className="text-sm font-medium">Theme</div>
              <div className="text-xs text-muted-foreground">Slide to change appearance</div>
            </div>
            <ThemeSlider />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
