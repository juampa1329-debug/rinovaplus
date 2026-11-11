import { useState } from "react";
import { Button, Field, Notice, TextArea } from "../../../shared/ui";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import { aiRequest } from "../../../shared/aiSettings";
import { operationDate } from "../../inbox/api/inboxOperations";
import {
  useAnalysis,
  type AnalysisConfiguration,
  type AnalysisPolicyDraft,
  type AnalysisDetail,
  type AnalysisContext,
} from "../api/analysis";

const stateLabels: Record<string, string> = {
  disabled: "Desactivado",
  running: "En ejecución",
  stopped: "Sin actividad confirmada",
  outbound_disabled: "Consultas externas deshabilitadas",
  provider_key_missing: "Falta la credencial del proveedor",
  model_unavailable: "Modelo no disponible",
  budget_exhausted: "Presupuesto diario agotado",
  storage_unavailable: "Almacenamiento no disponible",
  unavailable: "No disponible",
  pending: "Pendiente",
  current: "Contexto registrado",
  processing: "Analizando",
  failed: "Fallido",
  no_messages: "Sin mensajes para analizar",
  not_configured: "No configurado",
};
export function AnalysisSettings() {
  const store = useAnalysis<AnalysisConfiguration>("/configuration");
  const [savedDraft, setDraft] = useWorkspaceField("analysis", "policy");
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [catalogError, setCatalogError] = useState("");
  const policy = store.data?.policy;
  const draft: AnalysisPolicyDraft = savedDraft ?? {
    revision: store.data?.revision ?? "0",
    enabled: policy?.enabled ?? false,
    provider: policy?.provider ?? "",
    model: policy?.model ?? "",
    scopeAccepted: policy?.scopeAccepted ?? false,
    dailyRequests: policy ? String(policy.dailyRequests) : "",
    dailyOutputTokens: policy ? String(policy.dailyOutputTokens) : "",
    outputTokens: policy ? String(policy.outputTokens) : "",
  };
  function change<K extends keyof AnalysisPolicyDraft>(
    key: K,
    value: AnalysisPolicyDraft[K],
  ) {
    setDraft({ ...draft, [key]: value });
  }
  const configured =
    store.data?.connection.providers.some(
      (p) => p.id === draft.provider && p.configured,
    ) ?? false;
  const numbers = [
    draft.dailyRequests,
    draft.dailyOutputTokens,
    draft.outputTokens,
  ];
  const valid =
    !!draft.provider &&
    !!draft.model &&
    numbers.every((n) => /^\d+$/.test(n) && Number(n) > 0) &&
    Number(draft.outputTokens) >= 256 &&
    Number(draft.outputTokens) <= 8192 &&
    Number(draft.dailyRequests) <= 10000 &&
    Number(draft.dailyOutputTokens) <= 10000000 &&
    Number(draft.outputTokens) <= Number(draft.dailyOutputTokens) &&
    (!draft.enabled ||
      (draft.scopeAccepted && configured && store.data?.connection.outbound));
  async function loadModels() {
    setLoading(true);
    setCatalogError("");
    try {
      const value = await aiRequest<{ models: { id: string; name: string }[] }>(
        "models/" + draft.provider,
        "POST",
      );
      setModels(value.models);
    } catch {
      setCatalogError(
        "No se pudo cargar el catálogo real del proveedor. No se ofrecen modelos de demostración.",
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <section className="panel" aria-labelledby="analysis-settings-title">
      <h3 id="analysis-settings-title">
        Análisis continuo de conversaciones · R4
      </h3>
      <p>
        Activación independiente del Asistente. Incluye conversaciones abiertas
        y cerradas, también durante atención humana. Genera contexto de lectura;
        no responde ni envía mensajes.
      </p>
      {store.readError && (
        <Notice error>
          {store.readError}{" "}
          <Button variant="quiet" onClick={store.reload}>
            Actualizar análisis
          </Button>
        </Notice>
      )}
      {!store.data && !store.readError && (
        <p role="status">Consultando configuración de análisis…</p>
      )}
      {store.data && (
        <>
          <p>
            Procesador de análisis:{" "}
            {stateLabels[store.data.worker.state] ?? "No disponible"}. Consultas
            externas:{" "}
            {store.data.connection.outbound ? "permitidas" : "deshabilitadas"}.
          </p>
          <p>
            {store.data.coverage.withContext ?? 0} de{" "}
            {store.data.coverage.conversations} conversaciones con contexto
            registrado. Esta cifra incluye contextos antiguos; revise vigencia y
            cobertura en cada ficha.
          </p>
          <p>
            Presupuesto consumido hoy (día UTC): {store.data.usage.requests}{" "}
            solicitudes de generación; {store.data.usage.reservedOutputTokens}{" "}
            tokens de salida reservados. Se cuentan fallos y respuestas
            inciertas; no es una factura ni un conteo exacto de tokens usados.
          </p>
          {store.data.connection.serverCredentials && (
            <Notice>
              En este servidor las claves y el permiso de consultas externas se
              administran en el entorno privado y requieren reiniciar el
              servicio. Revise Ajustes → APIs. No introduzca claves en
              conversaciones ni en esta política.
            </Notice>
          )}
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (valid)
                void store
                  .save("/policy", {
                    expectedRevision: draft.revision,
                    enabled: draft.enabled,
                    provider: draft.provider,
                    model: draft.model,
                    inputScope: "redacted_messages",
                    scopeAccepted: draft.scopeAccepted,
                    dailyRequests: Number(draft.dailyRequests),
                    dailyOutputTokens: Number(draft.dailyOutputTokens),
                    outputTokens: Number(draft.outputTokens),
                  })
                  .then((ok) => {
                    if (ok) setDraft(null);
                  });
            }}
          >
            <fieldset disabled={store.busy || loading} className="ai-fieldset">
              <div className="field">
                <label htmlFor="analysis-provider">Proveedor de análisis</label>
                <select
                  id="analysis-provider"
                  value={draft.provider}
                  onChange={(event) => {
                    setDraft({
                      ...draft,
                      provider: event.target.value,
                      model: "",
                      enabled: false,
                      scopeAccepted: false,
                    });
                    setModels([]);
                  }}
                >
                  <option value="">Seleccione un proveedor</option>
                  {store.data.connection.providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.id}
                      {p.configured ? "" : " · sin credencial"}
                    </option>
                  ))}
                </select>
              </div>
              <Button
                disabled={
                  !configured || !store.data.connection.outbound || loading
                }
                onClick={() => void loadModels()}
              >
                Cargar modelos del proveedor
              </Button>
              {catalogError && <Notice error>{catalogError}</Notice>}
              <div className="field">
                <label htmlFor="analysis-model">Modelo de análisis</label>
                <select
                  id="analysis-model"
                  value={draft.model}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      model: event.target.value,
                      enabled: false,
                      scopeAccepted: false,
                    })
                  }
                >
                  <option value="">Seleccione un modelo del catálogo</option>
                  {draft.model && !models.some((m) => m.id === draft.model) && (
                    <option value={draft.model}>
                      {draft.model} · selección conservada
                    </option>
                  )}
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-grid">
                <Field
                  id="analysis-requests"
                  label="Máximo de solicitudes por día UTC"
                  type="number"
                  min={1}
                  max={10000}
                  value={draft.dailyRequests}
                  onChange={(e) => change("dailyRequests", e.target.value)}
                />
                <Field
                  id="analysis-daily-tokens"
                  label="Máximo de tokens de salida reservados por día UTC"
                  type="number"
                  min={256}
                  max={10000000}
                  value={draft.dailyOutputTokens}
                  onChange={(e) => change("dailyOutputTokens", e.target.value)}
                />
                <Field
                  id="analysis-output"
                  label="Límite de tokens de salida por solicitud"
                  type="number"
                  min={256}
                  max={8192}
                  value={draft.outputTokens}
                  onChange={(e) => change("outputTokens", e.target.value)}
                />
              </div>
              <p>
                Alcance: hasta seis mensajes nuevos por lote, contexto previo y
                hasta cinco correcciones humanas. Se ocultan identidad conocida,
                teléfonos, correos y patrones de credenciales/documentos. No se
                transmite la ficha ni adjuntos. La redacción automática no
                garantiza anonimato completo del texto libre.
              </p>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={draft.scopeAccepted}
                  onChange={(e) => change("scopeAccepted", e.target.checked)}
                />
                Autorizo este alcance de análisis con el proveedor y modelo
                seleccionados.
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={draft.enabled}
                  onChange={(e) => change("enabled", e.target.checked)}
                />
                Activar análisis continuo
              </label>
              <div className="button-row">
                <Button type="submit" disabled={!valid}>
                  Guardar política de análisis
                </Button>
                <Button
                  variant="quiet"
                  disabled={!savedDraft}
                  onClick={() => setDraft(null)}
                >
                  Descartar borrador de análisis
                </Button>
              </div>
            </fieldset>
          </form>
          <Button
            disabled={store.busy || !store.data.coverage.failed}
            onClick={() => void store.save("/retry", {})}
          >
            Reintentar hasta 25 análisis fallidos
          </Button>
        </>
      )}
      {store.writeError && <Notice error>{store.writeError}</Notice>}
      {store.feedback && <Notice>{store.feedback}</Notice>}
    </section>
  );
}
const sections: Record<keyof AnalysisContext, string> = {
  summary: "Resumen",
  intention: "Intención",
  behavior: "Comportamiento observable",
  objections: "Objeciones",
  commitments: "Compromisos",
  nextAction: "Siguiente acción sugerida",
};
const kinds = {
  fact: "Hecho del diálogo",
  declaration: "Declaración",
  inference: "Inferencia",
};
const subjects = {
  contact: "Contacto",
  operator: "Operador",
  conversation: "Conversación",
};
export function AnalysisConversation({
  conversationId,
}: {
  conversationId: string;
}) {
  const store = useAnalysis<AnalysisDetail>("/conversations/" + conversationId);
  const [drafts, setDrafts] = useWorkspaceField("analysis", "feedback");
  const draft = drafts[conversationId];
  function discard() {
    setDrafts((previous) => {
      const next = { ...previous };
      delete next[conversationId];
      return next;
    });
  }
  const data = store.data;
  return (
    <section className="mini-crm" aria-label="Contexto IA de la conversación">
      <h3>Contexto conversacional · IA</h3>
      {store.readError && (
        <Notice error>
          {store.readError}{" "}
          <Button variant="quiet" onClick={store.reload}>
            Actualizar contexto
          </Button>
        </Notice>
      )}
      {!data && !store.readError && <p role="status">Consultando contexto…</p>}
      {data && (
        <>
          <p>
            {stateLabels[data.status] ?? "Pendiente"}. Análisis{" "}
            {data.enabled ? "habilitado" : "desactivado"}.
          </p>
          <p>
            Mensajes cubiertos: {data.coveredMessages} de {data.totalMessages}.
            Referencias pendientes: {data.pendingReferences}.
          </p>
          {!data.context && (
            <p>
              Sin análisis generado. No se muestran evaluaciones de
              demostración.
            </p>
          )}
          {data.context && (
            <>
              {(data.stale || data.partial) && (
                <Notice>
                  Contexto parcial o pendiente de actualización. No representa
                  todavía todas las referencias actuales.
                </Notice>
              )}
              <p>
                Derivado de solo lectura · {operationDate(data.analyzedAt)} ·{" "}
                {data.provenance?.provider} / {data.provenance?.model} ·{" "}
                {data.provenance?.promptVersion} · política{" "}
                {data.provenance?.policyRevision}.
              </p>
              {(Object.keys(sections) as (keyof AnalysisContext)[]).map(
                (key) => (
                  <div key={key}>
                    <h4>{sections[key]}</h4>
                    {data.context![key].length ? (
                      data.context![key].map((claim, index) => (
                        <article key={index}>
                          <p>{claim.text}</p>
                          <small>
                            {kinds[claim.kind]} · {subjects[claim.subject]}
                          </small>
                          <details>
                            <summary>
                              Evidencia ({claim.evidenceIds.length})
                            </summary>
                            <ul>
                              {claim.evidenceIds.map((id) => {
                                const source = data.evidence.find(
                                  (e) => e.id === id,
                                );
                                return (
                                  <li key={id}>
                                    {source
                                      ? `${source.direction === "incoming" ? "Mensaje entrante" : source.direction === "outgoing" ? "Registro local del operador" : "Corrección humana"} · ${operationDate(source.createdAt)}`
                                      : "Referencia no disponible"}
                                  </li>
                                );
                              })}
                            </ul>
                          </details>
                        </article>
                      ))
                    ) : (
                      <p>Sin evidencia.</p>
                    )}
                  </div>
                ),
              )}
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  if (draft?.text.trim())
                    void store
                      .save("/conversations/" + conversationId + "/feedback", {
                        text: draft.text,
                        expectedRevision: draft.revision,
                      })
                      .then((ok) => {
                        if (ok) discard();
                      });
                }}
              >
                <TextArea
                  id={"analysis-feedback-" + conversationId}
                  label="Corrección humana del análisis"
                  maxLength={1000}
                  value={draft?.text ?? ""}
                  onChange={(event) =>
                    setDrafts((previous) => ({
                      ...previous,
                      [conversationId]: {
                        text: event.target.value,
                        revision: draft?.revision ?? data.revision,
                      },
                    }))
                  }
                />
                <p>
                  Se registra como evidencia del operador y solicita
                  reevaluación. No modifica directamente el resultado IA ni
                  equivale a una declaración del contacto. El análisis necesita
                  una política habilitada para procesarla.
                </p>
                <Button
                  type="submit"
                  disabled={store.busy || !draft?.text.trim()}
                >
                  Guardar corrección humana
                </Button>{" "}
                <Button variant="quiet" disabled={!draft} onClick={discard}>
                  Descartar corrección
                </Button>
              </form>
            </>
          )}
          {data.errorCode && (
            <Notice error>
              El análisis requiere atención: {data.errorCode}. Los mensajes
              originales se conservan.
            </Notice>
          )}
          {!!data.feedback.length && (
            <details>
              <summary>Correcciones humanas recientes</summary>
              {data.feedback.map((item) => (
                <p key={item.id}>
                  {item.text} · {operationDate(item.createdAt)}
                </p>
              ))}
            </details>
          )}
        </>
      )}
      {store.writeError && <Notice error>{store.writeError}</Notice>}
      {store.feedback && <Notice>{store.feedback}</Notice>}
    </section>
  );
}
