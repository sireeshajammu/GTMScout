import type { Report } from "@/services/types";
import { VerdictBadge } from "./VerdictBadge";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { StatTile } from "./StatTile";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Copy, Download, ExternalLink, FileText, AlertTriangle } from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";

const DONUT_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#06b6d4"];

function fmtNum(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}
function fmtCurrency(n: number, ccy = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: ccy, maximumFractionDigits: 0 }).format(n);
}

export function BriefCard({ report }: { report: Report }) {
  const copy = () => {
    navigator.clipboard.writeText(report.executive_summary);
    toast.success("Summary copied");
  };

  return (
    <div className="rounded-2xl border border-border bg-card text-card-foreground shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-border">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <VerdictBadge verdict={report.verdict} size="md" />
              <span className="text-sm text-muted-foreground">
                {report.request.target_country} · {report.request.business_type}
              </span>
              <span className="text-sm font-mono text-muted-foreground">
                {fmtCurrency(report.request.budget, report.request.currency)}
              </span>
            </div>
            <p className="text-sm leading-relaxed text-foreground/90">{report.executive_summary}</p>
          </div>
          <ConfidenceMeter value={report.confidence} />
        </div>

        {report.verification.flags.length > 0 && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <div>
              <div className="font-semibold">Verification notes</div>
              <ul className="mt-1 list-disc pl-4 space-y-0.5">
                {report.verification.flags.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Body accordion */}
      <Accordion type="multiple" defaultValue={["market", "platforms", "budget"]} className="px-5 sm:px-6">
        <AccordionItem value="market">
          <AccordionTrigger className="text-sm font-semibold">Market data</AccordionTrigger>
          <AccordionContent>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatTile
                label="Population"
                value={fmtNum(report.market_data.population)}
                hint={report.market_data.data_year}
                source="World Bank"
              />
              <StatTile
                label="GDP per capita"
                value={fmtCurrency(report.market_data.gdp_per_capita)}
                hint={report.market_data.data_year}
                source="World Bank"
              />
              <StatTile
                label="Internet penetration"
                value={`${report.market_data.internet_penetration}%`}
                hint={report.market_data.data_year}
                source="World Bank"
              />
              <StatTile
                label="Mobile subs"
                value={fmtNum(report.market_data.mobile_subscriptions)}
                hint={report.market_data.data_year}
                source="World Bank"
              />
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="platforms">
          <AccordionTrigger className="text-sm font-semibold">Platforms</AccordionTrigger>
          <AccordionContent>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={report.platform_recommendations}
                  layout="vertical"
                  margin={{ left: 12, right: 12 }}
                >
                  <XAxis type="number" domain={[0, 100]} stroke="currentColor" fontSize={11} />
                  <YAxis type="category" dataKey="platform" stroke="currentColor" fontSize={11} width={90} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-popover)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 8,
                      color: "var(--color-popover-foreground)",
                    }}
                  />
                  <Bar dataKey="interest_score" radius={[0, 6, 6, 0]} fill="#6366f1" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ul className="mt-3 space-y-2">
              {report.platform_recommendations.map((p) => (
                <li key={p.platform} className="flex gap-3 text-sm">
                  <span className="font-mono text-muted-foreground w-6">#{p.rank}</span>
                  <span className="font-semibold w-24 shrink-0">{p.platform}</span>
                  <span className="text-muted-foreground">{p.rationale}</span>
                </li>
              ))}
            </ul>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="budget">
          <AccordionTrigger className="text-sm font-semibold">Budget allocation</AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={report.budget_allocation}
                      dataKey="amount"
                      nameKey="platform"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                    >
                      {report.budget_allocation.map((_, i) => (
                        <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "var(--color-popover)",
                        border: "1px solid var(--color-border)",
                        borderRadius: 8,
                        color: "var(--color-popover-foreground)",
                      }}
                      formatter={(v: number) => fmtCurrency(v, report.request.currency)}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <table className="text-sm">
                <thead>
                  <tr className="text-muted-foreground">
                    <th className="text-left py-1">Platform</th>
                    <th className="text-right py-1">%</th>
                    <th className="text-right py-1">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {report.budget_allocation.map((b, i) => (
                    <tr key={b.platform} className="border-t border-border/60">
                      <td className="py-1.5 flex items-center gap-2">
                        <span
                          className="inline-block h-2 w-2 rounded-full"
                          style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }}
                        />
                        {b.platform}
                      </td>
                      <td className="text-right font-mono">{b.percentage}%</td>
                      <td className="text-right font-mono">{fmtCurrency(b.amount, report.request.currency)}</td>
                    </tr>
                  ))}
                  <tr className="border-t border-border">
                    <td className="py-2 font-semibold">Total</td>
                    <td />
                    <td className="text-right font-mono font-semibold">
                      {fmtCurrency(report.request.budget, report.request.currency)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="risks">
          <AccordionTrigger className="text-sm font-semibold">Risks</AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-2 md:grid-cols-2">
              {report.risks.map((r, i) => (
                <div key={i} className="rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium text-sm">{r.title}</div>
                    <SeverityPill s={r.severity} />
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{r.description}</p>
                </div>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="next">
          <AccordionTrigger className="text-sm font-semibold">Next steps</AccordionTrigger>
          <AccordionContent>
            <ul className="space-y-2">
              {report.next_steps.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1 h-3.5 w-3.5 shrink-0 rounded border border-border" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="cost">
          <AccordionTrigger className="text-sm font-semibold">Compute cost</AccordionTrigger>
          <AccordionContent>
            <div className="mb-3 grid grid-cols-3 gap-3">
              <StatTile label="Tokens in" value={fmtNum(report.cost.total_tokens_in)} />
              <StatTile label="Tokens out" value={fmtNum(report.cost.total_tokens_out)} />
              <StatTile label="USD" value={`$${report.cost.usd.toFixed(3)}`} />
            </div>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={report.cost.per_agent} margin={{ left: 0, right: 8 }}>
                  <XAxis dataKey="agent" stroke="currentColor" fontSize={11} />
                  <YAxis stroke="currentColor" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-popover)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 8,
                    }}
                  />
                  <Bar dataKey="tokens_in" stackId="a" fill="#6366f1" />
                  <Bar dataKey="tokens_out" stackId="a" fill="#a78bfa" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </AccordionContent>
        </AccordionItem>

        {report.competitors && report.competitors.length > 0 && (
          <AccordionItem value="competitors">
            <AccordionTrigger className="text-sm font-semibold">
              Competitors ({report.competitors.length})
            </AccordionTrigger>
            <AccordionContent>
              <ul className="space-y-2">
                {report.competitors.map((c, i) => (
                  <li key={i} className="text-sm">
                    <span className="font-semibold">{c.name}</span>
                    <span className="text-muted-foreground"> — {c.note}</span>
                  </li>
                ))}
              </ul>
            </AccordionContent>
          </AccordionItem>
        )}

        {report.unit_economics && report.unit_economics.length > 0 && (
          <AccordionItem value="unit-economics">
            <AccordionTrigger className="text-sm font-semibold">Unit economics (est.)</AccordionTrigger>
            <AccordionContent>
              <table className="w-full text-sm">
                <tbody>
                  {report.unit_economics.map((u, i) => (
                    <tr key={i} className="border-b border-border/60 last:border-0">
                      <td className="py-1.5 pr-3 text-muted-foreground">{u.metric}</td>
                      <td className="py-1.5 pr-3 font-mono font-semibold">{u.value}</td>
                      <td className="py-1.5 text-muted-foreground">{u.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </AccordionContent>
          </AccordionItem>
        )}

        {report.regulatory && report.regulatory.length > 0 && (
          <AccordionItem value="regulatory">
            <AccordionTrigger className="text-sm font-semibold">
              Regulatory ({report.regulatory.length})
            </AccordionTrigger>
            <AccordionContent>
              <ul className="space-y-2.5">
                {report.regulatory.map((r, i) => (
                  <li key={i} className="text-sm">
                    <div className="font-semibold">{r.title}</div>
                    <div className="text-muted-foreground">{r.detail}</div>
                  </li>
                ))}
              </ul>
            </AccordionContent>
          </AccordionItem>
        )}

        {report.gtm_timeline && report.gtm_timeline.length > 0 && (
          <AccordionItem value="gtm">
            <AccordionTrigger className="text-sm font-semibold">Go-to-market timeline</AccordionTrigger>
            <AccordionContent>
              <ol className="relative space-y-4 border-l border-border pl-5">
                {report.gtm_timeline.map((p, i) => (
                  <li key={i} className="relative">
                    <span className="absolute -left-[23px] top-1 h-3 w-3 rounded-full border-2 border-primary bg-background" />
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="font-semibold">{p.phase}</span>
                      <span className="text-xs text-muted-foreground">{p.timeframe}</span>
                    </div>
                    <ul className="mt-1 space-y-1">
                      {p.actions.map((a, j) => (
                        <li key={j} className="flex items-start gap-2 text-sm text-foreground/85">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground" />
                          <span>{a}</span>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            </AccordionContent>
          </AccordionItem>
        )}

        {report.research_findings && report.research_findings.length > 0 && (
          <AccordionItem value="research">
            <AccordionTrigger className="text-sm font-semibold">
              Live research ({report.research_findings.length})
            </AccordionTrigger>
            <AccordionContent>
              <ul className="space-y-2">
                {report.research_findings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-muted-foreground">
                Sourced live from the web — see Citations for links.
              </p>
            </AccordionContent>
          </AccordionItem>
        )}

        <AccordionItem value="citations">
          <AccordionTrigger className="text-sm font-semibold">Citations</AccordionTrigger>
          <AccordionContent>
            <ol className="space-y-2">
              {report.citations.map((c) => (
                <li key={c.id} className="flex items-start gap-2 text-sm">
                  <span className="font-mono text-muted-foreground">[{c.id}]</span>
                  <div className="flex-1">
                    <span className="font-semibold">{c.source}</span>
                    <span className="text-muted-foreground"> — {c.detail}</span>
                  </div>
                  {c.url && (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary hover:underline"
                      aria-label="Open source"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </li>
              ))}
            </ol>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* Footer actions */}
      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-border p-4">
        <Button variant="ghost" size="sm" onClick={() => toast.info("PDF export — coming soon")}>
          <FileText className="mr-1.5 h-4 w-4" /> Export PDF
        </Button>
        <Button variant="ghost" size="sm" onClick={() => toast.info("Markdown export — coming soon")}>
          <Download className="mr-1.5 h-4 w-4" /> Markdown
        </Button>
        <Button variant="ghost" size="sm" onClick={copy}>
          <Copy className="mr-1.5 h-4 w-4" /> Copy
        </Button>
      </div>
    </div>
  );
}

function SeverityPill({ s }: { s: "low" | "medium" | "high" }) {
  const map = {
    low: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
    medium: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
    high: "bg-red-500/15 text-red-600 dark:text-red-400",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${map[s]}`}>
      {s}
    </span>
  );
}
