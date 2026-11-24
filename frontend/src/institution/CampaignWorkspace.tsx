import { useState } from "react";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import { ResourceState, useResource } from "./Settings";
import { allowNavigation, useDraftGuard } from "./drafts";
import { variableKeys } from "./BroadcastWorkspace";
import "./campaign.css";
import { CampaignAssetInput } from "./CampaignAssetInput";

type Kind = "campaign" | "flow" | "trigger" | "template" | "segment";
type Binding = { source: string; value?: string };
type Filters = {
  contact_ids?: string[];
  program_ids?: number[];
  stages?: string[];
  cities?: string[];
  tags?: string[];
  keywords?: string[];
};
type Step = {
  kind: "wait" | "condition" | "send";
  name?: string;
  wait_minutes?: number;
  conditions?: Filters;
  on_false?: string;
  crm_template_id?: string | null;
  crm_template_version?: number;
  meta_template_id?: string | null;
  meta_template_version?: number;
  variables?: Record<string, Binding>;
  variant_b_crm_template_id?: string | null;
  variant_b_crm_template_version?: number;
  variant_b_template_id?: string | null;
  variant_b_template_version?: number;
  variant_b_variables?: Record<string, Binding>;
  header_media_url?: string;
};
type Doc = {
  channel?: string;
  body?: string;
  variables?: Record<string, Binding>;
  category?: string;
  template_scope?: string;
  render_mode?: string;
  blocks?: {
    type: string;
    text: string;
    url: string;
    asset_id?: string | null;
    filename?: string;
    delay_ms?: number;
  }[];
  filters?: Filters;
  description?: string;
  integration_id?: string;
  objective?: string;
  followup_only?: boolean;
  segment_id?: string | null;
  segment_version?: number;
  crm_template_id?: string | null;
  crm_template_version?: number;
  entry_conditions?: Filters;
  scheduled_local?: string | null;
  timezone?: string;
  quiet_hours?: {
    enabled: boolean;
    timezone: string;
    start_time: string;
    end_time: string;
    days: number[];
  };
  exit_on_response?: boolean;
  cooldown_minutes?: number;
  steps?: Step[];
  ab_test?: { enabled: boolean; a_percent: number; label: string };
  event_type?: string;
  flow_id?: string;
  flow_version?: number;
  conditions?: Filters;
  priority?: number;
  idle_minutes?: number;
  stop_on_match?: boolean;
  only_when_no_takeover?: true;
};
type Record8 = {
  id: string;
  name: string;
  kind: Kind;
  state: string;
  revision: number;
  version: number;
  epoch: number;
  document: Doc;
};
type Meta = {
  id: string;
  version: number;
  integration_id: string;
  name: string;
  status: string;
  language: string;
  category: string;
  origin: string;
  paused: boolean;
  components: {
    type: string;
    text?: string;
    format?: string;
    buttons?: { type: string; text: string; url?: string }[];
  }[];
};
type Options = {
  accounts: {
    id: string;
    name: string;
    channel: string;
    verified_status: string;
  }[];
  templates: Meta[];
  stages: string[];
  programs: { program_id: number; name: string }[];
};
type Preview = {
  items?: {
    identity_id?: string;
    id?: string;
    name: string;
    eligible?: boolean;
    reasons?: string[];
  }[];
  total?: number;
  counts?: { matched: number; eligible: number; excluded: number };
  issues?: string[];
};
type Version = {
  version: number;
  name: string;
  reason: string;
  created_at: string;
};
type Run = {
  id: string;
  name: string;
  state: string;
  step_index: number;
  version: number;
  variant: string;
  due_at: string;
  reason?: string;
};
type Metrics = {
  variants: {
    variant: string;
    enrollments: number;
    attempts: number;
    accepted: number;
    delivered: number;
    read: number;
    failed: number;
    uncertain: number;
    replied: number;
    reply_percent: number | null;
  }[];
};
type Simulation = {
  text?: string;
  matches?: boolean;
  timeline?: { index: number; kind: string; at: string; text: string }[];
  variant?: string;
};
const names: Record<Kind, string> = {
  campaign: "Campañas CRM",
  flow: "Flujos",
  trigger: "Activadores",
  template: "Plantillas CRM",
  segment: "Segmentos",
};
const labels: Record<string, string> = {
  campaign_already_active: "El registro ya está activo",
  campaign_CRM_text_limit: "Reduce el texto de cada bloque del mensaje",
  campaign_tiktok_live_capability_required:
    "Revisa Business Messaging y habilita el modo live de TikTok en Canales",
  campaign_tiktok_daily_quota: "Se alcanzó el cupo diario de TikTok",
  skipped: "Omitido",
  enrolled: "Persona inscrita",
  step_prepared: "Mensaje preparado",
  step_completed: "Paso completado",
  execution_completed: "Seguimiento completado",
  native_chat: "Mensaje en cola",
  execution_stopped: "Seguimiento detenido",
  trigger_checked: "Activador evaluado",
  execution_reviewed: "Ejecución revisada",
  catalog_refreshed: "Catálogo actualizado",
  step_image: "Imagen lista",
  image_failed: "Imagen no disponible",
  step_blocked: "Paso pendiente de revisión",
  draft: "Borrador",
  active: "Activo",
  paused: "Pausado",
  archived: "Archivado",
  waiting: "En espera",
  queued: "Pendiente de envío",
  completed: "Completado",
  cancelled: "Cancelado",
  failed: "Fallido",
  uncertain: "Resultado incierto",
  campaign_response_received: "La persona respondió",
  campaign_stage_changed: "Cambió la etapa",
  campaign_program_changed: "Cambió el programa",
  campaign_handoff_changed: "Cambió la atención de la conversación",
  marketing_consent_required: "Sin consentimiento vigente",
  human_control: "Atención humana",
  conversation_closed: "Conversación cerrada",
  no_contact: "No contactar",
  genuine_incoming_required: "La persona aún no inició una conversación",
  campaign_cadence_required: "Configura el intervalo de envío de esta cuenta",
  verified_connected_account_required:
    "Verifica y conecta la cuenta en Canales",
  campaign_reference_changed: "Revisa la versión del segmento o plantilla",
  messaging_response_window_closed: "La ventana de respuesta del canal terminó",
  campaign_Meta_template_required: "Selecciona una plantilla Meta",
  wait: "Espera",
  condition: "Condición",
  send: "Mensaje",
  message_in: "Mensaje entrante",
  stage_changed: "Cambio de etapa",
  program_changed: "Cambio de programa",
  inactivity: "Sin respuesta a un mensaje confirmado",
};
const label = (v: string) => labels[v] || v.replaceAll("_", " ");
const emptyFilters = (): Filters => ({
  contact_ids: [],
  program_ids: [],
  stages: [],
  cities: [],
  tags: [],
  keywords: [],
});
const blank = (kind: Kind): Doc =>
  kind === "template"
    ? {
        channel: "whatsapp",
        body: "Hola {{nombre}}, te compartimos información de admisiones.",
        variables: { nombre: { source: "customer_first_name" } },
        category: "admisiones",
        template_scope: "crm",
        render_mode: "chat",
        blocks: [],
      }
    : kind === "segment"
      ? { description: "", filters: emptyFilters() }
      : kind === "trigger"
        ? {
            channel: "whatsapp",
            event_type: "message_in",
            flow_id: "",
            flow_version: 1,
            conditions: emptyFilters(),
            priority: 100,
            cooldown_minutes: 60,
            idle_minutes: 1440,
            stop_on_match: true,
            only_when_no_takeover: true,
          }
        : {
            channel: "whatsapp",
            integration_id: "",
            objective: "",
            description: "",
            segment_id: null,
            segment_version: 1,
            entry_conditions: emptyFilters(),
            scheduled_local: null,
            timezone: "America/Bogota",
            quiet_hours: {
              enabled: false,
              timezone: "America/Bogota",
              start_time: "21:00",
              end_time: "08:00",
              days: [0, 1, 2, 3, 4, 5, 6],
            },
            exit_on_response: true,
            steps: [{ kind: "wait", wait_minutes: 60, name: "Espera inicial" }],
            ab_test: { enabled: false, a_percent: 50, label: "Experimento" },
            cooldown_minutes: 1440,
          };
