import { useEffect, useRef, useState } from "react";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { useInstitution, useTask, useIntent } from "./api";
import { useAdsResource } from "./adsResource";
import { ResourceState } from "./Settings";
import { OperationDialog } from "./ErrorFeedback";
import { allowNavigation, useDraftGuard } from "./drafts";
import { formatMetric as fmt, objectMetrics, safeAdUrl } from "./metaAdsData";
import type { AdObject, Snapshot } from "./metaAdsData";
import "./metaAds.css";

type Account = {
  id: string;
  name: string;
  provider: string;
  revision: number;
  status: string;
  external_account_id: string;
};
type Options = {
  accounts: Account[];
  integrations: { id: string; name: string; provider: string }[];
};
type Remote = { id: string; name: string; currency: string; timezone: string };
type Entity = "campaigns" | "adsets" | "ads";
type Draft = {
  id?: string;
  revision: number;
  entity: "campaign" | "adset" | "ad";
  mode: "create" | "edit";
  target_id: string;
  parent_id: string;
  name: string;
  objective: string;
  daily_budget_cents: number;
  body: string;
  headline: string;
  destination_url: string;
  image_url: string;
  countries: string[];
  review_valid?: boolean;
  issues?: string[];
};
const blank = (): Draft => ({
  revision: 0,
  entity: "campaign",
  mode: "create",
  target_id: "",
  parent_id: "",
  name: "",
  objective: "OUTCOME_LEADS",
  daily_budget_cents: 0,
  body: "",
  headline: "",
  destination_url: "",
  image_url: "",
  countries: ["CO"],
});
const labels = { campaigns: "Campañas", adsets: "Conjuntos", ads: "Anuncios" };
function initialPeriod() {
  const end = new Date(),
    start = new Date();
  start.setDate(start.getDate() - 29);
  const day = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  return { start: day(start), end: day(end) };
}

export function MetaAdsManager() {
  const options = useAdsResource<Options>("ads/options");
  const [chosen, setChosen] = useState("");
  if (!options.value) return <ResourceState error={options.error} />;
  const accounts = options.value.accounts.filter((v) => v.provider === "meta");
  const account = accounts.find((v) => v.id === chosen) ?? accounts[0];
  return (
    <section className="meta-ads" aria-label="Administrador de anuncios Meta">
      <header className="meta-heading">
        <div>
          <span className="meta-eyebrow">PUBLICIDAD / META</span>
          <h2>Tu inversión, con contexto.</h2>
          <p>Campañas, anuncios y resultados de tus cuentas autorizadas.</p>
        </div>
        <span className="badge">Consulta real · borradores locales</span>
      </header>
      <details className="panel meta-connect" open={!accounts.length}>
        <summary>Conexión y cuentas publicitarias</summary>
        <MetaConnection
          options={options.value}
          connected={async () => {
            await options.reload();
          }}
        />
      </details>
      {!!accounts.length && (
        <SelectField
          id="meta-account"
          label="Cuenta publicitaria"
          value={account?.id ?? ""}
          options={accounts.map((v) => ({
            value: v.id,
            label: `${v.name} · ${v.external_account_id}`,
          }))}
          onChange={(e) => {
            if (allowNavigation()) setChosen(e.target.value);
          }}
        />
      )}
      {account ? (
        <AccountDashboard key={account.id} account={account} />
      ) : (
        <div className="panel meta-empty">
          <span className="meta-empty-mark" aria-hidden="true">
            ↗
          </span>
          <h3>Conecta tu primera cuenta</h3>
          <p>
            Autoriza la consulta de publicidad y elige una cuenta de CBN. Aquí
            aparecerán sus campañas, anuncios y resultados reales.
          </p>
          <small>
            Sin una consulta válida, no se muestran cifras ni gráficas de
            ejemplo.
          </small>
        </div>
      )}
    </section>
  );
}

