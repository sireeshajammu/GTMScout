import { useEffect, useState } from "react";
import { subscribe, listConversations, getConversation, getProfile } from "@/services/api";
import type { ConversationSummary, Conversation, Profile } from "@/services/types";

function useApiValue<T>(fetcher: () => Promise<T>, depKey: string): T | null {
  const [value, setValue] = useState<T | null>(null);
  useEffect(() => {
    let cancel = false;
    const load = () => {
      fetcher()
        .then((v) => {
          if (!cancel) setValue(v);
        })
        .catch(() => {});
    };
    load();
    const unsub = subscribe(load);
    return () => {
      cancel = true;
      unsub();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depKey]);
  return value;
}

export function useConversations(): ConversationSummary[] {
  const v = useApiValue(() => listConversations(), "conversations");
  return v ?? [];
}

export function useConversation(id: string | undefined): Conversation | null {
  return useApiValue(
    () => (id ? getConversation(id) : Promise.resolve(null as unknown as Conversation)),
    `conv:${id ?? ""}`,
  );
}

export function useProfile(): Profile | null {
  return useApiValue(() => getProfile(), "profile");
}
