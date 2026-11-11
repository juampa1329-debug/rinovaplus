import type { Thread } from "../shared/demo";
import { AnalysisConversation } from "../modules/conversation-analysis/pages/ConversationAnalysis";
import { ContactActivity } from "../modules/contacts/components/ContactActivity";
import { ConversationStrategy } from "../modules/conversation-strategy/pages/ConversationStrategy";
import { useRuntime } from "../shared/runtimeCapabilities";
export function MiniCrm({
  thread,
  refresh,
}: {
  thread?: Thread;
  refresh?: string | number;
}) {
  const { features } = useRuntime().capabilities;
  if (!features.advancedCrm) return null;
  if (thread?.id)
    return (
      <>
        <AnalysisConversation
          key={`analysis:${thread.id}`}
          conversationId={thread.id}
        />
        <ConversationStrategy
          key={`strategy:${thread.id}`}
          conversationId={thread.id}
        />
        <ContactActivity
          key={`activity:${thread.clientId}`}
          contactId={thread.clientId}
          refresh={refresh}
        />
      </>
    );
  return (
    <section className="mini-crm" aria-label="Mini CRM conversacional">
      <h3>Contexto conversacional</h3>
      <p>
        {thread
          ? "Análisis automático no disponible. Revise los mensajes y la ficha antes de decidir."
          : "Seleccione una conversación para consultar su contexto."}
      </p>
    </section>
  );
}
