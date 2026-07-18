import { useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { ThemeSlider } from "./ThemeSlider";
import { UsageModal } from "./UsageModal";
import { useProfile } from "@/lib/store";

export function AppShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [usageOpen, setUsageOpen] = useState(false);
  const profile = useProfile();
  const totalTokens = (profile?.usage.total_tokens_in ?? 0) + (profile?.usage.total_tokens_out ?? 0);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        onOpenProfile={() => setUsageOpen(true)}
      />
      <main className="flex flex-1 flex-col min-w-0">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
          <h1 className="truncate text-sm font-semibold">{title}</h1>
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2.5 py-1 text-[11px] font-mono text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {formatK(totalTokens)} tokens
            </span>
            <ThemeSlider />
          </div>
        </header>
        <div className="flex-1 min-h-0">{children}</div>
      </main>
      <UsageModal open={usageOpen} onOpenChange={setUsageOpen} />
    </div>
  );
}

function formatK(n: number) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "k";
  return String(n);
}
