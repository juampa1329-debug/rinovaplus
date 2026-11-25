import { useEffect, useRef, useState } from "react";
import { BroadcastAudience } from "./BroadcastAudience";
import { BroadcastProspectSetup } from "./BroadcastProspectSetup";
import { ReadableRecord } from "./ReadableRecord";
import {
  BroadcastCampaignList,
  campaignStateLabels,
} from "./BroadcastCampaignList";
import type {
  AudienceFilters,
  CrmField,
  DemographicFields,
} from "./BroadcastAudience";
import {
  BroadcastAnalytics,
  BroadcastAnalyticsSkeleton,
} from "./BroadcastAnalytics";
import type { CampaignAnalytics } from "./BroadcastAnalytics";
import { Icon } from "../shared/Icon";
import { OperationDialog } from "./ErrorFeedback";
import { explainInboxError } from "./InboxDelivery";
import {
  metaExamples,
  qualityLabel,
  rejectionReason,
  standardVariables,
  TemplateChatPreview,
  TemplateVariableFields,
  templateStatus,
} from "./BroadcastTemplateTools";
import type { CrmVariable, VariableBinding } from "./BroadcastTemplateTools";
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
import "./broadcast.css";
import {
  TemplateExampleGuide,
  TemplateSamplePicker,
} from "./BroadcastTemplateMedia";

type Component = {
  type: string;
  text?: string;
  format?: string;
  buttons?: { type: string; text: string; url?: string }[];
};
type Template = {
  id: string;
  version: number;
  integration_id: string;
  name: string;
  language: string;
  category: string;
  status: string;
  origin: string;
  paused: boolean;
  components: Component[];
  metadata?: {
    library_removed?: boolean;
    quality_score?: string;
    rejection_reason?: string;
    variable_bindings?: Record<string, VariableBinding>;
  };
};
type Binding = VariableBinding;
type Document = {
  name: string;
  integration_id: string;
  template_id: string;
  template_version: number;
  filters: AudienceFilters;
  demographic_fields?: DemographicFields;
  variables: Record<string, Binding>;
  header_media_url: string;
  header_media_id?: string;
  header_media_operation?: string | null;
  scheduled_local: string | null;
  timezone: string;
  sent_stage?: string;
};
type Campaign = {
  id: string;
  name: string;
  state: string;
  revision: number;
  epoch: number;
  document: Document;
  scheduled_at?: string | null;
  timezone?: string;
};
type Options = {
  accounts: { id: string; name: string; verified_status: string }[];
  templates: Template[];
  programs: { program_id: number; name: string }[];
  stages: string[];
  outbound_enabled: boolean;
  variables?: CrmVariable[];
  crm_fields?: CrmField[];
  tags?: string[];
  audience_facets?: {
    schedules: string[];
    contact_types: string[];
    cities: string[];
  };
};
type Preview = {
  counts: { matched: number; eligible: number; excluded: number };
  exclusions: Record<string, number>;
  items: {
    identity_id: string;
    name: string;
    text: string;
    eligible: boolean;
    reasons: string[];
  }[];
};
type Report = {
  analytics?: CampaignAnalytics | null;
  metrics?: {
    replied: number;
    delivered_percent: number | null;
    read_percent: number | null;
    reply_percent: number | null;
  };
  counts: Record<string, number>;
  total: number;
  offset: number;
  has_more: boolean;
  items: {
    id: string;
    name: string;
    phone: string;
    status: string;
    attempts: number;
    error: string | null;
    provider_message_id: string | null;
    body?: string;
    prepared_at?: string;
    queued_at?: string;
    accepted_at?: string;
    sent_at?: string;
    delivered_at?: string;
    read_at?: string;
    replied_at?: string;
    failed_at?: string;
    profile?: Record<string, string>;
    template_parts?: { header: string; footer: string; buttons: string[] };
    contact?: {
      stage: string;
      program: string;
      requested_program: string;
      requested_at: string;
      request_channel: string;
      source: string;
      sent_stage: string;
    };
  }[];
};
const stateLabel: Record<string, string> = {
  ...campaignStateLabels,
  prepared: "Preparado",
  queued: "Pendiente",
  sending: "En curso de envío",
  replied: "Respondido con referencia al mensaje",
  accepted: "Aceptado por Meta",
  sent: "Enviado",
  delivered: "Entregado",
  read: "Leído",
  failed: "Fallido",
  uncertain: "Resultado incierto",
  blocked: "Bloqueado",
};
const reasonLabel: Record<string, string> = {
  commercial_progress_requires_case_followup: "Ya avanzó: requiere seguimiento de su caso, sin reactivación general",
  advanced_stage_no_reactivation: "Etapa avanzada: no corresponde reactivación general",
  broadcast_template_still_in_campaign:
    "Cambia la plantilla de las campañas que todavía la usan antes de eliminarla de la biblioteca.",
  broadcast_template_removed_from_library:
    "La plantilla está en la papelera. Restáurala antes de usarla.",
  human_control: "Atención humana",
  canonical_contact_prior_effect:
    "Esta persona ya tiene un envío aceptado o pendiente de conciliación",
  broadcast_cadence_wait: "Esperando el intervalo entre envíos",
  marketing_consent_required: "Sin consentimiento vigente",
  broadcast_variable_value_missing:
    "Faltan datos en la ficha para completar la plantilla",
  broadcast_crm_field_unavailable: "Un campo CRM de la plantilla está inactivo",
  broadcast_segment_field_unavailable: "Un campo de segmentación está inactivo",
  broadcast_variable_required:
    "Asigna los campos del CRM a las variables de la plantilla",
  no_contact: "No contactar",
  conversation_closed: "Conversación cerrada",
  duplicate_contact: "Contacto duplicado",
  broadcast_provider_approved_template_required:
    "La plantilla requiere aprobación de Meta",
  broadcast_template_refresh_required: "Sincroniza el catálogo de plantillas",
  broadcast_verified_whatsapp_account_required: "Cuenta sin verificar",
  broadcast_template_changed_review_required:
    "La plantilla cambió; revisa la campaña",
};
const label = (value: string) =>
  stateLabel[value] || reasonLabel[value] || value.replaceAll("_", " ");
const profileLabels: Record<string, string> = {
  gender: "Género",
  age_band: "Edad al preparar",
  city: "Ciudad",
  region: "Departamento o región",
  country: "País",
  program: "Programa",
  schedule: "Jornada",
  contact_type: "Tipo de contacto",
  stage: "Estado CRM",
  last_incoming: "Último mensaje recibido al preparar",
};
const sources = [
  "literal",
  "customer_name",
  "customer_first_name",
  "customer_email",
  "customer_city",
  "customer_phone",
  "program",
  "stage",
  "schedule",
  "campaign_name",
];
const sourceLabels = [
  "Texto fijo",
  "Nombre completo",
  "Primer nombre",
  "Correo",
  "Ciudad",
  "Teléfono",
  "Programa",
  "Etapa",
  "Jornada",
  "Nombre de campaña",
];
export function variableKeys(template?: Template) {
  const keys = new Set<string>();
  for (const c of template?.components || []) {
    if (["BODY", "HEADER"].includes(c.type))
      for (const match of (c.text || "").matchAll(/\{\{\s*(\d+)\s*\}\}/g))
        keys.add(`${c.type.toLowerCase()}.${match[1]}`);
    if (c.type === "BUTTONS")
      c.buttons?.forEach((b, i) => {
        for (const match of (b.url || "").matchAll(/\{\{\s*(\d+)\s*\}\}/g))
          keys.add(`button.${i}.${match[1]}`);
      });
  }
  return [...keys];
}
const blank = (): Document => ({
  name: "",
  integration_id: "",
  template_id: "",
  template_version: 1,
  filters: {
    contact_ids: [],
    program_ids: [],
    stages: [],
    cities: [],
    tags: [],
  },
  variables: {},
  header_media_url: "",
  scheduled_local: null,
  timezone:
    Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Bogota",
});