const sources = [
  { value: "literal", label: "Texto fijo" },
  { value: "customer_first_name", label: "Primer nombre" },
  { value: "customer_name", label: "Nombre completo" },
  { value: "customer_email", label: "Correo" },
  { value: "customer_city", label: "Ciudad" },
  { value: "customer_phone", label: "Teléfono" },
  { value: "program", label: "Programa" },
  { value: "stage", label: "Etapa" },
  { value: "schedule", label: "Jornada" },
  { value: "campaign_name", label: "Nombre de campaña" },
];

export function CampaignWorkspace() {
  const listing = useResource<{ items: Record8[] }>("campaigns"),
    options = useResource<Options>("campaigns/options");
  const [kind, setKind] = useState<Kind>("campaign"),
    [selected, setSelected] = useState<Record8 | null>(null),
    [creating, setCreating] = useState(false);
  if (!listing.value || !options.value)
    return <ResourceState error={listing.error || options.error} />;
  const choose = (item: Record8 | null) => {
    if (allowNavigation()) {
      setSelected(item);
      setCreating(!item);
    }
  };
  const saved = async (id: string) => {
    const next = await listing.reload();
    setSelected(next.items.find((v) => v.id === id) || null);
    setCreating(false);
  };
  return (
    <div className="campaign-workspace">
      <header>
        <h1>Campañas y remarketing</h1>
        <p>Organiza segmentos, mensajes y seguimientos por etapa y programa.</p>
      </header>
      <nav aria-label="Tipos de campañas" className="institution-actions">
        {(Object.keys(names) as Kind[]).map((k) => (
          <Button
            key={k}
            variant={kind === k ? "primary" : "quiet"}
            onClick={() => {
              if (allowNavigation()) {
                setKind(k);
                setSelected(null);
                setCreating(false);
              }
            }}
          >
            {names[k]}
          </Button>
        ))}
      </nav>
      <div className="campaign-layout">
        <aside className="panel">
          <Button onClick={() => choose(null)}>
            Crear{" "}
            {kind === "template"
              ? "plantilla"
              : kind === "segment"
                ? "segmento"
                : kind === "trigger"
                  ? "activador"
                  : kind === "flow"
                    ? "flujo"
                    : "campaña"}
          </Button>
          {listing.value.items.filter((v) => v.kind === kind).length === 0 && (
            <p>No hay registros de este tipo. Crea el primero.</p>
          )}
          {listing.value.items
            .filter((v) => v.kind === kind)
            .map((v) => (
              <Button
                key={v.id}
                variant={selected?.id === v.id ? "secondary" : "quiet"}
                onClick={() => choose(v)}
              >
                {v.name}
                <small>
                  {label(v.state)} · v{v.version}
                </small>
              </Button>
            ))}
        </aside>
        {creating || selected ? (
          <Editor
            key={
              selected ? `${selected.id}-${selected.revision}` : `new-${kind}`
            }
            initial={selected}
            kind={kind}
            records={listing.value.items}
            options={options.value}
            saved={saved}
          />
        ) : (
          <section className="panel">
            <h2>{names[kind]}</h2>
            <p>
              Selecciona un registro para revisar su contenido, historial y
              ejecución.
            </p>
            <p>
              Las plantillas CRM se utilizan en la ventana de respuesta del
              canal. WhatsApp también permite seleccionar una plantilla oficial
              de Meta aprobada. Cada envío requiere consentimiento y una cuenta
              verificada.
            </p>
            <a href="#/broadcasts">
              Configurar catálogo Meta, consentimiento e intervalo por cuenta
            </a>
          </section>
        )}
      </div>
    </div>
  );
}

function Bindings({
  keys,
  values,
  onChange,
  prefix,
}: {
  keys: string[];
  values: Record<string, Binding>;
  onChange: (v: Record<string, Binding>) => void;
  prefix: string;
}) {
  return (
    <>
      {keys.map((k, i) => (
        <div className="campaign-row" key={k}>
          <SelectField
            id={`${prefix}-source-${i}`}
            label={`Variable ${k}`}
            value={values[k]?.source || "literal"}
            options={sources}
            onChange={(e) =>
              onChange({
                ...values,
                [k]: { source: e.target.value, value: "" },
              })
            }
          />
          {(!values[k] || values[k].source === "literal") && (
            <Field
              id={`${prefix}-literal-${i}`}
              label={`Texto fijo de ${k}`}
              value={values[k]?.value || ""}
              required
              onChange={(e) =>
                onChange({
                  ...values,
                  [k]: { source: "literal", value: e.target.value },
                })
              }
            />
          )}
        </div>
      ))}
    </>
  );
}
function FilterEditor({
  value,
  onChange,
  prefix,
  options,
}: {
  value: Filters;
  onChange: (v: Filters) => void;
  prefix: string;
  options: Options;
}) {
  return (
    <fieldset>
      <legend>Condiciones de entrada</legend>
      <div className="campaign-row">
        <Field
          id={`${prefix}-stages`}
          label="Etapas (separadas por coma)"
          list={`${prefix}-stage-options`}
          value={(value.stages || []).join(", ")}
          onChange={(e) =>
            onChange({
              ...value,
              stages: e.target.value
                .split(",")
                .map((v) => v.trim())
                .filter(Boolean),
            })
          }
        />
        <div className="field">
          <label htmlFor={`${prefix}-programs`}>Programas de interés</label>
          <select
            id={`${prefix}-programs`}
            multiple
            value={(value.program_ids || []).map(String)}
            onChange={(e) =>
              onChange({
                ...value,
                program_ids: Array.from(e.currentTarget.selectedOptions, (v) =>
                  Number(v.value),
                ),
              })
            }
          >
            {options.programs.map((v) => (
              <option key={v.program_id} value={v.program_id}>
                {v.name}
              </option>
            ))}
          </select>
          <small>Sin selección: todos los programas declarados en CRM.</small>
        </div>
      </div>
      <datalist id={`${prefix}-stage-options`}>
        {options.stages.map((v) => (
          <option value={v} key={v} />
        ))}
      </datalist>
      {(
        [
          ["cities", "Ciudades"],
          ["tags", "Etiquetas"],
          ["keywords", "Palabras del último mensaje"],
        ] as const
      ).map(([k, title]) => (
        <Field
          key={k}
          id={`${prefix}-${k}`}
          label={`${title} (separadas por coma)`}
          value={(value[k] || []).join(", ")}
          onChange={(e) =>
            onChange({
              ...value,
              [k]: e.target.value
                .split(",")
                .map((v) => v.trim())
                .filter(Boolean),
            })
          }
        />
      ))}
    </fieldset>
  );
}

