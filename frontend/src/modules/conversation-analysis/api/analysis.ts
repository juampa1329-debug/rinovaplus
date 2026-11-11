import { useEffect, useRef, useState } from "react";
import { ClientsError } from "../../clients/api/clientsApi";
import { useInboxIntents } from "../../../shared/inboxSession";
export type AnalysisPolicy = {
  revision: string;
  enabled: boolean;
  provider: string;
  model: string;
  inputScope: "redacted_messages";
  scopeAccepted: boolean;
  dailyRequests: number;
  dailyOutputTokens: number;
  outputTokens: number;
};
export type AnalysisPolicyDraft = {
  revision: string;
  enabled: boolean;
  provider: string;
  model: string;
  scopeAccepted: boolean;
  dailyRequests: string;
  dailyOutputTokens: string;
  outputTokens: string;
};
export type AnalysisConfiguration = {
  revision: string;
  policy: AnalysisPolicy | null;
  usage: { requests: number; reservedOutputTokens: number };
  coverage: {
    conversations: number;
    withContext: number;
    processing: number;
    failed: number;
  };
  connection: {
    outbound: boolean;
    serverCredentials: boolean;
    providers: { id: string; configured: boolean }[];
  };
  worker: { state: string; alive: boolean; lastCycleAt: string | null };
};
export type AnalysisClaim = {
  text: string;
  kind: "fact" | "declaration" | "inference";
  subject: "contact" | "operator" | "conversation";
  evidenceIds: string[];
};
export type AnalysisContext = Record<
  | "summary"
  | "intention"
  | "behavior"
  | "objections"
  | "commitments"
  | "nextAction",
  AnalysisClaim[]
>;
export type AnalysisDetail = {
  revision: string;
  status: string;
  context: AnalysisContext | null;
  stale: boolean;
  partial: boolean;
  totalMessages: number;
  coveredMessages: number;
  pendingReferences: number;
  analyzedAt: string | null;
  errorCode: string | null;
  enabled: boolean;
  provenance: {
    provider: string;
    model: string;
    promptVersion: string;
    policyRevision: number;
    contextGeneration: number;
  } | null;
  evidence: { id: string; direction: string; createdAt: string }[];
  feedback: {
    id: string;
    text: string;
    sourceRevision: number;
    createdAt: string;
  }[];
};
export const analysisApi = {
  async read<T>(path: string, signal?: AbortSignal): Promise<T> {
    const response = await fetch("/api/local/crm/analysis" + path, {
      headers: { "X-CRM-Local": "1" },
      cache: "no-store",
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
        : AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new ClientsError(response.status);
    return response.json();
  },
  async write(path: string, body: object) {
    const response = await fetch("/api/local/crm/analysis" + path, {
      method: path === "/policy" ? "PUT" : "POST",
      headers: { "X-CRM-Local": "1", "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new ClientsError(response.status);
    return response.json();
  },
};
export function useAnalysis<T>(path: string) {
  const [value, setValue] = useState<{ path: string; data: T } | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [readError, setReadError] = useState("");
  const [writeError, setWriteError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
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
    void analysisApi
      .read<T>(path, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setValue({ path, data });
          setReadError("");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setReadError(
            "No se pudo consultar el análisis. Los datos anteriores pueden estar desactualizados.",
          );
      });
    const timer = setTimeout(() => setRefresh((n) => n + 1), 10000);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [path, refresh]);
  async function save(target: string, input: object) {
    if (lock.current) return false;
    lock.current = true;
    setBusy(true);
    setWriteError("");
    setFeedback("");
    const key = JSON.stringify(["analysis", target, input]);
    const intent = intents.get(key) ?? {
      operationId: crypto.randomUUID(),
      messageId: "",
    };
    intents.set(key, intent);
    try {
      await analysisApi.write(target, {
        ...input,
        operationId: intent.operationId,
      });
      intents.delete(key);
      if (mounted.current) {
        setFeedback("Cambio confirmado en SQL local.");
        setRefresh((n) => n + 1);
      }
      return true;
    } catch (error) {
      if (mounted.current)
        setWriteError(
          error instanceof ClientsError && error.status === 409
            ? "Los datos o la configuración cambiaron. El borrador conserva su revisión original; revise y descarte antes de iniciar una nueva edición."
            : "No se confirmó el cambio. Se conserva el borrador y la operación para reintentar.",
        );
      return false;
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return {
    data: value?.path === path ? value.data : null,
    readError,
    writeError,
    feedback,
    busy,
    save,
    reload: () => setRefresh((n) => n + 1),
  };
}
