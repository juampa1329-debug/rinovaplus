import { useEffect, useRef, useState } from "react";
import { Button, Notice } from "../../../shared/ui";
import { ClientsError } from "../../clients/api/clientsApi";
import { operationDate } from "../../inbox/api/inboxOperations";
import { useInboxIntents } from "../../../shared/inboxSession";
export type EventStatus = {
  counts: { pending: number; leased: number; prepared: number; failed: number };
  uncaptured: Record<string, number>;
  conversations: number;
  preparedConversations: number;
  lastPreparedAt: string | null;
  worker: { state: string; alive: boolean; lastCycleAt: string | null };
};
export const eventApi = {
  async status(signal?: AbortSignal): Promise<EventStatus> {
    const response = await fetch("/api/local/crm/events/status", {
      cache: "no-store",
      headers: { "X-CRM-Local": "1" },
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
        : AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new ClientsError(response.status);
    return response.json();
  },
  async retry(operationId: string): Promise<{ retried: number }> {
    const response = await fetch("/api/local/crm/events/retry", {
      method: "POST",
      headers: { "X-CRM-Local": "1", "Content-Type": "application/json" },
      body: JSON.stringify({ operationId }),
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new ClientsError(response.status);
    return response.json();
  },
};
export function ConversationProcessing() {
  const [snapshot, setSnapshot] = useState<EventStatus | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const intents = useInboxIntents();
  const lock = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    void eventApi
      .status(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) {
          setSnapshot(value);
          setError("");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError(
            "No se pudo consultar la preparación. Los contadores anteriores pueden estar desactualizados.",
          );
      });
    const timer = setTimeout(() => setAttempt((n) => n + 1), 10000);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [attempt]);
  async function retry() {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    const key = "conversation-events-retry";
    const intent = intents.get(key) ?? {
      operationId: crypto.randomUUID(),
      messageId: "",
    };
    intents.set(key, intent);
    try {
      const result = await eventApi.retry(intent.operationId);
      intents.delete(key);
      setMessage(`${result.retried} eventos devueltos a la cola técnica.`);
      setAttempt((n) => n + 1);
    } catch {
      setMessage(
        "No se confirmó el reintento. Vuelva a intentar; se conserva la misma operación.",
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const gaps = snapshot
    ? Object.values(snapshot.uncaptured).reduce((a, b) => a + b, 0)
    : null;
  return (
    <section className="panel" aria-labelledby="conversation-processing-title">
      <h3 id="conversation-processing-title">
        Preparación de conversaciones · R3A
      </h3>
      <p>
        El proceso local registra referencias y prepara metadatos para R4. No
        analiza con IA, no genera contexto ni envía respuestas. Funciona también
        durante atención humana.
      </p>
      {error && (
        <Notice error>
          {error}{" "}
          <Button variant="quiet" onClick={() => setAttempt((n) => n + 1)}>
            Actualizar preparación
          </Button>
        </Notice>
      )}
      {!snapshot && !error && (
        <p role="status">Consultando preparación técnica…</p>
      )}
      {snapshot && (
        <>
          <p>
            Procesador:{" "}
            {snapshot.worker.alive && snapshot.worker.state === "running"
              ? "En ejecución"
              : snapshot.worker.state === "storage_unavailable"
                ? "Almacenamiento no disponible"
                : "Sin actividad confirmada"}
            .
          </p>
          <dl className="detail-list">
            <dt>Referencias sin registrar</dt>
            <dd>{gaps}</dd>
            <dt>Eventos pendientes</dt>
            <dd>{snapshot.counts.pending}</dd>
            <dt>Eventos en preparación</dt>
            <dd>{snapshot.counts.leased}</dd>
            <dt>Eventos preparados técnicamente</dt>
            <dd>{snapshot.counts.prepared}</dd>
            <dt>Eventos fallidos</dt>
            <dd>{snapshot.counts.failed}</dd>
            <dt>Conversaciones con preparación registrada</dt>
            <dd>
              {snapshot.preparedConversations} de {snapshot.conversations}
            </dd>
            <dt>Última preparación (America/Bogota)</dt>
            <dd>{operationDate(snapshot.lastPreparedAt)}</dd>
            <dt>Último ciclo del proceso (America/Bogota)</dt>
            <dd>{operationDate(snapshot.worker.lastCycleAt)}</dd>
          </dl>
          <p>
            La cobertura registrada no elimina pendientes posteriores. Se
            actualiza cada diez segundos; la captura automática revisa fuentes
            cada cinco segundos, según disponibilidad y carga.
          </p>
          <Button
            disabled={busy || !snapshot.counts.failed || !!error}
            onClick={() => void retry()}
          >
            Reintentar hasta 25 eventos fallidos
          </Button>
        </>
      )}
      {message && <Notice>{message}</Notice>}
    </section>
  );
}
