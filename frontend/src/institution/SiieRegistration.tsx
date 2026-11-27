import { SiiePreicfes } from "./SiiePreicfes";
import { siieHeaders, type SiieEnvironment } from "../shared/siieEnvironment";
import { useEffect, useEffectEvent, useRef, useState } from "react";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import {
  institutionHeaders,
  institutionUnauthorized,
} from "../shared/institutionSession";
import { useInstitution, useTask } from "./api";
import "./siieRegistration.css";
import { SiieGeography, type GeographySelection } from "./SiieGeography";
import { SiieWebhookReadiness, SiieWebhookReceipts } from "./SiieWebhookPanel";

type Values = Record<string, unknown>;
type Choice = { value: string | number; label: string };
type FieldSpec = {
  name: string;
  label: string;
  kind: string;
  required: boolean;
  max_length: number;
  options: (string | number)[];
  catalog: string | null;
  geography?: "municipality" | "department" | null;
};
type Section = {
  name: string;
  label: string;
  optional?: boolean;
  max_items?: number;
  fields: FieldSpec[];
};
type Status = {
  environment?: SiieEnvironment | null;
  revision: number;
  api_configured: boolean;
  webhook_secret_configured: boolean;
  webhook_enabled: boolean;
  writes_enabled: boolean;
  stage_key: string;
  webhook_path: string;
  stages: { key: string; label: string }[];
  schema: Section[];
  applicant_fields: FieldSpec[];
};
type Context = {
  idOferta: number;
  idPeriodo: number;
  program_name: string;
  schedule: string;
  selection: Values;
};
type Draft = {
  environment_current?: boolean;
  id: string;
  revision: number;
  kind: "applicant" | "registration";
  state: string;
  form: Values;
  context: Context;
  result?: Result;
  last_result?: Result;
  pending_operation?: string;
  geography?: Record<string, GeographySelection>;
};
type Result = {
  state: string;
  code: string;
  correlation_id?: string | null;
  data?: Values;
  revision?: number;
  operation_id?: string;
  references?: Record<string, number>[];
  retry_after?: number;
  rate_remaining?: number;
};
type RecordRow = {
  id: string;
  state?: string;
  kind?: string;
  program_name?: string;
  event_type?: string;
  projection?: string;
  updated_at: string;
};
type Requirements = {
  idDocumento: number;
  nombre: string;
  descripcion?: string;
  obligatorioAlInscribir: boolean;
  soloMenores?: boolean;
  aplica: boolean | null;
  soportado: boolean;
  recibido: boolean | null;
  archivoExistente: boolean | null;
};
const base = "siie-registration";
const states: Record<string, string> = {
  draft: "Borrador",
  pending_review: "Envío iniciado · Revisar resultado",
  confirmed: "Confirmado por SIIE",
  rejected: "Rechazado · Revisar campos",
  conflict: "Registro existente · Conciliar",
  uncertain: "Resultado incierto · No repetir",
};
const referenceLabels: Record<string, string> = {
  idAspirante: "Aspirante SIIE",
  idEstudiante: "Estudiante SIIE",
  idInscripcion: "Inscripción SIIE",
  idAcudiente: "Acudiente SIIE",
  idOferta: "Oferta SIIE",
  idPeriodo: "Período SIIE",
  idDocumento: "Tipo de documento",
};
const valueOf = (value: unknown) => (value == null ? "" : String(value));

