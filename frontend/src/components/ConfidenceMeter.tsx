export function ConfidenceMeter({ value }: { value: number }) {
  const size = 72;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;
  const color =
    value >= 75 ? "stroke-emerald-500" : value >= 50 ? "stroke-amber-500" : "stroke-red-500";
  return (
    <div className="inline-flex items-center gap-3">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={stroke}
          className="stroke-muted"
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={stroke}
          strokeLinecap="round"
          className={color}
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 800ms ease" }}
        />
      </svg>
      <div className="flex flex-col leading-tight">
        <span className="font-mono text-2xl font-semibold">{value}</span>
        <span className="text-xs text-muted-foreground">confidence</span>
      </div>
    </div>
  );
}
