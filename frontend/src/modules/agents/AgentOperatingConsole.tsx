import { useState } from "react";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../../shared/ui";
import { api, message, mutation, type Agent, type AgentConsole } from "./api";

export function AgentOperatingConsole({
  agent,
  data,
  refresh,
  busy,
  act,
  changed,
  question,
  setQuestion,
  simulate,
  simulation,
  diagnose,
}: {
  agent: Agent;
  data: AgentConsole | null;
  refresh: () => Promise<void>;
  busy: boolean;
  act: (work: () => Promise<void>) => Promise<void>;
  changed: boolean;
  question: string;
  setQuestion: (value: string) => void;
  simulate: (call: boolean) => Promise<void>;
  simulation: {
    text?: string;
    handoff?: boolean;
    network_called: boolean;
    model?: string;
    sources: { id: string; title: string }[];
    usage: unknown;
  } | null;
  diagnose: () => void;
}) {
  const [note, setNote] = useState("");
  const [kind, setKind] = useState("recommendation");
  const [impact, setImpact] = useState("medium");
  const [risk, setRisk] = useState("medium");
  const [title, setTitle] = useState("");
  const [context, setContext] = useState("");
  const [conversation, setConversation] = useState("");
  const metrics = data?.metrics;
  const percent = Math.max(
    agent.configuration.monthly_token_limit
      ? (100 * (metrics?.tokens_budget_used ?? 0)) /
          agent.configuration.monthly_token_limit
      : 0,
    agent.configuration.monthly_usd_limit
      ? (100 * (metrics?.usd_reserved ?? 0)) /
          agent.configuration.monthly_usd_limit
      : 0,
  );
  const money = (value: number | null | undefined) =>
    value == null
      ? "Desconocido"
      : "USD " + value.toLocaleString("es-CO", { maximumFractionDigits: 6 });
  async function decision(actionId: string, value: string) {
    await api(`/profiles/${agent.id}/actions/decision`, "POST", {
      ...mutation(agent.revision),
      action_id: actionId,
      decision: value,
    });
    await refresh();
  }
  return (
    <div className="agents-operating-console">
      <section
        className="agents-editor-section"
        aria-labelledby="agent-observation-heading"
      >
        <div className="panel-heading">
          <h4 id="agent-observation-heading">Ejecución y observabilidad</h4>
          <Button
            variant="quiet"
            disabled={busy}
            onClick={() => void act(refresh)}
          >
            Actualizar actividad
          </Button>
        </div>
        <div className="agents-card-channels">
          <Badge>
            {agent.state === "active"
              ? "Disponible"
              : agent.state === "archived"
                ? "Archivado"
                : "En pausa"}
          </Badge>
          <Badge>
            {agent.configuration.allow_reply
              ? "Permite respuestas"
              : "Sin permiso de respuesta"}
          </Badge>
        </div>
        {data && !data.installed && (
          <Notice>
            El registro de ejecuciones está pendiente de habilitación.
          </Notice>
        )}
        <dl className="agents-summary">
          <div>
            <dt>Ejecuciones · 7 días</dt>
            <dd>{metrics?.runs_7d ?? 0}</dd>
          </div>
          <div>
            <dt>Incidencias · 7 días</dt>
            <dd>{metrics?.errors_7d ?? 0}</dd>
          </div>
          <div>
            <dt>Respaldo · 7 días</dt>
            <dd>{metrics?.fallbacks_7d ?? 0}</dd>
          </div>
          <div>
            <dt>Latencia media</dt>
            <dd>
              {metrics?.latency_ms == null
                ? "Sin medición"
                : metrics.latency_ms + " ms"}
            </dd>
          </div>
          <div>
            <dt>Salud operativa</dt>
            <dd>
              {metrics?.health == null ? "No evaluada" : metrics.health + "%"}
            </dd>
          </div>
          <div>
            <dt>Tokens reportados · mes</dt>
            <dd>
              {metrics?.tokens_reported?.toLocaleString("es-CO") ??
                "Sin reporte"}
            </dd>
          </div>
          <div>
            <dt>
              {metrics?.unknown_cost_runs
                ? "Costo estimado parcial · mes"
                : "Costo estimado · mes"}
            </dt>
            <dd>{money(metrics?.usd_estimate)}</dd>
          </div>
          <div>
            <dt>Reserva conservadora · mes</dt>
            <dd>
              {(metrics?.tokens_reserved ?? 0).toLocaleString("es-CO")} tokens
            </dd>
          </div>
        </dl>
        <p>
          Salud operativa significa proporción de ejecuciones completadas, no
          exactitud académica. Costos estimados con las tarifas declaradas; no
          son una factura.{" "}
          {metrics?.unknown_cost_runs
            ? `${metrics.unknown_cost_runs} ejecuciones sin costo confirmado.`
            : ""}
        </p>
        {percent >= (agent.configuration.usage_alert_percent ?? 80) && (
          <Notice error={percent >= 100}>
            Alerta de presupuesto: {percent.toFixed(1)}% de la reserva
            configurada.
          </Notice>
        )}
      </section>
      <section
        className="agents-editor-section"
        aria-labelledby="agent-response-heading"
      >
        <h4 id="agent-response-heading">Probar respuesta</h4>
        <p>
          La consulta utiliza la versión guardada y el proveedor del agente.
          Probar respuesta autoriza una llamada y su consumo; no envía mensajes
          al aspirante.
        </p>
        {changed && (
          <Notice>Guarde la configuración antes de probar sus cambios.</Notice>
        )}
        <TextArea
          id="agent-inline-question"
          label="Mensaje para el agente"
          rows={3}
          maxLength={2000}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <div className="form-actions">
          <Button
            disabled={
              busy || changed || !question.trim() || agent.state === "archived"
            }
            onClick={() => void act(() => simulate(true))}
          >
            Probar respuesta
          </Button>
          <Button
            variant="secondary"
            disabled={
              busy || changed || !question.trim() || agent.state === "archived"
            }
            onClick={() => void act(() => simulate(false))}
          >
            Ver contexto
          </Button>
          <Button variant="quiet" disabled={busy || changed} onClick={diagnose}>
            Ejecutar diagnóstico opcional
          </Button>
        </div>
        {simulation && (
          <div aria-label="Respuesta del agente">
            <Badge>
              {simulation.network_called
                ? "Proveedor consultado"
                : "Contexto sin consumo"}
            </Badge>
            {simulation.text && (
              <p className="agents-response-text">{simulation.text}</p>
            )}
            {simulation.handoff && <p>Corresponde derivar a un asesor.</p>}
            <ul>
              {simulation.sources.map((source) => (
                <li key={source.id}>{source.title}</li>
              ))}
            </ul>
          </div>
        )}
      </section>
      <section
        className="agents-editor-section"
        aria-labelledby="agent-actions-heading"
      >
        <h4 id="agent-actions-heading">Acciones asistidas</h4>
        <p>
          Prepare una recomendación, resumen, reporte, borrador de campaña o
          tarea interna. Una acción sensible conserva su aprobación propia; el
          agente no necesita aprobación para existir.
        </p>
        <div className="agents-form-grid">
          <SelectField
            id="agent-action-kind"
            label="Tipo de acción"
            value={kind}
            options={[
              { value: "recommendation", label: "Recomendación del asesor" },
              { value: "summary", label: "Resumen" },
              { value: "report", label: "Reporte" },
              { value: "campaign_draft", label: "Borrador de campaña" },
              { value: "followup_task", label: "Tarea de seguimiento" },
              { value: "crm_note", label: "Nota de seguimiento CRM" },
            ]}
            onChange={(e) => setKind(e.target.value)}
          />
          <SelectField
            id="agent-action-impact"
            label="Impacto"
            value={impact}
            options={[
              { value: "low", label: "Bajo" },
              { value: "medium", label: "Medio" },
              { value: "high", label: "Alto" },
            ]}
            onChange={(e) => setImpact(e.target.value)}
          />
          <SelectField
            id="agent-action-risk"
            label="Riesgo"
            value={risk}
            options={[
              { value: "low", label: "Bajo" },
              { value: "medium", label: "Medio" },
              { value: "high", label: "Alto" },
            ]}
            onChange={(e) => setRisk(e.target.value)}
          />
          <Field
            id="agent-action-title"
            label="Título"
            maxLength={120}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <SelectField
            id="agent-action-conversation"
            label="Conversación del mismo ámbito"
            value={conversation}
            options={[
              { value: "", label: "Sin conversación · documento interno" },
              ...(data?.conversations ?? []).map((c) => ({
                value: c.id,
                label: c.label,
              })),
            ]}
            onChange={(e) => setConversation(e.target.value)}
          />
        </div>
        <TextArea
          id="agent-action-context"
          label="Descripción y contexto"
          maxLength={4000}
          rows={4}
          value={context}
          onChange={(e) => setContext(e.target.value)}
        />
        <Button
          disabled={
            busy ||
            changed ||
            !title.trim() ||
            !context.trim() ||
            agent.state === "archived"
          }
          onClick={() =>
            void act(async () => {
              await api(`/profiles/${agent.id}/actions`, "POST", {
                ...mutation(agent.revision),
                kind,
                impact,
                risk,
                title,
                context,
                conversation_id: conversation || null,
              });
              setTitle("");
              setContext("");
              await refresh();
            })
          }
        >
          Crear borrador seguro
        </Button>
        {!data?.actions.length && (
          <p>No hay borradores de acción para este agente.</p>
        )}
        {data?.actions.map((action) => (
          <article className="agents-event" key={action.action_id}>
            <strong>{action.title}</strong>
            <p className="agents-response-text">{action.context}</p>
            <Badge>
              {(
                {
                  draft: "Borrador",
                  approved: "Aprobado",
                  rejected: "Rechazado",
                  executed: "Registrado",
                } as Record<string, string>
              )[action.state] ?? action.state}
            </Badge>
            <p>
              Impacto {action.impact} · riesgo {action.risk} · versión{" "}
              {action.agent_version}
            </p>
            <div className="form-actions">
              <Button
                variant="secondary"
                disabled={
                  busy ||
                  changed ||
                  action.state !== "draft" ||
                  action.agent_version !== agent.version
                }
                onClick={() =>
                  void act(() => decision(action.action_id, "approve"))
                }
              >
                Aprobar acción
              </Button>
              <Button
                variant="quiet"
                disabled={
                  busy ||
                  changed ||
                  !["draft", "approved"].includes(action.state)
                }
                onClick={() =>
                  void act(() => decision(action.action_id, "reject"))
                }
              >
                Rechazar
              </Button>
              <Button
                disabled={
                  busy ||
                  changed ||
                  !["draft", "approved"].includes(action.state) ||
                  action.agent_version !== agent.version
                }
                onClick={() =>
                  void act(() => decision(action.action_id, "execute"))
                }
              >
                Registrar acción
              </Button>
            </div>
            {action.task_id && <a href="#/inbox">Ver tarea en Inbox</a>}
          </article>
        ))}
      </section>
      <div className="agents-audit-columns">
        <section
          className="agents-editor-section"
          aria-labelledby="agent-runs-heading"
        >
          <h4 id="agent-runs-heading">Ejecuciones de la pasarela IA</h4>
          {!data?.runs.length && <p>No hay ejecuciones registradas.</p>}
          {data?.runs.map((run) => (
            <article className="agents-event" key={run.request_id}>
              <strong>
                {run.provider} · {run.model}
              </strong>
              <p>
                Versión {run.version} · {run.variant} ·{" "}
                {run.state === "completed"
                  ? "Completada"
                  : "Consumo por confirmar"}
              </p>
              <p>
                {run.latency_ms == null
                  ? "Latencia sin medición"
                  : run.latency_ms + " ms"}{" "}
                ·{" "}
                {run.input_tokens == null
                  ? "Tokens sin reporte"
                  : `${run.input_tokens} entrada / ${run.output_tokens ?? "?"} salida`}{" "}
                · {money(run.cost_usd_estimate)}
              </p>
              {run.error && <p>{message(run.error)}</p>}
              <small>{run.created_at}</small>
            </article>
          ))}
        </section>
        <section
          className="agents-editor-section"
          aria-labelledby="agent-notes-heading"
        >
          <h4 id="agent-notes-heading">Actividad y notas</h4>
          <TextArea
            id="agent-note"
            label="Agregar nota interna del agente"
            maxLength={1000}
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <Button
            disabled={busy || !note.trim()}
            onClick={() =>
              void act(async () => {
                await api(`/profiles/${agent.id}/notes`, "POST", {
                  ...mutation(agent.revision),
                  note,
                });
                setNote("");
                await refresh();
              })
            }
          >
            Agregar nota
          </Button>
          {!data?.notes.length && <p>No hay notas registradas.</p>}
          {data?.notes.map((item, index) => (
            <article className="agents-event" key={item.at + index}>
              <p className="agents-response-text">{item.text}</p>
              <small>{item.at}</small>
            </article>
          ))}
        </section>
      </div>
    </div>
  );
}
