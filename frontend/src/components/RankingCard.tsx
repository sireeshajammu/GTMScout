import type { RankingReport } from "@/services/types";
import { VerdictBadge } from "./VerdictBadge";

function fmtNum(n: number | null) {
  return n == null ? "—" : new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export function RankingCard({ ranking }: { ranking: RankingReport }) {
  return (
    <div className="w-full overflow-hidden rounded-2xl border border-border bg-card">
      <div className="border-b border-border p-4">
        <h3 className="text-sm font-semibold text-muted-foreground">
          Market ranking — {ranking.business_type}
        </h3>
        {ranking.note && <p className="mt-1 text-sm text-foreground/80">{ranking.note}</p>}
      </div>

      <ol className="divide-y divide-border/60">
        {ranking.items.map((it) => (
          <li key={it.country} className="flex items-start gap-3 p-4">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 font-mono text-sm font-semibold text-primary">
              {it.rank}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{it.country}</span>
                <VerdictBadge verdict={it.verdict} size="sm" />
                <span className="text-xs text-muted-foreground">
                  pop {fmtNum(it.population)} · GDP/cap {fmtNum(it.gdp_per_capita)} · internet{" "}
                  {it.internet_penetration == null ? "—" : `${Math.round(it.internet_penetration)}%`}
                </span>
              </div>
              {/* score bar */}
              <div className="mt-2 flex items-center gap-2">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${it.score}%` }}
                  />
                </div>
                <span className="w-10 text-right font-mono text-xs text-muted-foreground">{it.score}</span>
              </div>
              <p className="mt-1.5 text-sm text-foreground/80">{it.rationale}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
