import { useEffect, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Notice } from "../shared/ui";
import "./sales.css";
import { useInstitution } from "./api";
import { OperationDialog } from "./ErrorFeedback";

type Fact = {
  field: string;
  value: string;
  source_message_id: string;
  sequence: number;
  origin?: string;
};
type Memory = {
  last_skill_policy?: {
    version: string;
    active_ids: string[];
    available_count: number;
  } | null;
  generation?: {
    id: string;
    integration: string;
    status: string;
    code?: string | null;
    can_retry: boolean;
  } | null;
  ad_referral?: {
    source_id: string;
    headline?: string;
    body?: string;
    source_url?: string;
    program_id?: number;
  };
  revision: number;
  context_boundary?: number;
  reset_target_sequence?: number;
  can_restore_context?: boolean;
  facts: Fact[];
  qualification: {
    score: number | null;
    temperature: string | null;
    reasons: string[];
  } | null;
  assessment_authority?: string;
  interest?: {
    status: string;
    candidates?: { name: string; schedule: string }[];
  };
  graph: {
    nodes: { id: string; label: string; kind: string }[];
    edges: {
      source: string;
      target: string;
      relation: string;
      certainty: string;
    }[];
  };
  recent_history: { id: string; direction: string; text: string }[];
  memory_limit: string;
};
const labels: Record<string, string> = {
  goal: "Objetivo",
  budget: "Presupuesto declarado",
  schedule: "Jornada preferida",
  start_time: "Cuándo quiere empezar",
  objection: "Objeción",
  next_step: "Próximo paso solicitado",
  objection_resolved: "Objeción resuelta",
};

