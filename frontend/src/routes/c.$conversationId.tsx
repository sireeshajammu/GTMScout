import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { ChatThread } from "@/components/ChatThread";
import { useConversation } from "@/lib/store";

export const Route = createFileRoute("/c/$conversationId")({
  component: ConversationPage,
});

function ConversationPage() {
  const { conversationId } = Route.useParams();
  const conversation = useConversation(conversationId);

  if (!conversation) {
    return (
      <AppShell title="Loading…">
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          Loading conversation…
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={conversation.title}>
      <ChatThread conversation={conversation} />
    </AppShell>
  );
}
