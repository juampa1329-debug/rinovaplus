import { useEffect, useLayoutEffect, useRef } from "react";
import type { ReactNode } from "react";
import type { Client, Thread } from "../shared/demo";
import type { OverviewData } from "../shared/overview";
import {
  animateChart,
  observeChartMotion,
  stopChartMotion,
} from "../shared/chartMotion";
import { workflowOf } from "../shared/workflow";
import { Badge, Button, EmptyState } from "../shared/ui";

export function OverviewMetrics({ data }: { data: OverviewData }) {
  return (
    <section
      className="overview-metrics grid grid-cols-2 lg:grid-cols-4 gap-4"
      aria-label="Resumen de datos confirmados"
    >
      {[
        ["Contactos", data.contacts, "Fichas activas"],
        ["Sin leer", data.unread, "Mensajes pendientes"],
        ["Conversaciones", data.conversations, "Hilos activos"],
        ["Conversaciones abiertas", data.open, "Seguimiento en curso"],
      ].map(([label, value, hint]) => (
        <div key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
          <small>{hint}</small>
        </div>
      ))}
    </section>
  );
}

function ChartMark({
  active,
  value,
  signature,
  className,
  children,
}: {
  active: boolean;
  value: number;
  signature: string;
  className: string;
  children?: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const entered = useRef(false);
  const donut = Boolean(children);
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    const current = getComputedStyle(node);
    const previousClip = current.clipPath;
    const previousOpacity = current.opacity;
    stopChartMotion(node);
    const clip = donut
      ? "inset(0 0 0 0)"
      : `inset(0 ${100 - value * 100}% 0 0)`;
    node.style.clipPath = clip;
    node.style.opacity = value ? "1" : "0";
    if (!active) {
      entered.current = false;
      return;
    }
    const entering = !entered.current;
    entered.current = true;
    if (!value && entering) return;
    animateChart(
      node,
      [
        {
          clipPath: entering
            ? donut
              ? "inset(0 0 100% 0)"
              : "inset(0 100% 0 0)"
            : previousClip,
          opacity: entering ? 0 : previousOpacity,
        },
        { clipPath: value ? clip : previousClip, opacity: value ? 1 : 0 },
      ],
      entering ? "enter" : value ? "update" : "exit",
    );
  }, [active, value, signature, donut]);
  useEffect(() => {
    const node = ref.current;
    return () => {
      if (node) stopChartMotion(node);
      entered.current = false;
    };
  }, []);
  return (
    <div ref={ref} className={className} aria-hidden="true">
      {children}
    </div>
  );
}