export function BroadcastWorkspace() {
  const selectionVersion = useRef(0);
  const [visibleSelectionVersion, setVisibleSelectionVersion] = useState(0);
  const options = useResource<Options>("broadcasts/options"),
    listing = useResource<{ items: Campaign[] }>("broadcasts");
  const [tab, setTab] = useState("campaigns"),
    [chosen, setChosen] = useState<Campaign | null>(null),
    [creating, setCreating] = useState(false),
    [listVisible, setListVisible] = useState(true),
    [account, setAccount] = useState("");
  if (!options.value || !listing.value)
    return <ResourceState error={options.error || listing.error} />;
  const reload = async () => {
    await options.reload();
    await listing.reload();
  };
  return (
    <div className="broadcast-workspace">
      <nav className="institution-tabs" aria-label="Mensajería masiva">
        <Button
          variant={tab === "campaigns" ? "primary" : "quiet"}
          onClick={() => {
            if (allowNavigation()) setTab("campaigns");
          }}
        >
          Campañas de envío
        </Button>
        <Button
          variant={tab === "templates" ? "primary" : "quiet"}
          onClick={() => {
            if (allowNavigation()) setTab("templates");
          }}
        >
          Plantillas WhatsApp
        </Button>
        <Button
          variant={tab === "consent" ? "primary" : "quiet"}
          onClick={() => {
            if (allowNavigation()) setTab("consent");
          }}
        >
          Consentimiento y cadencia
        </Button>
      </nav>
      {!options.value.outbound_enabled && (
        <Notice>
          Los envíos están deshabilitados. Puedes preparar campañas; un
          administrador debe habilitar la salida en Canales antes de enviarlas.
        </Notice>
      )}
      {tab !== "campaigns" && (
        <SelectField
          id="bulk-account"
          label="Cuenta WhatsApp"
          value={account}
          options={[
            { value: "", label: "Selecciona una cuenta" },
            ...options.value.accounts.map((a) => ({
              value: a.id,
              label: `${a.name} · ${a.verified_status === "verified" ? "Verificada" : "Pendiente de verificar"}`,
            })),
          ]}
          onChange={(e) => {
            if (allowNavigation()) setAccount(e.target.value);
          }}
        />
      )}
      {tab === "campaigns" ? (
        <>
          <header className="broadcast-campaign-toolbar">
            <h2>Campañas de envío</h2>
            <div className="actions">
              <Button
                variant="quiet"
                aria-expanded={listVisible}
                aria-controls="broadcast-campaign-list"
                onClick={() => setListVisible(!listVisible)}
              >
                {listVisible
                  ? "Ocultar listado"
                  : `Mostrar campañas (${listing.value.items.length})`}
              </Button>
              <Button
                onClick={() => {
                  if (allowNavigation()) {
                    selectionVersion.current += 1;
                    setVisibleSelectionVersion(selectionVersion.current);
                    setCreating(true);
                    setChosen(null);
                  }
                }}
              >
                Nueva campaña
              </Button>
            </div>
          </header>
          <div
            className={`broadcast-columns broadcast-campaign-columns${listVisible ? "" : " broadcast-list-hidden"}`}
          >
            <BroadcastCampaignList
              items={listing.value.items}
              selectedId={chosen?.id}
              hidden={!listVisible}
              onSelect={(c) => {
                if (allowNavigation()) {
                  selectionVersion.current += 1;
                  setVisibleSelectionVersion(selectionVersion.current);
                  setCreating(false);
                  setChosen(c);
                }
              }}
            />
            {creating || chosen ? (
              <CampaignEditor
                key={chosen ? `${chosen.id}-${chosen.revision}` : "new"}
                initial={chosen}
                options={options.value}
                refreshOptions={async () => {
                  await options.reload();
                }}
                saved={async (id) => {
                  await reload();
                  const latest = await listing.reload();
                  if (selectionVersion.current !== visibleSelectionVersion)
                    return;
                  setChosen(latest.items.find((c) => c.id === id) || null);
                  setCreating(false);
                }}
              />
            ) : (
              <section className="panel">
                <h2>Mensajes con plantilla</h2>
                <p>
                  Elige una campaña para revisar destinatarios, programar el
                  envío y consultar resultados.
                </p>
                <p>
                  Cada cuenta utiliza su catálogo de Meta y su consentimiento
                  registrado. Los programas y etapas proceden del CRM
                  institucional.
                </p>
              </section>
            )}
          </div>
        </>
      ) : !account ? (
        <Notice>
          Selecciona una cuenta de Canales o{" "}
          <a href="#/channels">agrega una cuenta WhatsApp</a>.
        </Notice>
      ) : tab === "templates" ? (
        <TemplatePanel
          key={account}
          account={account}
          variables={options.value.variables || standardVariables}
          templates={options.value.templates.filter(
            (t) => t.integration_id === account,
          )}
          reload={reload}
        />
      ) : (
        <ConsentPanel key={account} account={account} />
      )}
    </div>
  );
}

