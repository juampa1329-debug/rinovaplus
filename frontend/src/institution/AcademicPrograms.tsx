import { useEffect, useState } from "react";
import { api } from "../modules/agents/api";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { useIntent, useTask } from "./api";
import { allowNavigation, useDraftGuard } from "./drafts";

type Commercial = {
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
          {extracted && (
            <div className="program-import-preview">
              <strong>Cambios propuestos</strong>
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
