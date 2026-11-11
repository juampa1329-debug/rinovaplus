import { useState } from "react";
import {
  Badge,
  Button,
  Field,
  Notice,
  PageHeading,
  SelectField,
  TextArea,
} from "../shared/ui";
import { send, useInstitution, useIntent, useTask } from "./api";
import { ResourceState, useResource } from "./Settings";
import { allowNavigation, useDraftGuard } from "./drafts";

type DNA = {
  mission: string;
  voice: string;
  principles: string;
  boundaries: string;
  escalation: string;
};
type Content = {
  kind: "document" | "collective" | "dna" | "private";
  title: string;
  body: string;
  owner: string;
  origin: string;
  valid_until: string;
  confidence: number;
  visibility: string;
  program_id: number | null;
  stage_id: string | null;
  dna: DNA | null;
  source_message_id: string | null;
  quote: string;
  fact_type: string;
  pages?: { page: number; text: string }[];
};
type Record = {
  id: string;
  kind: Content["kind"];
  state: string;
  revision: number;
  document: Content;
  context_current?: boolean;
};
type Listing = { items: Record[] };
type Version = {
  version: number;
  state: string;
  reason: string;
  created_at: string;
  document: Content;
};
type Citation = {
  id: string;
  document_id: string;
  title: string;
  page: number;
  revision: number;
  text: string;
};
const labels: { [key: string]: string } = {
  draft: "Borrador",
  published: "Publicado",
  archived: "Archivado",
};
const emptyDNA = {
  mission: "",
  voice: "",
  principles: "",
  boundaries: "",
  escalation: "",
};

export function KnowledgeWorkspace({ memory = false }: { memory?: boolean }) {
  const [kind, setKind] = useState<Content["kind"]>(
    memory ? "collective" : "document",
  );
  return (
    <section className="knowledge-workspace">
      <PageHeading
        title={memory ? "Memoria colectiva" : "Conocimiento"}
        description={
          memory
            ? "Criterios compartidos y ADN institucional, con revisión e historial."
            : "Fuentes con responsable, vigencia y citas. Publica la versión revisada para usarla en los agentes."
        }
      />
      {memory && (
        <div
          className="institution-actions"
          role="group"
          aria-label="Tipo de memoria"
        >
          <Button
            variant={kind === "collective" ? "primary" : "secondary"}
            onClick={() => {
              if (allowNavigation()) setKind("collective");
            }}
          >
            Memoria colectiva
          </Button>
          <Button
            variant={kind === "dna" ? "primary" : "secondary"}
            onClick={() => {
              if (allowNavigation()) setKind("dna");
            }}
          >
            ADN institucional
          </Button>
        </div>
      )}
      <Records key={kind} kind={kind} />
      {!memory && <SearchSources />}
    </section>
  );
}

export function PrivateMemory({
  conversation,
  canWrite,
}: {
  conversation: string;
  canWrite: boolean;
}) {
  return (
    <section className="panel">
      <h3>Memoria de esta conversación</h3>
      <p>
        Hechos declarados por el aspirante con mensaje de origen. La información
        se limita al contexto seleccionado.
      </p>
      <Records
        key={conversation}
        kind="private"
        conversation={conversation}
        canWrite={canWrite}
      />
    </section>
  );
}