function MetaConnection({
  options,
  connected,
}: {
  options: Options;
  connected: () => Promise<void>;
}) {
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const sources = options.integrations.filter((v) => v.provider === "meta");
  const [source, setSource] = useState(sources[0]?.id ?? ""),
    [remote, setRemote] = useState<Remote[] | null>(null);
  const [oauth, setOauth] = useState(() => {
    const m = window.location.hash.match(
      /^#\/ads\/oauth\/([a-f0-9-]{36})\/([a-f0-9-]{36})$/i,
    );
    return m ? { integration_id: m[1], oauth_session_id: m[2] } : null;
  });
  const [link, setLink] = useState(""),
    [success, setSuccess] = useState("");
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  const canConnect = session.actions.includes("settings.channels.write");
  const discover = async (id: string) => {
    const value = await call<{ items: Remote[] }>("ads/meta/discover", "POST", {
      operation_id: crypto.randomUUID(),
      integration_id: id,
    });
    if (active.current) setRemote(value.items);
  };
  return (
    <div className="meta-connect-body">
      <p>
        Usa una conexión de Facebook de CBN. Meta debe conceder{" "}
        <code>ads_read</code> para consultar tus cuentas y resultados.
      </p>
      <SelectField
        id="meta-source"
        label="Conexión de Meta"
        disabled={task.busy}
        value={source}
        options={[
          { value: "", label: "Selecciona una conexión" },
          ...sources.map((v) => ({ value: v.id, label: v.name })),
        ]}
        onChange={(e) => {
          setSource(e.target.value);
          setRemote(null);
        }}
      />
      <div className="button-row">
        <Button
          disabled={!source || !canConnect || task.busy}
          onClick={() =>
            void task.run(async () => {
              const value = await call<{
                authorization_url: string;
                oauth_session_id: string;
              }>(`channels/${source}/oauth`, "POST", {
                operation_id: crypto.randomUUID(),
                scopes: ["ads_read"],
              });
              if (!active.current) return;
              setOauth({
                integration_id: source,
                oauth_session_id: value.oauth_session_id,
              });
              setLink(value.authorization_url);
              window.open(
                value.authorization_url,
                "_blank",
                "noopener,noreferrer",
              );
            }, "Completa la autorización en Meta y vuelve para finalizar la conexión.")
          }
        >
          Conectar con Meta
        </Button>
        <Button
          variant="secondary"
          disabled={!source || !canConnect || task.busy}
          onClick={() =>
            void task.run(() => discover(source), "Consulta completada.")
          }
        >
          Consultar cuentas autorizadas
        </Button>
      </div>
      {link && (
        <a href={link} target="_blank" rel="noopener noreferrer">
          Abrir autorización de Meta
        </a>
      )}
      {oauth && (
        <Button
          disabled={task.busy || !canConnect}
          onClick={() =>
            void task.run(async () => {
              await call("ads/meta/oauth/complete", "POST", {
                operation_id: crypto.randomUUID(),
                ...oauth,
              });
              if (!active.current) return;
              setSource(oauth.integration_id);
              setOauth(null);
              setLink("");
              setSuccess(
                "Meta autorizó la consulta de publicidad. Elige la cuenta que quieres agregar a RinovaPlus.",
              );
              await discover(oauth.integration_id);
            }, "Autorización de Meta completada.")
          }
        >
          Completar conexión de publicidad
        </Button>
      )}
      {task.notices}
      {remote && !remote.length && (
        <Notice>
          Meta no devolvió cuentas publicitarias. Comprueba el acceso a los
          activos publicitarios del negocio en Meta Business.
        </Notice>
      )}
      <div className="meta-remote-list">
        {remote?.map((v) => (
          <article className="panel" key={v.id}>
            <div>
              <strong>{v.name}</strong>
              <small>
                {v.id} · {v.currency} · {v.timezone}
              </small>
            </div>
            <Button
              disabled={task.busy}
              onClick={() =>
                void task.run(async () => {
                  const body = {
                    integration_id: source,
                    external_account_id: v.id,
                  };
                  await call("ads/meta/connect", "POST", {
                    ...body,
                    operation_id: intent.get(body),
                  });
                  intent.clear();
                  await connected();
                  if (active.current)
                    setSuccess(
                      `Cuenta ${v.name} agregada. Ya puedes consultar campañas y resultados.`,
                    );
                }, "Cuenta publicitaria conectada.")
              }
            >
              Usar esta cuenta
            </Button>
          </article>
        ))}
      </div>
      {success && (
        <OperationDialog
          success
          guidance={{ title: "Conexión completada", detail: success }}
          dismiss={() => setSuccess("")}
        />
      )}
    </div>
  );
}