function CampaignEditor({
  initial,
  options,
  saved,
  refreshOptions,
}: {
  initial: Campaign | null;
  options: Options;
  saved: (id: string) => Promise<void>;
  refreshOptions: () => Promise<void>;
}) {
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [key] = useState(() => initial?.id || crypto.randomUUID()),
    [doc, setDoc] = useState<Document>(() => initial?.document || blank()),
    [baseline, setBaseline] = useState(() =>
      JSON.stringify(initial?.document || blank()),
    ),
    [preview, setPreview] = useState<Preview | null>(null),
    [reviewed, setReviewed] = useState(false),
    [reason, setReason] = useState(""),
    [showTemplateTools, setShowTemplateTools] = useState(false),
    [templateToolsOpened, setTemplateToolsOpened] = useState(false),
    [showResults, setShowResults] = useState(initial?.state === "completed"),
    [scheduleEnabled, setScheduleEnabled] = useState(
      !!initial?.document.scheduled_local,
    );
  const dirty = JSON.stringify(doc) !== baseline;
  useDraftGuard(dirty);
  const template = options.templates.find((t) => t.id === doc.template_id),
    editable =
      !initial ||
      !["running", "scheduled", "cancelled", "completed"].includes(
        initial.state,
      );
  const update = (changes: Partial<Document>) => {
    setDoc((current) => ({ ...current, ...changes }));
    setReviewed(false);
    setPreview(null);
  };
  const command = (extra = {}) => {
    const body = {
      revision: initial?.revision || 0,
      reason: reason.trim() || "Revisión de campaña institucional",
      ...extra,
    };
    return { ...body, operation_id: intent.get(body) };
  };
  const action = (name: string, ids?: string[]) =>
    void task.run(
      async () => {
        await call(
          `broadcasts/${key}/${name}`,
          "POST",
          command({ confirmed: reviewed, recipient_ids: ids || [] }),
        );
        intent.clear();
        await saved(key);
      },
      name === "prepare"
        ? "Destinatarios preparados. Aún no se han enviado mensajes."
        : "Estado de la campaña actualizado.",
    );
  return (
    <section className="panel">
      <h2>{initial ? initial.name : "Nueva campaña"}</h2>
      {task.notices}
      {initial && (
        <Badge>
          {label(initial.state)} · versión {initial.revision}
        </Badge>
      )}
      {initial && (
        <nav className="institution-actions" aria-label="Vista de campaña">
          <Button
            variant={showResults ? "quiet" : "secondary"}
            onClick={() => setShowResults(false)}
          >
            Configuración de campaña
          </Button>
          <Button
            variant={showResults ? "secondary" : "quiet"}
            onClick={() => setShowResults(true)}
          >
            <Icon name="chart" />
            Ver resultados y gráficos
          </Button>
        </nav>
      )}
      <form
        hidden={showResults}
        onSubmit={(e) => {
          e.preventDefault();
          void task.run(async () => {
            await call(`broadcasts/${key}`, "PUT", command(doc));
            setBaseline(JSON.stringify(doc));
            intent.clear();
            await saved(key);
          });
        }}
      >
        <fieldset disabled={task.busy || !editable}>
          <Field
            id="bulk-name"
            label="Nombre de campaña"
            required
            maxLength={160}
            value={doc.name}
            onChange={(e) => update({ name: e.target.value })}
          />
          <SelectField
            id="campaign-account"
            label="Cuenta de envío"
            required
            value={doc.integration_id}
            options={[
              { value: "", label: "Selecciona una cuenta WhatsApp" },
              ...options.accounts.map((a) => ({
                value: a.id,
                label: a.name,
              })),
            ]}
            onChange={(e) =>
              update({
                integration_id: e.target.value,
                template_id: "",
                variables: {},
                header_media_url: "",
                header_media_id: "",
                header_media_operation: null,
                filters: { ...doc.filters, contact_ids: [] },
              })
            }
          />
          <SelectField
            id="campaign-template"
            label="Plantilla e idioma"
            required
            value={doc.template_id}
            options={[
              { value: "", label: "Selecciona una plantilla" },
              ...options.templates
                .filter(
                  (t) =>
                    t.integration_id === doc.integration_id &&
                    !t.metadata?.library_removed &&
                    (!t.paused || t.id === doc.template_id),
                )
                .map((t) => ({
                  value: t.id,
                  label: `${t.name} · ${t.language} · ${templateStatus(t.status)}${t.paused ? " · Pausada" : ""}`,
                })),
            ]}
            onChange={(e) => {
              const t = options.templates.find((t) => t.id === e.target.value);
              update({
                template_id: e.target.value,
                template_version: t?.version || 1,
                header_media_url: "",
                header_media_id: "",
                header_media_operation: null,
                variables: Object.fromEntries(
                  variableKeys(t).map((k) => [
                    k,
                    t?.metadata?.variable_bindings?.[k] || {
                      source: "literal",
                      value: "",
                    },
                  ]),
                ),
              });
            }}
          />
          <Button
            variant="secondary"
            disabled={!doc.integration_id}
            aria-expanded={showTemplateTools}
            onClick={() => {
              setTemplateToolsOpened(true);
              setShowTemplateTools(!showTemplateTools);
            }}
          >
            Crear o gestionar plantillas de esta campaña
          </Button>
          <p className="broadcast-help">
            Crea la plantilla sin salir de la campaña. Podrás seleccionarla
            cuando Meta la apruebe; el borrador de campaña se conserva.
          </p>
          {template && (
            <div className="broadcast-message">
              {template.components
                .filter((c) => c.text)
                .map((c, i) => (
                  <p key={i}>{c.text}</p>
                ))}
              {template.components
                .flatMap((c) => c.buttons || [])
                .map((b, i) => (
                  <Badge key={i}>{b.text}</Badge>
                ))}
            </div>
          )}
          {template && template.version !== doc.template_version && (
            <Button
              variant="secondary"
              disabled={!editable}
              onClick={() =>
                update({
                  template_version: template.version,
                  variables: Object.fromEntries(
                    variableKeys(template).map((k) => [
                      k,
                      doc.variables[k] || { source: "literal", value: "" },
                    ]),
                  ),
                })
              }
            >
              Revisar versión actual de la plantilla
            </Button>
          )}
          {variableKeys(template).map((k) => (
            <div className="broadcast-binding" key={k}>
              <SelectField
                id={`variable-${k}`}
                label={`Variable ${k}`}
                value={
                  doc.variables[k]?.source === "custom_field"
                    ? `crm.${doc.variables[k]?.field_key}`
                    : doc.variables[k]?.source || "literal"
                }
                options={[
                  ...sources.map((s, i) => ({
                    value: s,
                    label: sourceLabels[i],
                  })),
                  ...(options.variables || [])
                    .filter((v) => v.source === "custom_field")
                    .map((v) => ({
                      value: v.token,
                      label: `Campo CRM · ${v.label}`,
                    })),
                ]}
                onChange={(e) =>
                  update({
                    variables: {
                      ...doc.variables,
                      [k]: e.target.value.startsWith("crm.")
                        ? {
                            source: "custom_field",
                            field_key: e.target.value.slice(4),
                          }
                        : { source: e.target.value, value: "" },
                    },
                  })
                }
              />
              {(!doc.variables[k] || doc.variables[k].source === "literal") && (
                <Field
                  id={`value-${k}`}
                  label={`Texto de ${k}`}
                  required
                  maxLength={1000}
                  value={doc.variables[k]?.value || ""}
                  onChange={(e) =>
                    update({
                      variables: {
                        ...doc.variables,
                        [k]: { source: "literal", value: e.target.value },
                      },
                    })
                  }
                />
              )}
            </div>
          ))}
          {template?.components.some(
            (c) =>
              c.type === "HEADER" &&
              ["IMAGE", "VIDEO", "DOCUMENT"].includes(c.format || ""),
          ) && (
            <section aria-label="Adjunto de la campaña">
              <TemplateSamplePicker
                key={`${doc.integration_id}-${doc.template_id}`}
                account={doc.integration_id}
                kind={
                  template.components.find((c) => c.type === "HEADER")
                    ?.format || "IMAGE"
                }
                purpose="delivery"
                onUploaded={() =>
                  update({ header_media_id: "", header_media_operation: null })
                }
                onDelivery={(id, operation) =>
                  update({
                    header_media_id: id,
                    header_media_operation: operation,
                    header_media_url: "",
                  })
                }
              />
              {doc.header_media_id && (
                <Notice>
                  Archivo de la campaña cargado y vinculado a esta cuenta de
                  WhatsApp.
                </Notice>
              )}
              <details>
                <summary>Usar una URL HTTPS en lugar de un archivo</summary>
                <Field
                  id="header-media"
                  label="URL HTTPS del archivo de cabecera"
                  type="url"
                  required={!doc.header_media_id}
                  value={doc.header_media_url}
                  onChange={(e) =>
                    update({
                      header_media_url: e.target.value,
                      header_media_id: "",
                      header_media_operation: null,
                    })
                  }
                />
              </details>
            </section>
          )}
          <BroadcastAudience
            account={doc.integration_id}
            filters={doc.filters}
            mapping={doc.demographic_fields || {}}
            fields={options.crm_fields || []}
            programs={options.programs}
            stages={options.stages}
            tags={options.tags || []}
            facets={options.audience_facets}
            change={(filters, demographic_fields) =>
              update({ filters, demographic_fields })
            }
          />
          <SelectField
            id="campaign-delivery-mode"
            label="Cuándo enviar"
            value={scheduleEnabled ? "scheduled" : "now"}
            options={[
              { value: "now", label: "Al activar la campaña" },
              { value: "scheduled", label: "Programar fecha y hora local" },
            ]}
            onChange={(e) => {
              setScheduleEnabled(e.target.value === "scheduled");
              if (e.target.value === "now") update({ scheduled_local: null });
            }}
          />
          <SelectField
            id="campaign-sent-stage"
            label="Etapa tras envío confirmado"
            value={doc.sent_stage || ""}
            disabled={!session.actions.includes("crm.write")}
            options={[
              { value: "", label: "Conservar la etapa actual" },
              ...options.stages.map(value => ({ value, label: value })),
            ]}
            onChange={e => update({ sent_stage: e.target.value })}
          />
          <p>Se aplica cuando Meta confirma enviado, entregado o leído.
            Si un asesor cambió la etapa después de preparar, se conserva su cambio.</p>
          <div className="broadcast-binding">
            <Field
              id="bulk-schedule"
              label="Fecha y hora local (opcional)"
              type="datetime-local"
              required={scheduleEnabled}
              disabled={!scheduleEnabled}
              value={doc.scheduled_local || ""}
              onChange={(e) =>
                update({ scheduled_local: e.target.value || null })
              }
            />
            <Field
              id="bulk-timezone"
              label="Zona horaria IANA"
              required
              value={doc.timezone}
              onChange={(e) => update({ timezone: e.target.value })}
            />
          </div>
          <p className="broadcast-schedule-summary">
            {scheduleEnabled
              ? `Se enviará desde ${doc.scheduled_local?.replace("T", " ") || "la fecha que selecciones"}, zona ${doc.timezone}. Debes guardar y activar la campaña.`
              : "Guardar sólo crea un borrador. El envío empieza cuando revises los destinatarios y actives la campaña."}
            {initial?.scheduled_at &&
              !dirty &&
              ` Fecha confirmada: ${new Date(initial.scheduled_at).toLocaleString("es-CO", { timeZone: initial.timezone || doc.timezone })} (${initial.timezone || doc.timezone}).`}
          </p>
          <Button
            type="submit"
            disabled={
              (doc.filters.audience_mode === "contacts" &&
                !doc.filters.contact_ids.length) ||
              (!!template?.components.some(
                (c) =>
                  c.type === "HEADER" &&
                  ["IMAGE", "VIDEO", "DOCUMENT"].includes(c.format || ""),
              ) &&
                !doc.header_media_id &&
                !doc.header_media_url)
            }
          >
            Guardar campaña
          </Button>
        </fieldset>
      </form>
      {templateToolsOpened && doc.integration_id && (
        <div hidden={showResults || !showTemplateTools}>
          <TemplatePanel
            key={doc.integration_id}
            account={doc.integration_id}
            templates={options.templates.filter(
              (t) => t.integration_id === doc.integration_id,
            )}
            variables={options.variables || standardVariables}
            reload={refreshOptions}
            initiallyCreating
          />
        </div>
      )}
      {initial && (
        <div hidden={showResults}>
          <Field
            id="campaign-reason"
            label="Motivo de la operación"
            value={reason}
            maxLength={1000}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="institution-actions">
            <Button
              variant="secondary"
              disabled={dirty || task.busy}
              onClick={() =>
                void task.run(async () => {
                  setPreview(await call<Preview>(`broadcasts/${key}/preview`));
                }, "Vista previa actualizada.")
              }
            >
              Vista previa de destinatarios
            </Button>
            <Button
              variant="secondary"
              disabled={dirty || task.busy || !editable}
              onClick={() => {
                setReviewed(true);
                void task.run(async () => {
                  await call(
                    `broadcasts/${key}/prepare`,
                    "POST",
                    command({ confirmed: true }),
                  );
                  await saved(key);
                }, "Preparación guardada sin enviar mensajes.");
              }}
            >
              Preparar sin enviar
            </Button>
          </div>
          {preview && (
            <div>
              <h3>
                {preview.counts.eligible} elegibles de {preview.counts.matched}{" "}
                · {preview.counts.excluded} excluidos
              </h3>
              {Object.entries(preview.exclusions).map(([k, n]) => (
                <p key={k}>
                  {label(k)}: {n}
                </p>
              ))}
              {preview.items.slice(0, 20).map((p) => (
                <article className="broadcast-message" key={p.identity_id}>
                  <strong>{p.name}</strong>
                  <p>{p.eligible ? p.text : p.reasons.map(label).join("; ")}</p>
                </article>
              ))}
              {preview.items.length > 20 && (
                <p>
                  Se muestran los primeros 20 resultados de la vista previa.
                </p>
              )}
            </div>
          )}
          <label className="broadcast-check">
            <input
              type="checkbox"
              checked={reviewed}
              onChange={(e) => setReviewed(e.target.checked)}
            />
            He revisado la cuenta, la plantilla, el consentimiento y los
            destinatarios.
          </label>
          <div className="institution-actions">
            <Button
              disabled={
                dirty ||
                task.busy ||
                !reviewed ||
                !session.actions.includes("inbox.write") ||
                ["cancelled", "completed"].includes(initial.state)
              }
              onClick={() => action("activate")}
            >
              Activar o reanudar envío
            </Button>
            <Button
              variant="secondary"
              disabled={dirty || task.busy || !reviewed}
              onClick={() => action("pause")}
            >
              Pausar campaña
            </Button>
            <Button
              variant="quiet"
              disabled={dirty || task.busy || !reviewed}
              onClick={() => action("cancel")}
            >
              Cancelar campaña
            </Button>
          </div>
          <p>
            La aceptación de Meta y la entrega son estados distintos. Un
            resultado incierto requiere revisión antes de repetir un envío.
          </p>
        </div>
      )}
      {initial && (
        <CampaignReport
          campaign={key}
          canRetry={!dirty && reviewed && !task.busy}
          retry={(ids) => action("retry", ids)}
        />
      )}
    </section>
  );
}

