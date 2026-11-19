import { useEffect, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Notice } from "../shared/ui";
import "./sales.css";

type Fact = {
  field: string;
  value: string;
  source_message_id: string;
  sequence: number;
};
type Memory = {
  ad_referral?: {
    source_id: string;
    headline?: string;
    body?: string;
    source_url?: string;
    program_id?: number;
  };
  revision: number;
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
}: {
  conversation: string;
  refresh: number;
}) {
  return (
    <SalesMemory
      key={conversation}
      conversation={conversation}
      refresh={refresh}
    />
  );
}
function SalesMemory({
  conversation,
  refresh,
}: {
  conversation: string;
  refresh: number;
}) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState<Memory | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
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
      {value && (
        <>
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
                  Cita del cliente · categoría interpretada por IA · mensaje{" "}
                  {fact.sequence}
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
        </>
      )}
    </details>
  );
}