// A single React-owned chart surface remains for the short, inert exit only.
export function OverviewCharts({
  active,
  data,
}: {
  active: boolean;
  data: OverviewData;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const wasActive = useRef(false);
  const activeRef = useRef(active);
  useLayoutEffect(() => {
    activeRef.current = active;
    const node = ref.current;
    if (!node) return;
    stopChartMotion(node);
    if (active) {
      node.hidden = false;
      node.style.cssText = "";
    } else if (wasActive.current) {
      const box = node.getBoundingClientRect();
      node.style.cssText = `position:fixed;left:${box.left}px;top:${box.top}px;width:${box.width}px;pointer-events:none;z-index:5`;
      animateChart(node, [{ opacity: 1 }, { opacity: 0 }], "exit", () => {
        node.hidden = true;
        node.style.cssText = "";
      });
    } else node.hidden = true;
    wasActive.current = active;
  }, [active]);
  useEffect(
    () =>
      observeChartMotion(() => {
        if (!activeRef.current && ref.current) {
          ref.current.hidden = true;
          ref.current.style.cssText = "";
        }
      }),
    [],
  );
  const stateSignature = data.states
    .map((state) => `${state.key}:${state.count}`)
    .join("|");
  return (
    <div
      ref={ref}
      className="overview-charts"
      aria-hidden={!active || undefined}
      inert={!active}
    >
      <section className="panel" aria-labelledby="stage-chart-title">
        <div className="panel-heading">
          <div>
            <h2 id="stage-chart-title">Contactos por etapa</h2>
            <p>Distribución de registros confirmados</p>
          </div>
          <Badge>{data.contacts} contactos</Badge>
        </div>
        <dl className="stage-chart">
          {data.stages.map((stage, index) => (
            <div className="stage-row" key={stage.key}>
              <dt>{stage.label}</dt>
              <dd
                className="bar-track"
                style={{ color: `var(--chart-${(index % 4) + 1})` }}
              >
                <ChartMark
                  active={active}
                  value={data.contacts ? stage.count / data.contacts : 0}
                  signature={`${stage.key}:${stage.count}:${data.contacts}`}
                  className="bar-value"
                />
              </dd>
              <dd className="stage-count">{stage.count}</dd>
            </div>
          ))}
        </dl>
        {!data.contacts && (
          <p className="chart-caption">Aún no hay contactos para mostrar.</p>
        )}
        <p className="chart-caption">
          Cantidad por etapa sobre {data.contacts} fichas. No representa
          conversión.
        </p>
      </section>
      <section className="panel" aria-labelledby="state-chart-title">
        <div className="panel-heading">
          <div>
            <h2 id="state-chart-title">Estado de las conversaciones</h2>
            <p>Seguimiento humano</p>
          </div>
        </div>
        <div className="donut-layout">
          <div className="donut">
            <svg
              viewBox="0 0 100 100"
              className="donut-track"
              aria-hidden="true"
            >
              <circle cx="50" cy="50" r="40" />
            </svg>
            <ChartMark
              active={active}
              value={data.conversations ? 1 : 0}
              signature={stateSignature}
              className="donut-marks"
            >
              <svg viewBox="0 0 100 100">
                {data.states.map((state, index) => {
                  const share = data.conversations
                    ? (state.count / data.conversations) * 100
                    : 0;
                  const start = data.conversations
                    ? (data.states
                        .slice(0, index)
                        .reduce((sum, item) => sum + item.count, 0) /
                        data.conversations) *
                      100
                    : 0;
                  return (
                    <circle
                      key={state.key}
                      cx="50"
                      cy="50"
                      r="40"
                      pathLength="100"
                      stroke={`var(--chart-${index === 1 ? 4 : index + 1})`}
                      strokeDasharray={`${share} ${100 - share}`}
                      strokeDashoffset={-start}
                    />
                  );
                })}
              </svg>
            </ChartMark>
            <div className="donut-label">
              <strong>{data.conversations}</strong>
              <span>conversaciones</span>
            </div>
          </div>
          <dl className="state-legend">
            {data.states.map((state, index) => (
              <div key={state.key}>
                <dt>
                  <span
                    className="chart-dot"
                    style={{
                      background: `var(--chart-${index === 1 ? 4 : index + 1})`,
                    }}
                    aria-hidden="true"
                  />
                  {state.label}
                </dt>
                <dd>{state.count}</dd>
              </div>
            ))}
          </dl>
        </div>
        <p className="chart-caption">
          {data.conversations
            ? "Todos los hilos confirmados; independiente de los filtros de Inbox."
            : "Sin conversaciones. No hay proporciones disponibles."}
        </p>
      </section>
    </div>
  );
}

export function OverviewQueue({
  clients,
  threads,
  onOpen,
  onNavigate,
}: {
  clients: Client[];
  threads: Thread[];
  onOpen: (id: string) => void;
  onNavigate: (path: string) => void;
}) {
  return (
    <section className="panel overview-queue-panel">
      <div className="panel-heading">
        <div>
          <h2>Atención pendiente</h2>
          <p>Revise el contexto antes de responder.</p>
        </div>
        <Button variant="quiet" onClick={() => onNavigate("inbox")}>
          Ver Inbox
        </Button>
      </div>
      {!threads.length && (
        <EmptyState title="Sin conversaciones">
          Aún no hay mensajes para mostrar.
        </EmptyState>
      )}
      <ul className="overview-queue">
        {threads.map((thread) => {
          const client = clients.find((item) => item.id === thread.clientId);
          return (
            <li key={thread.clientId} className="queue-row">
              <div className="queue-person">
                <span className="avatar" aria-hidden="true">
                  {client?.name.trim().charAt(0).toLocaleUpperCase("es") || "D"}
                </span>
                <div>
                  <strong>{client?.name || "Contacto no disponible"}</strong>
                  <p>{thread.messages.at(-1)?.body || "Sin mensajes"}</p>
                </div>
              </div>
              <span className="queue-channel">
                {thread.channel.toLowerCase() === "local"
                  ? "CRM"
                  : thread.channel}
              </span>
              <Badge>
                {workflowOf(thread).state}
                {thread.unread ? " · Sin leer" : ""}
              </Badge>
              <Button variant="quiet" onClick={() => onOpen(thread.clientId)}>
                Abrir hilo
              </Button>
            </li>
          );
        })}
      </ul>
      <details className="scope-note">
        <summary>Recorrido de revisión</summary>
        <p>
          Cree o edite una ficha y gestione sus mensajes desde el mismo lugar.
        </p>
        <Button variant="secondary" onClick={() => onNavigate("clients")}>
          Comenzar por Clientes
        </Button>
      </details>
    </section>
  );
}
