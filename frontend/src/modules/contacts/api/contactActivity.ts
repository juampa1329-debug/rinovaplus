import { ClientsError } from "../../clients/api/clientsApi";

export type ActivityKind =
  "all" | "contact" | "conversation" | "message" | "assignment" | "task";
export type ActivityFilters = {
  kind: ActivityKind;
  fromDate: string;
  toDate: string;
};
export type ActivityItem = {
  id: string;
  source: string;
  sourceId: string;
  occurredAt: string;
  kind: Exclude<ActivityKind, "all">;
  action: string;
  actor: string | null;
  direction: string | null;
  sourceContactId?: string;
  conversationId?: string;
};
export type ContactActivityPage = {
  items: ActivityItem[];
  limit: number;
  hasMore: boolean;
  nextCursor: string | null;
  metrics: {
    scope: string;
    memberCount?: number;
    slaConversationId?: string;
    calculatedAt: string;
    messages: {
      messages: number;
      incoming: number;
      outgoing: number;
      lastMessageAt: string | null;
    };
    tasks: {
      pendingTasks: number;
      completedTasks: number;
      cancelledTasks: number;
      overdueTasks: number;
    } | null;
    sla: { status: string; startedAt: string | null; dueAt: string | null };
  };
  historyScope: {
    contactId: string;
    kind: ActivityKind;
    fromDate: string | null;
    toDate: string | null;
    dateZone: string;
    upperBound: string;
    timestamps: string;
    fieldHistory: string;
    actorIdentity: string;
    inboxAvailable: boolean;
  };
};
export const contactActivityApi = {
  async read(
    id: string,
    filters: ActivityFilters,
    cursor: string | null,
    signal?: AbortSignal,
  ): Promise<ContactActivityPage> {
    const query = new URLSearchParams({ kind: filters.kind });
    if (filters.fromDate) query.set("fromDate", filters.fromDate);
    if (filters.toDate) query.set("toDate", filters.toDate);
    if (cursor) query.set("cursor", cursor);
    try {
      const response = await fetch(
        `/api/local/crm/clients/${encodeURIComponent(id)}/activity?${query}`,
        {
          headers: { "X-CRM-Local": "1" },
          cache: "no-store",
          signal: signal
            ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
            : AbortSignal.timeout(15000),
        },
      );
      if (!response.ok) throw new ClientsError(response.status);
      return await response.json();
    } catch (error) {
      if (signal?.aborted) throw error;
      throw new Error(
        "No se pudo consultar la actividad real. Reintente o vuelva al historial reciente; sus borradores se conservan.",
        { cause: error },
      );
    }
  },
};

export function activityLabel(item: ActivityItem) {
  if (item.action === "message_recorded")
    return item.direction === "incoming"
      ? "Registro entrante local"
      : "Registro saliente local";
  return (
    (
      {
        create_contact: "Contacto creado",
        edit_contact: "Ficha confirmada",
        update_conversation: "Operación de conversación confirmada",
        add_message: "Operación de registro de mensaje",
        assignment: "Responsables confirmados",
        task_create: "Tarea creada",
        task_edit: "Tarea confirmada",
        merge: "Relación de fichas confirmada",
        undo: "Relación de fichas revertida",
      } as Record<string, string>
    )[item.action] ?? "Operación registrada"
  );
}
