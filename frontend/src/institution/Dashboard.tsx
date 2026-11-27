import { useEffect, useState } from "react";
import { Button, Notice, SelectField } from "../shared/ui";
import { Icon } from "../shared/Icon";
import { send } from "./api";
import "./operations-design.css";

export type DashboardData = {
  generated_at: string;
  start: string;
  end: string;
  timezone: string;
  days: number;
  inbox: null | {
    conversations: number;
    attended: number;
    incoming: number;
    sent: number;
    ai_sent: number;
    daily: { day: string; incoming: number; sent: number }[];
    channels: { channel: string; count: number }[];
    modes: { mode: string; count: number }[];
  };
  followups: null | { pending: number; overdue: number; completed: number };
  comments: null | { received: number };
};
const number = (value: number | undefined) =>
  value === undefined ? "—" : new Intl.NumberFormat("es-CO").format(value);
const channelNames: Record<string, string> = {
  whatsapp: "WhatsApp",
  messenger: "Messenger",
  instagram: "Instagram",
  facebook: "Facebook",
  local: "CRM local",
  tiktok: "TikTok",
};

export function dailySeries(data: DashboardData) {
  const date = new Date(data.start);
  return Array.from({ length: data.days }, (_, index) => {
    const day = new Date(date.getTime() + index * 86400000).toLocaleDateString(
      "en-CA",
      { timeZone: "America/Bogota" },
    );
    return {
      day,
      incoming: 0,
      sent: 0,
      ...data.inbox?.daily.find((row) => row.day === day),
    };
  });
}

