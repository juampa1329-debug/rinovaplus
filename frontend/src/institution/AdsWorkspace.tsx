import { useEffect, useRef, useState } from "react";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../shared/ui";
import { useInstitution, useTask, useIntent } from "./api";
import { ResourceState } from "./Settings";
import { useAdsResource as useResource } from "./adsResource";
import { allowNavigation, useDraftGuard } from "./drafts";
import "./ads.css";
import { MetaAdsManager } from "./MetaAdsManager";
import { ErrorFeedback } from "./ErrorFeedback";
import { explainChannelError } from "./channelErrors";

type Tab = "leads" | "comments" | "campaigns" | "accounts" | "processes";
type Doc = {
  provider: string;
  external_account_id: string;
  name: string;
  status: string;
  currency: string;
  timezone: string;
  integration_id: string | null;
  program_id: number | null;
  initial_stage_key: string;
  form_ids: string[];
  account_id: string;
  channel: string;
  external_campaign_id: string;
  objective: string;
  daily_budget_cents: number;
  lifetime_budget_cents: number;
  metrics_json: { ctr: number; cpc: number; leads: number } | null;
  period_start: string | null;
  period_end: string | null;
  external_id: string;
  external_form_id: string;
  external_ad_id: string;
  author_id: string;
  contact_name: string;
  email: string;
  phone: string;
  message: string;
  external_post_id: string;
  external_parent_id: string;
  permalink_url: string;
  captured_at: string | null;
};
type Item = Partial<Doc> & {
  id: string;
  revision: number;
  contact_id?: string;
  conversation_id?: string;
  origin?: string;
  has_access_token?: boolean;
  state?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
  leads?: number;
  comments?: number;
  duplicates?: number;
  created_at?: string;
  updated_at?: string;
};
type Options = {
  accounts: Item[];
  integrations: {
    id: string;
    name: string;
    channel: string;
    provider: string;
  }[];
  programs: { program_id: number; name: string }[];
  stages: { key: string; label: string }[];
};
const names: Record<Tab, string> = {
  leads: "Leads",
  comments: "Comentarios de anuncios",
  campaigns: "Campañas publicitarias",
  accounts: "Cuentas publicitarias",
  processes: "Procesamiento",
};
const states: Record<string, string> = {
  new: "Nuevo",
  review: "En revisión",
  qualified: "Calificado",
  converted: "En CRM",
  lost: "Descartado",
  resolved: "Resuelto",
  hidden: "Oculto",
  deleted: "Eliminado",
  connected: "Disponible",
  paused: "Pausado",
  disconnected: "Desconectado",
  active: "Activo registrado",
  unknown: "Sin confirmar",
  draft: "Borrador",
  completed: "Completado",
  archived: "Archivado",
  processed: "Procesado",
  ignored: "Ignorado",
  quarantined: "Requiere revisión",
};
const origins: Record<string, string> = {
  operator: "Registro del equipo",
  synthetic_demo: "Ejemplo ficticio",
  verified_receipt: "Webhook firmado",
};
const reasons: Record<string, string> = {
  ads_channel_context_changed:
    "El canal vinculado cambió o está sin verificar. Revisa su conexión antes de reintentar.",
  ads_campaign_or_form_mapping_required:
    "Relaciona el formulario o la campaña con la cuenta y vuelve a procesar.",
  ads_ambiguous_account_mapping:
    "El formulario o la campaña están asociados a varias cuentas. Revisa la relación.",
  ads_receipt_unavailable:
    "El recibo venció o su canal dejó de estar disponible.",
  ads_payload_invalid:
    "Faltan datos válidos en el evento. Revisa su origen antes de reintentar.",
  ads_program_review_required:
    "Selecciona un programa vigente en el catálogo CRM.",
  ads_stage_review_required: "Revisa la etapa inicial de esta cuenta.",
};
const defaults = (tab: Tab, accountId: string): Doc => ({
  provider: "meta",
  external_account_id: "",
  name: "",
  status:
    tab === "accounts" ? "connected" : tab === "campaigns" ? "unknown" : "new",
  currency: "COP",
  timezone: "America/Bogota",
  integration_id: null,
  program_id: null,
  initial_stage_key: "",
  form_ids: [],
  account_id: accountId,
  channel: "facebook",
  external_campaign_id: "",
  objective: "messages",
  daily_budget_cents: 0,
  lifetime_budget_cents: 0,
  metrics_json: null,
  period_start: null,
  period_end: null,
  external_id: "",
  external_form_id: "",
  external_ad_id: "",
  author_id: "",
  contact_name: "",
  email: "",
  phone: "",
  message: "",
  external_post_id: "",
  external_parent_id: "",
  permalink_url: "",
  captured_at: null,
});
const command = (
  revision: number,
  intent: ReturnType<typeof useIntent>,
  path: string,
  changes: Record<string, unknown> = {},
) => {
  const body = {
    revision,
    reason: "Actualización local desde Publicidad",
    ...changes,
  };
  return { ...body, operation_id: intent.get({ path, body }) };
};
const stamp = (v?: string | null) =>
  v ? new Date(v).toLocaleString("es-CO") : "Sin registrar";