function CampaignReport({
  campaign,
  canRetry,
  retry,
}: {
  campaign: string;
  canRetry: boolean;
  retry: (ids: string[]) => void;
}) {
  const [state, setState] = useState(""),
    [recipientDetail, setRecipientDetail] = useState<{
      recipient: Report["items"][number];
      trigger: HTMLElement;
    } | null>(null),
    [search, setSearch] = useState(""),
    [searchQuery, setSearchQuery] = useState(""),
    [charts, setCharts] = useState(false),
    [failure, setFailure] = useState<{ code: string; trigger: Element } | null>(
      null,
    );
  useEffect(() => {
    const timer = setTimeout(() => setSearchQuery(search), 300);
    return () => clearTimeout(timer);
  }, [search]);
  const query = new URLSearchParams({
    state,
    search: searchQuery,
    ...(charts ? { analytics: "true" } : {}),
  }).toString();
  const [offset, setOffset] = useState(0),
    [selected, setSelected] = useState<string[]>([]),
    data = useResource<Report>(
      `broadcasts/${campaign}/report?offset=${offset}&${query}`,
    ),
    task = useTask();
  const { expire } = useInstitution();
  return (
    <section>
      <h3>Resultados por destinatario</h3>
      <Button
        variant="secondary"
        aria-expanded={charts}
        onClick={() => setCharts(!charts)}
      >
        <Icon name="chart" />
        {charts ? "Ocultar gráficos" : "Gráficos y detalles"}
      </Button>
      <div className="broadcast-binding">
        <SelectField
          id="report-status"
          label="Estado del destinatario"
          value={state}
          options={[
            { value: "", label: "Todos los estados" },
            ...Object.keys(stateLabel)
              .filter(
                (k) =>
                  ![
                    "draft",
                    "scheduled",
                    "running",
                    "paused",
                    "completed",
                  ].includes(k),
              )
              .map((k) => ({ value: k, label: label(k) })),
          ]}
          onChange={(e) => {
            setState(e.target.value);
            setOffset(0);
            setSelected([]);
          }}
        />
        <Field
          id="report-search"
          label="Buscar por nombre, teléfono o mensaje"
          maxLength={100}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
            setSelected([]);
          }}
        />
      </div>
      {task.notices}
      {!data.value ? (
        charts && !data.error ? (
          <BroadcastAnalyticsSkeleton />
        ) : (
          <ResourceState error={data.error} />
        )
      ) : (
        <>
          <p>
            {Object.entries(data.value.counts)
              .map(([k, n]) => `${label(k)}: ${n}`)
              .join(" · ") || "Sin destinatarios preparados"}
          </p>
          {charts && data.value.analytics && (
            <BroadcastAnalytics data={data.value.analytics} />
          )}
          {data.value.metrics && (
            <p>
              Respuestas atribuidas: {data.value.metrics.replied} · Entrega:{" "}
              {data.value.metrics.delivered_percent ?? "—"}% · Lectura:{" "}
              {data.value.metrics.read_percent ?? "—"}% · Respuesta:{" "}
              {data.value.metrics.reply_percent ?? "—"}%
            </p>
          )}
          <p>
            Las fechas de entrega, lectura y respuesta indican cuándo se observó
            el evento autenticado. Una respuesta sólo se atribuye si referencia
            este mensaje.
          </p>
          <p>
            WhatsApp informa lecturas cuando existe recibo de Meta. Abrir y
            visualizar no se cuentan como dos eventos distintos. Los clics en
            enlaces no están medidos en este informe.
          </p>
          <div className="institution-actions">
            <Button
              variant="secondary"
              onClick={() =>
                void task.run(async () => {
                  await data.reload();
                }, "Informe actualizado.")
              }
            >
              Actualizar resultados
            </Button>
            <Button
              variant="quiet"
              onClick={() =>
                void task.run(async () => {
                  const response = await fetch(
                    `/api/institution/broadcasts/${campaign}/export?${query}`,
                    {
                      credentials: "same-origin",
                      cache: "no-store",
                      headers: { "X-CRM-Local": "1" },
                      signal: AbortSignal.timeout(45000),
                    },
                  );
                  if (!response.ok) {
                    if (response.status === 401) expire();
                    throw Error("No se pudo exportar el informe.");
                  }
                  const url = URL.createObjectURL(await response.blob()),
                    link = document.createElement("a");
                  link.href = url;
                  link.download = "rinovaplus-destinatarios.csv";
                  link.click();
                  setTimeout(() => URL.revokeObjectURL(url), 1000);
                }, "Informe exportado.")
              }
            >
              Exportar CSV
            </Button>
          </div>
          <div className="broadcast-table">
            <table>
              <thead>
                <tr>
                  <th>Reintentar</th>
                  <th>Destinatario</th>
                  <th>Estado</th>
                  <th>Intentos</th>
                </tr>
              </thead>
              <tbody>
                {data.value.items.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <input
                        aria-label={`Reintentar ${p.name}`}
                        type="checkbox"
                        disabled={
                          p.status !== "failed" || !!p.provider_message_id
                        }
                        checked={selected.includes(p.id)}
                        onChange={(e) =>
                          setSelected(
                            e.target.checked
                              ? [...selected, p.id]
                              : selected.filter((id) => id !== p.id),
                          )
                        }
                      />
                    </td>
                    <td>
                      {p.name}
                      <small>{p.phone}</small>
                      <Button
                        variant="quiet"
                        onClick={(e) =>
                          setRecipientDetail({
                            recipient: p,
                            trigger: e.currentTarget,
                          })
                        }
                      >
                        Abrir detalle del envío
                      </Button>
                      <details>
                        <summary>Ver mensaje y fechas</summary>
                        <p>{p.body}</p>
                        <dl>
                          {(
                            [
                              "prepared_at",
                              "queued_at",
                              "accepted_at",
                              "sent_at",
                              "delivered_at",
                              "read_at",
                              "replied_at",
                              "failed_at",
                            ] as const
                          ).map((field, i) => (
                            <div key={field}>
                              <dt>
                                {
                                  [
                                    "Preparado",
                                    "Pendiente",
                                    "Aceptado",
                                    "Enviado observado",
                                    "Entregado observado",
                                    "Leído observado",
                                    "Respuesta atribuida observada",
                                    "Fallo observado",
                                  ][i]
                                }
                              </dt>
                              <dd>
                                {p[field]
                                  ? new Date(p[field]!).toLocaleString()
                                  : "Sin evento"}
                              </dd>
                            </div>
                          ))}
                        </dl>
                        {p.profile && (
                          <dl>
                            {Object.entries(p.profile).map(([key, value]) => (
                              <div key={key}>
                                <dt>{profileLabels[key] || key}</dt>
                                <dd>{value}</dd>
                              </div>
                            ))}
                          </dl>
                        )}
                      </details>
                    </td>
                    <td>
                      {label(p.status)}
                      {p.status === "queued" && p.error === "broadcast_cadence_wait" ? (
                        <p className="broadcast-help">El CRM respeta el intervalo entre mensajes. No hace falta reintentar este envío.</p>
                      ) : p.error && (
                        <Button
                          variant="quiet"
                          onClick={(e) =>
                            setFailure({
                              code: p.error!,
                              trigger: e.currentTarget,
                            })
                          }
                        >
                          Ver motivo y solución
                        </Button>
                      )}
                    </td>
                    <td>{p.attempts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {recipientDetail && (
            <RecipientDeliveryDialog
              item={recipientDetail.recipient}
              trigger={recipientDetail.trigger}
              close={() => setRecipientDetail(null)}
            />
          )}
          <Button
            variant="secondary"
            disabled={!canRetry || selected.length === 0}
            onClick={() => retry(selected)}
          >
            Reintentar fallidos seleccionados
          </Button>
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
              {offset + (data.value.total ? 1 : 0)}–
              {offset + data.value.items.length} de {data.value.total}
            </span>
            <Button
              variant="quiet"
              disabled={!data.value.has_more}
              onClick={() => {
                setOffset(offset + 100);
                setSelected([]);
              }}
            >
              Siguiente
            </Button>
          </div>
        </>
      )}
      {failure && (
        <OperationDialog
          guidance={explainInboxError({
            code: failure.code,
            message: "El canal informó un problema con este envío.",
          })}
          trigger={failure.trigger}
          dismiss={() => setFailure(null)}
        />
      )}
    </section>
  );
}

