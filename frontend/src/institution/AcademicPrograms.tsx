import { useEffect, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { useIntent, useTask } from "./api";
import { allowNavigation, useDraftGuard } from "./drafts";
import { SiieWorkspace, type SiieLocalDraft } from "./SiieWorkspace";
import { ErrorFeedback } from "./ErrorFeedback";

type Commercial = {
  price_valid_from?: string | null;
  full_cost_cash_cop?: number | null;
  cost_inclusions?: string;
  cost_exclusions?: string;
  siie_offer_id?: string;
  siie_program_id?: string;
  siie_period_id?: string;
  siie_campus_id?: string;
  siie_shift_id?: string;
  siie_source_revision?: string;
  financial_plans?: {
    external_id: string;
    name: string;
    valid_from: string | null;
    valid_until: string | null;
    initial_payment_cop: number | null;
    initial_payment_due_date: string | null;
    total_cost_cop: number | null;
    installments: {
      number: number;
      amount_cop: number | null;
      due_date: string | null;
    }[];
    conditions: string;
  }[];
  aliases: string;
  duration: string;
  modality: string;
  syllabus: string;
  requirements: string;
  price_cop: number | null;
  price_concept: string;
  price_valid_until: string | null;
  source_url: string;
  source_checked_at: string;
  source_note?: string;
  siie_offer_active?: boolean | null;
};
type Draft = {
  name: string;
  school: string;
  schedule: string;
  commercial: Commercial;
};
type Item = { program_id: number; name: string; school: string };
type Program = {
  exists: boolean;
  revision: number;
  program: {
    Name: string;
    School: string;
    Schedule: string;
    Active: boolean;
  } | null;
  commercial: Commercial | null;
  siie_source?: SiieLocalDraft["source"] | null;
};

const empty: Draft = {
  name: "",
  school: "",
  schedule: "",
  commercial: {
    aliases: "",
    duration: "",
    modality: "",
    syllabus: "",
    requirements: "",
    price_cop: null,
    price_concept: "",
    price_valid_until: null,
    source_url: "",
    source_checked_at: "",
  },
};

async function listPrograms() {
  const results: Item[] = [];
  while (true) {
    const page = await api<{ items: Item[]; has_more: boolean }>(
      `/programs?offset=${results.length}`,
    );
    results.push(...page.items);
    if (!page.has_more || !page.items.length) break;
  }
  return results.sort((a, b) => a.name.localeCompare(b.name, "es"));
}

function mergeImport(draft: Draft, result: Draft): Draft {
  const commercial = { ...draft.commercial };
  for (const key of [
    "aliases",
    "duration",
    "modality",
    "syllabus",
    "requirements",
    "source_url",
    "source_checked_at",
  ] as const)
    if (result.commercial[key]) commercial[key] = result.commercial[key];
  if (result.commercial.price_cop !== null) {
    commercial.price_cop = result.commercial.price_cop;
    commercial.price_concept = result.commercial.price_concept;
    commercial.price_valid_until = result.commercial.price_valid_until;
  }
  if (result.commercial.siie_offer_id) {
    Object.assign(commercial, {
      price_cop: result.commercial.price_cop,
      price_concept: result.commercial.price_concept,
      price_valid_until: result.commercial.price_valid_until,
      price_valid_from: result.commercial.price_valid_from,
      full_cost_cash_cop: result.commercial.full_cost_cash_cop,
      financial_plans: result.commercial.financial_plans,
      cost_inclusions: result.commercial.cost_inclusions,
      cost_exclusions: result.commercial.cost_exclusions,
      siie_offer_id: result.commercial.siie_offer_id,
      siie_program_id: result.commercial.siie_program_id,
      siie_period_id: result.commercial.siie_period_id,
      siie_campus_id: result.commercial.siie_campus_id,
      siie_shift_id: result.commercial.siie_shift_id,
      siie_source_revision: result.commercial.siie_source_revision,
    });
  }
  return {
    name: result.name || draft.name,
    school: result.school || draft.school,
    schedule: result.schedule || draft.schedule,
    commercial,
  };
}

function importChanges(draft: Draft, result: Draft) {
  const next = mergeImport(draft, result);
  const before = draft.commercial;
  const after = next.commercial;
  const values: [string, string | number | null, string | number | null][] = [
    ["Nombre oficial", draft.name, next.name],
    ["Escuela", draft.school, next.school],
    ["Jornada", draft.schedule, next.schedule],
    ["Otros nombres o alias", before.aliases, after.aliases],
    ["Duración", before.duration, after.duration],
    ["Modalidad", before.modality, after.modality],
    ["Precio en COP", before.price_cop, after.price_cop],
    ["Concepto de la tarifa", before.price_concept, after.price_concept],
    [
      "Vigencia de la tarifa",
      before.price_valid_until,
      after.price_valid_until,
    ],
    ["Materias o módulos", before.syllabus, after.syllabus],
    ["Requisitos", before.requirements, after.requirements],
    [
      "Costo total de contado",
      before.full_cost_cash_cop ?? null,
      after.full_cost_cash_cop ?? null,
    ],
    ["Oferta SIIE", before.siie_offer_id ?? null, after.siie_offer_id ?? null],
    [
      "Revisión SIIE",
      before.siie_source_revision ?? null,
      after.siie_source_revision ?? null,
    ],
    [
      "Planes financiados",
      before.financial_plans
        ?.map((v) => `${v.name}: ${v.total_cost_cop} COP`)
        .join("; ") ?? null,
      after.financial_plans
        ?.map((v) => `${v.name}: ${v.total_cost_cop} COP`)
        .join("; ") ?? null,
    ],
  ];
  return values.filter(([, oldValue, value]) => oldValue !== value);
}

export function AcademicPrograms() {
  return (
    <ErrorFeedback
      explain={(failure) => ({
        title: "No se pudo completar la ficha académica",
        detail: failure.message,
        nextStep:
          "Revisa los campos señalados. Las fechas pueden quedar vacías. Si informas abono, cuotas y total, sus valores deben coincidir. Si SIIE cambió, vuelve a preparar la sincronización; tus datos locales se conservan.",
      })}
    >
      <AcademicProgramsContent />
    </ErrorFeedback>
  );
}

function AcademicProgramsContent() {
  const task = useTask();
  const intent = useIntent();
  const [items, setItems] = useState<Item[] | null>(null);
  const [listError, setListError] = useState("");
  const [school, setSchool] = useState("");
  const [id, setId] = useState<number | null>(null);
  const [revision, setRevision] = useState(0);
  const [draft, setDraft] = useState(empty);
  const [saved, setSaved] = useState(empty);
  const [url, setUrl] = useState("");
  const [siieOffer, setSiieOffer] = useState("");
  const [extracted, setExtracted] = useState<Draft | null>(null);
  const [sync, setSync] = useState<Record<string, string> | null>(null);
  const [source, setSource] = useState<SiieLocalDraft["source"] | null>(null);
  const [manualFields, setManualFields] = useState<string[]>([]);
  useDraftGuard(JSON.stringify(draft) !== JSON.stringify(saved));

  useEffect(() => {
    let active = true;
    void listPrograms().then(
      (value) => {
        if (active) setItems(value);
      },
      (error) => {
        if (active) setListError(error.message);
      },
    );
    return () => {
      active = false;
    };
  }, []);

  const schools = [
    ...new Set(
      (items ?? []).map((item) => item.school || "Sin escuela asignada"),
    ),
  ].sort((a, b) => a.localeCompare(b, "es"));
  const setCommercial = <K extends keyof Commercial>(
    key: K,
    value: Commercial[K],
  ) =>
    setDraft((current) => ({
      ...current,
      commercial: { ...current.commercial, [key]: value },
    }));
  const open = (next: number | null) => {
    if (task.busy || !allowNavigation()) return;
    intent.clear();
    void task.run(async () => {
      let selected = empty;
      let nextRevision = 0;
      if (next !== null) {
        const entry = await api<Program>(`/programs/${next}`);
        if (!entry.program)
          throw new Error(
            "El programa ya no está disponible. Actualiza la lista.",
          );
        nextRevision = entry.revision;
        setSource(entry.siie_source ?? null);
        selected = {
          name: entry.program.Name,
          school: entry.program.School,
          schedule: entry.program.Schedule,
          commercial: { ...empty.commercial, ...entry.commercial },
        };
      }
      setId(next);
      setRevision(nextRevision);
      setDraft(selected);
      setSaved(selected);
      setUrl(selected.commercial.source_url);
      setExtracted(null);
      if (next === null) setSource(null);
      setSync(null);
      setManualFields([]);
    }, "");
  };
  const commercial = draft.commercial;
  const changes = extracted ? importChanges(draft, extracted) : [];
  const receiveSiie = async (result: SiieLocalDraft) => {
    if (!allowNavigation()) return;
    const entry = result.local_program_id
      ? await api<Program>(`/programs/${result.local_program_id}`)
      : null;
    if (entry && entry.revision !== result.local_revision)
      throw new Error(
        "La ficha cambió. Vuelve a preparar la sincronización para revisar la versión nueva.",
      );
    const previous = entry?.program
      ? {
          name: entry.program.Name,
          school: entry.program.School,
          schedule: entry.program.Schedule,
          commercial: { ...empty.commercial, ...entry.commercial },
        }
      : empty;
    setId(result.local_program_id ?? null);
    setRevision(entry?.revision ?? 0);
    setSaved(previous);
    setDraft({
      ...result.draft,
      commercial: {
        ...empty.commercial,
        ...result.draft.commercial,
      } as Commercial,
    });
    setSource(result.source);
    setManualFields(result.manual_fields_preserved ?? []);
    setExtracted(null);
    intent.clear();
    setSync({
      kind: result.source.kind,
      source_revision: result.source.source_revision,
      offer_id: result.source.kind === "offer" ? result.source.offer_id : "",
      program_id:
        result.source.kind === "program" ? result.source.program_id : "",
      ...result.source.request,
    });
  };
  return (
    <div className="program-workspace">
      <SiieWorkspace
        onSaved={async () => setItems(await listPrograms())}
        onImport={receiveSiie}
      />
      <aside className="panel" aria-label="Programas por escuela">
        <h2>Programas por escuela</h2>
        <Button type="button" onClick={() => open(null)} disabled={task.busy}>
          Nuevo programa
        </Button>
        {schools.length > 1 && (
          <SelectField
            id="program-school-filter"
            label="Filtrar por escuela"
            options={[{ value: "", label: "Todas las escuelas" }, ...schools]}
            value={school}
            onChange={(event) => setSchool(event.target.value)}
          />
        )}
        {listError && <Notice error>{listError}</Notice>}
        {!items && !listError && <p role="status">Cargando programas…</p>}
        {items?.length === 0 && <p>Aún no hay programas registrados.</p>}
        {schools
          .filter((label) => !school || label === school)
          .map((label) => (
            <section key={label} className="program-school">
              <h3>{label}</h3>
              {(items ?? [])
                .filter(
                  (item) => (item.school || "Sin escuela asignada") === label,
                )
                .map((item) => (
                  <Button
                    key={item.program_id}
                    type="button"
                    variant="quiet"
                    aria-pressed={item.program_id === id}
                    disabled={task.busy}
                    onClick={() => open(item.program_id)}
                  >
                    {item.name}
                  </Button>
                ))}
            </section>
          ))}
      </aside>
      <section className="panel program-editor">
        <h2>{id ? "Ficha del programa" : "Nuevo programa"}</h2>
        {task.notices}
        {source && (
          <Notice>
            Última copia de SIIE:{" "}
            {new Date(source.checked_at).toLocaleString("es-CO")}. Las
            correcciones que guardes aquí son locales.{" "}
            {sync
              ? "Revisa el borrador y guarda para aplicar esta sincronización."
              : "Puedes consultar y editar esta ficha aunque SIIE no esté disponible."}
            {manualFields.length > 0 && (
              <p>
                Se conservaron {manualFields.length} campos editados
                manualmente.
              </p>
            )}
            {source.issues?.map((issue, i) => (
              <p key={i}>{issue}</p>
            ))}
          </Notice>
        )}
        <fieldset disabled={task.busy}>
          <legend>Importar desde una página oficial</legend>
          <Field
            id="program-url-import"
            label="Enlace oficial del programa"
            placeholder="https://…"
            type="url"
            maxLength={1000}
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <Button
            type="button"
            variant="secondary"
            disabled={!url.trim()}
            onClick={() => {
              setExtracted(null);
              void task.run(
                async () =>
                  setExtracted(
                    await api<Draft>("/programs/import", "POST", { url }),
                  ),
                "Extracción lista para revisar.",
              );
            }}
          >
            Extraer con IA
          </Button>
          <details>
            <summary>Importador SIIE anterior por ID</summary>
            <p>
              Para la API actual usa «Abrir SIIE» en la parte superior: allí
              puedes obtener programas, seleccionar ofertas y consultar
              aspirantes. Este importador conserva el contrato anterior por ID y
              requiere una oferta completa revisada. No matricula, no cobra ni
              guarda datos automáticamente.
            </p>
            <Field
              id="program-siie-offer"
              label="ID de oferta en SIIE"
              value={siieOffer}
              maxLength={80}
              onChange={(event) => setSiieOffer(event.target.value)}
            />
            <Button
              type="button"
              variant="secondary"
              disabled={!/^[A-Za-z0-9_-]{1,80}$/.test(siieOffer)}
              onClick={() => {
                setExtracted(null);
                void task.run(async () => {
                  const result = await api<SiieLocalDraft>(
                    "/programs/import-siie",
                    "POST",
                    { offer_id: siieOffer },
                  );
                  if (result.source?.kind) await receiveSiie(result);
                  else setExtracted(result.draft as Draft);
                }, "Datos de SIIE listos para revisar. No se han guardado.");
              }}
            >
              Consultar SIIE
            </Button>
          </details>
          {extracted && (
            <div className="program-import-preview">
              <strong>Cambios propuestos</strong>
              <FinancialSummary commercial={extracted.commercial} />
              {changes.length ? (
                <dl>
                  {changes.map(([label, oldValue, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>
                        {oldValue !== null && oldValue !== "" && (
                          <del>{oldValue}</del>
                        )}
                        <span>{value ?? "Sin dato"}</span>
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p>Los datos encontrados coinciden con el borrador.</p>
              )}
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setDraft((current) => mergeImport(current, extracted));
                  setExtracted(null);
                }}
              >
                Aplicar al borrador
              </Button>
            </div>
          )}
        </fieldset>
        <FinancialSummary commercial={commercial} />
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const body = {
              ...draft,
              name: draft.name.trim(),
              school: draft.school.trim(),
              revision,
              active: true,
              ...(sync ? { siie_sync: sync } : {}),
            };
            if (!body.name) return;
            void task.run(async () => {
              const result = await api<{
                program_id: number;
                revision: number;
              }>(id ? `/programs/${id}` : "/programs", id ? "PUT" : "POST", {
                ...body,
                operation_id: intent.get({ id, ...body }),
              });
              setId(result.program_id);
              setRevision(result.revision);
              const savedDraft = {
                name: body.name,
                school: body.school,
                schedule: body.schedule,
                commercial: body.commercial,
              };
              setDraft(savedDraft);
              setSaved(savedDraft);
              setSync(null);
              intent.clear();
              try {
                setItems(await listPrograms());
                setListError("");
              } catch {
                setListError(
                  "La ficha se guardó. Recarga la página para actualizar la lista de escuelas.",
                );
              }
            }, "Programa guardado.");
          }}
        >
          <fieldset disabled={task.busy} className="program-fields">
            <legend>Datos de la ficha</legend>
            <Field
              id="program-name"
              label="Nombre oficial"
              required
              maxLength={180}
              value={draft.name}
              onChange={(event) =>
                setDraft({ ...draft, name: event.target.value })
              }
            />
            <Field
              id="program-school"
              label="Escuela"
              maxLength={100}
              list="program-school-names"
              value={draft.school}
              onChange={(event) =>
                setDraft({ ...draft, school: event.target.value })
              }
            />
            <datalist id="program-school-names">
              {schools
                .filter((label) => label !== "Sin escuela asignada")
                .map((label) => (
                  <option value={label} key={label} />
                ))}
            </datalist>
            <Field
              id="program-price-from"
              label="Tarifa válida desde"
              type="date"
              hint="Opcional. Si falta, la IA indicará que está por confirmar."
              value={commercial.price_valid_from ?? ""}
              onChange={(event) =>
                setCommercial("price_valid_from", event.target.value || null)
              }
            />
            <Field
              id="program-aliases"
              label="Otros nombres o alias"
              maxLength={400}
              value={commercial.aliases}
              onChange={(event) => setCommercial("aliases", event.target.value)}
            />
            <Field
              id="program-duration"
              label="Duración"
              maxLength={150}
              value={commercial.duration}
              onChange={(event) =>
                setCommercial("duration", event.target.value)
              }
            />
            <Field
              id="program-modality"
              label="Modalidad"
              maxLength={100}
              value={commercial.modality}
              onChange={(event) =>
                setCommercial("modality", event.target.value)
              }
            />
            <Field
              id="program-schedule"
              label="Jornada"
              maxLength={100}
              value={draft.schedule}
              onChange={(event) =>
                setDraft({ ...draft, schedule: event.target.value })
              }
            />
            <Field
              id="program-price"
              label="Precio en COP"
              type="number"
              min={0}
              max={1000000000}
              step={1}
              value={commercial.price_cop ?? ""}
              onChange={(event) =>
                setCommercial(
                  "price_cop",
                  event.target.value === "" ? null : Number(event.target.value),
                )
              }
            />
            <Field
              id="program-price-concept"
              label="Concepto de la tarifa"
              maxLength={150}
              value={commercial.price_concept}
              onChange={(event) =>
                setCommercial("price_concept", event.target.value)
              }
            />
            <Field
              id="program-price-validity"
              label="Tarifa válida hasta"
              type="date"
              value={commercial.price_valid_until ?? ""}
              onChange={(event) =>
                setCommercial("price_valid_until", event.target.value || null)
              }
            />
            <Field
              id="program-source"
              label="Fuente de la ficha"
              type="url"
              maxLength={1000}
              value={commercial.source_url}
              hint={
                commercial.source_checked_at
                  ? `Consultada el ${new Date(commercial.source_checked_at).toLocaleDateString("es-CO")}`
                  : undefined
              }
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  commercial: {
                    ...current.commercial,
                    source_url: event.target.value,
                    source_checked_at: "",
                  },
                }))
              }
            />
            <TextArea
              id="program-syllabus"
              label="Materias o módulos"
              maxLength={2500}
              rows={5}
              value={commercial.syllabus}
              onChange={(event) =>
                setCommercial("syllabus", event.target.value)
              }
            />
            <TextArea
              id="program-requirements"
              label="Requisitos"
              maxLength={1600}
              rows={5}
              value={commercial.requirements}
              onChange={(event) =>
                setCommercial("requirements", event.target.value)
              }
            />
          </fieldset>
          <FinancialEditor
            commercial={commercial}
            change={setCommercial}
            disabled={task.busy}
          />
          <p className="scope-text">
            Las fechas son opcionales. La IA puede informar los importes
            revisados y aclarará qué fechas o condiciones están por confirmar.
            Una vigencia conocida ya vencida no se ofrece como actual.
          </p>
          <Button type="submit" disabled={task.busy || !draft.name.trim()}>
            {task.busy ? "Procesando…" : "Guardar programa"}
          </Button>
        </form>
      </section>
    </div>
  );
}