export function AdsWorkspace(props: { initialView?: "manager" | "capture" }) {
  return (
    <ErrorFeedback explain={explainChannelError}>
      <AdsWorkspaceContent {...props} />
    </ErrorFeedback>
  );
}

function AdsWorkspaceContent({
  initialView = "manager",
}: {
  initialView?: "manager" | "capture";
}) {
  const [view, setView] = useState(initialView);
  return (
    <div className="ads-workspace">
      <nav className="button-row" aria-label="Área de publicidad">
        <Button
          variant={view === "manager" ? "primary" : "secondary"}
          aria-pressed={view === "manager"}
          onClick={() => {
            if (allowNavigation()) setView("manager");
          }}
        >
          Campañas y anuncios
        </Button>
        <Button
          variant={view === "capture" ? "primary" : "secondary"}
          aria-pressed={view === "capture"}
          onClick={() => {
            if (allowNavigation()) setView("capture");
          }}
        >
          Captación y CRM
        </Button>
      </nav>
      {view === "manager" ? <MetaAdsManager /> : <AdsCaptureWorkspace />}
    </div>
  );
}

function AdsCaptureWorkspace() {
  const { session, call } = useInstitution(),
    task = useTask(),
    intent = useIntent(),
    options = useResource<Options>("ads/options");
  const view = useRef(0);
  useEffect(
    () => () => {
      view.current += 1;
    },
    [],
  );
  const [tab, setTab] = useState<Tab>("leads"),
    [account, setAccount] = useState(""),
    [status, setStatus] = useState("all"),
    [start, setStart] = useState(""),
    [end, setEnd] = useState(""),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState<Item | null>(null),
    [creating, setCreating] = useState(false);
  const query = new URLSearchParams({
    offset: String(offset),
    ...(account ? { account_id: account } : {}),
    ...(status !== "all" ? { status } : {}),
    ...(start ? { start } : {}),
    ...(end ? { end } : {}),
  });
  const listing = useResource<{ items: Item[]; has_more: boolean }>(
      `ads/${tab}?${query}`,
    ),
    summary = useResource<{ summary: Record<string, number>; as_of: string }>(
      `ads/summary?${new URLSearchParams({ ...(account ? { account_id: account } : {}), ...(start ? { start } : {}), ...(end ? { end } : {}) })}`,
    );
  const refresh = async () => {
    await Promise.all([listing.reload(), options.reload(), summary.reload()]);
  };
  const change = (action: () => void) => {
    if (allowNavigation()) {
      view.current += 1;
      action();
      setOffset(0);
      setSelected(null);
      setCreating(false);
    }
  };
  const saved = async (row: Item) => {
    setSelected(row);
    setCreating(false);
    await refresh();
  };
  if (!options.value) return <ResourceState error={options.error} />;
  const chosen = options.value.accounts.find((v) => v.id === account);
  return (
    <div className="ads-workspace">
      <header>
        <h1>Publicidad y captación</h1>
        <p>
          Organiza tus cuentas, campañas y contactos interesados en programas
          educativos.
        </p>
      </header>
      <details>
        <summary>Origen y alcance de los datos</summary>
        <p>
          Los presupuestos e indicadores guardados aquí son registros locales.
          Esta pantalla no publica anuncios ni cambia el gasto en Meta o TikTok.
        </p>
        <a href="#/settings/channels">Configurar Canales y OAuth</a>
      </details>
      <section className="panel ads-filters" aria-label="Filtros de Publicidad">
        <SelectField
          id="ads-account-filter"
          label="Cuenta"
          value={account}
          options={[
            { value: "", label: "Todas las cuentas" },
            ...options.value.accounts.map((v) => ({
              value: v.id,
              label: v.name || v.external_account_id || v.id,
            })),
          ]}
          onChange={(e) => change(() => setAccount(e.target.value))}
        />
        <Field
          id="ads-date-start"
          label="Captaciones desde"
          type="date"
          value={start}
          onChange={(e) => change(() => setStart(e.target.value))}
        />
        <Field
          id="ads-date-end"
          label="Captaciones hasta"
          type="date"
          value={end}
          onChange={(e) => change(() => setEnd(e.target.value))}
        />
        <Button
          variant="secondary"
          disabled={task.busy}
          onClick={() => void task.run(refresh, "Información actualizada.")}
        >
          Actualizar datos locales
        </Button>
      </section>
      {task.notices}
      {summary.value ? (
        <section className="ads-summary" aria-label="Resumen de captación">
          {[
            ["accounts", "Cuentas"],
            ["campaigns", "Campañas"],
            ["open_leads", "Leads abiertos"],
            ["open_comments", "Comentarios abiertos"],
            ["webhook_events", "Webhooks firmados"],
            ["conversations", "Conversaciones vinculadas"],
          ].map(([key, label]) => (
            <div className="panel" key={key}>
              <small>{label}</small>
              <strong>{summary.value!.summary[key] || 0}</strong>
            </div>
          ))}
          <small>
            Registros locales · consultado {stamp(summary.value.as_of)}
          </small>
        </section>
      ) : (
        <ResourceState error={summary.error} />
      )}
      <nav aria-label="Vistas de Publicidad" className="institution-actions">
        {(Object.keys(names) as Tab[]).map((v) => (
          <Button
            key={v}
            variant={tab === v ? "primary" : "quiet"}
            onClick={() =>
              change(() => {
                setTab(v);
                setStatus("all");
              })
            }
          >
            {names[v]}
          </Button>
        ))}
      </nav>
      <div className="ads-layout">
        <aside className="panel ads-list">
          {tab !== "processes" && (
            <Button
              onClick={() => {
                if (allowNavigation()) {
                  view.current += 1;
                  setSelected(null);
                  setCreating(true);
                }
              }}
            >
              {tab === "accounts"
                ? "Agregar cuenta"
                : tab === "campaigns"
                  ? "Registrar campaña"
                  : tab === "leads"
                    ? "Importar lead"
                    : "Importar comentario"}
            </Button>
          )}
          {(tab === "leads" || tab === "comments") && (
            <SelectField
              id="ads-status"
              label="Estado"
              value={status}
              options={[
                { value: "all", label: "Todos" },
                ...[
                  "new",
                  "review",
                  "qualified",
                  "converted",
                  "lost",
                  "resolved",
                  "ignored",
                  "hidden",
                  "deleted",
                ].map((v) => ({ value: v, label: states[v] })),
              ]}
              onChange={(e) => change(() => setStatus(e.target.value))}
            />
          )}
          {!listing.value ? (
            <ResourceState error={listing.error} />
          ) : (
            <>
              {listing.value.items.length === 0 && (
                <p>No hay registros con estos filtros.</p>
              )}
              {listing.value.items.map((v) => (
                <Button
                  key={v.id}
                  variant="quiet"
                  className="ads-record"
                  onClick={() => {
                    if (allowNavigation()) {
                      view.current += 1;
                      setSelected(v);
                      setCreating(false);
                    }
                  }}
                >
                  <strong>
                    {v.name ||
                      v.contact_name ||
                      v.external_id ||
                      "Procesamiento de evento"}
                  </strong>
                  <small>
                    {states[v.state || v.status || ""] || "Registro local"} ·{" "}
                    {tab === "processes"
                      ? stamp(v.completed_at)
                      : v.external_account_id ||
                        v.external_campaign_id ||
                        v.external_id}
                  </small>
                </Button>
              ))}
              <div className="institution-actions">
                <Button
                  variant="quiet"
                  disabled={!offset}
                  onClick={() => {
                    if (allowNavigation()) {
                      view.current += 1;
                      setOffset(Math.max(0, offset - 50));
                      setSelected(null);
                      setCreating(false);
                    }
                  }}
                >
                  Anteriores
                </Button>
                <Button
                  variant="quiet"
                  disabled={!listing.value.has_more}
                  onClick={() => {
                    if (allowNavigation()) {
                      view.current += 1;
                      setOffset(offset + 50);
                      setSelected(null);
                      setCreating(false);
                    }
                  }}
                >
                  Siguientes
                </Button>
              </div>
            </>
          )}
        </aside>
        <section className="panel ads-editor">
          {tab === "processes" ? (
            <>
              <h2>Procesamiento de webhooks</h2>
              <p>
                Selecciona una cuenta vinculada a Canales para procesar el
                siguiente recibo firmado.
              </p>
              <Button
                disabled={
                  !chosen?.integration_id ||
                  chosen.status !== "connected" ||
                  task.busy ||
                  !session.actions.includes("crm.write") ||
                  !session.actions.includes("inbox.write")
                }
                onClick={() =>
                  void task.run(async () => {
                    const expectedView = view.current;
                    const result = await call<Item & { state: string }>(
                      `ads/accounts/${account}/process`,
                      "POST",
                      command(
                        chosen!.revision,
                        intent,
                        `ads/accounts/${account}/process`,
                      ),
                    );
                    if (view.current !== expectedView) return;
                    setSelected(result.state === "empty" ? null : result);
                    intent.clear();
                    await refresh();
                  }, "Procesamiento terminado. Consulta el resultado registrado.")
                }
              >
                Procesar siguiente evento
              </Button>
              {selected && (
                <>
                  <h3>{states[selected.state || ""] || "Resultado"}</h3>
                  <dl>
                    <dt>Origen</dt>
                    <dd>Webhook firmado del canal vinculado</dd>
                    <dt>Fecha</dt>
                    <dd>{stamp(selected.completed_at)}</dd>
                    <dt>Leads</dt>
                    <dd>{selected.leads || 0}</dd>
                    <dt>Comentarios</dt>
                    <dd>{selected.comments || 0}</dd>
                    <dt>Duplicados detectados</dt>
                    <dd>{selected.duplicates || 0}</dd>
                  </dl>
                  {selected.error && (
                    <Notice error>
                      {reasons[selected.error] ||
                        "Revisa el evento y la configuración de esta cuenta."}
                    </Notice>
                  )}
                  {selected.state === "quarantined" && (
                    <Button
                      disabled={task.busy}
                      onClick={() =>
                        void task.run(async () => {
                          const expectedView = view.current;
                          const result = await call<Item>(
                            `ads/accounts/${selected.account_id}/processes/${selected.id}/retry`,
                            "POST",
                            command(
                              selected.revision,
                              intent,
                              `ads/accounts/${selected.account_id}/processes/${selected.id}/retry`,
                            ),
                          );
                          if (view.current !== expectedView) return;
                          setSelected(result);
                          intent.clear();
                          await refresh();
                        }, "Reintento registrado.")
                      }
                    >
                      Reintentar evento revisado
                    </Button>
                  )}
                </>
              )}
            </>
          ) : selected || creating ? (
            <AdsEditor
              key={`${tab}:${selected?.id || "new"}:${selected?.revision || 0}`}
              tab={tab}
              initial={selected}
              options={options.value}
              defaultAccount={account}
              saved={saved}
            />
          ) : (
            <>
              <h2>{names[tab]}</h2>
              <p>
                Selecciona un registro o agrega uno nuevo para revisar sus datos
                y su vínculo con CRM.
              </p>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function AdsEditor({
  tab,
  initial,
  options,
  defaultAccount,
  saved,
}: {
  tab: Tab;
  initial: Item | null;
  options: Options;
  defaultAccount: string;
  saved: (v: Item) => Promise<void>;
}) {
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const live = useRef(true);
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  const accept = async (row: Item) => {
    if (live.current) await saved(row);
  };
  const [doc, setDoc] = useState<Doc>(() => {
      const value = defaults(tab, defaultAccount);
      for (const key of Object.keys(value) as (keyof Doc)[]) {
        if (initial && key in initial)
          Object.assign(value, { [key]: initial[key] });
      }
      return value;
    }),
    [convert, setConvert] = useState(
      !initial &&
        session.actions.includes("crm.write") &&
        session.actions.includes("inbox.write"),
    ),
    [token, setToken] = useState(""),
    [revoke, setRevoke] = useState(false),
    [history, setHistory] = useState<{
      items: { id: string; kind: string; at: string }[];
    } | null>(null);
  const [baseline] = useState(() => JSON.stringify(doc));
  useDraftGuard(JSON.stringify(doc) !== baseline || !!token || task.busy);
  const update = (v: Partial<Doc>) =>
    setDoc((current) => ({ ...current, ...v }));
  const account = options.accounts.find((v) => v.id === doc.account_id),
    isIntake = tab === "leads" || tab === "comments";
  const accountOptions = [
    { value: "", label: "Selecciona una cuenta" },
    ...options.accounts.map((v) => ({
      value: v.id,
      label: v.name || v.external_account_id || v.id,
    })),
  ];
  const field = (
    key: keyof Doc,
    label: string,
    maxLength = 180,
    type = "text",
    disabled = false,
  ) => (
    <Field
      id={`ads-edit-${key}`}
      label={label}
      value={String(doc[key] ?? "")}
      maxLength={maxLength}
      type={type}
      disabled={disabled}
      onChange={(e) => update({ [key]: e.target.value })}
    />
  );
  const chooseProgram = (
    <SelectField
      id="ads-edit-program"
      label="Programa de interés"
      value={doc.program_id === null ? "" : String(doc.program_id)}
      options={[
        { value: "", label: "Sin programa asignado" },
        ...options.programs.map((v) => ({
          value: String(v.program_id),
          label: v.name,
        })),
      ]}
      onChange={(e) =>
        update({ program_id: e.target.value ? Number(e.target.value) : null })
      }
    />
  );
  const payload = () => {
    const fields =
      tab === "accounts"
        ? [
            "provider",
            "external_account_id",
            "name",
            "status",
            "currency",
            "timezone",
            "integration_id",
            "program_id",
            "initial_stage_key",
            "form_ids",
          ]
        : tab === "campaigns"
          ? [
              "account_id",
              "channel",
              "external_campaign_id",
              "name",
              "objective",
              "status",
              "daily_budget_cents",
              "lifetime_budget_cents",
              "currency",
              "metrics_json",
              "period_start",
              "period_end",
            ]
          : [
              "account_id",
              "channel",
              "external_id",
              "external_form_id",
              "external_ad_id",
              "external_campaign_id",
              "author_id",
              "contact_name",
              "email",
              "phone",
              "message",
              "external_post_id",
              "external_parent_id",
              "permalink_url",
              "status",
              "program_id",
              "captured_at",
            ];
    return Object.fromEntries(
      fields.map((key) => [key, doc[key as keyof Doc]]),
    );
  };
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          const path = initial
            ? `ads/${tab}/${initial.id}`
            : isIntake
              ? `ads/${tab}/import`
              : `ads/${tab}`;
          const result = await call<Item>(
            path,
            initial ? "PATCH" : "POST",
            command(initial?.revision || 0, intent, path, {
              document: payload(),
              ...(isIntake ? { create_conversation: convert } : {}),
            }),
          );
          setToken("");
          await accept(result);
        }, "Registro guardado.");
      }}
    >
      {task.notices}
      <h2>
        {initial
          ? initial.name ||
            initial.contact_name ||
            initial.external_id ||
            names[tab]
          : tab === "accounts"
            ? "Nueva cuenta"
            : tab === "campaigns"
              ? "Nueva campaña"
              : tab === "leads"
                ? "Nuevo lead"
                : "Nuevo comentario"}
      </h2>
      {initial && (
        <p>
          <Badge>{states[initial.status || ""] || "Registro local"}</Badge>{" "}
          {isIntake
            ? origins[initial.origin || ""] || "Registro local"
            : "Registro local"}{" "}
          · {stamp(initial.updated_at)}
        </p>
      )}
      <fieldset disabled={task.busy} className="ads-fields">
        {tab === "accounts" ? (
          <>
            <SelectField
              id="ads-edit-provider"
              label="Proveedor"
              value={doc.provider}
              disabled={!!initial}
              options={[
                { value: "meta", label: "Meta" },
                { value: "tiktok", label: "TikTok" },
              ]}
              onChange={(e) =>
                update({ provider: e.target.value, integration_id: null })
              }
            />
            {field(
              "external_account_id",
              "ID de cuenta publicitaria",
              160,
              "text",
              !!initial,
            )}
            {field("name", "Nombre de cuenta")}
            <SelectField
              id="ads-edit-availability"
              label="Disponibilidad local"
              value={doc.status}
              options={["connected", "paused", "disconnected"].map((v) => ({
                value: v,
                label: states[v],
              }))}
              onChange={(e) => update({ status: e.target.value })}
            />
            {field("currency", "Moneda", 3)}
            {field("timezone", "Zona horaria", 80)}
            <SelectField
              id="ads-edit-integration"
              label="Canal vinculado"
              value={doc.integration_id || ""}
              options={[
                { value: "", label: "Sin canal vinculado" },
                ...options.integrations
                  .filter((v) => v.provider === doc.provider)
                  .map((v) => ({ value: v.id, label: v.name })),
              ]}
              onChange={(e) =>
                update({ integration_id: e.target.value || null })
              }
            />
            {chooseProgram}
            <SelectField
              id="ads-edit-stage"
              label="Etapa inicial CRM"
              value={doc.initial_stage_key || options.stages[0]?.key || ""}
              options={options.stages.map((v) => ({
                value: v.key,
                label: v.label,
              }))}
              onChange={(e) => update({ initial_stage_key: e.target.value })}
            />
            <TextArea
              id="ads-edit-formids"
              label="IDs de formularios asociados"
              value={doc.form_ids.join("\n")}
              maxLength={18000}
              onChange={(e) =>
                update({
                  form_ids: e.target.value
                    .split(/[\n,]/)
                    .map((v) => v.trim())
                    .filter(Boolean),
                })
              }
            />
          </>
        ) : (
          <>
            <SelectField
              id="ads-edit-account"
              label="Cuenta publicitaria"
              value={doc.account_id}
              disabled={!!initial}
              options={accountOptions}
              onChange={(e) => {
                const a = options.accounts.find((v) => v.id === e.target.value);
                update({
                  account_id: e.target.value,
                  channel: a?.provider === "tiktok" ? "tiktok" : "facebook",
                  currency: a?.currency || "COP",
                });
              }}
            />
            <SelectField
              id="ads-edit-channel"
              label="Canal"
              value={doc.channel}
              disabled={isIntake && !!initial}
              options={
                account?.provider === "tiktok"
                  ? [{ value: "tiktok", label: "TikTok" }]
                  : [
                      { value: "facebook", label: "Facebook" },
                      { value: "instagram", label: "Instagram" },
                    ]
              }
              onChange={(e) => update({ channel: e.target.value })}
            />
          </>
        )}
        {tab === "campaigns" ? (
          <>
            {field(
              "external_campaign_id",
              "ID de campaña",
              160,
              "text",
              !!initial,
            )}
            {field("name", "Nombre de campaña")}
            {field("objective", "Objetivo", 120)}
            <SelectField
              id="ads-edit-campaign-status"
              label="Estado registrado"
              value={doc.status}
              options={[
                "unknown",
                "draft",
                "active",
                "paused",
                "completed",
                "archived",
              ].map((v) => ({ value: v, label: states[v] }))}
              onChange={(e) => update({ status: e.target.value })}
            />
            {field("currency", "Moneda", 3)}
            <Field
              id="ads-edit-daily"
              label="Presupuesto diario registrado"
              type="number"
              min="0"
              step="0.01"
              value={doc.daily_budget_cents / 100}
              onChange={(e) =>
                update({
                  daily_budget_cents: Math.round(Number(e.target.value) * 100),
                })
              }
            />
            <Field
              id="ads-edit-lifetime"
              label="Presupuesto total registrado"
              type="number"
              min="0"
              step="0.01"
              value={doc.lifetime_budget_cents / 100}
              onChange={(e) =>
                update({
                  lifetime_budget_cents: Math.round(
                    Number(e.target.value) * 100,
                  ),
                })
              }
            />
          </>
        ) : null}
        {isIntake ? (
          <>
            {field(
              "external_id",
              tab === "leads" ? "ID del lead" : "ID del comentario",
              180,
              "text",
              !!initial,
            )}
            {field(
              "contact_name",
              tab === "leads" ? "Nombre del contacto" : "Nombre del autor",
            )}
            {field("email", "Correo electrónico", 180, "email")}
            {field("phone", "Teléfono", 40)}
            {chooseProgram}
            <SelectField
              id="ads-edit-intake-status"
              label="Estado de captación"
              value={doc.status}
              options={(initial?.contact_id
                ? [
                    "new",
                    "review",
                    "qualified",
                    "converted",
                    "lost",
                    "resolved",
                    "ignored",
                    "hidden",
                    "deleted",
                  ]
                : [
                    "new",
                    "review",
                    "qualified",
                    "lost",
                    "resolved",
                    "ignored",
                    "hidden",
                    "deleted",
                  ]
              ).map((v) => ({ value: v, label: states[v] }))}
              onChange={(e) => update({ status: e.target.value })}
            />
            {tab === "comments" ? (
              <>
                {field("author_id", "ID del autor")}
                <TextArea
                  id="ads-edit-message"
                  label="Comentario"
                  value={doc.message}
                  maxLength={4000}
                  onChange={(e) => update({ message: e.target.value })}
                />
              </>
            ) : null}
          </>
        ) : null}
      </fieldset>
      {tab === "campaigns" && (
        <fieldset disabled={task.busy}>
          <legend>Indicadores registrados</legend>
          <label>
            <input
              type="checkbox"
              checked={!!doc.metrics_json}
              onChange={(e) =>
                update({
                  metrics_json: e.target.checked
                    ? { ctr: 0, cpc: 0, leads: 0 }
                    : null,
                  period_start: null,
                  period_end: null,
                })
              }
            />{" "}
            Registrar indicadores con período
          </label>
          {doc.metrics_json && (
            <div className="ads-fields">
              <Field
                id="ads-edit-period-start"
                label="Inicio del período"
                type="date"
                required
                value={doc.period_start || ""}
                onChange={(e) =>
                  update({ period_start: e.target.value || null })
                }
              />
              <Field
                id="ads-edit-period-end"
                label="Fin del período"
                type="date"
                required
                value={doc.period_end || ""}
                onChange={(e) => update({ period_end: e.target.value || null })}
              />
              {(
                [
                  ["ctr", "CTR (%)"],
                  ["cpc", "CPC"],
                  ["leads", "Leads registrados"],
                ] as const
              ).map(([key, label]) => (
                <Field
                  key={key}
                  id={`ads-edit-metric-${key}`}
                  label={label}
                  type="number"
                  min="0"
                  max={key === "ctr" ? 100 : 1000000000}
                  step={key === "leads" ? 1 : "0.01"}
                  value={doc.metrics_json![key]}
                  onChange={(e) =>
                    update({
                      metrics_json: {
                        ...doc.metrics_json!,
                        [key]: Number(e.target.value),
                      },
                    })
                  }
                />
              ))}
            </div>
          )}
          <small>
            Guardar estos valores no modifica anuncios ni presupuestos en el
            proveedor.
          </small>
        </fieldset>
      )}
      {isIntake && (
        <details>
          <summary>Referencia del anuncio y formulario</summary>
          <div className="ads-fields">
            {field("external_form_id", "ID del formulario")}
            {field("external_ad_id", "ID del anuncio")}
            {field("external_campaign_id", "ID de campaña", 160)}
            {field("external_post_id", "ID de publicación")}
            {field("external_parent_id", "ID del comentario padre")}
            {field("permalink_url", "Enlace de la publicación", 1000, "url")}
          </div>
        </details>
      )}
      {isIntake && !initial?.contact_id && (
        <label>
          <input
            type="checkbox"
            checked={convert}
            disabled={
              !session.actions.includes("crm.write") ||
              !session.actions.includes("inbox.write")
            }
            onChange={(e) => setConvert(e.target.checked)}
          />{" "}
          Crear ficha y conversación local en CRM
        </label>
      )}
      <div className="institution-actions">
        <Button
          type="submit"
          disabled={task.busy || (!doc.account_id && tab !== "accounts")}
        >
          Guardar registro
        </Button>
        {initial?.conversation_id && (
          <a href={`#/inbox/${initial.conversation_id}`}>Abrir conversación</a>
        )}
        {initial?.contact_id && (
          <a href={`#/clients/${initial.conversation_id}`}>Ver ficha CRM</a>
        )}
      </div>
      {isIntake && initial && !initial.contact_id && (
        <Button
          variant="secondary"
          disabled={
            task.busy ||
            !session.actions.includes("crm.write") ||
            !session.actions.includes("inbox.write")
          }
          onClick={() =>
            void task.run(async () => {
              await call(
                `ads/${tab}/${initial.id}/to-inbox`,
                "POST",
                command(
                  initial.revision,
                  intent,
                  `ads/${tab}/${initial.id}/to-inbox`,
                ),
              );
              await accept(await call<Item>(`ads/intakes/${initial.id}`));
            }, "Captación vinculada a CRM.")
          }
        >
          Vincular a Inbox
        </Button>
      )}
      {isIntake && (
        <small>
          La captación no concede consentimiento comercial ni habilita envíos al
          proveedor.
        </small>
      )}
      {tab === "accounts" && initial && (
        <details>
          <summary>Acceso e historial</summary>
          {session.actions.includes("settings.channels.write") && (
            <div>
              <p>
                {initial.has_access_token
                  ? "Credencial guardada; verificación externa pendiente."
                  : "Sin credencial publicitaria guardada."}
              </p>
              <Field
                id="ads-access-token"
                label="Token de acceso publicitario"
                type="password"
                autoComplete="new-password"
                value={token}
                maxLength={16000}
                onChange={(e) => setToken(e.target.value)}
              />
              <Button
                disabled={!token || task.busy}
                onClick={() =>
                  void task.run(async () => {
                    await call(
                      `ads/accounts/${initial.id}/credential`,
                      "POST",
                      command(
                        initial.revision,
                        intent,
                        `ads/accounts/${initial.id}/credential`,
                        { value: token },
                      ),
                    );
                    setToken("");
                    await accept({
                      ...initial,
                      has_access_token: true,
                      revision: initial.revision + 1,
                    });
                  }, "Credencial guardada de forma privada.")
                }
              >
                Guardar credencial
              </Button>
              <label>
                <input
                  type="checkbox"
                  checked={revoke}
                  onChange={(e) => setRevoke(e.target.checked)}
                />{" "}
                Retirar la credencial de esta cuenta
              </label>
              <Button
                variant="quiet"
                disabled={!revoke || task.busy}
                onClick={() =>
                  void task.run(async () => {
                    await call(
                      `ads/accounts/${initial.id}/credential`,
                      "POST",
                      command(
                        initial.revision,
                        intent,
                        `ads/accounts/${initial.id}/credential`,
                        { value: null },
                      ),
                    );
                    setRevoke(false);
                    await accept({
                      ...initial,
                      has_access_token: false,
                      revision: initial.revision + 1,
                    });
                  }, "Acceso publicitario retirado.")
                }
              >
                Retirar credencial
              </Button>
            </div>
          )}
          <Button
            variant="quiet"
            onClick={() =>
              void task.run(async () =>
                setHistory(await call(`ads/accounts/${initial.id}/history`)),
              )
            }
          >
            Ver historial de cuenta
          </Button>
          {history && (
            <ol>
              {history.items.map((v) => (
                <li key={v.id}>
                  {stamp(v.at)} · {v.kind.replaceAll("_", " ")}
                </li>
              ))}
            </ol>
          )}
          <a href="#/settings/channels">Revisar conexión y OAuth en Canales</a>
        </details>
      )}
    </form>
  );
}
