import { useState } from "react";
import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { useConversations, useProfile } from "@/lib/store";
import { createConversation, deleteConversation, renameConversation } from "@/services/api";
import { Plus, MessageSquare, Trash2, Pencil, Globe2, PanelLeftClose, PanelLeft, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProfileCard } from "./ProfileCard";

function groupByDay(items: { id: string; title: string; updated_at: string }[]) {
  const now = Date.now();
  const day = 24 * 60 * 60 * 1000;
  const buckets: Record<string, typeof items> = { Today: [], Yesterday: [], "Previous 7 days": [], Older: [] };
  for (const it of items) {
    const age = now - new Date(it.updated_at).getTime();
    if (age < day) buckets.Today.push(it);
    else if (age < 2 * day) buckets.Yesterday.push(it);
    else if (age < 7 * day) buckets["Previous 7 days"].push(it);
    else buckets.Older.push(it);
  }
  return buckets;
}

export function Sidebar({
  collapsed,
  onToggle,
  onOpenProfile,
}: {
  collapsed: boolean;
  onToggle: () => void;
  onOpenProfile: () => void;
}) {
  const conversations = useConversations();
  const profile = useProfile();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const activeId = pathname.startsWith("/c/") ? pathname.slice(3) : null;

  const handleNew = async () => {
    const c = await createConversation();
    navigate({ to: "/c/$conversationId", params: { conversationId: c.id } });
  };

  const buckets = groupByDay(conversations);

  if (collapsed) {
    return (
      <aside className="hidden md:flex w-14 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground">
        <button
          onClick={onToggle}
          className="flex h-14 items-center justify-center border-b border-border hover:bg-sidebar-accent"
          aria-label="Expand sidebar"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
        <button
          onClick={handleNew}
          className="mx-2 mt-2 flex h-10 items-center justify-center rounded-lg bg-primary/15 text-primary hover:bg-primary/25"
          aria-label="New chat"
        >
          <Plus className="h-4 w-4" />
        </button>
        <div className="flex-1" />
        <button
          onClick={onOpenProfile}
          className="mx-2 mb-2 flex h-10 items-center justify-center rounded-lg bg-muted hover:bg-sidebar-accent"
          aria-label="Profile"
        >
          <span className="text-xs font-semibold">
            {profile?.name?.[0] ?? "?"}
          </span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex w-[280px] shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground">
      <div className="flex h-14 items-center justify-between px-3 border-b border-border">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Globe2 className="h-4 w-4" />
          </span>
          GTMScout
        </Link>
        <button
          onClick={onToggle}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
          aria-label="Collapse sidebar"
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>

      <div className="p-3">
        <button
          onClick={handleNew}
          className="flex w-full items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium hover:bg-sidebar-accent"
        >
          <Plus className="h-4 w-4" />
          New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {Object.entries(buckets).map(([label, items]) =>
          items.length === 0 ? null : (
            <div key={label} className="mb-3">
              <div className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {label}
              </div>
              <ul className="space-y-0.5">
                {items.map((c) => {
                  const isActive = activeId === c.id;
                  const isEditing = editingId === c.id;
                  return (
                    <li key={c.id} className="group relative">
                      {isEditing ? (
                        <div className="flex items-center gap-1 px-2 py-1.5">
                          <input
                            autoFocus
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                renameConversation(c.id, editValue.trim() || c.title);
                                setEditingId(null);
                              } else if (e.key === "Escape") {
                                setEditingId(null);
                              }
                            }}
                            className="flex-1 rounded bg-background border border-border px-1.5 py-1 text-sm"
                          />
                          <button
                            onClick={() => {
                              renameConversation(c.id, editValue.trim() || c.title);
                              setEditingId(null);
                            }}
                            className="p-1 rounded hover:bg-sidebar-accent"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => setEditingId(null)} className="p-1 rounded hover:bg-sidebar-accent">
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <Link
                          to="/c/$conversationId"
                          params={{ conversationId: c.id }}
                          className={cn(
                            "flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors",
                            isActive ? "bg-sidebar-accent text-foreground" : "text-foreground/80 hover:bg-sidebar-accent",
                          )}
                        >
                          <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-70" />
                          <span className="truncate flex-1">{c.title}</span>
                          <span className="hidden group-hover:flex items-center gap-0.5">
                            <button
                              onClick={(e) => {
                                e.preventDefault();
                                setEditingId(c.id);
                                setEditValue(c.title);
                              }}
                              className="p-1 rounded hover:bg-background"
                              aria-label="Rename"
                            >
                              <Pencil className="h-3 w-3" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.preventDefault();
                                deleteConversation(c.id);
                                if (isActive) navigate({ to: "/" });
                              }}
                              className="p-1 rounded hover:bg-background"
                              aria-label="Delete"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </span>
                        </Link>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ),
        )}
        {conversations.length === 0 && (
          <div className="px-3 py-8 text-center text-xs text-muted-foreground">
            No conversations yet. Start a new chat.
          </div>
        )}
      </div>

      <ProfileCard onOpen={onOpenProfile} />
    </aside>
  );
}