function RecipientDeliveryDialog({
  item,
  trigger,
  close,
}: {
  item: Report["items"][number];
  trigger: HTMLElement;
  close: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    dialog.current?.showModal?.();
    return () => {
      if (trigger.isConnected) trigger.focus();
    };
  }, [trigger]);
  const dates = [
    ["prepared_at", "Preparado"],
    ["queued_at", "En cola"],
    ["accepted_at", "Aceptado"],
    ["sent_at", "Enviado observado"],
    ["delivered_at", "Entregado observado"],
    ["read_at", "Leído observado"],
    ["replied_at", "Respuesta atribuida"],
    ["failed_at", "Fallo observado"],
  ] as const;
  return (
    <dialog
      ref={dialog}
      className="operation-error-dialog broadcast-recipient-dialog"
      aria-label={`Detalle del envío a ${item.name}`}
      onCancel={(e) => {
        e.preventDefault();
        close();
      }}
    >
      <div className="broadcast-recipient-header">
        <h2>Detalle del envío</h2>
        <p>
          {item.name} · {item.phone}
        </p>
        <p>
          Estado: {label(item.status)} · Intentos: {item.attempts}
        </p>
        <Button variant="quiet" onClick={close}>
          Cerrar detalle del envío
        </Button>
      </div>
      <div className="broadcast-recipient-content">
        <dl className="broadcast-recipient-request">
          <div>
            <dt>Información solicitada en preinscripción</dt>
            <dd>
              {item.contact?.requested_program ||
                item.profile?.program ||
                "Sin dato registrado"}
            </dd>
          </div>
          <div>
            <dt>Etapa actual en el CRM</dt>
            <dd>{item.contact?.stage || "No disponible en este informe"}</dd>
          </div>
          {item.contact?.program && (
            <div>
              <dt>Programa actual en el CRM</dt>
              <dd>{item.contact.program}</dd>
            </div>
          )}
          {item.contact?.sent_stage && (
            <div>
              <dt>Etapa configurada tras envío confirmado</dt>
              <dd>{item.contact.sent_stage}</dd>
            </div>
          )}
        </dl>
        {item.contact &&
          (item.contact.requested_at ||
            item.contact.request_channel ||
            item.contact.source) && (
            <details className="broadcast-recipient-source">
              <summary>Ver origen de la solicitud</summary>
              <dl className="readable-record-fields">
                {item.contact.requested_at && (
                  <div>
                    <dt>Última preinscripción</dt>
                    <dd>{item.contact.requested_at}</dd>
                  </div>
                )}
                {item.contact.request_channel && (
                  <div>
                    <dt>Canal declarado</dt>
                    <dd>{item.contact.request_channel}</dd>
                  </div>
                )}
                {item.contact.source && (
                  <div>
                    <dt>Archivo de origen</dt>
                    <dd>{item.contact.source}</dd>
                  </div>
                )}
              </dl>
              <p>
                La fecha de preinscripción no acredita una conversación ni una
                lectura.
              </p>
            </details>
          )}
        <h3>Mensaje de la campaña</h3>
        <div className="broadcast-phone-message">
          {item.template_parts?.header && (
            <p>
              <strong>{item.template_parts.header}</strong>
            </p>
          )}
          <ReadableRecord text={item.body || ""} />
          {item.template_parts?.footer && (
            <p className="broadcast-recipient-footer">
              {item.template_parts.footer}
            </p>
          )}
          {!!item.template_parts?.buttons.length && (
            <ul
              className="broadcast-recipient-buttons"
              aria-label="Opciones del mensaje enviado"
            >
              {item.template_parts.buttons.map((text, i) => (
                <li key={i}>{text}</li>
              ))}
            </ul>
          )}
        </div>
        <details className="broadcast-recipient-events">
          <summary>
            Entrega y actividad · {dates.filter(([key]) => item[key]).length}{" "}
            eventos registrados
          </summary>
          <dl>
            {dates
              .filter(([key]) => item[key])
              .map(([key, title]) => (
                <div key={key}>
                  <dt>{title}</dt>
                  <dd>
                    {new Date(item[key]!).toLocaleString("es-CO", {
                      timeZone: "America/Bogota",
                    })}
                  </dd>
                </div>
              ))}
          </dl>
          <p>
            Horas de Bogotá. Sólo se muestran eventos recibidos; no se infiere
            una lectura.
          </p>
        </details>
        <p>
          Este panel consulta la campaña. No envía mensajes ni abre una
          conversación en Inbox.
        </p>
      </div>
    </dialog>
  );
}