function AccountDashboard({ account }: { account: Account }) {
  const { call } = useInstitution(),
    task = useTask();
  const [period, setPeriod] = useState(initialPeriod),
    [query, setQuery] = useState(period);
  const data = useAdsResource<{ snapshot: Snapshot | null }>(
    `ads/meta/${account.id}/snapshot?${new URLSearchParams(query)}`,
  );
  const [tab, setTab] = useState<Entity | "drafts">("campaigns"),
    [draft, setDraft] = useState<Draft | null>(null);
  const current = useRef({ active: true });
  useEffect(() => {
    const scope = { active: true };
    current.current = scope;
    return () => {
      scope.active = false;
    };
  }, [query]);
  const snapshot = data.value?.snapshot;
  return (
    <>
      <form
        className="panel meta-period"
        onSubmit={(e) => {
          e.preventDefault();
          if (allowNavigation()) {
            setQuery({ ...period });
            setDraft(null);
          }
        }}
      >
        <Field
          id="meta-start"
          type="date"
          label="Desde"
          required
          value={period.start}
          onChange={(e) => setPeriod({ ...period, start: e.target.value })}
        />
        <Field
          id="meta-end"
          type="date"
          label="Hasta"
          required
          value={period.end}
          onChange={(e) => setPeriod({ ...period, end: e.target.value })}
        />
        <Button type="submit" variant="secondary">
          Ver período
        </Button>
        <Button
          disabled={task.busy || account.status !== "connected"}
          onClick={() => {
            if (!allowNavigation()) return;
            void task.run(async () => {
              setDraft(null);
              const generation = current.current;
              await call(`ads/meta/${account.id}/sync`, "POST", {
                operation_id: crypto.randomUUID(),
                revision: account.revision,
                ...query,
              });
              if (generation === current.current && generation.active)
                await data.reload();
            }, "Datos consultados y guardados desde Meta.");
          }}
        >
          {task.busy ? "Consultando Meta…" : "Sincronizar con Meta"}
        </Button>
      </form>
      {task.notices}
      {data.error && <Notice error>{data.error}</Notice>}
      {!data.value && !data.error && (
        <div
          className="meta-skeleton"
          role="status"
          aria-label="Cargando resultados"
        >
          <div />
          <div />
          <div />
        </div>
      )}
      {data.value && !snapshot && (
        <div className="panel meta-empty">
          <h3>Sin consulta para este período</h3>
          <p>
            Del {query.start} al {query.end}. Pulsa Sincronizar con Meta para
            obtener los resultados. Si falla, la última consulta guardada se
            conserva.
          </p>
        </div>
      )}
      {snapshot && (
        <>
          <div className="meta-source-line">
            <span className="meta-source-dot" />
            Meta Marketing API · {snapshot.account.currency} ·{" "}
            {snapshot.account.timezone}
            <small>
              Consultado: {new Date(snapshot.synced_at).toLocaleString("es-CO")}
            </small>
          </div>
          {snapshot.no_delivery && (
            <Notice>
              Meta no registró entrega de anuncios en este período. Los ceros
              corresponden a una consulta válida.
            </Notice>
          )}
          <div className="meta-kpis">
            {(
              [
                ["spend", "Importe gastado", true],
                ["impressions", "Impresiones", false],
                ["reach", "Personas alcanzadas", false],
                ["clicks", "Clics", false],
                ["leads", "Leads", false],
                ["cpl", "Costo por lead", true],
              ] as const
            ).map(([key, label, money]) => (
              <article key={key} className="panel meta-kpi">
                <small>{label}</small>
                <strong>
                  {fmt(
                    snapshot.totals[key],
                    money ? snapshot.account.currency : undefined,
                  )}
                </strong>
                <span>
                  {key === "cpl"
                    ? "Gasto ÷ leads"
                    : `${snapshot.period.start} — ${snapshot.period.end}`}
                </span>
              </article>
            ))}
          </div>
          <DailyChart
            key={`${snapshot.synced_at}:${query.start}:${query.end}`}
            snapshot={snapshot}
          />
          <nav className="button-row" aria-label="Nivel de publicidad">
            {(["campaigns", "adsets", "ads", "drafts"] as const).map((v) => (
              <Button
                key={v}
                variant={tab === v ? "primary" : "secondary"}
                aria-pressed={tab === v}
                onClick={() => {
                  if (allowNavigation()) {
                    setTab(v);
                    setDraft(null);
                  }
                }}
              >
                {v === "drafts"
                  ? "Borradores locales"
                  : `${labels[v]} (${snapshot[v].length})`}
              </Button>
            ))}
          </nav>
          {tab === "drafts" ? (
            <DraftLibrary
              key={snapshot.synced_at}
              account={account}
              snapshot={snapshot}
              draft={draft}
              edit={setDraft}
            />
          ) : (
            <ObjectTable
              key={tab}
              entity={tab}
              snapshot={snapshot}
              edit={(v) => {
                setDraft({
                  ...blank(),
                  entity:
                    tab === "campaigns"
                      ? "campaign"
                      : tab === "adsets"
                        ? "adset"
                        : "ad",
                  mode: "edit",
                  target_id: v.id,
                  parent_id: v.adset_id ?? v.campaign_id ?? "",
                  name: v.name,
                  objective: v.objective ?? "OUTCOME_LEADS",
                  body: v.creative?.body ?? "",
                  headline: v.creative?.title ?? "",
                  image_url: v.creative?.image_url ?? "",
                  destination_url: v.creative?.destination_url ?? "",
                });
                setTab("drafts");
              }}
            />
          )}
          <details className="meta-method">
            <summary>Cómo se calculan estos resultados</summary>
            <p>
              CTR = clics ÷ impresiones × 100. CPC = gasto ÷ clics. CPL = gasto
              ÷ leads. Sin denominador se muestra —. El alcance es el agregado
              de Meta; no se suman personas entre días o anuncios. Los leads
              usan el agregado de acciones de Meta sin duplicar sus alias. Meta
              puede revisar resultados y atribuciones después del envío. No son
              matrículas confirmadas en el CRM.
            </p>
            <a
              href={`https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=${snapshot.account.id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              Ver cuenta en Meta Ads Manager ↗
            </a>
          </details>
        </>
      )}
    </>
  );
}

function DailyChart({ snapshot }: { snapshot: Snapshot }) {
  const [metric, setMetric] = useState<
    "spend" | "impressions" | "clicks" | "leads"
  >("spend");
  const points = [...snapshot.daily].sort((a, b) =>
    a.date.localeCompare(b.date),
  );
  const maximum = Math.max(1, ...points.map((v) => v[metric] ?? 0));
  const plotted = points.filter((v) => v[metric] !== null);
  const label = {
    spend: "Gasto",
    impressions: "Impresiones",
    clicks: "Clics",
    leads: "Leads",
  }[metric];
  const value = (n: number | null) =>
    fmt(n, metric === "spend" ? snapshot.account.currency : undefined);
  return (
    <section className="panel meta-chart">
      <header>
        <div>
          <h3>Resultados por día</h3>
          <small>
            {snapshot.period.start} — {snapshot.period.end} · zona{" "}
            {snapshot.account.timezone}
          </small>
        </div>
        <SelectField
          id="meta-chart-metric"
          label="Métrica del gráfico"
          value={metric}
          options={[
            { value: "spend", label: "Gasto" },
            { value: "impressions", label: "Impresiones" },
            { value: "clicks", label: "Clics" },
            { value: "leads", label: "Leads" },
          ]}
          onChange={(e) => setMetric(e.target.value as typeof metric)}
        />
      </header>
      {points.length >= 4 && plotted.length === points.length ? (
        <div className="meta-plot">
          <span>{value(maximum)}</span>
          <svg
            viewBox="0 0 800 200"
            role="img"
            aria-label={`${label} por día. Datos exactos disponibles en la tabla.`}
            preserveAspectRatio="none"
          >
            <title>{label} diario</title>
            {[0, 1, 2, 3].map((v) => (
              <line
                key={v}
                x1="10"
                x2="790"
                y1={20 + v * 55}
                y2={20 + v * 55}
                className="meta-gridline"
              />
            ))}
            <polyline
              key={metric}
              pathLength="1"
              points={points
                .map(
                  (v, i) =>
                    `${10 + (i * 780) / (points.length - 1)},${185 - ((v[metric] ?? 0) / maximum) * 165}`,
                )
                .join(" ")}
              className="meta-chart-line"
            />
            {points.map((v, i) => (
              <circle
                key={v.date}
                cx={10 + (i * 780) / (points.length - 1)}
                cy={185 - ((v[metric] ?? 0) / maximum) * 165}
                r="3"
                tabIndex={0}
              >
                <title>
                  {v.date}: {value(v[metric])}
                </title>
              </circle>
            ))}
          </svg>
          <footer>
            <span>{points[0].date}</span>
            <span>{points.at(-1)?.date}</span>
          </footer>
        </div>
      ) : (
        <p className="meta-chart-empty">
          {points.length
            ? "Pocos días con datos: consulta sus valores exactos en la tabla."
            : "Meta no devolvió resultados diarios para este período."}
        </p>
      )}
      {!!points.length && (
        <details>
          <summary>Ver datos diarios en tabla</summary>
          <div className="meta-table-scroll">
            <table>
              <caption>{label} por fecha</caption>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>{label}</th>
                </tr>
              </thead>
              <tbody>
                {points.map((v) => (
                  <tr key={v.date}>
                    <th scope="row">{v.date}</th>
                    <td>{value(v[metric])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </section>
  );
}

function ObjectTable({
  snapshot,
  entity,
  edit,
}: {
  snapshot: Snapshot;
  entity: Entity;
  edit: (v: AdObject) => void;
}) {
  const [search, setSearch] = useState(""),
    [status, setStatus] = useState("all"),
    [selected, setSelected] = useState<AdObject | null>(null);
  const values = snapshot[entity].filter(
    (v) =>
      `${v.name} ${v.id}`
        .toLocaleLowerCase()
        .includes(search.toLocaleLowerCase()) &&
      (status === "all" || v.effective_status === status),
  );
  const statuses = [
    ...new Set(
      snapshot[entity]
        .map((v) => v.effective_status)
        .filter((v): v is string => !!v),
    ),
  ];
  return (
    <section className="panel meta-objects">
      <div className="meta-object-filters">
        <Field
          id="meta-search"
          label={`Buscar ${labels[entity].toLowerCase()}`}
          placeholder="Nombre o ID"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <SelectField
          id="meta-status"
          label="Estado en Meta"
          value={status}
          options={[
            { value: "all", label: "Todos los estados" },
            ...statuses.map((v) => ({ value: v, label: v })),
          ]}
          onChange={(e) => setStatus(e.target.value)}
        />
      </div>
      <div className="meta-table-scroll">
        <table>
          <caption>
            {labels[entity]} · {values.length} resultados
          </caption>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Estado</th>
              <th>Gasto</th>
              <th>Impresiones</th>
              <th>Clics</th>
              <th>CTR</th>
              <th>Leads</th>
              <th>CPL</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {values.map((v) => {
              const m = objectMetrics(snapshot, entity, v.id);
              return (
                <tr key={v.id}>
                  <th scope="row">
                    <button
                      className="meta-name"
                      onClick={() => setSelected(v)}
                    >
                      {v.name}
                    </button>
                    <small>{v.id}</small>
                  </th>
                  <td>
                    <span className="badge">
                      {v.effective_status ?? v.status ?? "Sin estado"}
                    </span>
                  </td>
                  <td>{fmt(m?.spend, snapshot.account.currency)}</td>
                  <td>{fmt(m?.impressions)}</td>
                  <td>{fmt(m?.clicks)}</td>
                  <td>
                    {m?.ctr === undefined || m?.ctr === null
                      ? "—"
                      : `${fmt(m.ctr)} %`}
                  </td>
                  <td>{fmt(m?.leads)}</td>
                  <td>{fmt(m?.cpl, snapshot.account.currency)}</td>
                  <td>
                    <Button variant="quiet" onClick={() => edit(v)}>
                      Preparar edición
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!values.length && (
        <p className="meta-chart-empty">
          No hay {labels[entity].toLowerCase()} para estos filtros.
        </p>
      )}
      {selected && (
        <div className="meta-object-detail">
          <div>
            <h3>{selected.name}</h3>
            <p>
              ID {selected.id}{" "}
              {selected.campaign_id && `· Campaña ${selected.campaign_id}`}{" "}
              {selected.adset_id && `· Conjunto ${selected.adset_id}`}
            </p>
            <Button variant="quiet" onClick={() => setSelected(null)}>
              Cerrar detalle
            </Button>
          </div>
          {selected.creative ? (
            <CreativePreview value={selected.creative} />
          ) : (
            <p>
              {selected.objective ??
                "Selecciona Anuncios para consultar la creatividad disponible."}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function CreativePreview({
  value,
}: {
  value: NonNullable<AdObject["creative"]>;
}) {
  const [failed, setFailed] = useState(false),
    image = safeAdUrl(value.image_url);
  return (
    <article className="meta-creative" aria-label="Vista previa del anuncio">
      <small>
        Vista previa de creatividad · el formato final depende de la ubicación
        en Meta
      </small>
      <p>{value.body || "Meta no devolvió texto de esta creatividad."}</p>
      {image && !failed ? (
        <img
          src={image}
          alt={value.title || "Creatividad del anuncio"}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="meta-preview-empty">
          Vista previa no disponible. Sincroniza de nuevo o consulta el anuncio
          en Meta.
        </div>
      )}
      <strong>{value.title}</strong>
      {safeAdUrl(value.destination_url) && (
        <a
          href={safeAdUrl(value.destination_url)}
          target="_blank"
          rel="noopener noreferrer"
        >
          Ver destino ↗
        </a>
      )}
    </article>
  );
}

function DraftLibrary({
  account,
  snapshot,
  draft,
  edit,
}: {
  account: Account;
  snapshot: Snapshot;
  draft: Draft | null;
  edit: (v: Draft | null) => void;
}) {
  const { call } = useInstitution(),
    task = useTask();
  const library = useAdsResource<{ items: Draft[] }>(
    `ads/meta/${account.id}/drafts`,
  );
  const [review, setReview] = useState<{
    message: string;
    success: boolean;
  } | null>(null);
  return (
    <section className="panel meta-drafts">
      <header>
        <div>
          <h3>Preparar, revisar y conservar</h3>
          <p>
            Borradores locales de creación o edición. La revisión no publica
            anuncios ni modifica presupuestos en Meta.
          </p>
        </div>
        <Button
          disabled={task.busy}
          onClick={() => {
            if (allowNavigation()) edit(blank());
          }}
        >
          Crear borrador
        </Button>
      </header>
      {task.notices}
      <div className="meta-draft-list">
        {library.value?.items.map((v) => (
          <article key={v.id}>
            <div>
              <strong>{v.name}</strong>
              <small>
                {v.entity} ·{" "}
                {v.mode === "edit" ? `Edición de ${v.target_id}` : "Creación"} ·
                versión {v.revision}
              </small>
              <span className="badge">
                {v.review_valid
                  ? "Revisado localmente"
                  : "Pendiente de revisión"}
              </span>
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                if (allowNavigation()) edit(v);
              }}
            >
              Editar borrador
            </Button>
            <Button
              disabled={task.busy}
              onClick={() =>
                void task.run(async () => {
                  const result = await call<{
                    reviewed: boolean;
                    issues: string[];
                    message: string;
                  }>(`ads/meta/${account.id}/drafts/${v.id}/review`, "POST", {
                    operation_id: crypto.randomUUID(),
                    revision: v.revision,
                  });
                  setReview({
                    message: result.reviewed
                      ? result.message
                      : result.issues.join(" "),
                    success: result.reviewed,
                  });
                  await library.reload();
                }, "Revisión local completada.")
              }
            >
              Revisar
            </Button>
          </article>
        ))}
      </div>
      {!library.value && <ResourceState error={library.error} />}
      {library.value && !library.value.items.length && (
        <p>Aún no hay borradores guardados en esta cuenta.</p>
      )}
      {draft && (
        <DraftEditor
          key={`${draft.id ?? "new"}:${draft.revision}`}
          initial={draft}
          snapshot={snapshot}
          account={account}
          saved={async () => {
            edit(null);
            await library.reload();
          }}
          close={() => {
            if (allowNavigation()) edit(null);
          }}
        />
      )}
      {review && (
        <OperationDialog
          success={review.success}
          guidance={{
            title: "Resultado de revisión local",
            detail: review.message,
            nextStep:
              "La publicación en Meta es un paso posterior que requiere autorización explícita.",
          }}
          dismiss={() => setReview(null)}
        />
      )}
    </section>
  );
}

function DraftEditor({
  initial,
  snapshot,
  account,
  saved,
  close,
}: {
  initial: Draft;
  snapshot: Snapshot;
  account: Account;
  saved: () => Promise<void>;
  close: () => void;
}) {
  const [value, setValue] = useState(initial),
    [clean, setClean] = useState(JSON.stringify(initial));
  const { call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  useDraftGuard(JSON.stringify(value) !== clean);
  const change = <K extends keyof Draft>(key: K, v: Draft[K]) =>
    setValue({ ...value, [key]: v });
  const parents = value.entity === "ad" ? snapshot.adsets : snapshot.campaigns;
  return (
    <form
      className="meta-draft-editor"
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          const {
            id,
            revision,
            entity,
            mode,
            target_id,
            parent_id,
            name,
            objective,
            daily_budget_cents,
            body: text,
            headline,
            destination_url,
            image_url,
            countries,
          } = value;
          const document = {
            entity,
            mode,
            target_id,
            parent_id,
            name,
            objective,
            daily_budget_cents,
            body: text,
            headline,
            destination_url,
            image_url,
            countries,
          };
          const body = {
            ...document,
            draft_id: id ?? null,
            draft_revision: revision,
          };
          await call(`ads/meta/${account.id}/drafts`, "POST", {
            ...body,
            operation_id: intent.get(body),
          });
          intent.clear();
          setClean(JSON.stringify(value));
          await saved();
        }, "Versión del borrador guardada.");
      }}
    >
      <h3>{value.id ? "Editar borrador" : "Nuevo borrador"}</h3>
      <div className="ads-fields">
        <SelectField
          id="meta-draft-entity"
          label="Tipo de elemento"
          disabled={value.mode === "edit"}
          value={value.entity}
          options={[
            { value: "campaign", label: "Campaña" },
            { value: "adset", label: "Conjunto de anuncios" },
            { value: "ad", label: "Anuncio" },
          ]}
          onChange={(e) =>
            setValue({ ...blank(), entity: e.target.value as Draft["entity"] })
          }
        />
        <Field
          id="meta-draft-name"
          label="Nombre del borrador"
          required
          maxLength={180}
          value={value.name}
          onChange={(e) => change("name", e.target.value)}
        />
        {value.entity !== "campaign" && (
          <SelectField
            id="meta-draft-parent"
            label={
              value.entity === "ad"
                ? "Conjunto de esta cuenta"
                : "Campaña de esta cuenta"
            }
            required
            value={value.parent_id}
            options={[
              { value: "", label: "Selecciona un elemento" },
              ...parents.map((v) => ({ value: v.id, label: v.name })),
            ]}
            onChange={(e) => change("parent_id", e.target.value)}
          />
        )}
        <SelectField
          id="meta-draft-objective"
          label="Objetivo propuesto"
          value={value.objective}
          options={[
            { value: "OUTCOME_LEADS", label: "Clientes potenciales" },
            { value: "OUTCOME_TRAFFIC", label: "Tráfico" },
            { value: "OUTCOME_ENGAGEMENT", label: "Interacción" },
            { value: "OUTCOME_AWARENESS", label: "Reconocimiento" },
            { value: "OUTCOME_SALES", label: "Ventas" },
          ]}
          onChange={(e) => change("objective", e.target.value)}
        />
        <Field
          id="meta-draft-budget"
          label={`Presupuesto diario propuesto (${snapshot.account.currency}, unidades menores de Meta)`}
          type="number"
          min={0}
          step={1}
          value={value.daily_budget_cents}
          onChange={(e) => change("daily_budget_cents", Number(e.target.value))}
          hint="Se conserva como propuesta local. No cambia el gasto en Meta."
        />
        <Field
          id="meta-draft-countries"
          label="Países propuestos (códigos separados por coma)"
          value={value.countries.join(",")}
          onChange={(e) =>
            change(
              "countries",
              e.target.value
                .toUpperCase()
                .split(",")
                .map((v) => v.trim()),
            )
          }
        />
      </div>
      {value.entity === "ad" && (
        <>
          <Field
            id="meta-draft-title"
            label="Título"
            value={value.headline}
            maxLength={250}
            onChange={(e) => change("headline", e.target.value)}
          />
          <TextArea
            id="meta-draft-body"
            label="Texto del anuncio"
            value={value.body}
            maxLength={8000}
            onChange={(e) => change("body", e.target.value)}
          />
          <Field
            id="meta-draft-link"
            label="URL de destino"
            type="url"
            value={value.destination_url}
            onChange={(e) => change("destination_url", e.target.value)}
          />
          <Field
            id="meta-draft-image"
            label="URL pública de imagen"
            type="url"
            value={value.image_url}
            onChange={(e) => change("image_url", e.target.value)}
          />
          <CreativePreview
            key={value.image_url}
            value={{
              title: value.headline,
              body: value.body,
              image_url: value.image_url,
              destination_url: value.destination_url,
            }}
          />
        </>
      )}
      {task.notices}
      <div className="button-row">
        <Button type="submit" disabled={task.busy}>
          Guardar versión del borrador
        </Button>
        <Button variant="secondary" onClick={close}>
          Cerrar editor
        </Button>
      </div>
    </form>
  );
}
