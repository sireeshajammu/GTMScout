export function StatTile({
  label,
  value,
  hint,
  source,
}: {
  label: string;
  value: string;
  hint?: string;
  source?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 font-mono text-xl font-semibold">{value}</div>
      {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      {source && (
        <div className="mt-1 inline-flex rounded-full bg-background px-2 py-0.5 text-[10px] font-medium text-muted-foreground ring-1 ring-border">
          {source}
        </div>
      )}
    </div>
  );
}