function TemplatePanel({
  account,
  templates,
  reload,
  variables,
  initiallyCreating = false,
}: {
  account: string;
  templates: Template[];
  reload: () => Promise<void>;
  variables: CrmVariable[];
  initiallyCreating?: boolean;
}) {
  const { call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [creating, setCreating] = useState(initiallyCreating),
    [showPaused, setShowPaused] = useState(false),
    [showRemoved, setShowRemoved] = useState(false),
    [reviewed, setReviewed] = useState("");
  const command = (revision = 0, extra = {}) => {
    const value = {
      revision,
      reason: "Gestión de plantilla WhatsApp institucional",
      ...extra,
    };
    return { ...value, operation_id: intent.get(value) };
  };
  return (
    <section className="panel">
      <h2>Plantillas WhatsApp</h2>
      {task.notices}
      <p>
        La aprobación y la calidad proceden de Meta. Guardar un borrador no lo
        aprueba ni envía mensajes.
      </p>
      <div className="institution-actions">
        {templates.some((t) => t.metadata?.library_removed) && (
          <Button
            variant="quiet"
            aria-pressed={showRemoved}
            onClick={() => setShowRemoved(!showRemoved)}
          >
            {showRemoved ? "Volver a plantillas" : "Ver papelera"}
            {` (${templates.filter((t) => t.metadata?.library_removed).length})`}
          </Button>
        )}
        {!showRemoved && templates.some((t) => t.paused && !t.metadata?.library_removed) && (
          <Button
            variant="quiet"
            aria-pressed={showPaused}
            onClick={() => setShowPaused(!showPaused)}
          >
            {showPaused ? "Ocultar versiones pausadas" : "Mostrar versiones pausadas"}
            {` (${templates.filter((t) => t.paused && !t.metadata?.library_removed).length})`}
          </Button>
        )}
        <Button
          disabled={task.busy}
          onClick={() =>
            void task.run(async () => {
              await call(
                `broadcasts/accounts/${account}/templates/sync`,
                "POST",
                command(),
              );
              intent.clear();
              await reload();
            }, "Catálogo sincronizado con Meta.")
          }
        >
          Sincronizar con Meta
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            if (allowNavigation()) setCreating(!creating);
          }}
        >
          Crear plantilla
        </Button>
      </div>
      {creating && (
        <TemplateForm
          account={account}
          variables={variables}
          saved={async () => {
            setCreating(false);
            await reload();
          }}
        />
      )}
      {templates.length === 0 && (
        <Notice>
          No hay plantillas para esta cuenta. Sincroniza el catálogo o crea un
          borrador.
        </Notice>
      )}
      {templates.filter((t) => showRemoved ? t.metadata?.library_removed : !t.metadata?.library_removed && (showPaused || !t.paused)).map((t) => (
        <article className="broadcast-message" key={t.id}>
          <h3>
            {t.name} · {t.language}
          </h3>
          <p>
            {t.category} ·{" "}
            {t.origin === "operator"
              ? "Borrador local"
              : t.origin === "controlled"
                ? "Proveedor de prueba controlado"
                : "Catálogo de Meta"}{" "}
            ·{" "}
            <span
              className={`broadcast-template-status status-${t.status.toLowerCase()}`}
            >
              {templateStatus(t.status)}
            </span>{" "}
            {t.paused && "· Pausada en CRM"}
            {t.metadata?.library_removed && " · Eliminada de biblioteca"}
          </p>
          {t.metadata?.quality_score && (
            <p>
              Calidad informada por Meta:{" "}
              {qualityLabel(t.metadata.quality_score)}
            </p>
          )}
          {t.status === "REJECTED" &&
            rejectionReason(t.metadata?.rejection_reason) && (
              <Notice error>
                Motivo de rechazo de Meta:{" "}
                {rejectionReason(t.metadata?.rejection_reason)}
              </Notice>
            )}
          {t.components
            .filter((c) => c.text)
            .map((c, i) => (
              <p key={i}>{c.text}</p>
            ))}
          {t.origin === "operator" && !t.metadata?.library_removed && (
            <div>
              <label className="broadcast-check">
                <input
                  type="checkbox"
                  checked={reviewed === t.id}
                  onChange={(e) => setReviewed(e.target.checked ? t.id : "")}
                />
                Confirmo enviar «{t.name}» a revisión de Meta.
              </label>
              <Button
                disabled={reviewed !== t.id || task.busy}
                onClick={() =>
                  void task.run(async () => {
                    const r = await call<{ status: string }>(
                      `broadcasts/templates/${t.id}/submit`,
                      "POST",
                      command(t.version, { confirmed: true }),
                    );
                    intent.clear();
                    await reload();
                    if (r.status !== "confirmed")
                      throw Error(
                        "La solicitud no quedó confirmada. Consulta su estado antes de repetirla.",
                      );
                  }, "Plantilla enviada a revisión. Sincroniza para consultar su aprobación.")
                }
              >
                Enviar a revisión de Meta
              </Button>
            </div>
          )}
          {!t.metadata?.library_removed && <Button
            variant="quiet"
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                await call(
                  `broadcasts/templates/${t.id}/pause`,
                  "POST",
                  command(t.version, { paused: !t.paused }),
                );
                intent.clear();
                await reload();
              })
            }
          >
            {t.paused ? "Permitir uso en CRM" : "Pausar uso en CRM"}
          </Button>}
          <Button
            variant="quiet"
            disabled={task.busy}
            onClick={() => void task.run(async () => {
              await call(`broadcasts/templates/${t.id}/library`, "POST",
                command(t.version, { removed: !t.metadata?.library_removed, confirmed: true }));
              intent.clear();
              await reload();
            }, t.metadata?.library_removed ? "Plantilla restaurada en pausa." : "Plantilla retirada de la biblioteca.")}
          >
            {t.metadata?.library_removed ? "Restaurar en pausa" : "Eliminar de biblioteca"}
          </Button>
        </article>
      ))}
    </section>
  );
}