function FinancialEditor({
  commercial,
  change,
  disabled,
}: {
  commercial: Commercial;
  change: <K extends keyof Commercial>(key: K, value: Commercial[K]) => void;
  disabled: boolean;
}) {
  type Plan = NonNullable<Commercial["financial_plans"]>[number];
  const plans = commercial.financial_plans ?? [];
  const update = (index: number, values: Partial<Plan>) =>
    change(
      "financial_plans",
      plans.map((p, i) => (i === index ? { ...p, ...values } : p)),
    );
  const amount = (value: string) => (value === "" ? null : Number(value));
  return (
    <fieldset disabled={disabled} className="program-fields">
      <legend>Contado, planes y fechas locales</legend>
      <p>
        Completa sólo los datos confirmados. Deja vacías las fechas
        desconocidas: no se inventan ni se calculan a partir del período
        académico. Tus cambios se conservan al volver a sincronizar.
      </p>
      <Field
        id="program-full-cash"
        label="Contado informado en COP"
        type="number"
        min={0}
        max={1000000000}
        step={1}
        value={commercial.full_cost_cash_cop ?? ""}
        onChange={(e) => change("full_cost_cash_cop", amount(e.target.value))}
      />
      {plans.map((plan, i) => (
        <fieldset key={plan.external_id} className="program-fields">
          <legend>
            Plan {i + 1}: {plan.name}
          </legend>
          <Field
            id={`plan-name-${i}`}
            label={`Nombre del plan ${i + 1}`}
            maxLength={160}
            required
            value={plan.name}
            onChange={(e) => update(i, { name: e.target.value })}
          />
          <Field
            id={`plan-initial-${i}`}
            label={`Abono inicial del plan ${i + 1} (COP)`}
            type="number"
            min={0}
            max={1000000000}
            step={1}
            value={plan.initial_payment_cop ?? ""}
            onChange={(e) =>
              update(i, { initial_payment_cop: amount(e.target.value) })
            }
          />
          <Field
            id={`plan-initial-date-${i}`}
            label={`Fecha del abono del plan ${i + 1}`}
            type="date"
            hint="Opcional · por confirmar si queda vacía"
            value={plan.initial_payment_due_date ?? ""}
            onChange={(e) =>
              update(i, { initial_payment_due_date: e.target.value || null })
            }
          />
          <Field
            id={`plan-total-${i}`}
            label={`Total del plan ${i + 1} (COP)`}
            type="number"
            min={0}
            max={1000000000}
            step={1}
            value={plan.total_cost_cop ?? ""}
            onChange={(e) =>
              update(i, { total_cost_cop: amount(e.target.value) })
            }
          />
          <Field
            id={`plan-from-${i}`}
            label={`Vigencia desde del plan ${i + 1}`}
            type="date"
            value={plan.valid_from ?? ""}
            onChange={(e) => update(i, { valid_from: e.target.value || null })}
          />
          <Field
            id={`plan-until-${i}`}
            label={`Vigencia hasta del plan ${i + 1}`}
            type="date"
            value={plan.valid_until ?? ""}
            onChange={(e) => update(i, { valid_until: e.target.value || null })}
          />
          {plan.installments.map((part, j) => (
            <div className="program-fields" key={part.number}>
              <Field
                id={`plan-part-amount-${i}-${j}`}
                label={`Plan ${i + 1} · Cuota ${part.number} (COP)`}
                type="number"
                min={0}
                max={1000000000}
                step={1}
                value={part.amount_cop ?? ""}
                onChange={(e) =>
                  update(i, {
                    installments: plan.installments.map((v, k) =>
                      k === j
                        ? { ...v, amount_cop: amount(e.target.value) }
                        : v,
                    ),
                  })
                }
              />
              <Field
                id={`plan-part-date-${i}-${j}`}
                label={`Plan ${i + 1} · Fecha de cuota ${part.number}`}
                type="date"
                hint="Opcional · puedes completarla manualmente"
                value={part.due_date ?? ""}
                onChange={(e) =>
                  update(i, {
                    installments: plan.installments.map((v, k) =>
                      k === j ? { ...v, due_date: e.target.value || null } : v,
                    ),
                  })
                }
              />
            </div>
          ))}
          <Button
            type="button"
            variant="secondary"
            disabled={plan.installments.length >= 120}
            onClick={() =>
              update(i, {
                installments: [
                  ...plan.installments,
                  {
                    number: plan.installments.length + 1,
                    amount_cop: null,
                    due_date: null,
                  },
                ],
              })
            }
          >
            Añadir cuota al plan {i + 1}
          </Button>
          <TextArea
            id={`plan-conditions-${i}`}
            label={`Condiciones del plan ${i + 1}`}
            maxLength={2000}
            value={plan.conditions}
            onChange={(e) => update(i, { conditions: e.target.value })}
          />
        </fieldset>
      ))}
      <Button
        type="button"
        variant="secondary"
        disabled={plans.length >= 12}
        onClick={() =>
          change("financial_plans", [
            ...plans,
            {
              external_id: `local-${crypto.randomUUID()}`,
              name: `Plan local ${plans.length + 1}`,
              valid_from: null,
              valid_until: null,
              initial_payment_cop: null,
              initial_payment_due_date: null,
              total_cost_cop: null,
              installments: [],
              conditions: "",
            },
          ])
        }
      >
        Añadir plan local
      </Button>
    </fieldset>
  );
}

