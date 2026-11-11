import { ClientsError } from "../../clients/api/clientsApi";

export type StrategyText = { text: string; evidenceIds: string[] };
export type StrategyDetail = {
  revision: string;
  conversationId: string;
  autonomy: {
    requested: boolean;
    effective: boolean;
    globalPaused: boolean;
    planCurrent: boolean;
    reasons: string[];
  };
  metrics: { tasksCreated: number; feedback: number; useful: number };
  plan: {
    index: number | null;
    signals: (StrategyText & { criterion: string })[];
    churn: StrategyText & { level: "unknown" | "concern" | "withdrawal" };
    noContact: boolean;
    recommendations: StrategyText[];
    objections: StrategyText[];
    remarketing: StrategyText[];
    drafts: StrategyText[];
  } | null;
  provenance: {
    id: string;
    revision: number;
    generation: number;
    provider: string;
    model: string;
    promptVersion: string;
    createdAt: string;
  } | null;
};
const root = "/api/local/crm/strategy/conversations/";
export const strategyApi = {
  async read(id: string, signal: AbortSignal): Promise<StrategyDetail> {
    const response = await fetch(root + encodeURIComponent(id), {
      headers: { "X-CRM-Local": "1" },
      cache: "no-store",
      signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
    });
    if (!response.ok) throw new ClientsError(response.status);
    return response.json();
  },
  async write(id: string, action: string, body: object) {
    const response = await fetch(root + encodeURIComponent(id) + "/" + action, {
      method: "POST",
      headers: { "X-CRM-Local": "1", "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new ClientsError(response.status);
    return response.json();
  },
};

export const strategyReasons: Record<string, string> = {
  analysis_reserved:
    "Hay un análisis reservado en esta conversación o en su historial de identidad; la tarea espera su resolución.",
  global_pause: "Pausa global de tareas automáticas activada.",
  not_requested: "Autonomía interna no solicitada para esta conversación.",
  human_control:
    "La atención humana pausa la ejecución; el análisis puede continuar.",
  conversation_closed: "La conversación está cerrada.",
  analysis_unavailable: "Análisis IA no habilitado o proveedor no disponible.",
  plan_missing_or_stale: "No hay un plan vigente con cobertura completa.",
  insufficient_incoming_evidence:
    "No existe una solicitud entrante de siguiente paso o compromiso comprobable.",
  no_contact:
    "Existe una solicitud de no contacto. No se permite seguimiento automático.",
  operator_no_contact_report:
    "Un operador reportó una solicitud de no contacto. El seguimiento automático permanece bloqueado.",
  pending_task: "Ya existe una tarea pendiente; no se duplicará.",
  plan_already_executed: "Este plan ya creó su única tarea interna.",
  human_assignee_unavailable:
    "El responsable humano asignado ya no está disponible en Admisiones.",
  ai_assignee_unavailable:
    "No hay un agente IA activo asignado a esta conversación.",
};
