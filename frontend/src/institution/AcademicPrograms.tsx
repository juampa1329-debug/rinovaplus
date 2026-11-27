import { useEffect, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { useIntent, useTask } from "./api";
import { allowNavigation, useDraftGuard } from "./drafts";
import { SiieWorkspace, type SiieLocalDraft } from "./SiieWorkspace";
import { ErrorFeedback } from "./ErrorFeedback";
import { Icon } from "../shared/Icon";
import { sourceGaps } from "./siieGaps";
import "./operations-design.css";

type Commercial = {
  presentation?: string;
  certification?: string;
  accreditation?: string;
  internships?: string;
  career_outcomes?: string;
  payment_mode?: "cash" | "financing" | "both";
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
    valid_until_confirmed_open?: boolean;
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
  active?: boolean;
  name: string;
  school: string;
  schedule: string;
  commercial: Commercial;
};
type Item = {
  active?: boolean;
  program_id: number;
  name: string;
  school: string;
  schedule?: string;
};
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
  active: true,
  name: "",
  school: "",
  schedule: "",
  commercial: {
    presentation: "",
    certification: "",
    accreditation: "",
    internships: "",
    career_outcomes: "",
    payment_mode: "both",
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
      `/programs?offset=${results.length}&include_inactive=true`,
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
    "presentation",
    "certification",
    "accreditation",
    "internships",
    "career_outcomes",
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
    active: draft.active ?? true,
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
    ["Presentación", before.presentation ?? null, after.presentation ?? null],
    [
      "Certificación",
      before.certification ?? null,
      after.certification ?? null,
    ],
    ["Acreditación", before.accreditation ?? null, after.accreditation ?? null],
    ["Prácticas", before.internships ?? null, after.internships ?? null],
    [
      "Campo ocupacional",
      before.career_outcomes ?? null,
      after.career_outcomes ?? null,
    ],
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
        nextStep: /SIIE no pudo entregar|respuesta de SIIE|SIIE devolvió/.test(
          failure.message,
        )
          ? "La ficha local se conserva. Entrega la referencia de consulta al equipo de SIIE para revisar la oferta financiera. Cuando el servicio vuelva a entregar datos, prepara la sincronización y revisa el borrador. Las fechas ausentes pueden quedar por confirmar."
          : "Revisa los campos señalados. Las fechas pueden quedar vacías. Si informas abono, cuotas y total, sus valores deben coincidir. Si SIIE cambió, vuelve a preparar la sincronización; tus datos locales se conservan.",
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
  const [search, setSearch] = useState("");
  const [showPaused, setShowPaused] = useState(false);
  const [reportCopied, setReportCopied] = useState(false);
  const [openSiie, setOpenSiie] = useState(0);
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
  const [copyFrom, setCopyFrom] = useState("");
  const [copyPart, setCopyPart] = useState("requirements");
  const [replacePlans, setReplacePlans] = useState(false);
  const [copyReady, setCopyReady] = useState<{
    id: number;
    name: string;
    commercial: Commercial;
  } | null>(null);
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
          active: entry.program.Active ?? true,
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
      setCopyFrom("");
      setCopyReady(null);
      setReplacePlans(false);
    }, "");
  };
  const commercial = draft.commercial;
  const gaps = source?.values
    ? sourceGaps(
        draft as unknown as Record<string, unknown>,
        source.values,
        source.kind,
      )
    : [];
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
          active: entry.program.Active ?? true,
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
      active: previous.active ?? true,
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
      <header className="operations-hero academic-hero">
        <div>
          <span className="operations-eyebrow">CONOCIMIENTO QUE CONECTA</span>
          <h2>Una ficha. Toda la información.</h2>
          <p>
            Programas por escuela, datos financieros y contenido para tus
            agentes.
          </p>
        </div>
        <div className="academic-count">
          <strong>{items?.length ?? "—"}</strong>
          <span>programas locales</span>
        </div>
      </header>
      <SiieWorkspace
        openRequest={openSiie}
        onSaved={async () => setItems(await listPrograms())}
        onImport={receiveSiie}
      />
      <aside className="panel" aria-label="Programas por escuela">
        <div className="operations-section-heading">
          <Icon name="academic" />
          <h2>Biblioteca académica</h2>
        </div>
        <Button type="button" onClick={() => open(null)} disabled={task.busy}>
          Nuevo programa
        </Button>
        <Field
          id="academic-search"
          label="Buscar programa"
          placeholder="Nombre del programa…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={showPaused}
            onChange={(event) => setShowPaused(event.target.checked)}
          />
          Mostrar programas pausados
        </label>
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
                  (item) =>
                    (item.school || "Sin escuela asignada") === label &&
                    (showPaused || item.active !== false) &&
                    item.name
                      .toLocaleLowerCase("es")
                      .includes(search.trim().toLocaleLowerCase("es")),
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
                    <span>{item.name}</span>
                    {item.active === false && (
                      <small>Pausado · fuera de la oferta actual</small>
                    )}
                    {item.schedule && <small>{item.schedule}</small>}
                  </Button>
                ))}
            </section>
          ))}
      </aside>
      <section className="panel program-editor">
        <header className="academic-editor-heading">
          <div>
            <span className="operations-eyebrow">
              {id ? `FICHA LOCAL · REVISIÓN ${revision}` : "COMIENZA AQUÍ"}
            </span>
            <h2>{draft.name || "Nuevo programa"}</h2>
            <p>{draft.school || "Organiza este programa por escuela"}</p>
          </div>
          <Button
            type="button"
            variant="secondary"
            disabled={task.busy}
            onClick={() => {
              setReportCopied(false);
              if (!source) {
                setOpenSiie((value) => value + 1);
                return;
              }
              if (!allowNavigation()) return;
              void task.run(async () => {
                const result = await api<SiieLocalDraft>(
                  "/programs/import-siie",
                  "POST",
                  {
                    ...(source.kind === "offer"
                      ? { offer_id: source.offer_id }
                      : { program_id: source.program_id }),
                    ...source.request,
                    local_program_id: id,
                  },
                );
                await receiveSiie(result);
              }, "Datos de SIIE preparados. Revisa el borrador y guarda para aplicar; tus correcciones locales se conservan.");
            }}
          >
            <Icon name="channels" />
            Sincronizar con SIIE
          </Button>
        </header>
        {!source && (
          <p className="scope-text">
            Para vincularlo, abre SIIE y elige su programa u oferta. Después
            podrás sincronizar esta ficha con un clic.
          </p>
        )}
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
        {source && (
          <details className="academic-source-review">
            <summary>
              Calidad de los datos ·{" "}
              {gaps.length
                ? `${gaps.length} datos locales ausentes en SIIE`
                : "Revisar procedencia"}
            </summary>
            <p>
              Comparación con la última copia recibida, no con una consulta en
              tiempo real.{" "}
              {source.kind === "program"
                ? "Esta copia es del catálogo base: no confirma precios ni calendario financiero. Consulta una oferta en SIIE para revisarlos."
                : "Se respetan los valores y fechas completados localmente."}
            </p>
            {gaps.length > 0 && (
              <>
                <ul>
                  {gaps.map((gap) => (
                    <li key={gap}>{gap}</li>
                  ))}
                </ul>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() =>
                    void task.run(async () => {
                      await navigator.clipboard.writeText(
                        `Revisión para SIIE · ${draft.name}\nPrograma SIIE: ${source.program_id}\nOferta: ${source.offer_id || "Catálogo base"}\nCopia recibida: ${source.checked_at}\nDatos disponibles en RinovaPlus pero ausentes en esta copia:\n${gaps.map((gap) => `- ${gap}`).join("\n")}\nSolicitamos revisar estos campos en la API. No se adjuntan valores personales ni se ha enviado este informe automáticamente.`,
                      );
                      setReportCopied(true);
                    }, "")
                  }
                >
                  {reportCopied
                    ? "Informe copiado"
                    : "Copiar informe para SIIE"}
                </Button>
              </>
            )}
          </details>
        )}
        <details className="academic-import-tools">
          <summary>Otras fuentes · Extraer información de una página</summary>
          <fieldset disabled={task.busy}>
            <legend>Importar desde una página oficial</legend>
            <Field
              id="program-url-import"
              label="Enlace oficial del programa"
              placeholder="https://…"
              type="url"
              maxLength={1000}
              value={url}
              onChange={(event) => {
                setUrl(event.target.value);
                setDraft((current) => ({
                  ...current,
                  commercial: {
                    ...current.commercial,
                    source_url: event.target.value,
                    source_checked_at: "",
                  },
                }));
              }}
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
                aspirantes. Este importador conserva el contrato anterior por ID
                y requiere una oferta completa revisada. No matricula, no cobra
                ni guarda datos automáticamente.
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
        </details>
        <details className="academic-import-tools academic-copy-tools">
          <summary>Copiar requisitos o planes de otro programa</summary>
          <p>
            Reutiliza información guardada localmente. Se aplica primero al
            borrador; revisa los requisitos, importes, cuotas y vigencias del
            programa destino antes de Guardar programa. No se copian el precio
            de contado ni los identificadores de SIIE.
          </p>
          <fieldset disabled={task.busy}>
            <legend>Programa de origen y contenido</legend>
            <SelectField
              id="program-copy-from"
              label="Copiar desde el programa"
              value={copyFrom}
              onChange={(event) => {
                setCopyFrom(event.target.value);
                setCopyReady(null);
              }}
              options={[
                { value: "", label: "Selecciona un programa de origen" },
                ...(items ?? [])
                  .filter((p) => p.program_id !== id)
                  .map((p) => ({
                    value: String(p.program_id),
                    label: `${p.name} · ${p.school || "Sin escuela"}${p.schedule ? " · " + p.schedule : ""}`,
                  })),
              ]}
            />
            <SelectField
              id="program-copy-part"
              label="Contenido que quieres copiar"
              value={copyPart}
              onChange={(event) => {
                setCopyPart(event.target.value);
                setCopyReady(null);
              }}
              options={[
                { value: "requirements", label: "Sólo requisitos" },
                { value: "plans", label: "Sólo planes de financiación" },
                { value: "both", label: "Requisitos y planes de financiación" },
              ]}
            />
            {copyPart !== "requirements" && (
              <label>
                <input
                  type="checkbox"
                  checked={replacePlans}
                  onChange={(event) => setReplacePlans(event.target.checked)}
                />
                Reemplazar los planes existentes; sin marcar, se añaden al final
              </label>
            )}
            <Button
              type="button"
              variant="secondary"
              disabled={!copyFrom}
              onClick={() =>
                void task.run(async () => {
                  setCopyReady(null);
                  const source = await api<Program>(
                    `/programs/${Number(copyFrom)}`,
                  );
                  if (!source.program || !source.commercial)
                    throw new Error(
                      "El programa de origen no tiene una ficha disponible para copiar.",
                    );
                  if (
                    copyPart !== "plans" &&
                    !source.commercial.requirements?.trim()
                  )
                    throw new Error(
                      "El programa de origen no tiene requisitos guardados. Complétalos allí o selecciona otro programa.",
                    );
                  if (
                    copyPart !== "requirements" &&
                    !source.commercial.financial_plans?.length
                  )
                    throw new Error(
                      "El programa de origen no tiene planes de financiación guardados. Añade un plan en su ficha o selecciona otro programa.",
                    );
                  setCopyReady({
                    id: Number(copyFrom),
                    name: source.program.Name,
                    commercial: source.commercial,
                  });
                }, "")
              }
            >
              Preparar copia
            </Button>
            {copyReady && (
              <div className="panel">
                <h3>Copia propuesta desde {copyReady.name}</h3>
                {copyPart !== "plans" && (
                  <>
                    <h4>Requisitos</h4>
                    <p style={{ whiteSpace: "pre-wrap" }}>
                      {copyReady.commercial.requirements}
                    </p>
                    <p>Reemplazará los requisitos actuales del borrador.</p>
                  </>
                )}
                {copyPart !== "requirements" && (
                  <>
                    <h4>Planes de financiación</h4>
                    <ul>
                      {copyReady.commercial.financial_plans?.map((plan) => (
                        <li key={plan.external_id}>
                          {plan.name} · abono:{" "}
                          {plan.initial_payment_cop == null
                            ? "por confirmar"
                            : `${plan.initial_payment_cop.toLocaleString("es-CO")} COP`}{" "}
                          · {plan.installments.length} cuotas · total:{" "}
                          {plan.total_cost_cop == null
                            ? "por confirmar"
                            : `${plan.total_cost_cop.toLocaleString("es-CO")} COP`}
                        </li>
                      ))}
                    </ul>
                    <p>
                      Se copiarán también fechas, condiciones y vigencia;
                      confirma que correspondan al programa destino.
                    </p>
                  </>
                )}
                <Button
                  type="button"
                  onClick={() =>
                    void task.run(async () => {
                      const plans =
                        copyReady.commercial.financial_plans?.map((plan) => ({
                          ...plan,
                          external_id: `local-${crypto.randomUUID()}`,
                          installments: plan.installments.map((part) => ({
                            ...part,
                          })),
                        })) ?? [];
                      if (
                        copyPart !== "requirements" &&
                        (replacePlans
                          ? 0
                          : (commercial.financial_plans?.length ?? 0)) +
                          plans.length >
                          12
                      )
                        throw new Error(
                          "Una ficha admite hasta 12 planes. Revisa los planes actuales o marca Reemplazar antes de aplicar la copia.",
                        );
                      setDraft((current) => ({
                        ...current,
                        commercial: {
                          ...current.commercial,
                          ...(copyPart !== "plans"
                            ? {
                                requirements: copyReady.commercial.requirements,
                              }
                            : {}),
                          ...(copyPart !== "requirements"
                            ? {
                                financial_plans: [
                                  ...(replacePlans
                                    ? []
                                    : (current.commercial.financial_plans ??
                                      [])),
                                  ...plans,
                                ],
                              }
                            : {}),
                        },
                      }));
                      setCopyReady(null);
                    }, "Copia aplicada al borrador. Revisa los requisitos y los planes para este programa y pulsa Guardar programa.")
                  }
                >
                  Aplicar copia al borrador
                </Button>
              </div>
            )}
          </fieldset>
        </details>
        <FinancialSummary commercial={commercial} />
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const body = {
              ...draft,
              name: draft.name.trim(),
              school: draft.school.trim(),
              revision,
              active: draft.active ?? true,
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
                active: body.active,
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
            <legend>
              <Icon name="academic" /> Datos del programa
            </legend>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={draft.active !== false}
                onChange={(event) =>
                  setDraft({ ...draft, active: event.target.checked })
                }
              />
              Programa disponible en la oferta actual
            </label>
            <p>
              Pausarlo conserva la ficha y sus datos históricos. La IA deja de
              ofrecerlo; puedes volver a activarlo desde Mostrar programas
              pausados.
            </p>
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
              id="program-price-validity"
              label="Tarifa válida hasta"
              type="date"
              value={commercial.price_valid_until ?? ""}
              onChange={(event) =>
                setCommercial("price_valid_until", event.target.value || null)
              }
            />
            <details className="program-source-content">
              <summary>Contenido académico y fuente oficial</summary>
              <div className="program-fields">
                <Field
                  id="program-source"
                  label="Enlace oficial guardado del programa"
                  type="url"
                  maxLength={1000}
                  value={commercial.source_url}
                  hint={
                    commercial.source_checked_at
                      ? `Consultada el ${new Date(commercial.source_checked_at).toLocaleDateString("es-CO")}`
                      : undefined
                  }
                  onChange={(event) => {
                    setUrl(event.target.value);
                    setDraft((current) => ({
                      ...current,
                      commercial: {
                        ...current.commercial,
                        source_url: event.target.value,
                        source_checked_at: "",
                      },
                    }));
                  }}
                />
                <p>
                  Usa este enlace en «Otras fuentes → Extraer con IA» para
                  preparar contenido académico. Revisa y guarda el borrador para
                  que lo consulten los agentes asignados a este programa.
                </p>
                <TextArea
                  id="program-presentation"
                  label="Presentación y objetivos del programa"
                  maxLength={2000}
                  rows={4}
                  value={commercial.presentation ?? ""}
                  onChange={(event) =>
                    setCommercial("presentation", event.target.value)
                  }
                />
                <TextArea
                  id="program-syllabus"
                  label="Semestres, niveles y materias"
                  maxLength={2500}
                  rows={5}
                  value={commercial.syllabus}
                  onChange={(event) =>
                    setCommercial("syllabus", event.target.value)
                  }
                />
                <TextArea
                  id="program-certification"
                  label="Título o certificación que otorga"
                  maxLength={1600}
                  rows={3}
                  value={commercial.certification ?? ""}
                  onChange={(event) =>
                    setCommercial("certification", event.target.value)
                  }
                />
                <TextArea
                  id="program-accreditation"
                  label="Acreditaciones verificadas del programa"
                  maxLength={1600}
                  rows={3}
                  value={commercial.accreditation ?? ""}
                  onChange={(event) =>
                    setCommercial("accreditation", event.target.value)
                  }
                />
                <TextArea
                  id="program-internships"
                  label="Prácticas y sus condiciones"
                  maxLength={2000}
                  rows={4}
                  value={commercial.internships ?? ""}
                  onChange={(event) =>
                    setCommercial("internships", event.target.value)
                  }
                />
                <TextArea
                  id="program-career"
                  label="Campo ocupacional y salidas laborales"
                  maxLength={1600}
                  rows={3}
                  value={commercial.career_outcomes ?? ""}
                  onChange={(event) =>
                    setCommercial("career_outcomes", event.target.value)
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
              </div>
            </details>
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
      <legend>Contado y financiación</legend>
      <SelectField
        id="program-payment-mode"
        label="Modalidades de pago que puede ofrecer la IA"
        value={commercial.payment_mode ?? "both"}
        options={[
          { value: "both", label: "Contado y financiación" },
          { value: "cash", label: "Sólo contado" },
          { value: "financing", label: "Sólo financiación" },
        ]}
        onChange={(event) =>
          change(
            "payment_mode",
            event.target.value as Commercial["payment_mode"],
          )
        }
      />
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
            disabled={plan.valid_until_confirmed_open === true}
            onChange={(e) => update(i, { valid_until: e.target.value || null })}
          />
          <label className="institution-check">
            <input
              type="checkbox"
              checked={plan.valid_until_confirmed_open === true}
              onChange={(event) =>
                update(i, {
                  valid_until_confirmed_open: event.target.checked,
                  ...(event.target.checked ? { valid_until: null } : {}),
                })
              }
            />
            Vigencia del plan {i + 1} confirmada hasta nueva indicación
          </label>
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