export function SiieRegistration() {
  const { call, session } = useInstitution();
  const task = useTask();
  const [status, setStatus] = useState<Status | null>(null);
  const [drafts, setDrafts] = useState<RecordRow[]>([]);
  const [selected, setSelected] = useState<Draft | null>(null);
  const [form, setForm] = useState<Values>({});
  const [dirty, setDirty] = useState(false);
  const [catalogs, setCatalogs] = useState<Record<string, Choice[]>>({});
  const [missing, setMissing] = useState<string[]>([]);
  const [countries, setCountries] = useState<Choice[]>([]);
  const [geography, setGeography] = useState<
    Record<string, GeographySelection>
  >({});
  const [geoVersion, setGeoVersion] = useState(0);
  const [allowsCreation, setAllowsCreation] = useState(true);
  const [requirements, setRequirements] = useState<Requirements[] | null>(null);
  const [files, setFiles] = useState<Record<number, File>>({});
  const [review, setReview] = useState<"submit" | "documents" | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [operation, setOperation] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [configuration, setConfiguration] = useState<Pick<
    Status,
    "revision" | "webhook_enabled" | "writes_enabled" | "stage_key"
  > | null>(null);
  const [newKind, setNewKind] = useState<"applicant" | "registration">(
    "applicant",
  );
  const [programs, setPrograms] = useState<Values[]>([]);
  const [offers, setOffers] = useState<Values[]>([]);
  const [programId, setProgramId] = useState("");
  const [programCursor, setProgramCursor] = useState("");
  const [nextPrograms, setNextPrograms] = useState("");
  const [offerCursor, setOfferCursor] = useState("");
  const [nextOffers, setNextOffers] = useState("");
  const [offerRef, setOfferRef] = useState("");
  const epoch = useRef(0);
  const editable = session.actions.includes("crm.write");
  const configurable = session.actions.includes("settings.webhooks.write");
  const activeDraft =
    !!selected &&
    selected.environment_current !== false &&
    ["draft", "rejected"].includes(selected.state);
  const configurationDirty =
    !!status &&
    !!configuration &&
    (status.webhook_enabled !== configuration.webhook_enabled ||
      status.writes_enabled !== configuration.writes_enabled ||
      status.stage_key !== configuration.stage_key);
  const refresh = async () => {
    const [s, d] = await Promise.all([
      call<Status>(`${base}/status`),
      call<{ items: RecordRow[] }>(`${base}/records/sd`),
    ]);
    setStatus(s);
    setDrafts(d.items);
    setConfiguration(s);
    setRefreshKey((v) => v + 1);
  };
  const initialRead = useEffectEvent(() => {
    void task.run(refresh, "");
  });
  useEffect(() => {
    const counter = epoch;
    initialRead();
    return () => {
      counter.current++;
    };
  }, []); // Initial bounded read; user refreshes receipts explicitly.

  const open = async (id: string) => {
    const ticket = ++epoch.current;
    const draft = await call<Draft>(`${base}/records/sd/${id}`);
    const choices =
      draft.environment_current === false
        ? { items: {}, missing: [], countries: [], allows_creation: false }
        : await call<{
            items: Record<string, Choice[]>;
            missing: string[];
            countries?: Choice[];
            allows_creation?: boolean;
          }>(`${base}/catalogs?draft_id=${id}`);
    if (ticket !== epoch.current) return;
    setSelected(draft);
    setForm(draft.form);
    setCatalogs(choices.items);
    setMissing(choices.missing);
    setCountries(choices.countries ?? []);
    setAllowsCreation(choices.allows_creation !== false);
    setGeography(draft.geography ?? {});
    setGeoVersion((v) => v + 1);
    setDirty(false);
    setResult(draft.last_result ?? draft.result ?? null);
    setRequirements(null);
    setFiles({});
    setReview(null);
    setOperation("");
  };
  const loadPrograms = async (cursor = "") => {
    const response = await call<{
      data: { items: Values[]; next_cursor?: string };
    }>(`${base}/selection/programs?cursor=${encodeURIComponent(cursor)}`);
    setPrograms(response.data.items);
    setProgramCursor(cursor);
    setNextPrograms(response.data.next_cursor ?? "");
    setProgramId("");
    setOffers([]);
    setOfferRef("");
  };
  const loadOffers = async (id: string, cursor = "") => {
    const response = await call<{
      data: { items: Values[]; next_cursor?: string };
    }>(
      `${base}/selection/offers?program_id=${encodeURIComponent(id)}&cursor=${encodeURIComponent(cursor)}`,
    );
    setProgramId(id);
    setOfferRef("");
    setOffers(response.data.items.filter((v) => v.active === true));
    setOfferCursor(cursor);
    setNextOffers(response.data.next_cursor ?? "");
  };
  const create = async () => {
    const id = crypto.randomUUID();
    await call(`${base}/drafts/${id}`, "PUT", {
      operation_id: crypto.randomUUID(),
      revision: 0,
      kind: newKind,
      selection: {
        program_id: programId,
        program_cursor: programCursor,
        offer_cursor: offerCursor,
        offer_ref: offerRef,
      },
      form: {},
    });
    await open(id);
    await refresh();
  };
  const save = async () => {
    if (!selected) return;
    await call(`${base}/drafts/${selected.id}`, "PUT", {
      operation_id: crypto.randomUUID(),
      revision: selected.revision,
      kind: selected.kind,
      selection: selected.context.selection,
      form,
      geography,
    });
    await open(selected.id);
    await refresh();
  };
  const loadRequirements = async () => {
    if (!selected) return;
    const response = await call<{ data: { items: Requirements[] } }>(
      `${base}/drafts/${selected.id}/requirements`,
    );
    setRequirements(response.data.items);
  };
  const change = (name: string, row: Values, index?: number) => {
    setForm((previous) => ({
      ...previous,
      [name]:
        index === undefined
          ? row
          : ((previous[name] as Values[] | undefined) ?? []).map((v, i) =>
              i === index ? row : v,
            ),
    }));
    setDirty(true);
    setReview(null);
    setOperation("");
  };
  const submit = async () => {
    if (!selected || !review || !operation) return;
    const data = new FormData();
    data.append(
      "command",
      JSON.stringify({
        operation_id: operation,
        revision: selected.revision,
        reviewed: true,
      }),
    );
    Object.entries(files).forEach(([id, file]) =>
      data.append(`documentos[${id}]`, file),
    );
    const response = await fetch(
      `/api/institution/${base}/drafts/${selected.id}/${review}`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CRM-Local": "1",
          ...institutionHeaders(),
          ...siieHeaders(base),
        },
        body: data,
        signal: AbortSignal.timeout(45000),
      },
    );
    institutionUnauthorized(response.status);
    const receipt = (await response.json().catch(() => null)) as
      (Result & { detail?: string }) | null;
    if (!response.ok)
      throw Error(
        receipt?.detail === "siie_registration_catalogs_required"
          ? "Faltan catálogos de SIIE para validar la inscripción. El borrador se conserva."
          : "No se confirmó el envío. Consulta el recibo antes de volver a enviar.",
      );
    if (!receipt)
      throw Error(
        "No llegó un recibo válido. Consulta el estado; conserva esta solicitud sin repetirla.",
      );
    setResult(receipt);
    setReview(null);
    setFiles({});
    await open(selected.id);
    await refresh();
  };
  const renderFields = (
    fields: FieldSpec[],
    row: Values,
    update: (value: Values) => void,
    prefix: string,
    path = "",
  ) => (
    <div className="form-grid">
      {fields.map((f) => {
        const fieldPath = `${path}${f.name}`;
        const options = f.catalog
          ? (catalogs[f.catalog] ?? [])
          : f.options.map((v) => ({ value: v, label: String(v) }));
        const updateValue = (value: string) =>
          update({
            ...row,
            [f.name]:
              f.kind === "integer" && value !== "" ? Number(value) : value,
            ...(f.catalog === "otrosEstudios[].Id_TipoEstudio" && value
              ? {
                  TituloCarrera:
                    options.find((v) => String(v.value) === value)?.label ?? "",
                }
              : f.catalog === "otrosEstudios[].TituloCarrera" &&
                  row.Id_TipoEstudio &&
                  catalogs["otrosEstudios[].Id_TipoEstudio"]?.find(
                    (v) => v.value === row.Id_TipoEstudio,
                  )?.label !== value
                ? { Id_TipoEstudio: "" }
                : {}),
          });
        if (f.geography && selected)
          return (
            <SiieGeography
              key={`${selected.id}-${selected.revision}-${geoVersion}-${fieldPath}`}
              id={`${prefix}-${f.name}`}
              draftId={selected.id}
              label={`${f.label}${f.required ? " *" : ""}`}
              value={valueOf(row[f.name])}
              numeric={f.kind === "integer"}
              departmentOnly={f.geography === "department"}
              countries={countries}
              initial={geography[fieldPath]}
              disabled={!activeDraft || !editable}
              call={call}
              onChange={(value, scope) => {
                updateValue(value);
                setGeography((previous) => ({
                  ...previous,
                  [fieldPath]: scope,
                }));
                setDirty(true);
              }}
            />
          );
        return options.length || f.catalog || f.options.length ? (
          <div key={f.name}>
            <SelectField
              id={`${prefix}-${f.name}`}
              label={`${f.label}${f.required ? " *" : ""}`}
              value={valueOf(row[f.name])}
              disabled={
                !activeDraft || !editable || (!!f.catalog && !options.length)
              }
              options={[
                {
                  value: "",
                  label:
                    f.catalog && !options.length
                      ? "Catálogo de SIIE pendiente"
                      : "Selecciona una opción",
                },
                ...options.map((v) => ({
                  value: String(v.value),
                  label: v.label,
                })),
              ]}
              onChange={(e) => updateValue(e.target.value)}
            />
            {f.catalog && !options.length && (
              <small>
                Falta conectar el catálogo de {f.catalog}. No se deducen
                identificadores.
              </small>
            )}
          </div>
        ) : (
          <Field
            key={f.name}
            id={`${prefix}-${f.name}`}
            label={`${f.label}${f.required ? " *" : ""}`}
            value={valueOf(row[f.name])}
            type={
              f.kind === "date" ? "date" : f.kind === "email" ? "email" : "text"
            }
            maxLength={f.max_length}
            disabled={!activeDraft || !editable}
            onChange={(e) => updateValue(e.target.value)}
          />
        );
      })}
    </div>
  );

  return (
    <section
      className="siie-registration"
      aria-label="Inscripción y recepción de SIIE"
    >
      <header className="siie-registration-heading">
        <div>
          <span className="operations-eyebrow">ADMISIONES · SIIE</span>
          <h3>Del interés a la inscripción</h3>
          <p>
            Preinscritos en CRM, inscritos identificados y documentos
            conservados en SIIE.
          </p>
        </div>
        <Button
          variant="secondary"
          disabled={task.busy || configurationDirty}
          onClick={() => void task.run(refresh, "Estado actualizado")}
        >
          Actualizar estado
        </Button>
      </header>
      {task.notices}
      {status && editable && (
        <SiiePreicfes environment={status.environment} editable={editable} />
      )}
      {!status ? (
        <Notice>Cargando preparación de SIIE…</Notice>
      ) : (
        <>
          <div className="siie-registration-summary">
            <span>
              {status.api_configured
                ? "Clave única configurada"
                : "Conexión pendiente"}
            </span>
            <span>
              {status.webhook_enabled
                ? "Recepción habilitada"
                : "Recepción pendiente de habilitar"}
            </span>
            <span>
              {status.writes_enabled
                ? "Envíos revisados habilitados"
                : "Envíos finales desactivados"}
            </span>
          </div>
          <SiieWebhookReadiness status={status} />
          {configurationDirty && (
            <Notice>
              Hay cambios de preparación sin guardar. Guárdalos o descártalos
              antes de actualizar el estado.
            </Notice>
          )}
          <details>
            <summary>Conexión del webhook y permisos de operación</summary>
            <p>Comparte esta dirección con el desarrollador de SIIE:</p>
            <code>
              {window.location.origin}
              {status.webhook_path}
            </code>
            <p>
              El emisor debe firmar cada evento, conservar su identificador al
              reintentar y distinguir preinscripción de inscripción. La ficha y
              el bloqueo de promociones se guardan antes de confirmar recepción.
            </p>
            {!status.webhook_secret_configured && (
              <Notice>
                Falta SIIE_WEBHOOK_SECRET en Runtime del backend. Es la clave de
                firma del webhook; la API de SIIE conserva su clave única
                actual.
              </Notice>
            )}
            <SelectField
              id="siie-initial-stage"
              label="Etapa inicial de los preinscritos de SIIE"
              value={configuration?.stage_key ?? status.stage_key}
              disabled={!configurable || task.busy}
              options={[
                { value: "", label: "Selecciona la etapa" },
                ...status.stages.map((v) => ({ value: v.key, label: v.label })),
              ]}
              onChange={(e) =>
                setConfiguration({
                  ...(configuration ?? status),
                  stage_key: e.target.value,
                })
              }
            />
            <label>
              <input
                type="checkbox"
                checked={
                  configuration?.webhook_enabled ?? status.webhook_enabled
                }
                disabled={
                  task.busy ||
                  !configurable ||
                  (!(
                    configuration?.webhook_enabled ?? status.webhook_enabled
                  ) &&
                    (!status.webhook_secret_configured ||
                      !status.stages.some(
                        (stage) =>
                          stage.key ===
                          (configuration?.stage_key ?? status.stage_key),
                      )))
                }
                onChange={(e) =>
                  setConfiguration({
                    ...(configuration ?? status),
                    webhook_enabled: e.target.checked,
                  })
                }
              />{" "}
              Recibir eventos firmados de SIIE
            </label>
            <label>
              <input
                type="checkbox"
                checked={configuration?.writes_enabled ?? status.writes_enabled}
                disabled={task.busy || !configurable}
                onChange={(e) =>
                  setConfiguration({
                    ...(configuration ?? status),
                    writes_enabled: e.target.checked,
                  })
                }
              />{" "}
              Habilitar envíos finales revisados a SIIE
            </label>
            {configurable && (
              <div className="siie-registration-actions">
                <Button
                  disabled={task.busy || !configurationDirty}
                  onClick={() =>
                    void task.run(async () => {
                      await call(`${base}/configuration`, "PUT", {
                        revision: status.revision,
                        webhook_enabled:
                          configuration?.webhook_enabled ??
                          status.webhook_enabled,
                        writes_enabled:
                          configuration?.writes_enabled ??
                          status.writes_enabled,
                        stage_key: configuration?.stage_key ?? status.stage_key,
                      });
                      await refresh();
                    }, "Configuración guardada")
                  }
                >
                  Guardar preparación de SIIE
                </Button>
                <Button
                  variant="quiet"
                  disabled={task.busy || !configurationDirty}
                  onClick={() => setConfiguration(status)}
                >
                  Descartar cambios de preparación
                </Button>
              </div>
            )}
          </details>
          <div className="siie-registration-grid">
            <aside>
              <h4>Solicitudes y borradores</h4>
              <div className="siie-registration-list">
                {drafts.map((row) => (
                  <Button
                    key={row.id}
                    variant="secondary"
                    aria-pressed={selected?.id === row.id}
                    disabled={task.busy || dirty || !editable}
                    onClick={() => void task.run(() => open(row.id), "")}
                  >
                    <strong>{row.program_name || "Solicitud SIIE"}</strong>
                    <span>
                      {row.kind === "applicant" ? "Aspirante" : "Inscripción"} ·{" "}
                      {states[row.state ?? ""] ?? row.state}
                    </span>
                  </Button>
                ))}
                {!drafts.length && <p>No hay solicitudes guardadas.</p>}
              </div>
              {editable && (
                <details>
                  <summary>Preparar nueva solicitud</summary>
                  <SelectField
                    id="siie-new-kind"
                    label="Tipo de solicitud"
                    value={newKind}
                    options={[
                      { value: "applicant", label: "Alta de aspirante" },
                      { value: "registration", label: "Inscripción completa" },
                    ]}
                    onChange={(e) =>
                      setNewKind(e.target.value as typeof newKind)
                    }
                  />
                  <Button
                    variant="secondary"
                    disabled={task.busy || dirty}
                    onClick={() => void task.run(() => loadPrograms(), "")}
                  >
                    Consultar programas ofrecidos
                  </Button>
                  <SelectField
                    id="siie-register-program"
                    label="Programa de SIIE"
                    value={programId}
                    options={[
                      { value: "", label: "Selecciona un programa" },
                      ...programs.map((v) => ({
                        value: valueOf(v.program_id),
                        label: valueOf(v.name),
                      })),
                    ]}
                    disabled={task.busy}
                    onChange={(e) => {
                      if (e.target.value)
                        void task.run(() => loadOffers(e.target.value), "");
                    }}
                  />
                  {nextPrograms && (
                    <Button
                      variant="quiet"
                      disabled={task.busy}
                      onClick={() =>
                        void task.run(() => loadPrograms(nextPrograms), "")
                      }
                    >
                      Más programas de SIIE
                    </Button>
                  )}
                  <SelectField
                    id="siie-register-offer"
                    label="Oferta vigente"
                    value={offerRef}
                    options={[
                      { value: "", label: "Selecciona una oferta" },
                      ...offers.map((v) => ({
                        value: valueOf(v.offer_id),
                        label: `${valueOf(v.period_name)} · ${valueOf(v.schedule)} · Nivel ${valueOf(v.level)}`,
                      })),
                    ]}
                    disabled={task.busy}
                    onChange={(e) => setOfferRef(e.target.value)}
                  />
                  {nextOffers && (
                    <Button
                      variant="quiet"
                      disabled={task.busy}
                      onClick={() =>
                        void task.run(
                          () => loadOffers(programId, nextOffers),
                          "",
                        )
                      }
                    >
                      Más ofertas
                    </Button>
                  )}
                  <Button
                    disabled={task.busy || !offerRef || dirty}
                    onClick={() => void task.run(create, "Borrador preparado")}
                  >
                    Crear borrador protegido
                  </Button>
                </details>
              )}
            </aside>
            <div>
              {!selected ? (
                <div className="siie-registration-empty">
                  <h4>Un proceso revisado, con su recibo</h4>
                  <p>
                    Selecciona una solicitud o prepara un borrador. El guardado
                    conserva la información en RinovaPlus; el envío final
                    requiere una revisión adicional.
                  </p>
                </div>
              ) : (
                <>
                  <h4>{selected.context.program_name}</h4>
                  {selected.environment_current === false && (
                    <Notice>
                      Solicitud de otro entorno o anterior a esta verificación.
                      Se conserva en consulta; prepara una nueva solicitud con
                      los catálogos actuales para realizar otra operación.
                    </Notice>
                  )}
                  <p>
                    {selected.context.schedule} ·{" "}
                    {states[selected.state] ?? selected.state}
                  </p>
                  {result &&
                    !["draft", "rejected", "confirmed"].includes(
                      result.state,
                    ) && (
                      <Notice error>
                        El resultado requiere conciliación con SIIE. No repitas
                        el envío. Referencia:{" "}
                        {result.correlation_id ||
                          selected.pending_operation ||
                          selected.id}
                        .
                      </Notice>
                    )}
                  {missing.length > 0 && (
                    <Notice>
                      Catálogos pendientes: {missing.join(", ")}. Puedes guardar
                      el borrador; los campos dependientes requieren datos
                      reales de SIIE antes del envío.
                    </Notice>
                  )}
                  {!!result?.references?.length && (
                    <details>
                      <summary>Referencias para conciliar con SIIE</summary>
                      <p>
                        Estos registros existentes no confirman que el último
                        formulario se haya guardado. No repitas la operación sin
                        revisar su resultado.
                      </p>
                      {result.references.map((reference, index) => (
                        <dl key={index}>
                          {Object.entries(referenceLabels)
                            .filter(
                              ([key]) => typeof reference[key] === "number",
                            )
                            .map(([key, label]) => (
                              <div key={key}>
                                <dt>{label}</dt>
                                <dd>{reference[key]}</dd>
                              </div>
                            ))}
                        </dl>
                      ))}
                    </details>
                  )}
                  {!allowsCreation &&
                    selected.environment_current !== false && (
                      <Notice error>
                        El período consultado permite revisión histórica, pero
                        SIIE no permite crear una inscripción en él.
                      </Notice>
                    )}
                  {selected.kind === "applicant"
                    ? renderFields(
                        status.applicant_fields,
                        form,
                        (row) => {
                          setForm(row);
                          setDirty(true);
                        },
                        "siie-applicant",
                      )
                    : status.schema.map((section, i) => {
                        const enabled = section.name in form;
                        const values = form[section.name] as
                          Values | Values[] | undefined;
                        const rows = section.max_items
                          ? Array.isArray(values)
                            ? values
                            : [{}]
                          : [values && !Array.isArray(values) ? values : {}];
                        return (
                          <details
                            key={section.name}
                            open={i === 0}
                            className="siie-registration-section"
                          >
                            <summary>
                              {i + 1}. {section.label}
                              {section.optional ? " · Opcional" : ""}
                            </summary>
                            {section.optional && (
                              <label>
                                <input
                                  type="checkbox"
                                  checked={enabled}
                                  disabled={!activeDraft || !editable}
                                  onChange={(e) => {
                                    setForm((previous) => {
                                      const next = { ...previous };
                                      if (e.target.checked)
                                        next[section.name] = section.max_items
                                          ? [{}]
                                          : {};
                                      else delete next[section.name];
                                      return next;
                                    });
                                    setDirty(true);
                                  }}
                                />{" "}
                                Esta sección aplica a la persona
                              </label>
                            )}
                            {(!section.optional || enabled) &&
                              rows.map((row, index) => (
                                <fieldset key={index}>
                                  <legend>
                                    {section.label}
                                    {section.max_items ? ` ${index + 1}` : ""}
                                  </legend>
                                  {renderFields(
                                    section.fields,
                                    row,
                                    (value) => {
                                      if (section.max_items) {
                                        const next = [...rows];
                                        next[index] = value;
                                        setForm((previous) => ({
                                          ...previous,
                                          [section.name]: next,
                                        }));
                                        setDirty(true);
                                      } else change(section.name, value);
                                    },
                                    `siie-${section.name}-${index}`,
                                    `${section.name}.${section.max_items ? `${index}.` : ""}`,
                                  )}
                                  {section.max_items && index > 0 && (
                                    <Button
                                      variant="quiet"
                                      disabled={!activeDraft || !editable}
                                      onClick={() => {
                                        setGeoVersion((v) => v + 1);
                                        setGeography((previous) =>
                                          Object.fromEntries(
                                            Object.entries(previous).flatMap(
                                              ([key, scope]) => {
                                                const match = key.match(
                                                  new RegExp(
                                                    `^${section.name}\\.(\\d)\\.(.+)$`,
                                                  ),
                                                );
                                                if (!match)
                                                  return [[key, scope]];
                                                const position = Number(
                                                  match[1],
                                                );
                                                return position === index
                                                  ? []
                                                  : [
                                                      [
                                                        `${section.name}.${position > index ? position - 1 : position}.${match[2]}`,
                                                        scope,
                                                      ],
                                                    ];
                                              },
                                            ),
                                          ),
                                        );
                                        setForm({
                                          ...form,
                                          [section.name]: rows.filter(
                                            (_, j) => j !== index,
                                          ),
                                        });
                                        setDirty(true);
                                      }}
                                    >
                                      Quitar registro {index + 1}
                                    </Button>
                                  )}
                                </fieldset>
                              ))}
                            {section.max_items &&
                              (!section.optional || enabled) &&
                              rows.length < section.max_items && (
                                <Button
                                  variant="secondary"
                                  disabled={!activeDraft || !editable}
                                  onClick={() => {
                                    setForm({
                                      ...form,
                                      [section.name]: [...rows, {}],
                                    });
                                    setDirty(true);
                                  }}
                                >
                                  Añadir registro de{" "}
                                  {section.label.toLowerCase()}
                                </Button>
                              )}
                          </details>
                        );
                      })}
                  {selected.kind === "registration" && (
                    <>
                      <TextArea
                        id="siie-condition"
                        label="Condición psicomotora o cognitiva, si aplica"
                        value={valueOf(form.condicion)}
                        maxLength={4000}
                        disabled={!activeDraft || !editable}
                        onChange={(e) => {
                          setForm({ ...form, condicion: e.target.value });
                          setDirty(true);
                        }}
                      />
                      <label>
                        <input
                          type="checkbox"
                          checked={form.aceptaTratamientoDatos === true}
                          disabled={!activeDraft || !editable}
                          onChange={(e) => {
                            setForm({
                              ...form,
                              aceptaTratamientoDatos: e.target.checked,
                            });
                            setDirty(true);
                          }}
                        />{" "}
                        La persona aceptó el tratamiento de datos del formulario
                        de SIIE
                      </label>
                      <small>
                        Registra la aceptación de la persona; este campo no
                        concede consentimiento comercial.
                      </small>
                    </>
                  )}
                  <div className="siie-registration-actions">
                    {activeDraft && editable && (
                      <Button
                        disabled={task.busy || !dirty}
                        onClick={() => void task.run(save, "Borrador guardado")}
                      >
                        Guardar borrador
                      </Button>
                    )}
                    <Button
                      variant="secondary"
                      disabled={
                        task.busy ||
                        dirty ||
                        !editable ||
                        selected.environment_current === false
                      }
                      onClick={() =>
                        void task.run(
                          loadRequirements,
                          "Requisitos consultados",
                        )
                      }
                    >
                      Consultar documentos de la oferta
                    </Button>
                  </div>
                  {requirements && (
                    <section>
                      <h4>Documentos en SIIE</h4>
                      <p>
                        Hasta 10 MiB por archivo y 50 MiB en total. La
                        fotografía admite JPG o PNG; los demás también PDF.
                      </p>
                      {requirements.map((item) => (
                        <div
                          className="siie-registration-document"
                          key={item.idDocumento}
                        >
                          <strong>{item.nombre}</strong>
                          <span>
                            {item.obligatorioAlInscribir
                              ? "Obligatorio inicial"
                              : "Entrega posterior"}{" "}
                            ·{" "}
                            {item.recibido == null
                              ? "Entrega sin consultar para una persona"
                              : item.recibido
                                ? "Entrega registrada"
                                : "Sin marca de entrega"}{" "}
                            ·{" "}
                            {item.archivoExistente == null
                              ? "Archivo sin comprobar"
                              : item.archivoExistente
                                ? "Archivo encontrado"
                                : "Archivo no acreditado"}
                            {item.aplica === null
                              ? " · Aplicación pendiente de edad"
                              : item.aplica === false
                                ? " · No aplica"
                                : ""}
                          </span>
                          {editable &&
                            item.soportado &&
                            item.aplica !== false &&
                            !item.recibido && (
                              <Field
                                id={`siie-document-${item.idDocumento}`}
                                label={`Adjuntar ${item.nombre}`}
                                type="file"
                                accept={
                                  item.idDocumento === 5
                                    ? ".jpg,.jpeg,.png"
                                    : ".pdf,.jpg,.jpeg,.png"
                                }
                                disabled={task.busy || dirty}
                                onChange={(e) => {
                                  const file = e.target.files?.[0];
                                  if (file && file.size <= 10 * 1024 * 1024)
                                    setFiles((previous) => ({
                                      ...previous,
                                      [item.idDocumento]: file,
                                    }));
                                  else if (file)
                                    void task.run(async () => {
                                      throw Error("El archivo supera 10 MiB.");
                                    }, "");
                                }}
                              />
                            )}
                        </div>
                      ))}
                    </section>
                  )}
                  {editable && (
                    <Button
                      disabled={
                        task.busy ||
                        dirty ||
                        !status.writes_enabled ||
                        selected.environment_current === false ||
                        (!allowsCreation && activeDraft) ||
                        !(
                          activeDraft ||
                          (selected.state === "confirmed" &&
                            selected.kind === "registration")
                        ) ||
                        (selected.kind === "registration" &&
                          activeDraft &&
                          (missing.includes("generos") ||
                            missing.includes("estudiante.Id_Genero")))
                      }
                      onClick={() => {
                        setReview(
                          selected.state === "confirmed"
                            ? "documents"
                            : "submit",
                        );
                        setOperation(crypto.randomUUID());
                      }}
                    >
                      Revisar envío a SIIE
                    </Button>
                  )}
                  {review && (
                    <section
                      className="panel"
                      aria-label="Revisión final de SIIE"
                    >
                      <h4>Confirma esta solicitud</h4>
                      <p>
                        {review === "documents"
                          ? "Se enviarán únicamente los anexos seleccionados."
                          : selected.kind === "applicant"
                            ? "Se creará un aspirante, sin inscripción ni matrícula."
                            : "Se enviarán las once secciones aplicables y sus anexos. La inscripción no crea matrícula académica, cobros ni cuenta de acceso."}
                      </p>
                      <dl>
                        {(selected.kind === "applicant"
                          ? [
                              {
                                label: "Aspirante",
                                fields: status.applicant_fields,
                                values: form,
                              },
                            ]
                          : status.schema.flatMap((s) => {
                              const values = form[s.name];
                              if (!values) return [];
                              return (
                                Array.isArray(values) ? values : [values]
                              ).map((v) => ({
                                label: s.label,
                                fields: s.fields,
                                values: v as Values,
                              }));
                            })
                        ).map((s, i) => (
                          <div key={i}>
                            <dt>{s.label}</dt>
                            <dd>
                              {s.fields
                                .filter(
                                  (f) =>
                                    s.values[f.name] != null &&
                                    s.values[f.name] !== "",
                                )
                                .map(
                                  (f) =>
                                    `${f.label}: ${valueOf(s.values[f.name])}`,
                                )
                                .join(" · ")}
                            </dd>
                          </div>
                        ))}
                      </dl>
                      <p>
                        {Object.keys(files).length} archivos seleccionados. Ante
                        un resultado incierto, la solicitud quedará bloqueada
                        para conciliación.
                      </p>
                      <Button
                        disabled={task.busy}
                        onClick={() =>
                          void task.run(submit, "Resultado de SIIE consultado")
                        }
                      >
                        Confirmar envío a SIIE
                      </Button>
                      <Button
                        variant="quiet"
                        disabled={task.busy}
                        onClick={() => setReview(null)}
                      >
                        Volver al borrador
                      </Button>
                    </section>
                  )}
                </>
              )}
            </div>
          </div>
          <SiieWebhookReceipts refreshKey={refreshKey} />
        </>
      )}
    </section>
  );
}
