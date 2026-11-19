import { useEffect, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { useIntent, useTask } from "./api";
import { allowNavigation, useDraftGuard } from "./drafts";
import { SiieWorkspace } from "./SiieWorkspace";

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
    valid_from: string;
    valid_until: string;
    initial_payment_cop: number;
    initial_payment_due_date: string;
    total_cost_cop: number;
    installments: { number: number; amount_cop: number; due_date: string }[];
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
    }, "");
  };
  const commercial = draft.commercial;
  const changes = extracted ? importChanges(draft, extracted) : [];
  return (
    <div className="program-workspace">
      <SiieWorkspace />
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
            <summary>Consultar catálogo comercial de SIIE</summary>
            <p>
              Consulta de sólo lectura por oferta: programa, sede, jornada y
              período. Requiere que el equipo de SIIE entregue la API y se
              configure en el servidor. La consulta no matricula, no cobra y no
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
                  const result = await api<{ draft: Draft }>(
                    "/programs/import-siie",
                    "POST",
                    { offer_id: siieOffer },
                  );
                  setExtracted(result.draft);
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
            };
            if (!body.name || !body.school) return;
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
              setDraft(body);
              setSaved(body);
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
              required
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
          <p className="scope-text">
            Para que el agente pueda citar una tarifa, completa su concepto y su
            fecha de vigencia.
          </p>
          <Button
            type="submit"
            disabled={task.busy || !draft.name.trim() || !draft.school.trim()}
          >
            {task.busy ? "Procesando…" : "Guardar programa"}
          </Button>
        </form>
      </section>
    </div>
  );
}

function FinancialSummary({ commercial }: { commercial: Commercial }) {
  if (!commercial.siie_offer_id) return null;
  const money = (value: number) =>
    new Intl.NumberFormat("es-CO", {
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
            Vigencia: {plan.valid_from} a {plan.valid_until}
          </p>
          <p>
            Abono inicial: {money(plan.initial_payment_cop)} · Fecha:{" "}
            {plan.initial_payment_due_date}
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
                  <td>{part.due_date}</td>
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
