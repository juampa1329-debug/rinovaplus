import { useMemo, useState } from "react";
import { Button, Notice, SelectField } from "../shared/ui";
import { useResource, ResourceState } from "./Settings";
import { explainInboxError } from "./InboxDelivery";

type Entry = {
  id: string;
  section: string;
  action: string;
  state: string;
  code?: string;
  at: string;
  channel: string;
  account: string;
  provider?: string;
  model?: string;
  fallback_used?: boolean;
  context_changes?: string[];
  own_projection_context_refreshed?: boolean;
  attempt_count?: number;
  conversation_id?: string;
  attempts?: {
    provider: string;
    model: string;
    state: string;
    code?: string;
  }[];
};
const sections = [
  { value: "", label: "Todas las secciones" },
  { value: "ai", label: "Inteligencia artificial" },
  { value: "outbound", label: "Envíos" },
  { value: "webhook", label: "Recepción y webhooks" },
  { value: "channel", label: "Conexiones y cuentas" },
];
const stateLabels: Record<string, string> = {
  confirmed: "Confirmado",
  processed: "Procesado",
  cancelled: "Cancelado",
  abandoned: "Detenido",
  failed: "Fallido",
  uncertain: "Sin confirmar",
  pending: "Pendiente",
  queued: "En cola",
  running: "En curso",
  accepted: "Aceptado",
  sent: "Enviado",
  delivered: "Entregado",
  read: "Leído",
  quarantined: "Revisión necesaria",
};
export function DiagnosticsWorkspace() {
  const selectedConversation =
    new URLSearchParams(window.location.hash.split("?")[1] ?? "").get(
      "conversation",
    ) ?? "";
  const data = useResource<{ items: Entry[]; limit_per_section: number }>(
    `diagnostics${selectedConversation ? `?conversation_id=${encodeURIComponent(selectedConversation)}` : ""}`,
  );
  const [section, setSection] = useState(""),
    [channel, setChannel] = useState(""),
    [onlyProblems, setOnlyProblems] = useState(false);
  const items = useMemo(
    () =>
      (data.value?.items ?? []).filter(
        (v) =>
          (!section || v.section === section) &&
          (!channel || v.channel === channel) &&
          (!onlyProblems ||
            [
              "cancelled",
              "abandoned",
              "failed",
              "uncertain",
              "quarantined",
            ].includes(v.state)),
      ),
    [data.value, section, channel, onlyProblems],
  );
  if (!data.value) return <ResourceState error={data.error} />;
  return (
    <section
      aria-label="Diagnósticos de RinovaPlus"
      className="diagnostics-workspace"
    >
      <header>
        <h2>Qué está pasando en RinovaPlus</h2>
        <p>
          Sigue la recepción, la generación de IA y el envío. Consultar este
          registro no reenvía mensajes ni consume modelos.
        </p>
      </header>
      <div className="form-grid">
        <SelectField
          id="diagnostic-section"
          label="Sección"
          value={section}
          options={sections}
          onChange={(e) => setSection(e.target.value)}
        />
        <SelectField
          id="diagnostic-channel"
          label="Canal"
          value={channel}
          options={[
            { value: "", label: "Todos los canales" },
            ...["whatsapp", "instagram", "messenger", "facebook"].map(
              (value) => ({ value, label: value }),
            ),
          ]}
          onChange={(e) => setChannel(e.target.value)}
        />
        <label>
          <input
            type="checkbox"
            checked={onlyProblems}
            onChange={(e) => setOnlyProblems(e.target.checked)}
          />{" "}
          Sólo incidencias
        </label>
        <Button variant="secondary" onClick={() => void data.reload()}>
          Actualizar diagnóstico
        </Button>
      </div>
      <p>
        {items.length} registros visibles · hasta {data.value.limit_per_section}{" "}
        recientes por sección. Las fechas se muestran en tu zona horaria.
      </p>
      {selectedConversation && (
        <p>
          Filtrado por conversación.{" "}
          <a href="#/settings/diagnostics">Ver todos los registros</a>
        </p>
      )}
      {data.error && <Notice error>{data.error}</Notice>}
      {!items.length && <Notice>No hay registros para estos filtros.</Notice>}
      <ol className="diagnostic-timeline">
        {items.map((item) => {
          const issue = [
            "cancelled",
            "abandoned",
            "failed",
            "uncertain",
            "quarantined",
          ].includes(item.state);
          const explanation = explainInboxError({
            code: item.code,
            message:
              "Consulta la cuenta y la conversación antes de repetir una operación.",
          });
          return (
            <li key={`${item.section}:${item.id}`} data-problem={issue}>
              <article>
                <header>
                  <strong>{item.account}</strong>
                  <span>{stateLabels[item.state] ?? item.state}</span>
                  <time dateTime={item.at}>
                    {new Date(item.at).toLocaleString("es-CO")}
                  </time>
                </header>
                <p>
                  {sections.find((v) => v.value === item.section)?.label} ·{" "}
                  {item.channel}
                  {item.attempt_count !== undefined &&
                    ` · ${item.attempt_count} intentos de envío`}
                </p>
                {issue && (
                  <>
                    <h3>{explanation.title}</h3>
                    <p>{explanation.detail}</p>
                    <p>
                      <strong>Qué hacer:</strong> {explanation.nextStep}
                    </p>
                  </>
                )}
                {item.model && (
                  <p>
                    {item.provider} · {item.model}
                    {item.fallback_used && " · respondió el respaldo"}
                  </p>
                )}
                <details>
                  <summary>Ver detalle técnico</summary>
                  <p>
                    Acción: {item.action}. Código: {item.code || "sin error"}.
                    Referencia: {item.id}
                  </p>
                  {!!item.context_changes?.length && <p>Partes del contexto que cambiaron: {item.context_changes.join(", ")}</p>}
                  {item.own_projection_context_refreshed && <p>La ficha se actualizó y la autorización quedó ligada a esa misma versión, dentro de la transacción.</p>}
                  {item.attempts?.map((a, i) => (
                    <p key={i}>
                      {a.provider} · {a.model} · {a.state} {a.code}
                    </p>
                  ))}
                </details>
              </article>
            </li>
          );
        })}
      </ol>
      <p>
        Voces, informes, modelos y usuarios conservan sus historiales en{" "}
        <a href="#/settings/voice">Voces y audios</a>,{" "}
        <a href="#/settings/notifications">Correos</a>,{" "}
        <a href="#/agents">Agentes</a> y{" "}
        <a href="#/settings/audit">Auditoría</a>.
      </p>
    </section>
  );
}
