import { useEffect, useRef, useState } from "react";
import {
  strategyApi,
  strategyReasons,
  type StrategyDetail,
  type StrategyText,
} from "../api/strategy";
import { Button, Notice, SelectField, TextArea } from "../../../shared/ui";
import { operationDate } from "../../inbox/api/inboxOperations";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import { useInboxIntents } from "../../../shared/inboxSession";
import { ClientsError } from "../../clients/api/clientsApi";

const criteria: Record<string, string> = {
  interest: "Interés expresado",
  next_step: "Siguiente paso solicitado",
  commitment: "Compromiso declarado",
};

export function ConversationStrategy({
  conversationId,
}: {
  conversationId: string;
}) {
  const [result, setResult] = useState<{
    id: string;
    data: StrategyDetail;
  } | null>(null);
  const [error, setError] = useState<{ id: string; text: string } | null>(null);
  const [readError, setReadError] = useState<{
    id: string;
    text: string;
  } | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const sequence = useRef(0);
  const intents = useInboxIntents();
  const [drafts, setDrafts] = useWorkspaceField("analysis", "strategyFeedback");
  const draft = drafts[conversationId] ?? {
    planId: "",
    usefulness: "useful",
    outcome: "not_observed",
    correction: "",
  };
  const data = result?.id === conversationId ? result.data : null;
  const failure =
    error?.id === conversationId
      ? error.text
      : readError?.id === conversationId
        ? readError.text
        : "";
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      const token = ++sequence.current;
      try {
        const value = await strategyApi.read(conversationId, controller.signal);
        if (!controller.signal.aborted && token === sequence.current) {
          setResult({ id: conversationId, data: value });
          setReadError(null);
        }
      } catch {
        if (!controller.signal.aborted && token === sequence.current)
          setReadError({
            id: conversationId,
            text: "No se pudo consultar la estrategia real. Sus borradores se conservan.",
          });
      }
    }
    void load();
    const timer = window.setInterval(() => void load(), 10000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [conversationId, refresh]);
  function change(key: "usefulness" | "outcome" | "correction", value: string) {
    setDrafts((previous) => ({
      ...previous,
      [conversationId]: {
        ...draft,
        planId: draft.planId || data?.provenance?.id || "",
        [key]: value,
      },
    }));
  }
  async function save(action: string, fields: object) {
    if (!data || lock.current) return;
    lock.current = true;
    setBusy(true);
    const id = conversationId;
    const key = "strategy:" + JSON.stringify([id, action, fields]);
    let intent = intents.get(key);
    if (!intent) {
      intent = {
        operationId: crypto.randomUUID(),
        messageId: crypto.randomUUID(),
        expectedRevision: data.revision,
      };
      intents.set(key, intent);
    }
    try {
      await strategyApi.write(id, action, {
        operationId: intent.operationId,
        expectedRevision: intent.expectedRevision ?? data.revision,
        ...fields,
      });
      intents.delete(key);
      if (action === "feedback")
        setDrafts((previous) => {
          const next = { ...previous };
          delete next[id];
          return next;
        });
      setError(null);
      setRefresh((n) => n + 1);
    } catch (cause) {
      if (cause instanceof ClientsError && cause.status === 409)
        intents.delete(key);
      setError({
        id,
        text:
          cause instanceof ClientsError && cause.status === 409
            ? "La conversación o el plan cambió. Actualice y revise la propuesta; su borrador se conserva."
            : "No se pudo confirmar la operación. Puede reintentar; no se crearán duplicados.",
      });
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const plan = data?.plan;
  const provenance = data?.provenance;
  const draftStale = !!draft.planId && draft.planId !== provenance?.id;
  function items(label: string, values: StrategyText[]) {
    if (!values.length) return null;
    return (
      <div>
        <h4>{label}</h4>
        <ul>
          {values.map((item, i) => (
            <li key={i}>
              {item.text}
              <small>
                {" "}
                · {item.evidenceIds.length} referencia(s) de la conversación
              </small>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  return (
    <section
      className="mini-crm"
      aria-label="Estrategia y autonomía interna IA"
    >
      <h3>Inteligencia predictiva · IA</h3>
      <p>
        Estimación cualitativa experimental. El índice cuenta tres señales
        observables; no es una probabilidad de conversión ni un modelo
        estadístico calibrado.
      </p>
      {failure && (
        <Notice error>
          {failure}{" "}
          <Button variant="quiet" onClick={() => setRefresh((n) => n + 1)}>
            Actualizar estrategia
          </Button>
        </Notice>
      )}
      {!data && !failure && <p role="status">Consultando estrategia…</p>}
      {data && (
        <>
          <dl>
            <dt>Señales comerciales</dt>
            <dd>
              {plan?.index == null
                ? "No evaluable"
                : `${plan.index} de 3 señales documentadas`}
            </dd>
            <dt>Riesgo de abandono · estimación cualitativa</dt>
            <dd>
              {!plan || plan.churn.level === "unknown"
                ? "Desconocido"
                : plan.churn.level === "concern"
                  ? "Señales de preocupación"
                  : "Retirada expresada en la conversación"}
            </dd>
          </dl>
          <details>
            <summary>Rúbrica de las tres señales</summary>
            <ul>
              {Object.values(criteria).map((label) => (
                <li key={label}>
                  {label}: requiere evidencia entrante identificable.
                </li>
              ))}
            </ul>
            <p>
              La ausencia de evidencia no significa desinterés. Una objeción o
              el silencio no confirman abandono.
            </p>
          </details>
          {!plan && (
            <p>
              Sin evaluación generada. No se muestran puntuaciones, riesgos ni
              recomendaciones de demostración.
            </p>
          )}
          {plan && (
            <>
              {!data.autonomy.planCurrent && (
                <Notice>
                  Evaluación anterior: requiere un análisis vigente antes de
                  ejecutar acciones.
                </Notice>
              )}
              {plan.signals.map((signal) => (
                <p key={signal.criterion}>
                  <strong>{criteria[signal.criterion]}:</strong> {signal.text} ·{" "}
                  {signal.evidenceIds.length} referencia(s) entrante(s).
                </p>
              ))}
              {plan.churn.text && (
                <p>
                  {plan.churn.text} · {plan.churn.evidenceIds.length}{" "}
                  referencia(s).
                </p>
              )}
              {items("Estrategia sugerida", plan.recommendations)}
              {items("Manejo informativo de objeciones", plan.objections)}
              {items("Propuestas de remarketing · sin envío", plan.remarketing)}
              {items("Borradores de lectura · no enviados", plan.drafts)}
              {provenance && (
                <p className="muted">
                  {provenance.provider} / {provenance.model} · revisión{" "}
                  {provenance.revision} · {operationDate(provenance.createdAt)}{" "}
                  · {provenance.promptVersion}
                </p>
              )}
            </>
          )}
          <h4>Autonomía de esta conversación</h4>
          <p>
            Solicitada: {data.autonomy.requested ? "Sí" : "No"}. Estado
            efectivo:{" "}
            {data.autonomy.effective
              ? "Puede crear una tarea interna"
              : "Pausada o bloqueada"}
            .
          </p>
          <p>
            Únicamente una tarea de seguimiento por plan, sin fecha inventada y
            sin duplicar tareas pendientes. No responde, envía mensajes ni
            activa campañas. La atención humana pausa la ejecución; el análisis
            continúa según su configuración.
          </p>
          <ul>
            {data.autonomy.reasons.map((reason) => (
              <li key={reason}>
                {strategyReasons[reason] ?? "Acción no disponible."}
              </li>
            ))}
          </ul>
          <div className="inline-actions">
            <Button
              disabled={busy}
              onClick={() =>
                void save("autonomy", { enabled: !data.autonomy.requested })
              }
            >
              {data.autonomy.requested
                ? "Desactivar autonomía interna"
                : "Solicitar autonomía interna"}
            </Button>
            <Button
              variant="quiet"
              disabled={busy}
              onClick={() =>
                void save("pause", { paused: !data.autonomy.globalPaused })
              }
            >
              {data.autonomy.globalPaused
                ? "Quitar pausa global de tareas IA"
                : "Pausar todas las tareas IA"}
            </Button>
          </div>
          <p>
            Tareas internas creadas: {data.metrics.tasksCreated}. Evaluaciones
            humanas: {data.metrics.feedback}; útiles: {data.metrics.useful}.
            Alcance: esta conversación.
          </p>
          {provenance && (
            <details>
              <summary>Evaluar esta propuesta</summary>
              <p>
                Su evaluación se conserva con la revisión del plan. No cambia la
                calificación derivada ni confirma matrícula o pago.
              </p>
              {draftStale && (
                <Notice>
                  El borrador pertenece a un plan anterior. Revise el plan
                  actual antes de iniciar una nueva evaluación.
                  <Button
                    variant="quiet"
                    onClick={() =>
                      setDrafts((previous) => ({
                        ...previous,
                        [conversationId]: {
                          planId: provenance.id,
                          usefulness: "useful",
                          outcome: "not_observed",
                          correction: "",
                        },
                      }))
                    }
                  >
                    Empezar evaluación del plan actual
                  </Button>
                </Notice>
              )}
              <SelectField
                id={"strategy-usefulness-" + conversationId}
                label="Utilidad"
                value={draft.usefulness}
                onChange={(e) => change("usefulness", e.target.value)}
                options={[
                  { value: "useful", label: "Útil" },
                  { value: "not_useful", label: "No útil" },
                  { value: "correction", label: "Requiere corrección" },
                ]}
              />
              <SelectField
                id={"strategy-outcome-" + conversationId}
                label="Resultado observado por el operador"
                value={draft.outcome}
                onChange={(e) => change("outcome", e.target.value)}
                options={[
                  { value: "not_observed", label: "Sin resultado observado" },
                  { value: "followup_needed", label: "Requiere seguimiento" },
                  { value: "reply_observed", label: "Respuesta observada" },
                  {
                    value: "no_contact",
                    label: "Solicitud de no contacto observada",
                  },
                ]}
              />
              <TextArea
                id={"strategy-correction-" + conversationId}
                label="Corrección o comentario"
                value={draft.correction}
                maxLength={1000}
                onChange={(e) => change("correction", e.target.value)}
              />
              <Button
                disabled={
                  busy ||
                  draftStale ||
                  (draft.usefulness === "correction" &&
                    !draft.correction.trim())
                }
                onClick={() =>
                  void save("feedback", {
                    planId: provenance.id,
                    planRevision: provenance.revision,
                    usefulness: draft.usefulness,
                    outcome: draft.outcome,
                    correction: draft.correction,
                  })
                }
              >
                Guardar evaluación de propuesta
              </Button>
            </details>
          )}
        </>
      )}
    </section>
  );
}
