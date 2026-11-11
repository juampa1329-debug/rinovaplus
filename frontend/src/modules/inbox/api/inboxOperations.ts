import { useEffect, useRef, useState } from "react";
import { ClientsError } from "../../clients/api/clientsApi";
import { useInboxIntents } from "../../../shared/inboxSession";
export type DirectoryItem = {
  revision?: string;
  id: string | number;
  name: string;
  description?: string;
  enabled: boolean;
  sourceActive?: boolean;
  selectable: boolean;
};
export type DirectoryPage = {
  items: DirectoryItem[];
  offset: number;
  hasMore: boolean;
  revision: string;
};
export type Policy = {
  enabled: boolean;
  thresholdMinutes: number;
  updatedAt: string;
};
export type Configuration = { policy: Policy | null; revision: string };
export type Task = {
  id: string;
  title: string;
  priority: string;
  status: string;
  humanEmployeeId: number | null;
  humanName: string;
  humanSelectable: boolean;
  dueAt: string | null;
  overdue: boolean;
  createdAt: string;
};
export type OperationDetail = {
  revision: string;
  offset: number;
  hasMore: boolean;
  tasks: Task[];
  assignment: {
    humanEmployeeId: number | null;
    aiAgentId: string | null;
    humanName: string;
    aiName: string | null;
    humanSelectable: boolean;
    aiSelectable: boolean;
    controlMode: string;
    slaStatus: string;
    startedAt: string | null;
    dueAt: string | null;
    thresholdMinutes: number | null;
    firstResponseDueAt: string | null;
  };
};
export type TaskDraft = {
  revision: string;
  id: string;
  title: string;
  priority: string;
  human: string;
  humanName: string;
  due: string;
  status: string;
  editing: boolean;
};
export type AssignmentDraft = {
  revision: string;
  human: string;
  humanName: string;
  ai: string;
  aiName: string;
};
export type AgentDraft = {
  revision: string;
  id: string;
  name: string;
  description: string;
  enabled: boolean;
};
export const slaLabels: Record<string, string> = {
  not_configured: "SLA no configurado",
  closed: "Conversación cerrada · sin SLA pendiente",
  no_incoming: "Sin mensaje entrante pendiente · sin medición",
  on_time: "Próxima respuesta en plazo",
  overdue: "Próxima respuesta vencida",
};
export const priorityOptions = [
  { value: "low", label: "Baja" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "Alta" },
  { value: "urgent", label: "Urgente" },
];
export function operationDate(value: string | null) {
  return value
    ? new Date(value).toLocaleString("es-CO", {
        timeZone: "America/Bogota",
        dateStyle: "short",
        timeStyle: "short",
      })
    : "Sin fecha";
}
export function taskInputDate(value: string | null) {
  if (!value) return "";
  return new Date(new Date(value).getTime() - 5 * 3600000)
    .toISOString()
    .slice(0, 16);
}
export const inboxOperationsApi = {
  async read<T>(path: string, signal?: AbortSignal): Promise<T> {
    return request<T>(path, undefined, signal);
  },
  async write(path: string, body: object) {
    return request<{ revision: string }>(path, body);
  },
};
async function request<T>(
  path: string,
  body?: object,
  signal?: AbortSignal,
): Promise<T> {
  try {
    const response = await fetch("/api/local/crm/inbox/operations" + path, {
      method: body ? "PUT" : "GET",
      cache: "no-store",
      headers: {
        "X-CRM-Local": "1",
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
        : AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new ClientsError(response.status);
    return (await response.json()) as T;
  } catch (error) {
    if (signal?.aborted) throw error;
    throw error instanceof ClientsError ? error : new ClientsError(0);
  }
}
export function useOperations<T extends { revision: string }>(
  path: string,
  externalRefresh: number,
  onConfirmed?: () => void,
) {
  const [value, setValue] = useState<{ path: string; data: T } | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [readError, setReadError] = useState("");
  const [feedback, setFeedback] = useState("");
  const lock = useRef(false);
  const mounted = useRef(false);
  const intents = useInboxIntents();
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void inboxOperationsApi
      .read<T>(path, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setValue({ path, data });
          setReadError("");
          setLoading(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setReadError(
            "No se pudo cargar la operación de Inbox. Reintente; los borradores se conservan.",
          );
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [path, refresh, externalRefresh]);
  const data = value?.path === path ? value.data : null;
  function reload() {
    setLoading(true);
    setRefresh((n) => n + 1);
  }
  async function save(target: string, input: object, revision?: string) {
    if (lock.current || loading || !data) return false;
    const key = JSON.stringify(["inbox-operations", target, input]);
    const intent = intents.get(key) ?? {
      operationId: crypto.randomUUID(),
      messageId: crypto.randomUUID(),
    };
    intents.set(key, intent);
    lock.current = true;
    setBusy(true);
    setError("");
    setFeedback("");
    try {
      await inboxOperationsApi.write(target, {
        ...input,
        operationId: intent.operationId,
        expectedRevision: revision ?? data.revision,
      });
      intents.delete(key);
      if (mounted.current) {
        setFeedback("Cambio confirmado.");
        reload();
      }
      onConfirmed?.();
      return true;
    } catch (failure) {
      if (mounted.current) {
        setError(
          failure instanceof ClientsError && failure.status === 409
            ? "Los datos cambiaron. El borrador conserva su revisión original; revise los datos actuales y descarte el borrador para iniciar una edición nueva."
            : failure instanceof Error
              ? failure.message
              : "No se pudo confirmar la operación.",
        );
        if (failure instanceof ClientsError && failure.status === 409) reload();
      }
      return false;
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return {
    data,
    loading,
    busy,
    error: error || readError,
    feedback,
    reload,
    save,
  };
}