function TemplateForm({
  account,
  saved,
  variables,
}: {
  account: string;
  saved: () => Promise<void>;
  variables: CrmVariable[];
}) {
  const { call } = useInstitution(),
    task = useTask(),
    intent = useIntent(),
    [key] = useState(() => crypto.randomUUID());
  const initial = {
    name: "",
    language: "es",
    category: "MARKETING",
    body_text: "",
    header_type: "",
    header_text: "",
    header_media_handle: "",
    footer_text: "",
    buttons: [] as {
      type: string;
      text: string;
      url: string;
      phone_number: string;
      url_example: string;
    }[],
    allow_category_change: true,
    examples: {} as Record<string, string>,
  };
  const [doc, setDoc] = useState(initial),
    [clean, setClean] = useState(false);
  const [mediaPreview, setMediaPreview] = useState(""),
    [sampleGeneration, setSampleGeneration] = useState(0);
  useEffect(
    () => () => {
      if (mediaPreview) URL.revokeObjectURL(mediaPreview);
    },
    [mediaPreview],
  );
  useDraftGuard(!clean && JSON.stringify(doc) !== JSON.stringify(initial));
  const change = (value: Partial<typeof doc>) =>
    setDoc((current) => ({ ...current, ...value }));
  const bodySelection = useRef({ start: 0, end: 0 });
  const insertBody = (token: string) => {
    const { start, end } = bodySelection.current;
    const inserted = `{{${token}}}`;
    change({
      body_text:
        doc.body_text.slice(0, start) + inserted + doc.body_text.slice(end),
    });
    bodySelection.current = {
      start: start + inserted.length,
      end: start + inserted.length,
    };
    requestAnimationFrame(() => {
      const field = document.getElementById(
        "template-body",
      ) as HTMLTextAreaElement | null;
      field?.focus();
      field?.setSelectionRange(
        start + inserted.length,
        start + inserted.length,
      );
    });
  };
  return (
    <div className="broadcast-template-editor">
      <form
        className="broadcast-message"
        onSubmit={(e) => {
          e.preventDefault();
          void task.run(async () => {
            const body = {
              ...doc,
              examples: metaExamples(doc, variables),
              revision: 0,
              reason: "Borrador de plantilla institucional",
            };
            await call(
              `broadcasts/accounts/${account}/templates/${key}`,
              "PUT",
              {
                ...body,
                operation_id: intent.get(body),
              },
            );
            setClean(true);
            await saved();
          });
        }}
      >
        {task.notices}
        <fieldset disabled={task.busy}>
          <h3>Nueva plantilla</h3>
          <ol
            className="broadcast-composer-steps"
            aria-label="Pasos para crear la plantilla"
          >
            <li>Categoría y formato</li>
            <li>Contenido y ejemplos</li>
            <li>Revisión de Meta</li>
          </ol>
          <TemplateExampleGuide
            choose={(example) => {
              change({
                name: doc.name || example.name,
                category: example.category,
                body_text: example.body,
                header_type: example.header,
                header_text: "",
                header_media_handle: "",
                examples: {},
                footer_text: "Corporación Bolivariana del Norte · CBN",
                buttons: example.buttons.map((text) => ({
                  type: "QUICK_REPLY",
                  text,
                  url: "",
                  phone_number: "",
                  url_example: "",
                })),
              });
              setMediaPreview("");
              setSampleGeneration((value) => value + 1);
            }}
          />
          <Field
            id="template-name"
            label="Nombre de plantilla"
            pattern="[a-z][a-z0-9_]*"
            maxLength={128}
            required
            value={doc.name}
            onChange={(e) => change({ name: e.target.value })}
          />
          <p className="broadcast-help">
            Usa minúsculas, números y guion bajo. Por ejemplo:
            informacion_programas_cbn.
          </p>
          <SelectField
            id="template-language"
            label="Idioma"
            required
            value={doc.language}
            options={[
              { value: "es", label: "Español" },
              { value: "en_US", label: "Inglés · Estados Unidos" },
              { value: "pt_BR", label: "Portugués · Brasil" },
            ]}
            onChange={(e) => change({ language: e.target.value })}
          />
          <SelectField
            id="template-category"
            label="Categoría"
            value={doc.category}
            options={[
              {
                value: "MARKETING",
                label: "Marketing · información y promociones",
              },
              {
                value: "UTILITY",
                label: "Utilidad · solicitudes y actualizaciones",
              },
            ]}
            onChange={(e) => change({ category: e.target.value })}
          />
          <TextArea
            id="template-body"
            label="Cuerpo del mensaje"
            required
            maxLength={1024}
            value={doc.body_text}
            onChange={(e) => change({ body_text: e.target.value })}
            onSelect={(e) => {
              bodySelection.current = {
                start: e.currentTarget.selectionStart,
                end: e.currentTarget.selectionEnd,
              };
            }}
          />
          <p className="broadcast-help">
            {doc.body_text.length}/1024 caracteres. Inserta los campos del CRM
            para personalizar cada envío.
          </p>
          <TemplateVariableFields
            group="body"
            text={doc.body_text}
            samples={doc.examples}
            variables={variables}
            insert={insertBody}
            change={(key, value) =>
              change({ examples: { ...doc.examples, [key]: value } })
            }
          />
          <SelectField
            id="template-header"
            label="Tipo de cabecera"
            value={doc.header_type}
            options={[
              { value: "", label: "Sin cabecera" },
              { value: "TEXT", label: "Texto" },
              { value: "IMAGE", label: "Imagen" },
              { value: "VIDEO", label: "Video" },
              { value: "DOCUMENT", label: "Documento" },
            ]}
            onChange={(e) => {
              change({ header_type: e.target.value, header_media_handle: "" });
              setMediaPreview("");
              setSampleGeneration((value) => value + 1);
            }}
          />
          {doc.header_type === "TEXT" ? (
            <>
              <Field
                id="template-header-text"
                label="Texto de cabecera"
                required
                maxLength={60}
                value={doc.header_text}
                onChange={(e) => change({ header_text: e.target.value })}
              />
              <TemplateVariableFields
                group="header"
                text={doc.header_text}
                samples={doc.examples}
                variables={variables}
                insert={(token) =>
                  change({ header_text: `${doc.header_text}{{${token}}}` })
                }
                change={(key, value) =>
                  change({ examples: { ...doc.examples, [key]: value } })
                }
              />
            </>
          ) : (
            doc.header_type && (
              <div>
                <TemplateSamplePicker
                  key={`${account}-${doc.header_type}-${sampleGeneration}`}
                  account={account}
                  kind={doc.header_type}
                  onUploaded={(handle) =>
                    change({ header_media_handle: handle })
                  }
                  onPreview={setMediaPreview}
                />
                {doc.header_media_handle && (
                  <Notice>Muestra lista para la revisión de Meta.</Notice>
                )}
                <details>
                  <summary>Usar un identificador de muestra existente</summary>
                  <Field
                    id="template-header-example"
                    label="Identificador de archivo de ejemplo de Meta"
                    value={doc.header_media_handle}
                    onChange={(e) =>
                      change({ header_media_handle: e.target.value })
                    }
                  />
                </details>
              </div>
            )
          )}
          <Field
            id="template-footer"
            label="Pie del mensaje"
            maxLength={60}
            value={doc.footer_text}
            onChange={(e) => change({ footer_text: e.target.value })}
          />
          {doc.buttons.map((b, i) => (
            <div key={i} className="broadcast-message">
              <SelectField
                id={`button-type-${i}`}
                label={`Tipo de botón ${i + 1}`}
                value={b.type}
                options={[
                  { value: "QUICK_REPLY", label: "Respuesta rápida" },
                  { value: "URL", label: "Abrir enlace" },
                  { value: "PHONE_NUMBER", label: "Llamar por teléfono" },
                ]}
                onChange={(e) =>
                  change({
                    buttons: doc.buttons.map((v, j) =>
                      j === i ? { ...v, type: e.target.value } : v,
                    ),
                  })
                }
              />
              <Field
                id={`button-text-${i}`}
                label={`Texto de botón ${i + 1}`}
                required
                maxLength={25}
                value={b.text}
                onChange={(e) =>
                  change({
                    buttons: doc.buttons.map((v, j) =>
                      j === i ? { ...v, text: e.target.value } : v,
                    ),
                  })
                }
              />
              {b.type !== "QUICK_REPLY" && (
                <Field
                  id={`button-target-${i}`}
                  label={
                    b.type === "URL"
                      ? "URL HTTPS del botón"
                      : "Teléfono con prefijo internacional"
                  }
                  required
                  value={b.type === "URL" ? b.url : b.phone_number}
                  onChange={(e) =>
                    change({
                      buttons: doc.buttons.map((v, j) =>
                        j === i
                          ? {
                              ...v,
                              [b.type === "URL" ? "url" : "phone_number"]:
                                e.target.value,
                            }
                          : v,
                      ),
                    })
                  }
                />
              )}
              {b.type === "URL" && b.url.includes("{{") && (
                <Field
                  id={`button-example-${i}`}
                  label={`Ejemplo de la variable del enlace ${i + 1}`}
                  required
                  value={b.url_example}
                  onChange={(e) =>
                    change({
                      buttons: doc.buttons.map((v, j) =>
                        j === i ? { ...v, url_example: e.target.value } : v,
                      ),
                    })
                  }
                  hint="Usa {{1}} al final de la URL. Al preparar la campaña asignarás su valor desde el CRM."
                />
              )}
              <div className="institution-actions">
                <Button
                  variant="quiet"
                  disabled={i === 0}
                  onClick={() => {
                    const buttons = [...doc.buttons];
                    [buttons[i - 1], buttons[i]] = [buttons[i], buttons[i - 1]];
                    change({ buttons });
                  }}
                >
                  Subir botón {i + 1}
                </Button>
                <Button
                  variant="quiet"
                  disabled={i === doc.buttons.length - 1}
                  onClick={() => {
                    const buttons = [...doc.buttons];
                    [buttons[i + 1], buttons[i]] = [buttons[i], buttons[i + 1]];
                    change({ buttons });
                  }}
                >
                  Bajar botón {i + 1}
                </Button>
              </div>
              <Button
                variant="quiet"
                onClick={() =>
                  change({ buttons: doc.buttons.filter((_, j) => j !== i) })
                }
              >
                Quitar botón {i + 1}
              </Button>
            </div>
          ))}
          <Button
            variant="secondary"
            disabled={doc.buttons.length >= 10}
            onClick={() =>
              change({
                buttons: [
                  ...doc.buttons,
                  {
                    type: "QUICK_REPLY",
                    text: "",
                    url: "",
                    phone_number: "",
                    url_example: "",
                  },
                ],
              })
            }
          >
            Agregar botón
          </Button>
          <p className="broadcast-help">
            {doc.buttons.length}/10 botones. Hasta 2 enlaces y 1 teléfono.
            Agrupa juntas las respuestas rápidas. Con 4 o más botones, WhatsApp
            puede pedir abrir el mensaje en el teléfono.
          </p>
          <label className="broadcast-check">
            <input
              type="checkbox"
              checked={doc.allow_category_change}
              onChange={(e) =>
                change({ allow_category_change: e.target.checked })
              }
            />
            Permitir que Meta ajuste la categoría
          </label>
          <Button
            type="submit"
            disabled={
              ["IMAGE", "VIDEO", "DOCUMENT"].includes(doc.header_type) &&
              !doc.header_media_handle
            }
          >
            Guardar borrador de plantilla
          </Button>
        </fieldset>
      </form>
      <TemplateChatPreview
        doc={doc}
        variables={variables}
        mediaPreview={mediaPreview}
      />
    </div>
  );
}