function Records({
  kind,
  conversation,
  canWrite = true,
}: {
  kind: Content["kind"];
  conversation?: string;
  canWrite?: boolean;
}) {
  const collection = conversation
    ? `conversation-memory/${conversation}`
    : kind === "document"
      ? "knowledge"
      : "memory";
  const data = useResource<Listing>(
    conversation || kind === "document"
      ? collection
      : `${collection}?kind=${kind}`,
  );
  const [selected, setSelected] = useState<Record | null>(null),
    [creating, setCreating] = useState(false),
    [editorKey, setEditorKey] = useState(0);
  if (!data.value) return <ResourceState error={data.error} />;
  return (
    <>
      {data.error && <Notice error>{data.error}</Notice>}
      <div className="knowledge-layout">
        <section aria-label="Registros" className="panel">
          {canWrite && (
            <Button
              onClick={() => {
                if (allowNavigation()) {
                  setSelected(null);
                  setCreating(true);
                  setEditorKey((v) => v + 1);
                }
              }}
            >
              {" "}
              {kind === "document"
                ? "Nueva fuente"
                : kind === "dna"
                  ? "Nuevo ADN"
                  : "Nueva memoria"}{" "}
            </Button>
          )}
          {!data.value.items.length && (
            <p>
              No hay registros. Crea un borrador y revisa su contenido antes de
              publicarlo.
            </p>
          )}
          <ul className="knowledge-records">
            {data.value.items.map((item) => (
              <li key={item.id}>
                <button
                  className="knowledge-record"
                  aria-pressed={selected?.id === item.id}
                  onClick={() => {
                    if (allowNavigation()) {
                      setSelected(item);
                      setCreating(false);
                      setEditorKey((v) => v + 1);
                    }
                  }}
                >
                  <strong>{item.document.title}</strong>
                  <span>
                    <Badge>{labels[item.state]}</Badge> · v{item.revision}
                  </span>
                  <small>
                    {item.document.owner} · Vigencia:{" "}
                    {item.document.valid_until}
                    {item.context_current === false
                      ? " · Contexto anterior"
                      : ""}
                  </small>
                </button>
              </li>
            ))}
          </ul>
        </section>
        {selected || creating ? (
          <Editor
            key={editorKey}
            kind={kind}
            initial={selected}
            collection={collection}
            conversation={conversation}
            canWrite={canWrite}
            saved={async (id) => {
              const next = await data.reload();
              setSelected(next.items.find((v) => v.id === id) ?? null);
              setCreating(false);
              setEditorKey((v) => v + 1);
            }}
          />
        ) : (
          <section className="panel">
            <p>Selecciona un registro para consultar contenido e historial.</p>
          </section>
        )}
      </div>
    </>
  );
}

