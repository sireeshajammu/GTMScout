import { useEffect, useRef, useState } from "react";
import { SendHorizonal } from "lucide-react";
import { cn } from "@/lib/utils";

export function ChatInput({
  onSend,
  disabled,
  autoFillText,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
  autoFillText?: string;
}) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (autoFillText != null) {
      setValue(autoFillText);
      ref.current?.focus();
    }
  }, [autoFillText]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 240) + "px";
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  return (
    <div className="border-t border-border bg-background/80 backdrop-blur">
      <div className="mx-auto max-w-3xl px-4 py-4">
        <div
          className={cn(
            "flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm",
            "focus-within:ring-2 focus-within:ring-primary/30",
          )}
        >
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Ask about a market… (country, business type, budget)"
            className="flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground"
            disabled={disabled}
          />
          <button
            onClick={submit}
            disabled={disabled || !value.trim()}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-xl transition-colors",
              "bg-primary text-primary-foreground disabled:bg-muted disabled:text-muted-foreground",
              !disabled && value.trim() && "hover:bg-primary/90",
            )}
            aria-label="Send"
          >
            <SendHorizonal className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-2 flex items-center justify-between px-1 text-[11px] text-muted-foreground">
          <span>Agents: Data · Platform · Strategy · Critic</span>
          <span className="font-mono">~{Math.max(1, Math.ceil(value.length / 4))} tokens</span>
        </div>
      </div>
    </div>
  );
}