export function ConversationSalesMemory({
  conversation,
  refresh,
  onChanged,
}: {
  conversation: string;
  refresh: number | string;
  onChanged?: () => void;
}) {
  return (
    <SalesMemory
      key={conversation}
      conversation={conversation}
      refresh={refresh}
      onChanged={onChanged}
    />
  );
}
function SalesMemory({
  conversation,
  refresh,
  onChanged,
}: {
  conversation: string;
  refresh: number | string;
  onChanged?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState<Memory | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [recover, setRecover] = useState(false);
  const [resetAction, setResetAction] = useState<"reset" | "restore" | null>(
    null,
  );
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const { call, session } = useInstitution();
  useEffect(() => {
    let live = true;
    if (open)
      void api<Memory>(`/conversations/${conversation}/sales-memory`)
        .then((result) => {
          if (live) {
            setValue(result);
            setError("");
          }
        })
        .catch((failure: Error) => {
          if (live) setError(failure.message);
        });
    return () => {
      live = false;
    };
  }, [conversation, refresh, retry, open]);
  const nodes =
    value?.graph.nodes
      .filter((node) => node.id !== "conversation")
      .slice(0, 10) ?? [];
  return (
    <details
      className="panel sales-memory"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>Memoria y contexto del agente</summary>
      <p>
        Datos declarados, respuestas y próximos pasos de este hilo. Continúan
        disponibles al cambiar de especialista.
      </p>
      {error && (
        <Notice error>
          {error}
          <Button variant="quiet" onClick={() => setRetry((v) => v + 1)}>
            Reintentar memoria
          </Button>
        </Notice>
      )}
      {!value && !error && <p>Cargando contexto…</p>}
      {feedback && <Notice>{feedback}</Notice>}
      {resetAction && value && (
        <OperationDialog
          guidance={{
            title:
              resetAction === "reset"
                ? "Empezar un contexto de IA nuevo"
                : "Restaurar el contexto anterior",
            detail:
              resetAction === "reset"
                ? "La IA comenzará desde el próximo mensaje sin usar los intercambios ni la memoria comercial anteriores. El historial, la ficha CRM, los recibos y el consumo de voz se conservan. Las respuestas anteriores que sigan pendientes perderán su autorización. Podrás restaurar el contexto anterior."
                : "La IA volverá a disponer de la memoria y los intercambios anteriores. El historial y los límites de voz se conservan. Se cancelará la autorización de respuestas pendientes del contexto actual.",
          }}
          dismiss={() => setResetAction(null)}
          dismissLabel="Cancelar"
          confirm={{
            label:
              resetAction === "reset"
                ? "Reiniciar contexto"
                : "Restaurar contexto",
            run: async () => {
              if (busy) return;
              setBusy(true);
              try {
                await call(
                  `conversation-memory/${conversation}/reset`,
                  "POST",
                  {
                    operation_id: crypto.randomUUID(),
                    revision: value.revision,
                    sequence: value.reset_target_sequence,
                    confirmed: true,
                    action: resetAction,
                  },
                );
                setFeedback(
                  resetAction === "reset"
                    ? "Contexto reiniciado. El próximo mensaje empezará una atención nueva; el historial se conserva."
                    : "Contexto anterior restaurado.",
                );
                setResetAction(null);
                setRetry((v) => v + 1);
                onChanged?.();
                setError("");
              } catch (failure) {
                setError(
                  failure instanceof Error
                    ? failure.message
                    : "No se pudo cambiar el contexto.",
                );
                setResetAction(null);
              } finally {
                setBusy(false);
              }
            },
          }}
        />
      )}
      {recover && value?.generation && (
        <OperationDialog
          guidance={{
            title: "Recuperar respuesta de IA",
            detail:
              "La respuesta anterior no quedó guardada para envío. Se comprobará que no exista otra respuesta, que el chat siga en IA y que este sea el último mensaje. Esta nueva generación puede consumir tokens.",
          }}
          dismiss={() => setRecover(false)}
          dismissLabel="Cancelar"
          confirm={{
            label: "Recuperar respuesta",
            run: async () => {
              if (!value.generation || busy) return;
              setBusy(true);
              try {
                await call(
                  `channels/${value.generation.integration}/recover-generation`,
                  "POST",
                  {
                    operation_id: crypto.randomUUID(),
                    generation_id: value.generation.id,
                    confirmed: true,
                    acknowledge_consumption: true,
                  },
                );
                setRecover(false);
                setRetry((v) => v + 1);
                setError("");
              } catch (failure) {
                setError(
                  failure instanceof Error
                    ? failure.message
                    : "No se pudo recuperar la respuesta.",
                );
                setRecover(false);
              } finally {
                setBusy(false);
              }
            },
          }}
        />
      )}
      {value && (
        <>
          {value.last_skill_policy && (
            <details>
              <summary>
                Skills del último turno ·{" "}
                {value.last_skill_policy.active_ids.length} aplicadas
              </summary>
              <p>
                {value.last_skill_policy.version} ·{" "}
                {value.last_skill_policy.available_count} disponibles por
                política central
              </p>
              <p>{value.last_skill_policy.active_ids.join(" · ")}</p>
            </details>
          )}
          {value.generation &&
            ["failed", "uncertain", "running"].includes(
              value.generation.status,
            ) && (
              <div role="status">
                <strong>Revisión de respuesta automática</strong>
                <p>
                  {value.generation.status === "running"
                    ? "La generación no ha confirmado su resultado."
                    : "La respuesta se detuvo antes de completar el recorrido."}
                </p>
                {value.generation.code && <code>{value.generation.code}</code>}
                {value.generation.can_retry &&
                  session.actions.includes("settings.channels.write") &&
                  session.actions.includes("inbox.write") && (
                    <Button disabled={busy} onClick={() => setRecover(true)}>
                      Revisar recuperación de respuesta
                    </Button>
                  )}
              </div>
            )}
          {value.ad_referral && (
            <details>
              <summary>Anuncio de origen</summary>
              <strong>
                {value.ad_referral.headline ||
                  `Anuncio ${value.ad_referral.source_id}`}
              </strong>
              <p>{value.ad_referral.body}</p>
              <p>
                {value.ad_referral.program_id
                  ? "Vinculado al programa por el equipo"
                  : "Programa del anuncio por vincular"}
              </p>
              {value.ad_referral.source_url && (
                <a
                  href={value.ad_referral.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Ver anuncio en Meta
                </a>
              )}
            </details>
          )}
          {value.interest?.candidates?.length ? (
            <p>
              <strong>Interés comercial:</strong>{" "}
              {value.interest.candidates
                .map((v) => v.name + (v.schedule ? " · " + v.schedule : ""))
                .join(" / ")}{" "}
              ·{" "}
              {value.interest.status === "needs_clarification"
                ? "Por aclarar"
                : "No acredita matrícula"}
            </p>
          ) : null}
          {nodes.length > 0 && (
            <svg
              className="sales-memory-graph"
              viewBox="0 0 320 280"
              role="img"
              aria-label="Grafo de hechos y atención de esta conversación"
            >
              <title>
                La conversación conecta hechos declarados y los intercambios
                atendidos
              </title>
              {nodes.map((node, i) => {
                const angle = (i * Math.PI * 2) / nodes.length;
                const x = 160 + Math.cos(angle) * 108;
                const y = 140 + Math.sin(angle) * 100;
                return (
                  <g key={node.id}>
                    <line x1="160" y1="140" x2={x} y2={y} />
                    <circle cx={x} cy={y} r="18" />
                    <text x={x} y={y + 32} textAnchor="middle">
                      {node.label.split(" · ")[0].slice(0, 20)}
                    </text>
                    <title>{node.label}</title>
                  </g>
                );
              })}
              <circle cx="160" cy="140" r="30" />
              <text x="160" y="144" textAnchor="middle">
                Este hilo
              </text>
            </svg>
          )}
          {!value.facts.length && (
            <p>
              Aún no hay datos comerciales extraídos. El historial del chat se
              conserva; el agente no inventará recuerdos.
            </p>
          )}
          <dl>
            {value.facts.map((fact) => (
              <div key={fact.field}>
                <dt>{labels[fact.field] ?? fact.field}</dt>
                <dd>{fact.value}</dd>
                <small>
                  {fact.origin === "automatic_audio_transcription"
                    ? "Transcripción automática · confirma datos importantes"
                    : "Cita del cliente"}{" "}
                  · categoría interpretada por IA · mensaje {fact.sequence}
                </small>
              </div>
            ))}
          </dl>
          {value.qualification && (
            <details>
              <summary>Por qué tiene esta calificación</summary>
              <p>
                {value.qualification.score === null
                  ? "Sin señales suficientes"
                  : `${value.qualification.score}/100 · rúbrica de interés comercial`}
                . No es una probabilidad de matrícula.
              </p>
              <ul>
                {value.qualification.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
              {value.assessment_authority === "manual_preserved" && (
                <p>
                  La calificación manual se conserva por encima de la propuesta
                  automática.
                </p>
              )}
            </details>
          )}
          <details>
            <summary>Qué se ha hablado recientemente</summary>
            <ol>
              {value.recent_history.map((item) => (
                <li key={item.id}>
                  <strong>
                    {item.direction === "incoming" ? "Cliente" : "Equipo / IA"}:
                  </strong>{" "}
                  {item.text}
                </li>
              ))}
            </ol>
          </details>
          <small>{value.memory_limit}</small>
          {session.actions.includes("inbox.write") &&
            value.reset_target_sequence !== undefined && (
              <div className="form-actions">
                <Button
                  variant="quiet"
                  disabled={busy}
                  onClick={() => setResetAction("reset")}
                >
                  Empezar desde cero con IA
                </Button>
                {value.can_restore_context && (
                  <Button
                    variant="quiet"
                    disabled={busy}
                    onClick={() => setResetAction("restore")}
                  >
                    Restaurar contexto anterior
                  </Button>
                )}
              </div>
            )}
        </>
      )}
    </details>
  );
}
