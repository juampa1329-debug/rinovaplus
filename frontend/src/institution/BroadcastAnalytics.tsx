import { useState } from "react";
import { Field, Notice, SelectField } from "../shared/ui";

export type CampaignAnalytics = {
  totals: Record<"total" | "delivered" | "read" | "replied" | "failed", number>;
  dimensions: Record<
    string,
    {
      label: string;
      total: number;
      delivered: number;
      read: number;
      replied: number;
      failed: number;
    }[]
  >;
};
export function BroadcastAnalyticsSkeleton() {
  return (
    <div className="broadcast-chart-skeleton" role="status" aria-busy="true">
      <p>Cargando gráficos de la campaña…</p>
      <div className="broadcast-skeleton-metrics" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((v) => (
          <span key={v} />
        ))}
      </div>
      <div className="broadcast-skeleton-bars" aria-hidden="true">
        {[80, 55, 68, 35].map((v, i) => (
          <span key={i} style={{ width: `${v}%` }} />
        ))}
      </div>
    </div>
  );
}
const dimensions = [
  ["gender", "Género"],
  ["age_band", "Edad"],
  ["city", "Ciudad"],
  ["region", "Departamento o región"],
  ["country", "País"],
  ["program", "Programa"],
  ["schedule", "Jornada"],
  ["contact_type", "Tipo de contacto"],
  ["stage", "Estado CRM"],
  ["last_incoming", "Último mensaje recibido al preparar"],
];
const metrics = [
  ["total", "Destinatarios"],
  ["delivered", "Entregados"],
  ["read", "Leídos"],
  ["replied", "Respuestas atribuidas"],
  ["failed", "Fallidos"],
] as const;
export function BroadcastAnalytics({ data }: { data: CampaignAnalytics }) {
  const [dimension, setDimension] = useState("gender"),
    [metric, setMetric] = useState<keyof CampaignAnalytics["totals"]>("read"),
    [search, setSearch] = useState("");
  const buckets = (data.dimensions[dimension] || []).filter((v) =>
    v.label.toLocaleLowerCase("es").includes(search.toLocaleLowerCase("es")),
  );
  const max = Math.max(1, ...buckets.map((v) => v[metric]));
  const unknown =
    (data.dimensions[dimension] || []).find((v) => v.label === "Sin dato")
      ?.total || 0;
  return (
    <section
      className="broadcast-analytics"
      aria-label="Gráficos de la campaña"
    >
      <div className="broadcast-analytics-heading">
        <div>
          <h3>Alcance y respuestas</h3>
          <p>
            {data.totals.total} destinatarios preparados en la selección del
            informe.
          </p>
        </div>
        <span className="badge">Recibos reales de WhatsApp</span>
      </div>
      <dl className="broadcast-metrics">
        {metrics.map(([key, label]) => (
          <div key={key}>
            <dt>{label}</dt>
            <dd>
              {data.totals[key]}
              {key !== "total" && (
                <small>
                  {data.totals.total
                    ? `${((data.totals[key] * 100) / data.totals.total).toLocaleString("es-CO", { maximumFractionDigits: 1 })}%`
                    : "Sin envíos"}
                </small>
              )}
            </dd>
          </div>
        ))}
      </dl>
      <div className="broadcast-filter-grid">
        <SelectField
          id="analytics-dimension"
          label="Desglosar por"
          value={dimension}
          options={dimensions.map(([value, label]) => ({ value, label }))}
          onChange={(e) => {
            setDimension(e.target.value);
            setSearch("");
          }}
        />
        <SelectField
          id="analytics-metric"
          label="Comparar"
          value={metric}
          options={metrics.map(([value, label]) => ({ value, label }))}
          onChange={(e) =>
            setMetric(e.target.value as keyof CampaignAnalytics["totals"])
          }
        />
        <Field
          id="analytics-search"
          label="Buscar en el gráfico"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {!data.totals.total && (
        <Notice>
          Prepara destinatarios para empezar a medir. Los gráficos no generan
          envíos ni datos de ejemplo.
        </Notice>
      )}
      <figure className="broadcast-bars">
        <figcaption>
          {dimensions.find(([key]) => key === dimension)?.[1]} ·{" "}
          {metrics.find(([key]) => key === metric)?.[1]}
        </figcaption>
        <div className="broadcast-bar-scroll">
          {buckets.map((v) => (
            <div
              className="broadcast-bar-row"
              key={`${dimension}-${metric}-${v.label}-${v[metric]}`}
            >
              <span>{v.label}</span>
              <span
                className={`broadcast-bar-track metric-${metric}`}
                aria-hidden="true"
              >
                <span style={{ width: `${(v[metric] * 100) / max}%` }} />
              </span>
              <strong>
                {v[metric]} <small>de {v.total}</small>
              </strong>
            </div>
          ))}
          {!buckets.length && data.totals.total > 0 && (
            <p>No hay grupos que coincidan con la búsqueda.</p>
          )}
        </div>
      </figure>
      <p className="broadcast-help">
        {unknown} destinatarios sin dato de{" "}
        {dimensions
          .find(([key]) => key === dimension)?.[1]
          .toLocaleLowerCase("es")}
        . Los perfiles reflejan la ficha CRM al preparar la campaña; las
        campañas anteriores sin esa captura aparecen como Sin dato. No se
        infieren género, edad ni ubicación.
      </p>
      <details>
        <summary>Ver tabla del desglose</summary>
        <div className="broadcast-table">
          <table>
            <caption>
              Resultados por{" "}
              {dimensions
                .find(([key]) => key === dimension)?.[1]
                .toLocaleLowerCase("es")}
            </caption>
            <thead>
              <tr>
                <th>Grupo</th>
                {metrics.map(([key, label]) => (
                  <th key={key}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {buckets.map((v) => (
                <tr key={v.label}>
                  <th scope="row">{v.label}</th>
                  {metrics.map(([key]) => (
                    <td key={key}>{v[key]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="broadcast-help">
        Leído significa que WhatsApp envió un recibo de lectura. No existe una
        métrica independiente de «abierto», ni se puede detectar una lectura si
        el proveedor no la informa. Respuestas atribuidas requiere que la
        persona responda citando el mensaje de esta campaña.
      </p>
    </section>
  );
}