function Editor({
  initial,
  kind,
  records,
  options,
  saved,
}: {
  initial: Record8 | null;
  kind: Kind;
  records: Record8[];
  options: Options;
  saved: (id: string) => Promise<void>;
}) {
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [id] = useState(() => initial?.id || crypto.randomUUID()),
    [name, setName] = useState(initial?.name || ""),
    [doc, setDoc] = useState<Doc>(() => initial?.document || blank(kind)),
    [baseline, setBaseline] = useState(() =>
      JSON.stringify({
        name: initial?.name || "",
        doc: initial?.document || blank(kind),
      }),
    ),
    [reason, setReason] = useState(""),
    [review, setReview] = useState(false),
    [preflight, setPreflight] = useState<{
      id: string;
      valid: boolean;
      issues: string[];
    } | null>(null),
    [preview, setPreview] = useState<Preview | null>(null),
    [simulation, setSimulation] = useState<Simulation | null>(null),
    [variant, setVariant] = useState("A"),
    [identity, setIdentity] = useState(""),
    [chosen, setChosen] = useState<string[]>([]),
    [history, setHistory] = useState<Version[]>([]),
    [historyMore, setHistoryMore] = useState(false),
    [assetBusy, setAssetBusy] = useState(false);
  const dirty = JSON.stringify({ name, doc }) !== baseline;
  useDraftGuard(dirty || assetBusy);
  const flow = kind === "flow" || kind === "campaign",
    canSend = session.actions.includes("inbox.write");
  const update = (v: Partial<Doc>) => {
    const next = { ...doc, ...v };
    if (kind === "template" && ("body" in v || "blocks" in v)) {
      const text = [
        next.body || "",
        ...(next.blocks || []).map((b) => b.text),
      ].join("\n");
      const keys = [
        ...new Set(
          [
            ...text.matchAll(/\{\{\s*([A-Za-z_][A-Za-z0-9_]{0,40})\s*\}\}/g),
          ].map((m) => m[1]),
        ),
      ];
      next.variables = Object.fromEntries(
        keys.map((k) => [
          k,
          next.variables?.[k] ||
            doc.variables?.[k] || { source: "literal", value: "" },
        ]),
      );
    }
    setDoc(next);
    setPreflight(null);
    setReview(false);
    setPreview(null);
    setChosen([]);
  };
  const command = (extra: object = {}) => {
    const data = {
      revision: initial?.revision || 0,
      reason: reason.trim() || "Revisión de campaña institucional",
      ...extra,
    };
    return { ...data, operation_id: intent.get(data) };
  };
  const action = (action: string, extra: object = {}) =>
    void task.run(
      async () => {
        const value = await call<Record8>(
          `campaigns/${id}/${action}`,
          "POST",
          command({ confirmed: review, preflight_id: preflight?.id, ...extra }),
        );
        intent.clear();
        setBaseline(JSON.stringify({ name, doc }));
        await saved(action === "copy" ? value.id : id);
      },
      action === "enroll"
        ? "Inscripciones revisadas. Consulta las ejecuciones."
        : "Registro actualizado.",
    );
  const activeTemplates = records.filter(
      (v) => v.kind === "template" && v.document.channel === doc.channel,
    ),
    segments = records.filter((v) => v.kind === "segment"),
    flows = records.filter(
      (v) =>
        ["flow", "campaign"].includes(v.kind) &&
        v.document.channel === doc.channel,
    );
  return (
    <section className="panel campaign-editor">
      <h2>{initial?.name || `Nuevo registro: ${names[kind]}`}</h2>
      {initial && (
        <Badge>
          {label(initial.state)} · versión {initial.version} · revisión{" "}
          {initial.revision}
        </Badge>
      )}
      {task.notices}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void task.run(async () => {
            await call(
              `campaigns/${id}`,
              "PUT",
              command({ kind, name, document: doc }),
            );
            setBaseline(JSON.stringify({ name, doc }));
            intent.clear();
            await saved(id);
          }, "Borrador guardado. El guardado no activa envíos.");
        }}
      >
        <Field
          id="campaign8-name"
          label="Nombre"
          value={name}
          maxLength={160}
          required
          onChange={(e) => {
            setName(e.target.value);
            setPreflight(null);
            setReview(false);
          }}
        />
        {kind !== "segment" && (
          <SelectField
            id="campaign8-channel"
            label="Canal"
            value={doc.channel}
            options={["whatsapp", "instagram", "messenger", "tiktok"]}
            onChange={(e) =>
              update({
                channel: e.target.value,
                ...(flow
                  ? {
                      integration_id: "",
                      steps: [{ kind: "wait", wait_minutes: 60 }],
                    }
                  : {}),
              })
            }
          />
        )}
        {kind === "template" ? (
          <>
            <Notice>
              Plantilla CRM: requiere una conversación dentro de la ventana del
              canal. Este registro no representa aprobación de Meta.
            </Notice>
            <Field
              id="campaign8-category"
              label="Categoría"
              value={doc.category || ""}
              maxLength={80}
              onChange={(e) => update({ category: e.target.value })}
            />
            <TextArea
              id="campaign8-body"
              label="Mensaje"
              value={doc.body || ""}
              maxLength={8000}
              onChange={(e) => {
                const body = e.target.value;
                const keys = [
                  ...new Set(
                    [
                      ...body.matchAll(
                        /\{\{\s*([A-Za-z_][A-Za-z0-9_]{0,40})\s*\}\}/g,
                      ),
                    ].map((v) => v[1]),
                  ),
                ];
                update({
                  body,
                  variables: Object.fromEntries(
                    keys.map((k) => [
                      k,
                      doc.variables?.[k] || { source: "literal", value: "" },
                    ]),
                  ),
                });
              }}
            />
            <p className="campaign-hint">
              Usa variables como {"{{nombre}}"} y elige su origen.
            </p>
            <Bindings
              prefix="crm-template"
              keys={Object.keys(doc.variables || {})}
              values={doc.variables || {}}
              onChange={(variables) => update({ variables })}
            />
            <h3>Bloques de contenido</h3>
            <p>
              Los bloques se envían en orden. Los adjuntos se inspeccionan y se
              conservan de forma privada antes de enviarlos.
            </p>
            {(doc.blocks || []).map((b, i) => (
              <fieldset key={i} disabled={task.busy}>
                <legend>Bloque {i + 1}</legend>
                <SelectField
                  id={`block-${i}-kind`}
                  label="Tipo de bloque"
                  disabled={assetBusy}
                  value={b.type}
                  options={[
                    { value: "text", label: "Texto" },
                    { value: "heading", label: "Encabezado" },
                    { value: "button", label: "Enlace" },
                    { value: "image", label: "Imagen" },
                    { value: "audio", label: "Audio" },
                    { value: "video", label: "Video" },
                    { value: "document", label: "Documento" },
                  ]}
                  onChange={(e) =>
                    update({
                      blocks: doc.blocks?.map((v, n) =>
                        n === i
                          ? {
                              ...v,
                              type: e.target.value,
                              asset_id: null,
                              url: "",
                              text: e.target.value === "audio" ? "" : v.text,
                            }
                          : v,
                      ),
                    })
                  }
                />
                <Field
                  id={`block-${i}-text`}
                  label="Texto del bloque"
                  disabled={b.type === "audio"}
                  value={b.text}
                  maxLength={2000}
                  onChange={(e) =>
                    update({
                      blocks: doc.blocks?.map((v, n) =>
                        n === i ? { ...v, text: e.target.value } : v,
                      ),
                    })
                  }
                />
                {b.type === "document" && (
                  <Field
                    id={`block-${i}-filename`}
                    label="Nombre del documento"
                    value={b.filename || ""}
                    maxLength={160}
                    onChange={(e) =>
                      update({
                        blocks: doc.blocks?.map((v, n) =>
                          n === i ? { ...v, filename: e.target.value } : v,
                        ),
                      })
                    }
                  />
                )}
                <Field
                  id={`block-${i}-url`}
                  label="URL pública HTTPS"
                  value={b.url}
                  disabled={!!b.asset_id || assetBusy}
                  onChange={(e) =>
                    update({
                      blocks: doc.blocks?.map((v, n) =>
                        n === i ? { ...v, url: e.target.value } : v,
                      ),
                    })
                  }
                />
                {["image", "audio", "video", "document"].includes(b.type) && (
                  <CampaignAssetInput
                    key={`${b.type}-${b.asset_id || "none"}`}
                    id={`asset-${i}`}
                    kind={b.type}
                    assetId={b.asset_id}
                    filename={b.filename}
                    onBusy={setAssetBusy}
                    onChange={(asset_id, filename) => {
                      setDoc((current) => ({
                        ...current,
                        blocks: current.blocks?.map((v, n) =>
                          n === i ? { ...v, asset_id, filename, url: "" } : v,
                        ),
                      }));
                      setReview(false);
                      setPreflight(null);
                    }}
                  />
                )}
                {b.asset_id && (
                  <Button
                    variant="quiet"
                    onClick={() =>
                      update({
                        blocks: doc.blocks?.map((v, n) =>
                          n === i ? { ...v, asset_id: null, filename: "" } : v,
                        ),
                      })
                    }
                  >
                    Usar URL en lugar del adjunto
                  </Button>
                )}
                <Field
                  id={`block-${i}-delay`}
                  label="Espera antes de este bloque (segundos)"
                  type="number"
                  min={0}
                  max={300}
                  step={0.1}
                  value={(b.delay_ms || 0) / 1000}
                  onChange={(e) =>
                    update({
                      blocks: doc.blocks?.map((v, n) =>
                        n === i
                          ? {
                              ...v,
                              delay_ms: Math.round(
                                Number(e.target.value) * 1000,
                              ),
                            }
                          : v,
                      ),
                    })
                  }
                />
                <div className="institution-actions">
                  <Button
                    variant="quiet"
                    disabled={i === 0 || assetBusy}
                    onClick={() => {
                      const blocks = [...doc.blocks!];
                      [blocks[i - 1], blocks[i]] = [blocks[i], blocks[i - 1]];
                      update({ blocks });
                    }}
                  >
                    Subir bloque {i + 1}
                  </Button>
                  <Button
                    variant="quiet"
                    disabled={i === (doc.blocks?.length || 0) - 1 || assetBusy}
                    onClick={() => {
                      const blocks = [...doc.blocks!];
                      [blocks[i + 1], blocks[i]] = [blocks[i], blocks[i + 1]];
                      update({ blocks });
                    }}
                  >
                    Bajar bloque {i + 1}
                  </Button>
                </div>
                <Button
                  variant="quiet"
                  onClick={() =>
                    !assetBusy &&
                    update({ blocks: doc.blocks?.filter((_, n) => n !== i) })
                  }
                >
                  Quitar bloque {i + 1}
                </Button>
              </fieldset>
            ))}
            <Button
              variant="secondary"
              disabled={(doc.blocks?.length || 0) >= 20}
              onClick={() =>
                update({
                  blocks: [
                    ...(doc.blocks || []),
                    { type: "text", text: "", url: "" },
                  ],
                  render_mode: "builder",
                })
              }
            >
              Agregar bloque
            </Button>
          </>
        ) : kind === "segment" ? (
          <>
            <TextArea
              id="segment-description"
              label="Descripción"
              value={doc.description || ""}
              onChange={(e) => update({ description: e.target.value })}
            />
            <FilterEditor
              prefix="segment"
              value={doc.filters || {}}
              onChange={(filters) => update({ filters })}
              options={options}
            />
          </>
        ) : kind === "trigger" ? (
          <>
            <SelectField
              id="trigger-event"
              label="Evento"
              value={doc.event_type}
              options={[
                "message_in",
                "stage_changed",
                "program_changed",
                "inactivity",
              ].map((v) => ({ value: v, label: label(v) }))}
              onChange={(e) => update({ event_type: e.target.value })}
            />
            <SelectField
              id="trigger-flow"
              label="Flujo activo"
              value={doc.flow_id || ""}
              options={[
                { value: "", label: "Selecciona un flujo" },
                ...flows.map((v) => ({
                  value: v.id,
                  label: `${v.name} · v${v.version} · ${label(v.state)}`,
                })),
              ]}
              onChange={(e) => {
                const f = flows.find((v) => v.id === e.target.value);
                update({ flow_id: f?.id || "", flow_version: f?.version || 1 });
              }}
            />
            <Field
              id="trigger-priority"
              label="Prioridad (menor valor primero)"
              type="number"
              min={1}
              max={10000}
              value={doc.priority}
              onChange={(e) => update({ priority: Number(e.target.value) })}
            />
            <Field
              id="trigger-cooldown"
              label="Minutos entre inscripciones de una persona"
              type="number"
              min={0}
              max={43200}
              value={doc.cooldown_minutes}
              onChange={(e) =>
                update({ cooldown_minutes: Number(e.target.value) })
              }
            />
            {doc.event_type === "inactivity" && (
              <Field
                id="trigger-idle"
                label="Minutos sin respuesta desde envío confirmado"
                type="number"
                min={1}
                max={43200}
                value={doc.idle_minutes}
                onChange={(e) =>
                  update({ idle_minutes: Number(e.target.value) })
                }
              />
            )}
            <label>
              <input
                type="checkbox"
                checked={doc.stop_on_match}
                onChange={(e) => update({ stop_on_match: e.target.checked })}
              />{" "}
              Detener reglas de menor prioridad al coincidir
            </label>
            <FilterEditor
              prefix="trigger"
              value={doc.conditions || {}}
              onChange={(conditions) => update({ conditions })}
              options={options}
            />
          </>
        ) : (
          <>
            <SelectField
              id="flow-account"
              label="Cuenta de Canales"
              value={doc.integration_id || ""}
              options={[
                { value: "", label: "Selecciona una cuenta" },
                ...options.accounts
                  .filter((v) => v.channel === doc.channel)
                  .map((v) => ({
                    value: v.id,
                    label: `${v.name} · ${label(v.verified_status)}`,
                  })),
              ]}
              onChange={(e) => update({ integration_id: e.target.value })}
            />
            <TextArea
              id="flow-objective"
              label="Objetivo"
              value={doc.objective || ""}
              maxLength={1000}
              onChange={(e) => update({ objective: e.target.value })}
            />
            <label>
              <input type="checkbox" checked={doc.followup_only ?? false} onChange={(e) => update({ followup_only: e.target.checked, ...(e.target.checked ? {exit_on_response: true, quiet_hours: {...doc.quiet_hours!, enabled: true}} : {}) })} />
              Sólo seguimiento de personas que ya conversaron
            </label>
            {doc.followup_only && <Notice>Requiere una entrada real del contacto, modo IA, consentimiento vigente y horario de silencio activo. Una respuesta, baja o intervención humana detiene el flujo. Fuera de la ventana del canal se necesita una plantilla Meta aprobada para WhatsApp.</Notice>}
            <SelectField
              id="flow-segment"
              label="Segmento guardado"
              value={doc.segment_id || ""}
              options={[
                { value: "", label: "Sin segmento guardado" },
                ...segments.map((v) => ({
                  value: v.id,
                  label: `${v.name} · v${v.version} · ${label(v.state)}`,
                })),
              ]}
              onChange={(e) => {
                const s = segments.find((v) => v.id === e.target.value);
                update({
                  segment_id: s?.id || null,
                  segment_version: s?.version || 1,
                });
              }}
            />
            <FilterEditor
              prefix="flow"
              value={doc.entry_conditions || {}}
              onChange={(entry_conditions) => update({ entry_conditions })}
              options={options}
            />
            <div className="campaign-row">
              <Field
                id="flow-date"
                label="Inicio (hora local)"
                type="datetime-local"
                value={doc.scheduled_local || ""}
                onChange={(e) =>
                  update({ scheduled_local: e.target.value || null })
                }
              />
              <Field
                id="flow-timezone"
                label="Zona horaria IANA"
                value={doc.timezone}
                onChange={(e) => update({ timezone: e.target.value })}
              />
            </div>
            <fieldset>
              <legend>Horario de silencio</legend>
              <label>
                <input
                  type="checkbox"
                  checked={doc.quiet_hours?.enabled}
                  onChange={(e) =>
                    update({
                      quiet_hours: {
                        ...doc.quiet_hours!,
                        enabled: e.target.checked,
                      },
                    })
                  }
                />{" "}
                Esperar durante el horario de silencio
              </label>
              {doc.quiet_hours?.enabled && (
                <>
                  <div className="campaign-row">
                    <Field
                      id="quiet-start"
                      label="Desde"
                      type="time"
                      value={doc.quiet_hours.start_time}
                      onChange={(e) =>
                        update({
                          quiet_hours: {
                            ...doc.quiet_hours!,
                            start_time: e.target.value,
                          },
                        })
                      }
                    />
                    <Field
                      id="quiet-end"
                      label="Hasta"
                      type="time"
                      value={doc.quiet_hours.end_time}
                      onChange={(e) =>
                        update({
                          quiet_hours: {
                            ...doc.quiet_hours!,
                            end_time: e.target.value,
                          },
                        })
                      }
                    />
                  </div>
                  <Field
                    id="quiet-timezone"
                    label="Zona horaria del silencio"
                    value={doc.quiet_hours.timezone}
                    onChange={(e) =>
                      update({
                        quiet_hours: {
                          ...doc.quiet_hours!,
                          timezone: e.target.value,
                        },
                      })
                    }
                  />
                  <div className="institution-actions">
                    {["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"].map(
                      (v, i) => (
                        <label key={v}>
                          <input
                            type="checkbox"
                            checked={doc.quiet_hours!.days.includes(i)}
                            onChange={(e) =>
                              update({
                                quiet_hours: {
                                  ...doc.quiet_hours!,
                                  days: e.target.checked
                                    ? [...doc.quiet_hours!.days, i]
                                    : doc.quiet_hours!.days.filter(
                                        (n) => n !== i,
                                      ),
                                },
                              })
                            }
                          />
                          {v}
                        </label>
                      ),
                    )}
                  </div>
                </>
              )}
            </fieldset>
            <label>
              <input
                type="checkbox"
                checked={doc.exit_on_response}
                onChange={(e) => update({ exit_on_response: e.target.checked })}
              />{" "}
              Salir cuando la persona responda
            </label>
            <p className="campaign-hint">
              El cambio de etapa, programa, identidad o atención humana y la
              baja siempre detienen el seguimiento.
            </p>
            <Field
              id="flow-cooldown"
              label="Minutos antes de otra inscripción"
              type="number"
              min={0}
              max={43200}
              value={doc.cooldown_minutes}
              onChange={(e) =>
                update({ cooldown_minutes: Number(e.target.value) })
              }
            />
            <fieldset>
              <legend>Variantes A/B</legend>
              <label>
                <input
                  type="checkbox"
                  checked={doc.ab_test?.enabled}
                  onChange={(e) =>
                    update({
                      ab_test: { ...doc.ab_test!, enabled: e.target.checked },
                    })
                  }
                />{" "}
                Distribuir mensajes entre A y B
              </label>
              {doc.ab_test?.enabled && (
                <>
                  <Field
                    id="ab-label"
                    label="Nombre del experimento"
                    value={doc.ab_test.label}
                    maxLength={100}
                    onChange={(e) =>
                      update({
                        ab_test: { ...doc.ab_test!, label: e.target.value },
                      })
                    }
                  />
                  <Field
                    id="ab-percent"
                    label="Porcentaje de personas en A"
                    type="number"
                    min={1}
                    max={99}
                    value={doc.ab_test.a_percent}
                    onChange={(e) =>
                      update({
                        ab_test: {
                          ...doc.ab_test!,
                          a_percent: Number(e.target.value),
                        },
                      })
                    }
                  />
                  <p>
                    La asignación se conserva por persona y versión. No se elige
                    un ganador automáticamente.
                  </p>
                </>
              )}
            </fieldset>
            <h3>Pasos del flujo</h3>
            {(doc.steps || []).map((step, i) => (
              <StepEditor
                key={i}
                index={i}
                step={step}
                options={options}
                templates={activeTemplates}
                doc={doc}
                update={(value) =>
                  update({
                    steps: doc.steps?.map((v, n) => (n === i ? value : v)),
                  })
                }
                move={(delta) => {
                  const steps = [...doc.steps!];
                  [steps[i], steps[i + delta]] = [steps[i + delta], steps[i]];
                  update({ steps });
                }}
                remove={() =>
                  update({ steps: doc.steps?.filter((_, n) => n !== i) })
                }
              />
            ))}
            <Button
              variant="secondary"
              disabled={(doc.steps?.length || 0) >= 20}
              onClick={() =>
                update({
                  steps: [
                    ...(doc.steps || []),
                    { kind: "wait", wait_minutes: 60 },
                  ],
                })
              }
            >
              Agregar paso
            </Button>
          </>
        )}
        <TextArea
          id="campaign8-reason"
          label="Motivo de la revisión"
          value={reason}
          maxLength={1000}
          onChange={(e) => setReason(e.target.value)}
        />
        <div className="institution-actions">
          <Button type="submit" disabled={task.busy || assetBusy || assetBusy}>
            Guardar borrador
          </Button>
          {initial && (
            <span>
              Editar crea una versión y detiene las ejecuciones anteriores.
            </span>
          )}
        </div>
      </form>
      {initial && (
        <>
          <hr />
          <h3>Revisión y ejecución</h3>
          {dirty && (
            <Notice>
              Guarda los cambios antes de revisar, simular o activar.
            </Notice>
          )}
          <div className="institution-actions">
            <Button
              variant="secondary"
              disabled={dirty || task.busy || assetBusy}
              onClick={() =>
                void task.run(
                  async () =>
                    setPreview(await call<Preview>(`campaigns/${id}/preview`)),
                  "Audiencia consultada.",
                )
              }
            >
              Ver audiencia
            </Button>
            <Button
              variant="secondary"
              disabled={dirty || task.busy || assetBusy}
              onClick={() =>
                void task.run(async () => {
                  setPreflight(
                    await call(`campaigns/${id}/preflight`, "POST", command()),
                  );
                  intent.clear();
                }, "Comprobaciones actualizadas.")
              }
            >
              Comprobar configuración
            </Button>
            <Button
              variant="quiet"
              disabled={task.busy || assetBusy}
              onClick={() =>
                void task.run(async () => {
                  const page = await call<{
                    items: Version[];
                    has_more: boolean;
                  }>(`campaigns/${id}/versions`);
                  setHistory(page.items);
                  setHistoryMore(page.has_more);
                }, "Historial cargado.")
              }
            >
              Ver versiones
            </Button>
          </div>
          {preflight && (
            <Notice error={!preflight.valid}>
              {preflight.valid
                ? "Configuración revisada. Puedes activar después de confirmar."
                : preflight.issues.map(label).join(" · ")}
            </Notice>
          )}
          {preview && (
            <section>
              <h4>Audiencia</h4>
              <p>
                {preview.counts
                  ? `${preview.counts.eligible} elegibles · ${preview.counts.excluded} excluidos · ${preview.counts.matched} evaluados`
                  : `${preview.total || 0} contactos coinciden`}
              </p>
              {preview.issues?.map((v) => (
                <Notice key={v} error>
                  {label(v)}
                </Notice>
              ))}
              <p className="campaign-hint">
                Información declarada en CRM; la admisión académica requiere
                consultar SIIE.
              </p>
              {preview.items?.map((v, i) => (
                <label
                  className="campaign-audience"
                  key={v.identity_id || v.id || i}
                >
                  {v.identity_id && (
                    <input
                      type="checkbox"
                      disabled={!v.eligible}
                      checked={chosen.includes(v.identity_id)}
                      onChange={(e) =>
                        setChosen(
                          e.target.checked
                            ? [...chosen, v.identity_id!]
                            : chosen.filter((x) => x !== v.identity_id),
                        )
                      }
                    />
                  )}
                  <span>
                    {v.name}
                    <small>{v.reasons?.map(label).join(" · ")}</small>
                  </span>
                </label>
              ))}
            </section>
          )}
          <fieldset>
            <legend>Simulación sin envío</legend>
            <SelectField
              id="simulation-person"
              label="Persona para simular"
              value={identity}
              options={[
                { value: "", label: "Aspirante ficticio de ejemplo" },
                ...(preview?.items || [])
                  .filter((v) => v.identity_id)
                  .map((v) => ({ value: v.identity_id!, label: v.name })),
              ]}
              onChange={(e) => setIdentity(e.target.value)}
            />
            <SelectField
              id="simulation-variant"
              label="Variante"
              value={variant}
              options={["A", "B"]}
              onChange={(e) => setVariant(e.target.value)}
            />
            <Button
              variant="secondary"
              disabled={dirty || task.busy || assetBusy}
              onClick={() =>
                void task.run(async () => {
                  setSimulation(
                    await call<Simulation>(
                      `campaigns/${id}/simulate`,
                      "POST",
                      command({
                        identity_id: identity || null,
                        sample: { name: "Aspirante de ejemplo" },
                        variant,
                      }),
                    ),
                  );
                  intent.clear();
                }, "Simulación terminada; no se crearon envíos.")
              }
            >
              Simular
            </Button>
            {simulation && (
              <div className="campaign-simulation">
                {simulation.text && <p>{simulation.text}</p>}
                {simulation.matches !== undefined && (
                  <p>
                    {simulation.matches
                      ? "Cumple las condiciones"
                      : "No cumple las condiciones"}
                  </p>
                )}
                <ol>
                  {simulation.timeline?.map((v) => (
                    <li key={v.index}>
                      <strong>{label(v.kind)}</strong> ·{" "}
                      {new Date(v.at).toLocaleString()}
                      <p>{v.text}</p>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </fieldset>
          <label>
            <input
              type="checkbox"
              checked={review}
              onChange={(e) => setReview(e.target.checked)}
            />{" "}
            Revisé el contenido, las versiones y el alcance de esta acción
          </label>
          <div className="institution-actions">
            <Button
              disabled={
                dirty ||
                !review ||
                !preflight?.valid ||
                initial.state === "active" ||
                task.busy ||
                assetBusy ||
                ((flow || kind === "trigger") && !canSend)
              }
              onClick={() => action("activate")}
            >
              Activar
            </Button>
            <Button
              variant="secondary"
              disabled={dirty || !review || task.busy || assetBusy}
              onClick={() => action("pause")}
            >
              Pausar
            </Button>
            <Button
              variant="quiet"
              disabled={dirty || !review || task.busy || assetBusy}
              onClick={() => action("archive")}
            >
              Archivar
            </Button>
            <Button
              variant="quiet"
              disabled={dirty || !review || task.busy || assetBusy}
              onClick={() => action("copy")}
            >
              Duplicar como borrador
            </Button>
            {flow && (
              <Button
                disabled={
                  dirty ||
                  !review ||
                  !chosen.length ||
                  initial.state !== "active" ||
                  !canSend ||
                  task.busy ||
                  assetBusy
                }
                onClick={() => action("enroll", { identity_ids: chosen })}
              >
                Inscribir seleccionados ({chosen.length})
              </Button>
            )}
          </div>
          {!!history.length && (
            <section>
              <h3>Versiones guardadas</h3>
              {historyMore && (
                <Button
                  variant="quiet"
                  disabled={task.busy || assetBusy}
                  onClick={() =>
                    void task.run(async () => {
                      const page = await call<{
                        items: Version[];
                        has_more: boolean;
                      }>(`campaigns/${id}/versions?offset=${history.length}`);
                      setHistory([...history, ...page.items]);
                      setHistoryMore(page.has_more);
                    }, "Versiones anteriores cargadas.")
                  }
                >
                  Mostrar versiones anteriores
                </Button>
              )}
              {history.map((v) => (
                <div className="campaign-version" key={v.version}>
                  <span>
                    v{v.version} · {v.name}
                    <small>
                      {v.reason} · {new Date(v.created_at).toLocaleString()}
                    </small>
                  </span>
                  <Button
                    variant="quiet"
                    disabled={dirty || !review || task.busy || assetBusy}
                    onClick={() => action("restore", { version: v.version })}
                  >
                    Restaurar v{v.version} como borrador
                  </Button>
                </div>
              ))}
            </section>
          )}
          {flow && (
            <Executions
              key={`${id}-${initial.revision}`}
              id={id}
              revision={initial.revision}
              review={review}
              canSend={canSend}
              action={action}
            />
          )}
        </>
      )}
    </section>
  );
}

function StepEditor({
  step,
  index,
  doc,
  templates,
  options,
  update,
  move,
  remove,
}: {
  step: Step;
  index: number;
  doc: Doc;
  templates: Record8[];
  options: Options;
  update: (v: Step) => void;
  move: (n: number) => void;
  remove: () => void;
}) {
  const set = (v: Partial<Step>) => update({ ...step, ...v }),
    metas = options.templates.filter(
      (v) => v.integration_id === doc.integration_id,
    ),
    prefix = `step-${index}`;
  const selector = (b = false) => {
    const crmId = b ? step.variant_b_crm_template_id : step.crm_template_id,
      metaId = b ? step.variant_b_template_id : step.meta_template_id;
    const selected = crmId ? `crm:${crmId}` : metaId ? `meta:${metaId}` : "";
    const meta = metas.find((v) => v.id === metaId);
    return (
      <>
        <SelectField
          id={`${prefix}-${b ? "b" : "a"}`}
          label={`Plantilla ${b ? "B" : "A"}`}
          value={selected}
          options={[
            { value: "", label: "Selecciona una plantilla" },
            ...templates.map((v) => ({
              value: `crm:${v.id}`,
              label: `CRM · ${v.name} · v${v.version} · ${label(v.state)}`,
            })),
            ...(doc.channel === "whatsapp"
              ? metas.map((v) => ({
                  value: `meta:${v.id}`,
                  label: `Meta · ${v.name} · ${v.status}`,
                }))
              : []),
          ]}
          onChange={(e) => {
            const [scope, id] = e.target.value.split(":");
            const crm = templates.find((v) => v.id === id),
              m = metas.find((v) => v.id === id);
            set(
              b
                ? {
                    variant_b_crm_template_id: scope === "crm" ? id : null,
                    variant_b_crm_template_version: crm?.version || 1,
                    variant_b_template_id: scope === "meta" ? id : null,
                    variant_b_template_version: m?.version || 1,
                    variant_b_variables: {},
                  }
                : {
                    crm_template_id: scope === "crm" ? id : null,
                    crm_template_version: crm?.version || 1,
                    meta_template_id: scope === "meta" ? id : null,
                    meta_template_version: m?.version || 1,
                    variables: {},
                  },
            );
          }}
        />
        {meta && (
          <Bindings
            prefix={`${prefix}-${b ? "b" : "a"}`}
            keys={variableKeys(meta)}
            values={(b ? step.variant_b_variables : step.variables) || {}}
            onChange={(v) =>
              set(b ? { variant_b_variables: v } : { variables: v })
            }
          />
        )}
      </>
    );
  };
  return (
    <fieldset className="campaign-step">
      <legend>Paso {index + 1}</legend>
      <Field
        id={`${prefix}-name`}
        label="Nombre del paso"
        value={step.name || ""}
        maxLength={160}
        onChange={(e) => set({ name: e.target.value })}
      />
      <SelectField
        id={`${prefix}-kind`}
        label="Acción del paso"
        value={step.kind}
        options={["wait", "condition", "send"].map((v) => ({
          value: v,
          label: label(v),
        }))}
        onChange={(e) =>
          update({ kind: e.target.value as Step["kind"], wait_minutes: 60 })
        }
      />
      {step.kind === "wait" ? (
        <Field
          id={`${prefix}-wait`}
          label="Esperar minutos"
          type="number"
          min={0}
          max={43200}
          value={step.wait_minutes || 0}
          onChange={(e) => set({ wait_minutes: Number(e.target.value) })}
        />
      ) : step.kind === "condition" ? (
        <>
          <FilterEditor
            prefix={prefix}
            value={step.conditions || {}}
            onChange={(conditions) => set({ conditions })}
            options={options}
          />
          <SelectField
            id={`${prefix}-false`}
            label="Si no coincide"
            value={step.on_false || "stop"}
            options={[
              { value: "stop", label: "Detener seguimiento" },
              { value: "skip", label: "Continuar con el siguiente paso" },
            ]}
            onChange={(e) => set({ on_false: e.target.value })}
          />
        </>
      ) : (
        <>
          {selector()}
          {doc.ab_test?.enabled && selector(true)}
          {step.meta_template_id && (
            <Field
              id={`${prefix}-media`}
              label="URL pública HTTPS de cabecera multimedia, si la plantilla Meta la requiere"
              value={step.header_media_url || ""}
              onChange={(e) => set({ header_media_url: e.target.value })}
            />
          )}
        </>
      )}
      <div className="institution-actions">
        <Button variant="quiet" disabled={index === 0} onClick={() => move(-1)}>
          Subir paso {index + 1}
        </Button>
        <Button
          variant="quiet"
          disabled={index === (doc.steps?.length || 0) - 1}
          onClick={() => move(1)}
        >
          Bajar paso {index + 1}
        </Button>
        <Button
          variant="quiet"
          disabled={doc.steps?.length === 1}
          onClick={remove}
        >
          Quitar paso {index + 1}
        </Button>
      </div>
    </fieldset>
  );
}

function Executions({
  id,
  review,
  canSend,
  action,
}: {
  id: string;
  revision: number;
  review: boolean;
  canSend: boolean;
  action: (v: string, extra?: object) => void;
}) {
  const [offset, setOffset] = useState(0),
    [selected, setSelected] = useState<string[]>([]),
    [trace, setTrace] = useState<{
      events: { kind: string; at: string; data: unknown }[];
      steps: { index: number; kind: string; state: string; reason?: string }[];
    } | null>(null);
  const resource = useResource<{
      items: Run[];
      total: number;
      has_more: boolean;
    }>(`campaigns/${id}/runs?offset=${offset}`),
    metrics = useResource<Metrics>(`campaigns/${id}/metrics`),
    { call } = useInstitution(),
    task = useTask();
  if (!resource.value || !metrics.value)
    return <ResourceState error={resource.error || metrics.error} />;
  return (
    <section>
      <h3>Ejecuciones y resultados</h3>
      {task.notices}
      <Button
        variant="quiet"
        onClick={() =>
          void task.run(async () => {
            await resource.reload();
            await metrics.reload();
          }, "Resultados actualizados.")
        }
      >
        Actualizar resultados
      </Button>
      <div className="campaign-table">
        <table>
          <caption>
            Medición por variante, con todos los intentos registrados
          </caption>
          <thead>
            <tr>
              {[
                "Variante",
                "Personas",
                "Intentos",
                "Aceptados",
                "Entregados",
                "Leídos",
                "Respuestas atribuibles",
                "Fallidos",
                "Inciertos",
              ].map((v) => (
                <th key={v}>{v}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.value.variants.map((v) => (
              <tr key={v.variant}>
                <th>{v.variant}</th>
                <td>{v.enrollments}</td>
                <td>{v.attempts}</td>
                <td>{v.accepted}</td>
                <td>{v.delivered}</td>
                <td>{v.read}</td>
                <td>{v.replied}</td>
                <td>{v.failed}</td>
                <td>{v.uncertain}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="campaign-hint">
        Las respuestas sólo se atribuyen si el proveedor referencia el mensaje
        de la misma cuenta y persona. No se infieren matrículas ni conversiones.
      </p>
      {resource.value.items.length === 0 && (
        <p>
          No hay ejecuciones. Revisa la audiencia e inscribe personas, o activa
          una regla para futuros eventos.
        </p>
      )}
      {resource.value.items.map((v) => (
        <div className="campaign-run" key={v.id}>
          <label>
            <input
              type="checkbox"
              checked={selected.includes(v.id)}
              onChange={(e) =>
                setSelected(
                  e.target.checked
                    ? [...selected, v.id]
                    : selected.filter((x) => x !== v.id),
                )
              }
            />
            <span>
              {v.name} · {label(v.state)} · {v.variant}
              <small>
                Paso {v.step_index + 1} · v{v.version} ·{" "}
                {new Date(v.due_at).toLocaleString()} ·{" "}
                {v.reason ? label(v.reason) : ""}
              </small>
            </span>
          </label>
          <Button
            variant="quiet"
            onClick={() =>
              void task.run(
                async () =>
                  setTrace(await call(`campaigns/${id}/runs/${v.id}`)),
                "Detalle cargado.",
              )
            }
          >
            Ver detalle de {v.name}
          </Button>
        </div>
      ))}
      <div className="institution-actions">
        <Button
          variant="secondary"
          disabled={!review || !selected.length || !canSend}
          onClick={() => action("resume", { identity_ids: selected })}
        >
          Reanudar seleccionadas
        </Button>
        <Button
          variant="secondary"
          disabled={!review || !selected.length || !canSend}
          onClick={() => action("retry", { identity_ids: selected })}
        >
          Reintentar fallos definitivos
        </Button>
        <Button
          variant="quiet"
          disabled={!review || !selected.length}
          onClick={() => action("cancel_runs", { identity_ids: selected })}
        >
          Cancelar seleccionadas
        </Button>
      </div>
      <p>
        Los resultados inciertos permanecen bloqueados para evitar mensajes
        duplicados.
      </p>
      <div className="institution-actions">
        <Button
          variant="quiet"
          disabled={offset === 0}
          onClick={() => {
            setOffset(Math.max(0, offset - 100));
            setSelected([]);
          }}
        >
          Anterior
        </Button>
        <span>
          {resource.value.total} ejecuciones · página {offset / 100 + 1}
        </span>
        <Button
          variant="quiet"
          disabled={!resource.value.has_more}
          onClick={() => {
            setOffset(offset + 100);
            setSelected([]);
          }}
        >
          Siguiente
        </Button>
      </div>
      {trace && (
        <section>
          <h4>Detalle de la ejecución</h4>
          {trace.steps.map((v) => (
            <p key={v.index}>
              Paso {v.index + 1} · {label(v.kind)} · {label(v.state)}{" "}
              {v.reason ? label(v.reason) : ""}
            </p>
          ))}
          <ol>
            {trace.events.map((v, i) => (
              <li key={i}>
                {label(v.kind)} · {new Date(v.at).toLocaleString()}
                <p>
                  {Object.entries((v.data || {}) as Record<string, unknown>)
                    .filter(([k]) =>
                      [
                        "state",
                        "reason",
                        "variant",
                        "step_index",
                        "version",
                        "retry",
                        "part_index",
                        "attempt",
                      ].includes(k),
                    )
                    .map(
                      ([k, value]) =>
                        `${({ state: "Estado", reason: "Motivo", variant: "Variante", step_index: "Paso", version: "Versión", retry: "Reintento", part_index: "Bloque", attempt: "Intento" } as Record<string, string>)[k]}: ${typeof value === "string" ? label(value) : String(value)}`,
                    )
                    .join(" · ")}
                </p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </section>
  );
}
