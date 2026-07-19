import type { ComparisonReport } from "@/services/types";
import { VerdictBadge } from "./VerdictBadge";
import { Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

function fmtNum(n: number | null) {
  return n == null ? "—" : new Intl.NumberFormat("en-US").format(Math.round(n));
}
function fmtPct(n: number | null) {
  return n == null ? "—" : `${n.toFixed(1)}%`;
}
function fmtMoney(n: number | null, ccy = "USD") {
  return n == null
    ? "—"
    : new Intl.NumberFormat("en-US", { style: "currency", currency: ccy, maximumFractionDigits: 0 }).format(n);
}

export function ComparisonCard({ comparison }: { comparison: ComparisonReport }) {
  const { markets, recommendation } = comparison;
  const pick = recommendation?.pick;

  const rows: { label: string; get: (m: (typeof markets)[number]) => React.ReactNode }[] = [
    { label: "Verdict", get: (m) => <VerdictBadge verdict={m.verdict} size="sm" /> },
    { label: "Confidence", get: (m) => `${m.confidence}/100` },
    { label: "Population", get: (m) => fmtNum(m.population) },
    { label: "GDP / capita", get: (m) => fmtMoney(m.gdp_per_capita, m.currency) },
    { label: "Internet", get: (m) => fmtPct(m.internet_penetration) },
    { label: "Top platform", get: (m) => m.top_platform ?? "—" },
    { label: "Budget", get: (m) => fmtMoney(m.budget, m.currency) },
  ];

  return (
    <div className="w-full overflow-hidden rounded-2xl border border-border bg-card">
      <div className="border-b border-border p-4">
        <h3 className="text-sm font-semibold text-muted-foreground">Market comparison</h3>
      </div>

      {/* Recommendation banner */}
      {pick && (
        <div className="m-4 rounded-xl border border-primary/30 bg-primary/10 p-4">
          <div className="mb-2 flex items-center gap-2 font-semibold text-primary">
            <Trophy className="h-4 w-4" /> Recommended: {pick}
          </div>
          <ul className="space-y-1.5">
            {recommendation.reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Side-by-side table */}
      <div className="overflow-x-auto p-4 pt-0">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th className="p-2 text-left font-medium text-muted-foreground"></th>
              {markets.map((m) => (
                <th
                  key={m.country}
                  className={cn(
                    "min-w-[140px] p-2 text-left align-bottom",
                    m.country === pick && "rounded-t-lg bg-primary/10",
                  )}
                >
                  <div className="font-semibold">{m.country}</div>
                  <div className="text-xs font-normal text-muted-foreground">{m.business_type}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-t border-border/60">
                <td className="p-2 text-muted-foreground">{row.label}</td>
                {markets.map((m) => (
                  <td key={m.country} className={cn("p-2", m.country === pick && "bg-primary/10")}>
                    {row.get(m)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
