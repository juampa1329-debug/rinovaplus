import { useEffect, useEffectEvent, useRef, useState } from "react";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import {
  institutionHeaders,
  institutionUnauthorized,
} from "../shared/institutionSession";
import { useInstitution, useTask } from "./api";
import "./siieRegistration.css";

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
};
type Section = {
  name: string;
  label: string;
  optional?: boolean;
  max_items?: number;
  fields: FieldSpec[];
};
type Status = {
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
  id: string;
  revision: number;
  kind: "applicant" | "registration";
  state: string;
  form: Values;
  context: Context;
  result?: Result;
  last_result?: Result;
  pending_operation?: string;
};
type Result = {
  state: string;
  code: string;
  correlation_id?: string | null;
  data?: Values;
  revision?: number;
  operation_id?: string;
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
const eventTypes: Record<string, string> = {
  "pre_registration.created": "Preinscripción nueva",
  "pre_registration.updated": "Preinscripción actualizada",
  "applicant.created": "Aspirante nuevo",
  "registration.created": "Inscripción nueva",
  "registration.updated": "Inscripción actualizada",
  "documents.updated": "Documentos actualizados",
};
const valueOf = (value: unknown) => (value == null ? "" : String(value));

export function SiieRegistration() {
  const { call, session } = useInstitution();
  const task = useTask();
  const [status, setStatus] = useState<Status | null>(null);
  const [drafts, setDrafts] = useState<RecordRow[]>([]);
  const [events, setEvents] = useState<RecordRow[]>([]);
  const [selected, setSelected] = useState<Draft | null>(null);
  const [form, setForm] = useState<Values>({});
  const [dirty, setDirty] = useState(false);
  const [catalogs, setCatalogs] = useState<Record<string, Choice[]>>({});
  const [missing, setMissing] = useState<string[]>([]);
  const [requirements, setRequirements] = useState<Requirements[] | null>(null);
  const [files, setFiles] = useState<Record<number, File>>({});
  const [review, setReview] = useState<"submit" | "documents" | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [operation, setOperation] = useState("");
  const [event, setEvent] = useState<Values | null>(null);
  const [eventId, setEventId] = useState("");
  const [candidates, setCandidates] = useState<
    { id: string; name: string; phone: string }[]
  >([]);
  const [candidateId, setCandidateId] = useState("");
  const [linkReviewed, setLinkReviewed] = useState(false);
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
    !!selected && ["draft", "rejected"].includes(selected.state);
  const refresh = async () => {
    const [s, d, e] = await Promise.all([
      call<Status>(`${base}/status`),
      call<{ items: RecordRow[] }>(`${base}/records/sd`),
      call<{ items: RecordRow[] }>(`${base}/records/se`),
    ]);
    setStatus(s);
    setDrafts(d.items);
    setEvents(e.items);
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
    const choices = await call<{
      items: Record<string, Choice[]>;
      missing: string[];
    }>(`${base}/catalogs?draft_id=${id}`);
    if (ticket !== epoch.current) return;
    setSelected(draft);
    setForm(draft.form);
    setCatalogs(choices.items);
    setMissing(choices.missing);
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
        headers: { "X-CRM-Local": "1", ...institutionHeaders() },
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
  ) => (
    <div className="form-grid">
      {fields.map((f) => {
        const options = f.catalog
          ? (catalogs[f.catalog] ?? [])
          : f.options.map((v) => ({ value: v, label: String(v) }));
        const updateValue = (value: string) =>
          update({
            ...row,
            [f.name]:
              f.kind === "integer" && value !== "" ? Number(value) : value,
          });
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
          disabled={task.busy}
          onClick={() => void task.run(refresh, "Estado actualizado")}
        >
          Actualizar estado
        </Button>
      </header>
      {task.notices}
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
              value={status.stage_key}
              disabled={!configurable || task.busy}
              options={[
                { value: "", label: "Selecciona la etapa" },
                ...status.stages.map((v) => ({ value: v.key, label: v.label })),
              ]}
              onChange={(e) =>
                setStatus({ ...status, stage_key: e.target.value })
              }
            />
            <label>
              <input
                type="checkbox"
                checked={status.webhook_enabled}
                disabled={!configurable || !status.webhook_secret_configured}
                onChange={(e) =>
                  setStatus({ ...status, webhook_enabled: e.target.checked })
                }
              />{" "}
              Recibir eventos firmados de SIIE
            </label>
            <label>
              <input
                type="checkbox"
                checked={status.writes_enabled}
                disabled={!configurable}
                onChange={(e) =>
                  setStatus({ ...status, writes_enabled: e.target.checked })
                }
              />{" "}
              Habilitar envíos finales revisados a SIIE
            </label>
            {configurable && (
              <Button
                disabled={task.busy}
                onClick={() =>
                  void task.run(async () => {
                    await call(`${base}/configuration`, "PUT", {
                      revision: status.revision,
                      webhook_enabled: status.webhook_enabled,
                      writes_enabled: status.writes_enabled,
                      stage_key: status.stage_key,
                    });
                    await refresh();
                  }, "Configuración guardada")
                }
              >
                Guardar preparación de SIIE
              </Button>
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
                    disabled={task.busy || dirty}
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
                                  )}
                                  {section.max_items && index > 0 && (
                                    <Button
                                      variant="quiet"
                                      disabled={!activeDraft || !editable}
                                      onClick={() => {
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
                      disabled={task.busy || dirty}
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
                        !(
                          activeDraft ||
                          (selected.state === "confirmed" &&
                            selected.kind === "registration")
                        ) ||
                        (selected.kind === "registration" &&
                          activeDraft &&
                          missing.includes("generos"))
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
          <section>
            <h4>Recepción desde SIIE</h4>
            <p>
              Los inscritos quedan fuera de promociones. Las coincidencias con
              contactos existentes se conservan para revisar el vínculo.
            </p>
            <div className="siie-registration-list">
              {events.map((row) => (
                <Button
                  key={row.id}
                  variant="secondary"
                  disabled={task.busy}
                  onClick={() =>
                    void task.run(async () => {
                      const value = await call<{
                        event: Values;
                        candidates: typeof candidates;
                      }>(`${base}/records/se/${row.id}`);
                      setEvent(value.event);
                      setEventId(row.id);
                      setCandidates(value.candidates);
                      setCandidateId("");
                      setLinkReviewed(false);
                    }, "")
                  }
                >
                  <strong>
                    {eventTypes[row.event_type ?? ""] ?? row.event_type}
                  </strong>
                  <span>
                    {row.projection === "created"
                      ? "Contacto creado en CRM"
                      : row.projection === "linked"
                        ? "Vínculo actualizado"
                        : row.projection === "stale_ignored"
                          ? "Evento anterior conservado"
                          : "Vínculo por revisar"}
                  </span>
                </Button>
              ))}
              {!events.length && <p>No se han recibido eventos verificados.</p>}
            </div>
            {event && (
              <div className="panel">
                <h4>{eventTypes[valueOf(event.event_type)]}</h4>
                <p>
                  {valueOf((event.persona as Values | undefined)?.nombres)}{" "}
                  {valueOf(
                    (event.persona as Values | undefined)?.primerApellido,
                  )}{" "}
                  · {valueOf(event.programa)}
                </p>
                <p>
                  {valueOf(event.event_type).startsWith("registration.")
                    ? "Inscrito en SIIE · Sin promociones"
                    : "Origen SIIE"}
                </p>
                {editable && candidates.length > 0 && (
                  <section aria-label="Revisión del vínculo de SIIE">
                    <SelectField
                      id="siie-link-candidate"
                      label="Contacto existente que corresponde a esta persona"
                      value={candidateId}
                      options={[
                        { value: "", label: "Selecciona después de verificar" },
                        ...candidates.map((v) => ({
                          value: v.id,
                          label: `${v.name} · ${v.phone}`,
                        })),
                      ]}
                      onChange={(e) => {
                        setCandidateId(e.target.value);
                        setLinkReviewed(false);
                      }}
                    />
                    <label>
                      <input
                        type="checkbox"
                        checked={linkReviewed}
                        onChange={(e) => setLinkReviewed(e.target.checked)}
                      />{" "}
                      Verifiqué que la inscripción y el contacto pertenecen a la
                      misma persona
                    </label>
                    <Button
                      disabled={task.busy || !candidateId || !linkReviewed}
                      onClick={() =>
                        void task.run(async () => {
                          await call(`${base}/events/${eventId}/link`, "POST", {
                            contact_id: candidateId,
                            reviewed: true,
                          });
                          setCandidates([]);
                          await refresh();
                        }, "Vínculo de SIIE confirmado")
                      }
                    >
                      Confirmar vínculo con el contacto
                    </Button>
                  </section>
                )}
                <Button variant="quiet" onClick={() => setEvent(null)}>
                  Cerrar detalle del evento
                </Button>
              </div>
            )}
          </section>
        </>
      )}
    </section>
  );
}