type Cadence = {
  revision: number;
  enabled: boolean;
  daily_limit: number;
  interval_seconds: number;
  reserved: number;
};
type Identity = {
  id: string;
  name: string;
  phone: string;
  consent: null | {
    state: string;
    version: number;
    evidence: string;
    expires_at: string | null;
  };
};
function ConsentPanel({ account }: { account: string }) {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => { setQuery(search); setOffset(0); }, 300);
    return () => clearTimeout(timer);
  }, [search]);
  const data = useResource<Cadence>(`broadcasts/accounts/${account}/cadence`),
    people = useResource<{ items: Identity[]; has_more?: boolean }>(
      `broadcasts/accounts/${account}/identities${query || offset ? `?search=${encodeURIComponent(query)}&offset=${offset}` : ""}`,
    );
  return (
    <div className="broadcast-columns">
      <section className="panel">
        <h2>Cadencia por cuenta</h2>
        {data.value ? (
          <CadenceEditor
            key={data.value.revision}
            account={account}
            initial={data.value}
            reload={data.reload}
          />
        ) : (
          <ResourceState error={data.error} />
        )}
      </section>
      <section className="panel">
        <h2>Consentimiento de mensajería</h2>
        <p>
          Registra la evidencia de autorización para esta cuenta. No se deduce
          del teléfono ni de una conversación anterior.
        </p>
        <Field id="consent-recipient-search" label="Buscar destinatario por nombre o número"
          maxLength={100} value={search} onChange={e => setSearch(e.target.value)} />
        {!people.value ? (
          <ResourceState error={people.error} />
        ) : people.value.items.length === 0 ? (
          <Notice>
            No hay destinatarios que coincidan con esta búsqueda en la cuenta.
          </Notice>
        ) : (
          <ConsentEditor
            key={JSON.stringify(
              people.value.items.map((p) => [p.id, p.consent?.version]),
            )}
            account={account}
            people={people.value.items}
            reload={people.reload}
          />
        )}
        <div className="actions">
          <Button variant="secondary" disabled={!offset}
            onClick={() => setOffset(Math.max(0, offset - 100))}>Destinatarios anteriores</Button>
          <span>Página {Math.floor(offset / 100) + 1}</span>
          <Button variant="secondary" disabled={!people.value?.has_more}
            onClick={() => setOffset(offset + 100)}>Más destinatarios</Button>
        </div>
      </section>
      <BroadcastProspectSetup account={account} changed={people.reload} />
    </div>
  );
}
function CadenceEditor({
  account,
  initial,
  reload,
}: {
  account: string;
  initial: Cadence;
  reload: () => Promise<unknown>;
}) {
  const { call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [doc, setDoc] = useState(initial),
    [clean, setClean] = useState(false);
  useDraftGuard(!clean && JSON.stringify(doc) !== JSON.stringify(initial));
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          const { enabled, daily_limit, interval_seconds, revision } = doc,
            body = {
              enabled,
              daily_limit,
              interval_seconds,
              revision,
              reason: "Revisión de límites de mensajería",
            };
          await call(`broadcasts/accounts/${account}/cadence`, "PUT", {
            ...body,
            operation_id: intent.get(body),
          });
          setClean(true);
          await reload();
        });
      }}
    >
      {task.notices}
      <fieldset disabled={task.busy}>
        <label className="broadcast-check">
          <input
            type="checkbox"
            checked={doc.enabled}
            onChange={(e) => setDoc({ ...doc, enabled: e.target.checked })}
          />
          Permitir campañas en esta cuenta
        </label>
        <Field
          id="cadence-daily"
          label="Máximo en 24 horas"
          type="number"
          min={1}
          max={100000}
          required
          value={doc.daily_limit}
          onChange={(e) =>
            setDoc({ ...doc, daily_limit: Number(e.target.value) })
          }
        />
        <Field
          id="cadence-interval"
          label="Intervalo mínimo entre mensajes (segundos)"
          type="number"
          min={1}
          max={86400}
          required
          value={doc.interval_seconds}
          onChange={(e) =>
            setDoc({ ...doc, interval_seconds: Number(e.target.value) })
          }
        />
        <p>
          {initial.reserved} reservas en la ventana actual. Los resultados
          inciertos conservan su reserva.
        </p>
        <Button type="submit">Guardar cadencia</Button>
      </fieldset>
    </form>
  );
}
function ConsentEditor({
  account,
  people,
  reload,
}: {
  account: string;
  people: Identity[];
  reload: () => Promise<unknown>;
}) {
  const { call } = useInstitution(),
    task = useTask(),
    intent = useIntent(),
    [id, setId] = useState(people[0].id),
    [evidence, setEvidence] = useState(""),
    [origin, setOrigin] = useState(""),
    [expires, setExpires] = useState(""),
    [confirmed, setConfirmed] = useState(false),
    [clean, setClean] = useState(false);
  useDraftGuard(!clean && !!(evidence || origin || expires));
  const person = people.find((p) => p.id === id)!;
  const save = (state: string) =>
    void task.run(async () => {
      const body = {
        revision: person.consent?.version || 0,
        reason: "Registro de consentimiento de mensajería",
        state,
        evidence,
        origin,
        expires_at:
          state === "granted" ? new Date(expires).toISOString() : null,
        confirmed,
      };
      await call(`broadcasts/accounts/${account}/consent/${id}`, "PUT", {
        ...body,
        operation_id: intent.get(body),
      });
      setClean(true);
      await reload();
    });
  return (
    <div>
      {task.notices}
      <fieldset disabled={task.busy}>
        <SelectField
          id="consent-person"
          label="Destinatario"
          value={id}
          options={people.map((p) => ({
            value: p.id,
            label: `${p.name} · ${p.phone}`,
          }))}
          onChange={(e) => {
            if (allowNavigation()) {
              setId(e.target.value);
              setEvidence("");
              setOrigin("");
              setExpires("");
              setConfirmed(false);
            }
          }}
        />
        <p>
          Estado:{" "}
          {person.consent
            ? person.consent.state === "granted"
              ? "Autorizado"
              : "Revocado"
            : "Sin autorización registrada"}
          {person.consent?.expires_at &&
            ` · Vigencia: ${person.consent.expires_at}`}
        </p>
        <TextArea
          id="consent-evidence"
          label="Evidencia de autorización o revocación"
          maxLength={1000}
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
        />
        <Field
          id="consent-origin"
          label="Origen de la evidencia"
          maxLength={200}
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
        />
        <Field
          id="consent-expiry"
          label="Vigencia hasta (hora de este navegador)"
          type="datetime-local"
          value={expires}
          onChange={(e) => setExpires(e.target.value)}
        />
        <label className="broadcast-check">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          Confirmo que la evidencia corresponde a esta persona y cuenta.
        </label>
        <div className="institution-actions">
          <Button
            disabled={
              !confirmed || !evidence.trim() || !origin.trim() || !expires
            }
            onClick={() => save("granted")}
          >
            Registrar autorización
          </Button>
          <Button
            variant="secondary"
            disabled={!confirmed || !evidence.trim() || !origin.trim()}
            onClick={() => save("revoked")}
          >
            Revocar consentimiento
          </Button>
        </div>
      </fieldset>
    </div>
  );
}