function FinancialSummary({ commercial }: { commercial: Commercial }) {
  if (!commercial.siie_offer_id) return null;
  const money = (value: number | null) =>
    value == null
      ? "Por confirmar"
      : new Intl.NumberFormat("es-CO", {
          style: "currency",
          currency: "COP",
          maximumFractionDigits: 0,
        }).format(value);
  return (
    <section aria-label="Información financiera de SIIE">
      <h3>Información financiera importada de SIIE</h3>
      <p>
        Oferta {commercial.siie_offer_id} · Revisión{" "}
        {commercial.siie_source_revision}
      </p>
      <p>
        Período {commercial.siie_period_id} · Sede {commercial.siie_campus_id} ·
        Jornada {commercial.siie_shift_id}
      </p>
      {commercial.full_cost_cash_cop != null && (
        <p>
          Costo total de contado:{" "}
          <strong>{money(commercial.full_cost_cash_cop)}</strong>
        </p>
      )}
      {commercial.cost_inclusions && (
        <p>Incluye: {commercial.cost_inclusions}</p>
      )}
      {commercial.cost_exclusions && (
        <p>No incluye: {commercial.cost_exclusions}</p>
      )}
      {commercial.financial_plans?.map((plan) => (
        <details key={plan.external_id}>
          <summary>
            {plan.name} · Total {money(plan.total_cost_cop)}
          </summary>
          <p>
            Vigencia: {plan.valid_from || "Por confirmar"} a{" "}
            {plan.valid_until || "Por confirmar"}
          </p>
          <p>
            Abono inicial: {money(plan.initial_payment_cop)} · Fecha:{" "}
            {plan.initial_payment_due_date || "Por confirmar"}
          </p>
          <table>
            <caption>Cuotas y fechas del plan {plan.name}</caption>
            <thead>
              <tr>
                <th>Cuota</th>
                <th>Valor</th>
                <th>Vencimiento</th>
              </tr>
            </thead>
            <tbody>
              {plan.installments.map((part) => (
                <tr key={part.number}>
                  <td>{part.number}</td>
                  <td>{money(part.amount_cop)}</td>
                  <td>{part.due_date || "Por confirmar"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {plan.conditions && <p>{plan.conditions}</p>}
        </details>
      ))}
      <p className="scope-text">
        Revisa el costo completo y sus condiciones antes de guardar. Una tarifa
        vencida no se utiliza en respuestas de IA.
      </p>
    </section>
  );
}
