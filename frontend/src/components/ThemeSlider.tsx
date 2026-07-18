import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

export function ThemeSlider() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      onClick={toggle}
      aria-label="Toggle theme"
      className={cn(
        "relative inline-flex h-8 w-16 items-center rounded-full border transition-colors",
        "border-border bg-muted",
      )}
    >
      <span
        className={cn(
          "absolute top-1 left-1 flex h-6 w-6 items-center justify-center rounded-full bg-background shadow-sm transition-transform",
          isDark && "translate-x-8",
        )}
      >
        {isDark ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5" />}
      </span>
      <Sun className="absolute left-2 h-3.5 w-3.5 text-muted-foreground opacity-60" />
      <Moon className="absolute right-2 h-3.5 w-3.5 text-muted-foreground opacity-60" />
    </button>
  );
}