export function Dashboard({ name }: { name: string }) {
  const [days, setDays] = useState("7");
  const [refresh, setRefresh] = useState(0);
  const [result, setResult] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [barDetail, setBarDetail] = useState("");
  useEffect(() => {
    let active = true;
    void send<DashboardData>(`dashboard?days=${days}`).then(
      (value) => {
        if (active) {
          setResult(value);
          setError("");
          setLoading(false);
        }
      },
      () => {
        if (active) {
          setError(
            "No pudimos actualizar el resumen. Reintenta para consultar los indicadores actuales.",
          );
          setLoading(false);
        }
      },
    );
    return () => {
      active = false;
    };
  }, [days, refresh]);
  const data = result?.days === Number(days) ? result : null;
  const points = data ? dailySeries(data) : [];
  const peak = Math.max(
    100,
    Math.ceil(
      Math.max(0, ...points.flatMap((row) => [row.incoming, row.sent])) / 100,
    ) * 100,
  );
  const chartHeight = Math.max(230, (peak / 100) * 24 + 70);
  const chartBottom = chartHeight - 40;
  const chartPlot = chartBottom - 22;
  const maxChannel = Math.max(
    1,
    ...(data?.inbox?.channels.map((row) => row.count) ?? []),
  );
  const metrics = [
    {
      label: "Conversaciones recibidas",
      value: data?.inbox?.conversations,
      hint: "Chats con al menos un mensaje entrante",
      icon: "inbox",
      href: "#/inbox",
    },
    {
      label: "Conversaciones atendidas",
      value: data?.inbox?.attended,
      hint: "Con una respuesta posterior confirmada por Meta",
      icon: "doubleCheck",
      href: "#/inbox",
    },
    {
      label: "Respuestas de IA",
      value: data?.inbox?.ai_sent,
      hint: "Envíos automáticos confirmados por el canal",
      icon: "assistant",
      href: "#/inbox",
    },
    {
      label: "Seguimientos completados",
      value: data?.followups?.completed,
      hint: "Tareas hoy completadas y actualizadas en el período",
      icon: "review",
      href: "#/clients",
    },
  ];
  return (
    <div className="operations-dashboard" aria-busy={loading}>
      <header className="operations-hero">
        <div>
          <span className="operations-eyebrow">
            TU OPERACIÓN, EN UN VISTAZO
          </span>
          <h2>Hola, {name.split(" ")[0]}.</h2>
          <p>Cada conversación es una oportunidad de conectar.</p>
        </div>
        <div className="operations-toolbar">
          <SelectField
            id="dashboard-range"
            label="Período · Bogotá"
            value={days}
            options={[
              { value: "7", label: "Últimos 7 días" },
              { value: "30", label: "Últimos 30 días" },
            ]}
            onChange={(e) => {
              setLoading(true);
              setDays(e.target.value);
            }}
          />
          <Button
            variant="secondary"
            disabled={loading}
            onClick={() => {
              setLoading(true);
              setRefresh((v) => v + 1);
            }}
          >
            Actualizar resumen
          </Button>
        </div>
      </header>
      {error && <Notice error>{error}</Notice>}
      {data && (
        <p className="operations-freshness">
          Datos del CRM ·{" "}
          {new Date(data.start).toLocaleDateString("es-CO", {
            timeZone: "America/Bogota",
          })}{" "}
          al{" "}
          {new Date(data.end).toLocaleDateString("es-CO", {
            timeZone: "America/Bogota",
          })}{" "}
          · Actualizado{" "}
          {new Date(data.generated_at).toLocaleTimeString("es-CO", {
            timeZone: "America/Bogota",
          })}
        </p>
      )}
      <div className="operations-kpis">
        {metrics.map((metric) => (
          <a key={metric.label} className="operations-kpi" href={metric.href}>
            <span className="operations-kpi-label">
              <Icon name={metric.icon} />
              {metric.label}
            </span>
            <strong>{number(metric.value)}</strong>
            <small>{metric.hint}</small>
          </a>
        ))}
      </div>
      <div className="operations-charts">
        <section className="panel operations-volume">
          <div className="operations-section-heading">
            <div>
              <span className="operations-eyebrow">ACTIVIDAD</span>
              <h2>El pulso de tus conversaciones</h2>
            </div>
            <span className="operations-live">Historial real</span>
          </div>
          <div className="operations-legend">
            <span>● Recibidos</span>
            <span>● Enviados confirmados</span>
          </div>
          {!data?.inbox ? (
            <p>
              {loading
                ? "Consultando actividad…"
                : "La actividad del Inbox no está disponible para tus permisos o módulos habilitados."}
            </p>
          ) : (
            <>
              <div className="operations-chart-detail" aria-live="polite">
                {barDetail ? (
                  <span role="tooltip">{barDetail}</span>
                ) : (
                  "Pasa el cursor o selecciona una barra para ver su detalle."
                )}
              </div>
              <div className="operations-chart-scroll">
                <svg
                  className="operations-volume-chart"
                  viewBox={`0 0 720 ${chartHeight}`}
                  style={{ height: chartHeight }}
                  role="group"
                  aria-label="Mensajes recibidos y enviados por día. Valores disponibles en Ver datos de la gráfica."
                >
                  {Array.from(
                    { length: peak / 100 + 1 },
                    (_, i) => i * 100,
                  ).map((tick) => (
                    <g key={tick}>
                      <line
                        x1="38"
                        x2="705"
                        y1={chartBottom - (tick / peak) * chartPlot}
                        y2={chartBottom - (tick / peak) * chartPlot}
                        className="operations-gridline"
                      />
                      <text
                        x="36"
                        y={chartBottom + 4 - (tick / peak) * chartPlot}
                        textAnchor="end"
                      >
                        {number(tick)}
                      </text>
                    </g>
                  ))}
                  {points.map((point, index) => {
                    const x = 44 + (index * 655) / points.length;
                    const width = Math.min(25, 260 / points.length);
                    return (
                      <g key={point.day}>
                        <title>
                          {point.day}: {point.incoming} recibidos, {point.sent}{" "}
                          enviados
                        </title>
                        <rect
                          className="operations-bar received"
                          role="img"
                          tabIndex={0}
                          aria-label={`${point.day}: ${number(point.incoming)} mensajes recibidos`}
                          onPointerEnter={() =>
                            setBarDetail(
                              `${point.day} · Recibidos: ${number(point.incoming)}`,
                            )
                          }
                          onFocus={() =>
                            setBarDetail(
                              `${point.day} · Recibidos: ${number(point.incoming)}`,
                            )
                          }
                          onPointerLeave={() => setBarDetail("")}
                          onBlur={() => setBarDetail("")}
                          onKeyDown={(event) => {
                            if (event.key === "Escape") setBarDetail("");
                          }}
                          x={x}
                          y={chartBottom - (point.incoming / peak) * chartPlot}
                          width={width}
                          height={Math.max(
                            1,
                            (point.incoming / peak) * chartPlot,
                          )}
                          rx="3"
                        />
                        <rect
                          className="operations-bar sent"
                          role="img"
                          tabIndex={0}
                          aria-label={`${point.day}: ${number(point.sent)} mensajes enviados confirmados`}
                          onPointerEnter={() =>
                            setBarDetail(
                              `${point.day} · Enviados confirmados: ${number(point.sent)}`,
                            )
                          }
                          onFocus={() =>
                            setBarDetail(
                              `${point.day} · Enviados confirmados: ${number(point.sent)}`,
                            )
                          }
                          onPointerLeave={() => setBarDetail("")}
                          onBlur={() => setBarDetail("")}
                          onKeyDown={(event) => {
                            if (event.key === "Escape") setBarDetail("");
                          }}
                          x={x + width + 2}
                          y={chartBottom - (point.sent / peak) * chartPlot}
                          width={width}
                          height={Math.max(1, (point.sent / peak) * chartPlot)}
                          rx="3"
                        />
                        {(points.length < 10 || index % 5 === 0) && (
                          <text
                            x={x + width}
                            y={chartBottom + 24}
                            textAnchor="middle"
                          >
                            {point.day.slice(8)}/{point.day.slice(5, 7)}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </svg>
              </div>
              {!data.inbox.incoming && !data.inbox.sent && (
                <p>Sin mensajes registrados en este período.</p>
              )}
              <details>
                <summary>Ver datos de la gráfica</summary>
                <div className="operations-table">
                  <table>
                    <caption>
                      Mensajes por fecha de creación, hora de Bogotá
                    </caption>
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Recibidos</th>
                        <th>Enviados confirmados</th>
                      </tr>
                    </thead>
                    <tbody>
                      {points.map((row) => (
                        <tr key={row.day}>
                          <th scope="row">{row.day}</th>
                          <td>{row.incoming}</td>
                          <td>{row.sent}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </>
          )}
        </section>
        <section className="panel operations-channel-chart">
          <span className="operations-eyebrow">ORIGEN</span>
          <h2>¿Dónde conectamos?</h2>
          <p>Mensajes entrantes por canal en el período.</p>
          {data?.inbox?.channels.map((row) => (
            <div className="operations-channel" key={row.channel}>
              <div>
                <span>
                  <Icon
                    name={`channel${row.channel.charAt(0).toUpperCase() + row.channel.slice(1)}`}
                  />
                  {channelNames[row.channel] ?? row.channel}
                </span>
                <strong>{number(row.count)}</strong>
              </div>
              <div className="operations-track">
                <span
                  className={`operations-channel-fill ${row.channel}`}
                  style={{ width: `${(row.count / maxChannel) * 100}%` }}
                />
              </div>
            </div>
          ))}
          {data?.inbox?.channels.length === 0 && (
            <p>Todavía no hay actividad en este período.</p>
          )}
        </section>
      </div>
      <div className="operations-bottom">
        <section className="panel">
          <span className="operations-eyebrow">LO QUE SIGUE</span>
          <h2>Tu agenda de seguimiento</h2>
          <div className="operations-agenda">
            <a href="#/clients">
              <strong>{number(data?.followups?.pending)}</strong>
              <span>Pendientes ahora</span>
            </a>
            <a href="#/clients">
              <strong className="operations-warning">
                {number(data?.followups?.overdue)}
              </strong>
              <span>Con fecha vencida</span>
            </a>
            <a href="#/comments">
              <strong>{number(data?.comments?.received)}</strong>
              <span>Comentarios recibidos en el período</span>
            </a>
          </div>
        </section>
        <section className="panel">
          <span className="operations-eyebrow">EQUIPO HÍBRIDO</span>
          <h2>Atención, a tu manera</h2>
          <p>
            Modo actual de todos los chats del CRM; no es una métrica de
            respuestas.
          </p>
          <div className="operations-agenda">
            {data?.inbox?.modes.map((row) => (
              <a href="#/inbox" key={row.mode}>
                <strong>{number(row.count)}</strong>
                <span>
                  {row.mode === "ai"
                    ? "En IA"
                    : row.mode === "human"
                      ? "En Humano"
                      : row.mode}
                </span>
              </a>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