function Editor({
  kind,
  initial,
  collection,
  conversation,
  canWrite,
  saved,
}: {
  kind: Content["kind"];
  initial: Record | null;
  collection: string;
  conversation?: string;
  canWrite: boolean;
  saved: (id: string) => Promise<void>;
}) {
  const { session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [id] = useState(initial?.id ?? crypto.randomUUID());
  const [form, setForm] = useState<Content>(() =>
    initial
      ? {
          ...initial.document,
          body:
            kind === "document"
              ? (initial.document.pages ?? []).map((v) => v.text).join("\n\n")
              : initial.document.body,
        }
      : {
          kind,
          title: "",
          body: "",
          owner: session.user.full_name,
          origin: "",
          valid_until: new Date(Date.now() + 90 * 86400000)
            .toISOString()
            .slice(0, 10),
          confidence: 80,
          visibility:
            kind === "private" ? "conversation_only" : "agent_context",
          program_id: null,
          stage_id: null,
          dna: kind === "dna" ? { ...emptyDNA } : null,
          source_message_id: null,
          quote: "",
          fact_type: "followup_note",
        },
  );
  const [dirty, setDirty] = useState(false),
    [reason, setReason] = useState(""),
    [confirmed, setConfirmed] = useState(false),
    [file, setFile] = useState<File | null>(null),
    [history, setHistory] = useState<Version[] | null>(null);
  useDraftGuard(dirty);
  const prefix = conversation
    ? `${collection}/${id}`
    : `${collection}/records/${id}`;
  const revision = initial?.revision ?? 0;
  const change = <K extends keyof Content>(key: K, value: Content[K]) => {
    setForm((v) => ({ ...v, [key]: value }));
    setDirty(true);
  };
  const mutate = (path: string, method: string, body: object) =>
    send(
      path,
      method,
      { ...body, operation_id: intent.get({ path, body }) },
      session.csrf_token,
    );
  const commit = () =>
    task.run(async () => {
      if (file && !initial) {
        if (file.size > 5_000_000) throw Error("El archivo supera 5 MB.");
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        for (let offset = 0; offset < bytes.length; offset += 16384)
          binary += String.fromCharCode(
            ...bytes.subarray(offset, offset + 16384),
          );
        await mutate("knowledge/upload", "POST", {
          record_id: id,
          revision: 0,
          reason,
          title: form.title,
          filename: file.name,
          content_base64: btoa(binary),
          owner: form.owner,
          confidence: form.confidence,
          origin: form.origin,
          valid_until: form.valid_until,
          visibility: form.visibility,
          program_id: form.program_id,
          stage_id: form.stage_id,
        });
      } else {
        const body = {
          kind: form.kind,
          title: form.title,
          body: form.kind === "dna" ? "" : form.body,
          owner: form.owner,
          origin: form.origin,
          valid_until: form.valid_until,
          confidence: form.confidence,
          visibility: form.visibility,
          program_id: form.program_id,
          stage_id: form.stage_id,
          dna: form.dna,
          source_message_id: form.source_message_id,
          quote: form.quote,
          fact_type: form.fact_type,
          revision,
          reason,
        };
        await mutate(prefix, "PUT", body);
      }
      setDirty(false);
      intent.clear();
      await saved(id);
    }, "Borrador guardado. Revisa y publica su versión.");
  const action = (name: string, version?: number) =>
    task.run(async () => {
      if (dirty)
        throw Error("Guarda el borrador antes de revisar una versión.");
      await mutate(`${prefix}/${name}`, "POST", {
        revision,
        reason,
        confirmed,
        version: version ?? null,
      });
      intent.clear();
      await saved(id);
    });
  return (
    <section
      className="panel knowledge-editor"
      aria-label="Editor de conocimiento"
    >
      <h3>{initial ? `${form.title} · v${revision}` : "Nuevo borrador"}</h3>
      {kind === "dna" && (
        <Notice>
          El ADN orienta misión, voz y criterios. SIIE conserva la autoridad
          académica y los permisos del agente siguen vigentes.
        </Notice>
      )}
      {initial && <Badge>{labels[initial.state]}</Badge>}
      <fieldset disabled={!canWrite || task.busy}>
        <Field
          id="knowledge-title"
          label="Título"
          maxLength={160}
          value={form.title}
          onChange={(e) => change("title", e.target.value)}
          required
        />
        {kind === "document" && !initial && (
          <Field
            id="knowledge-file"
            type="file"
            label="Archivo PDF o TXT (hasta 5 MB)"
            accept=".pdf,.txt"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setDirty(true);
            }}
          />
        )}
        {kind === "dna" ? (
          (
            Object.entries({
              mission: "Misión",
              voice: "Voz y tono",
              principles: "Principios",
              boundaries: "Límites institucionales",
              escalation: "Derivación al equipo",
            }) as [keyof DNA, string][]
          ).map(([key, label]) => (
            <TextArea
              key={key}
              id={`dna-${key}`}
              label={label}
              value={form.dna?.[key] ?? ""}
              onChange={(e) =>
                change("dna", {
                  ...(form.dna ?? emptyDNA),
                  [key]: e.target.value,
                })
              }
            />
          ))
        ) : (
          <TextArea
            id="knowledge-body"
            label={
              kind === "document"
                ? "Texto o corrección de la fuente"
                : "Contenido"
            }
            value={form.body}
            maxLength={kind === "document" ? 300000 : 10000}
            onChange={(e) => change("body", e.target.value)}
          />
        )}
        {kind === "document" && initial?.document.pages && (
          <details>
            <summary>Páginas de la versión guardada</summary>
            {initial.document.pages.map((page) => (
              <p key={page.page}>
                <strong>Página {page.page}</strong>
                <br />
                {page.text}
              </p>
            ))}
          </details>
        )}
        <div className="institution-grid">
          <Field
            id="knowledge-owner"
            label="Responsable"
            value={form.owner}
            maxLength={kind === "document" ? 100 : 160}
            onChange={(e) => change("owner", e.target.value)}
            required
          />
          <Field
            id="knowledge-valid"
            type="date"
            label="Vigente hasta"
            value={form.valid_until}
            onChange={(e) => change("valid_until", e.target.value)}
            required
          />
          <Field
            id="knowledge-confidence"
            type="number"
            min={0}
            max={100}
            label="Confianza editorial (0–100)"
            value={form.confidence}
            onChange={(e) => change("confidence", Number(e.target.value))}
          />
        </div>
        <TextArea
          id="knowledge-origin"
          label="Origen y procedencia"
          value={form.origin}
          maxLength={1000}
          onChange={(e) => change("origin", e.target.value)}
        />
        {kind !== "private" && (
          <SelectField
            id="knowledge-visibility"
            label="Visibilidad"
            value={form.visibility}
            onChange={(e) => change("visibility", e.target.value)}
            options={[
              { value: "agent_context", label: "Compartida con asistentes" },
              { value: "staff_only", label: "Sólo equipo editor" },
            ]}
          />
        )}
        {!["private", "dna"].includes(kind) && (
          <ScopeFields form={form} change={change} />
        )}
        {kind === "private" && (
          <Evidence conversation={conversation!} form={form} change={change} />
        )}
        <TextArea
          id="knowledge-reason"
          label="Motivo de cambio o revisión"
          value={reason}
          maxLength={1000}
          onChange={(e) => setReason(e.target.value)}
        />
        <Button
          disabled={task.busy || !reason.trim() || !dirty}
          onClick={() => void commit()}
        >
          Guardar borrador
        </Button>
        {initial && (
          <>
            <label className="knowledge-confirm">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              He revisado contenido, ámbito y vigencia de esta versión
            </label>
            <div className="institution-actions">
              <Button
                disabled={task.busy || dirty || !confirmed || !reason.trim()}
                onClick={() => void action("publish")}
              >
                Publicar versión revisada
              </Button>
              <Button
                variant="secondary"
                disabled={task.busy || dirty || !confirmed || !reason.trim()}
                onClick={() => void action("archive")}
              >
                Archivar
              </Button>
              {kind === "document" && (
                <Button
                  variant="secondary"
                  disabled={task.busy || dirty || !confirmed || !reason.trim()}
                  onClick={() => void action("reindex")}
                >
                  Reconstruir índice
                </Button>
              )}
            </div>
          </>
        )}
      </fieldset>
      {task.notices}
      {initial && (
        <>
          <Button
            variant="secondary"
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                const result = await send<{ items: Version[] }>(
                  `${prefix}/history`,
                );
                setHistory(result.items);
              }, "Historial consultado.")
            }
          >
            Consultar historial
          </Button>
          {history && (
            <ol className="knowledge-history">
              {history.map((v) => (
                <li key={v.version}>
                  <strong>
                    v{v.version} · {labels[v.state]}
                  </strong>
                  <p>
                    {v.reason} · {v.created_at}
                  </p>
                  <details>
                    <summary>Contenido de esta versión</summary>
                    <pre>
                      {v.document.kind === "dna"
                        ? JSON.stringify(v.document.dna, null, 2)
                        : (v.document.pages?.map((p) => p.text).join("\n") ??
                          v.document.body)}
                    </pre>
                  </details>
                  {canWrite && v.state === "published" && (
                    <Button
                      variant="secondary"
                      disabled={
                        task.busy || dirty || !confirmed || !reason.trim()
                      }
                      onClick={() => void action("restore", v.version)}
                    >
                      Restaurar v{v.version} revisada
                    </Button>
                  )}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </section>
  );
}

function ScopeFields({
  form,
  change,
}: {
  form: Content;
  change: <K extends keyof Content>(key: K, value: Content[K]) => void;
}) {
  const data = useResource<{
    programs: { program_id: number; name: string }[];
    stages: { id: string; name: string; program_id: number }[];
    has_more: boolean;
  }>(`${form.kind === "document" ? "knowledge" : "memory"}/options`);
  if (!data.value) return <ResourceState error={data.error} />;
  return (
    <div className="institution-grid">
      <SelectField
        id="knowledge-program"
        label="Ámbito de programa"
        value={String(form.program_id ?? "")}
        options={[
          { value: "", label: "Toda la institución" },
          ...data.value.programs.map((v) => ({
            value: String(v.program_id),
            label: v.name,
          })),
        ]}
        onChange={(e) => {
          change("program_id", e.target.value ? Number(e.target.value) : null);
          change("stage_id", null);
        }}
      />
      <SelectField
        id="knowledge-stage"
        label="Etapa aprobada"
        value={form.stage_id ?? ""}
        disabled={!form.program_id}
        options={[
          { value: "", label: "Todas las etapas del ámbito" },
          ...data.value.stages
            .filter((v) => v.program_id === form.program_id)
            .map((v) => ({ value: v.id, label: v.name })),
        ]}
        onChange={(e) => change("stage_id", e.target.value || null)}
      />
      {data.value.has_more && (
        <Notice>
          El catálogo tiene más programas; consulta al administrador para
          ampliar la selección.
        </Notice>
      )}
    </div>
  );
}

function Evidence({
  conversation,
  form,
  change,
}: {
  conversation: string;
  form: Content;
  change: <K extends keyof Content>(key: K, value: Content[K]) => void;
}) {
  const messages = useResource<{
    items: { id: string; body: string; direction: string }[];
  }>(`workspace/conversations/${conversation}/messages`);
  return (
    <>
      <SelectField
        id="memory-fact"
        label="Tipo de hecho declarado"
        value={form.fact_type}
        onChange={(e) => change("fact_type", e.target.value)}
        options={Object.entries({
          program_interest: "Interés en programa",
          schedule_availability: "Disponibilidad horaria",
          registration_reported: "Inscripción declarada",
          contact_preference: "Preferencia de contacto",
          followup_note: "Seguimiento declarado",
        }).map(([value, label]) => ({ value, label }))}
      />
      <SelectField
        id="memory-source"
        label="Mensaje entrante de origen"
        value={form.source_message_id ?? ""}
        onChange={(e) => change("source_message_id", e.target.value || null)}
        options={[
          { value: "", label: "Selecciona un mensaje" },
          ...(messages.value?.items
            .filter((v) => v.direction === "incoming")
            .map((v) => ({ value: v.id, label: v.body.slice(0, 120) })) ?? []),
        ]}
      />
      {messages.error && <Notice error>{messages.error}</Notice>}
      <TextArea
        id="memory-quote"
        label="Cita literal del mensaje (debe contener el hecho)"
        value={form.quote}
        onChange={(e) => change("quote", e.target.value)}
      />
    </>
  );
}

function SearchSources() {
  const { session } = useInstitution(),
    task = useTask();
  const [query, setQuery] = useState(""),
    [program, setProgram] = useState(""),
    [stage, setStage] = useState(""),
    [expected, setExpected] = useState(""),
    [items, setItems] = useState<Citation[]>([]),
    [rank, setRank] = useState<number | null | undefined>();
  return (
    <section className="panel">
      <h3>Buscar y evaluar fuentes vigentes</h3>
      <Field
        id="knowledge-query"
        label="Pregunta educativa"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="institution-grid">
        <Field
          id="search-program"
          label="ID de programa"
          type="number"
          value={program}
          onChange={(e) => setProgram(e.target.value)}
        />
        <Field
          id="search-stage"
          label="ID de etapa"
          value={stage}
          onChange={(e) => setStage(e.target.value)}
        />
        <Field
          id="search-expected"
          label="ID de fuente esperada (evaluación opcional)"
          value={expected}
          onChange={(e) => setExpected(e.target.value)}
        />
      </div>
      <Button
        disabled={task.busy || !query.trim()}
        onClick={() =>
          void task.run(async () => {
            const result = await send<{
              items: Citation[];
              rank?: number | null;
            }>(
              `knowledge/${expected ? "evaluate" : "search"}`,
              "POST",
              {
                query,
                program_id: program ? Number(program) : null,
                stage_id: stage || null,
                ...(expected ? { expected_document_id: expected } : {}),
              },
              session.csrf_token,
            );
            setItems(result.items);
            setRank(result.rank);
          }, "Consulta completada.")
        }
      >
        Buscar fuentes
      </Button>
      {task.notices}
      {rank !== undefined && (
        <p>
          {rank
            ? `Fuente esperada en posición ${rank}.`
            : "La fuente esperada no aparece entre los resultados vigentes."}
        </p>
      )}
      <ul className="knowledge-citations">
        {items.map((v) => (
          <li key={v.id}>
            <strong>
              {v.title} · página {v.page} · v{v.revision}
            </strong>
            <p>{v.text}</p>
            <small>
              Fuente {v.document_id}
              <br />
              Cita {v.id}
            </small>
          </li>
        ))}
      </ul>
    </section>
  );
}
