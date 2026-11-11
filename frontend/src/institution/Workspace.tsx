import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import type { Dispatch, SetStateAction } from "react";
import type { Client } from "../shared/demo";
import type { CrmConfig } from "../shared/crm";
import { validateCrmClient } from "../shared/crm";
import { ClientFields } from "../modules/clients/components/ClientFields";
import { useCrmConfiguration } from "../modules/crm-configuration/hooks/useCrmConfiguration";
import { CrmConfiguration } from "../modules/crm-configuration/pages/CrmConfiguration";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { ApiError, useInstitution } from "./api";
import { MediaDownload, MediaUpload } from "./ChannelMedia";
import type { Attachment } from "./ChannelMedia";
import { useWorkspaceState } from "../shared/workspaceSession";
import "./workspace.css";
import { AgentConversationPanel } from "../modules/agents/AgentConversationPanel";
import { PrivateMemory } from "./KnowledgeWorkspace";

export type Risk = {
  status: string;
  level: string;
  score: number | null;
  source: string;
  asOf: string | null;
  fresh: boolean;
  reasons: string[];
  nextAction: string;
  trainedPrediction: boolean;
};
type Row = {
  id: string;
  conversationId: string;
  name: string;
  phone: string;
  stage: string;
  state: string;
  mode: string;
  unread: boolean;
  assignee: string | null;
  risk: Risk;
};
type Page = {
  items: Row[];
  total: number;
  offset: number;
  limit: number;
  hasMore: boolean;
  revision: string;
};
type Detail = {
  agentOperations?: boolean;
  knowledgeOperations?: boolean;
  mediaAvailable?: boolean;
  channelAccounts?: { id: string; name: string; channel: string }[];
  client: Client;
  thread: {
    ConversationId: string;
    ContactId: string;
    State: string;
    Priority: string;
    ControlMode: string;
    Unread: boolean;
    UserId: string | null;
    Assignee?: string | null;
  };
  risk: Risk;
  manual: {
    score: number | null;
    temperature: string | null;
    asOf: string;
  } | null;
  members: Client[];
  inFlightOrUncertain?: number;
  notes: { id: string; body: string; author: string; createdAt: string }[];
  revision: string;
};
type Message = {
  attachments?: Attachment[];
  id: string;
  body: string;
  direction: string;
  createdAt: string;
  sequence: string;
  deliveryState?: string;
  deliveryError?: string;
  channelAccount?: string;
};
type Tasks = {
  items: {
    id: string;
    conversationId: string;
    title: string;
    status: string;
    priority: string;
    dueAt: string | null;
    userId: string | null;
    assignee: string | null;
    contactName?: string;
  }[];
  total: number;
  hasMore: boolean;
  revision: string;
};
const states = [
  { value: "open", label: "Abierta" },
  { value: "waiting", label: "En espera" },
  { value: "closed", label: "Cerrada" },
];
const priorities = [
  { value: "low", label: "Baja" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "Alta" },
  { value: "urgent", label: "Urgente" },
];
const statuses = [
  { value: "pending", label: "Pendiente" },
  { value: "completed", label: "Completada" },
  { value: "cancelled", label: "Cancelada" },
];
const queues = [
  { value: "all", label: "Todas" },
  { value: "unread", label: "No leídas" },
  { value: "mine", label: "Mis conversaciones" },
  { value: "unassigned", label: "Sin asignar" },
  { value: "open", label: "Abiertas" },
  { value: "waiting", label: "En espera" },
  { value: "closed", label: "Cerradas" },
  { value: "human", label: "Control humano" },
  { value: "ai", label: "Control IA" },
  { value: "hot", label: "Interés alto · valoración manual" },
  { value: "churn", label: "Abandono alto · evaluación vigente" },
  { value: "sla", label: "Tiempo de respuesta vencido" },
];
const prefix = "workspace/";
const options = (values: string[]) =>
  values.map((value) => ({ value, label: value }));
const DateZone = createContext("America/Bogota");
function DateText({ value }: { value: string | null }) {
  const zone = useContext(DateZone);
  return (
    <>
      {value
        ? new Intl.DateTimeFormat("es-CO", {
            timeZone: zone,
            dateStyle: "short",
            timeStyle: "short",
          }).format(new Date(value))
        : "Sin fecha"}
    </>
  );
}
const DraftCache = createContext<Map<string, unknown> | null>(null);
function useCache() {
  const cache = useContext(DraftCache);
  if (!cache) throw Error("Workspace session required");
  return cache;
}
function useCachedDraft<T>(
  key: string,
  initial: T,
): [T, Dispatch<SetStateAction<T>>] {
  const cache = useCache(),
    signature = JSON.stringify(initial);
  const [entry, setEntry] = useState(() => {
    const value = cache.has(key) ? (cache.get(key) as T) : initial;
    return {
      key,
      base: signature,
      value,
      dirty: JSON.stringify(value) !== signature,
    };
  });
  if (entry.key !== key || entry.base !== signature) {
    const dirty =
      entry.key === key &&
      entry.dirty &&
      JSON.stringify(entry.value) !== signature;
    setEntry({
      key,
      base: signature,
      value: dirty ? entry.value : initial,
      dirty,
    });
  }
  useEffect(() => {
    if (entry.dirty) cache.set(entry.key, entry.value);
    else cache.delete(entry.key);
  }, [cache, entry]);
  const update: Dispatch<SetStateAction<T>> = (next) =>
    setEntry((previous) => {
      const value =
        typeof next === "function"
          ? (next as (old: T) => T)(previous.value)
          : next;
      return { ...previous, value, dirty: JSON.stringify(value) !== signature };
    });
  return [entry.value, update];
}
function useEntity(key: string) {
  const cache = useCache();
  return {
    get: () => {
      if (!cache.has(key)) cache.set(key, crypto.randomUUID());
      return cache.get(key) as string;
    },
    reset: () => cache.delete(key),
  };
}

function useRead<T>(path: string, refresh = 0, enabled = true) {
  const { call } = useInstitution();
  const [data, setData] = useState<{ path: string; value: T } | null>(null),
    [error, setError] = useState<{ path: string; message: string } | null>(
      null,
    );
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const timer = setTimeout(() => {
      void call<T>(prefix + path)
        .then((value) => {
          if (active) {
            setData({ path, value });
            setError(null);
          }
        })
        .catch((failure: unknown) => {
          if (active)
            setError({
              path,
              message:
                failure instanceof Error
                  ? failure.message
                  : "No se pudo consultar.",
            });
        });
    }, 180);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [path, refresh, enabled, call]);
  return {
    value: enabled && data?.path === path ? data.value : null,
    error: error?.path === path ? error.message : "",
  };
}
function useCommand(onSaved: () => void) {
  const { call } = useInstitution(),
    cache = useCache();
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function save(
    path: string,
    method: string,
    body: Record<string, unknown>,
  ) {
    setBusy(true);
    setError("");
    const identity = { ...body };
    delete identity.revision;
    const key = "command:" + JSON.stringify({ path, method, ...identity });
    if (!cache.has(key))
      cache.set(key, { operationId: crypto.randomUUID(), body });
    const attempt = cache.get(key) as {
      operationId: string;
      body: Record<string, unknown>;
    };
    try {
      const payload = { ...attempt.body, operationId: attempt.operationId };
      const result = await call<Record<string, unknown>>(
        prefix + path,
        method,
        payload,
      );
      cache.delete(key);
      onSaved();
      return result;
    } catch (failure) {
      if (
        failure instanceof ApiError &&
        failure.status === 409 &&
        failure.detail === "revision_conflict"
      )
        cache.delete(key);
      setError(
        failure instanceof Error
          ? failure.message
          : "No se pudo guardar. Tu borrador se conserva.",
      );
      return null;
    } finally {
      setBusy(false);
    }
  }
  return { save, error, busy };
}
export function RiskSummary({ risk }: { risk: Risk }) {
  const known = risk.status === "known" && risk.fresh;
  return (
    <section className="p3-risk" aria-label="Riesgo de abandono">
      <h3>Riesgo de abandono</h3>
      <strong>
        {known
          ? ({ low: "Bajo", medium: "Medio", high: "Alto" }[risk.level] ??
            "Sin evaluación")
          : risk.status === "not_applicable"
            ? "No aplica"
            : "Sin evaluación"}
      </strong>
      <p>
        {known
          ? "Rúbrica de seguimiento · no es una probabilidad"
          : "Evidencia insuficiente o pendiente de actualizar"}
        {risk.asOf && (
          <>
            {" "}
            · <DateText value={risk.asOf} />
          </>
        )}
      </p>
      <p>{risk.nextAction}</p>
      <details>
        <summary>Origen y razones</summary>
        <ul>
          {risk.reasons.map((reason, index) => (
            <li key={index}>{reason}</li>
          ))}
        </ul>
        <p>
          {known
            ? "Origen: reglas con evidencia registrada."
            : "Origen: sin evaluación válida."}{" "}
          La predicción entrenada aún no está disponible.
        </p>
      </details>
    </section>
  );
}
export function WorkspaceP3({ page }: { page: string }) {
  const [workspaceSession] = useWorkspaceState("institutional");
  const cache = workspaceSession.cache;
  const { session } = useInstitution();
  return (
    <DateZone.Provider
      value={session.user.profile.timezone || "America/Bogota"}
    >
      <DraftCache.Provider value={cache}>
        <WorkspaceView page={page} />
      </DraftCache.Provider>
    </DateZone.Provider>
  );
}
function WorkspaceView({ page }: { page: string }) {
  const gridRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const grid = gridRef.current;
    if (!grid) return;
    const resize = () => {
      const height = `${Math.max(360, innerHeight - (grid.getBoundingClientRect().top + scrollY) - 24)}px`;
      if (grid.style.getPropertyValue("--p3-panel-height") !== height)
        grid.style.setProperty("--p3-panel-height", height);
    };
    resize();
    const observer =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null;
    if (grid.parentElement) observer?.observe(grid.parentElement);
    window.addEventListener("resize", resize);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", resize);
    };
  }, [page]);
  const cfg = useCrmConfiguration(),
    { session } = useInstitution();
  const [selected, setSelected] = useState(() => {
      const value = window.location.hash.split("/")[2] || "";
      return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        value,
      )
        ? value
        : "";
    }),
    [refresh, setRefresh] = useState(0),
    [q, setQuery] = useState(""),
    [stage, setStage] = useState(""),
    [tag, setTag] = useState(""),
    [city, setCity] = useState(""),
    [type, setType] = useState(""),
    [program, setProgram] = useState(""),
    [queue, setQueue] = useState("all"),
    [channel, setChannel] = useState(""),
    [offset, setOffset] = useState(0),
    [anchor, setAnchor] = useState(""),
    [tab, setTab] = useState("contacts"),
    [creating, setCreating] = useState(false);
  const [workspaceSession] = useWorkspaceState("institutional");
  const drafts = workspaceSession.contacts,
    messages = workspaceSession.messages;
  const changed = () => setRefresh((n) => n + 1);
  const params = new URLSearchParams({
    q,
    stage,
    offset: String(offset),
    anchor: offset ? anchor : "",
    ...(page === "inbox"
      ? { queue, channel }
      : { tag, city, contactType: type, program }),
  });
  const list = useRead<Page>(
    (page === "inbox" ? "inbox" : "clients") + "?" + params.toString(),
    refresh,
    page !== "settings",
  );
  const directory = { value: { items: [] as { id: string; name: string }[] } };
  const filterKey = JSON.stringify([
    page,
    q,
    stage,
    tag,
    city,
    type,
    program,
    queue,
    channel,
  ]);
  const [lastFilterKey, setLastFilterKey] = useState(filterKey);
  if (lastFilterKey !== filterKey) {
    setLastFilterKey(filterKey);
    setOffset(0);
    setAnchor("");
  }
  if (page === "settings")
    return (
      <>
        <fieldset disabled={!session.actions.includes("settings.crm.write")}>
          <CrmConfiguration
            config={cfg.config}
            clients={[]}
            onChange={async (next) => {
              await cfg.save(next);
              changed();
            }}
            onReload={() => void cfg.reload()}
            revision={cfg.revision}
            loadError={cfg.error}
            ready={cfg.ready}
            openRequest={1}
          />
        </fieldset>
        <SlaPolicy refresh={refresh} changed={changed} />
      </>
    );
  const canRead = session.actions.includes(
    page === "inbox" ? "inbox.read" : "crm.read",
  );
  if (!canRead)
    return <Notice>Tu rol no permite consultar este apartado.</Notice>;
  return (
    <div className="p3-workspace">
      {page === "clients" && (
        <nav className="institution-tabs" aria-label="Vistas CRM">
          <Button
            variant="quiet"
            onClick={() => setTab("contacts")}
            aria-pressed={tab === "contacts"}
          >
            Contactos
          </Button>
          <Button
            variant="quiet"
            onClick={() => setTab("tasks")}
            aria-pressed={tab === "tasks"}
          >
            Tareas
          </Button>
        </nav>
      )}
      {tab === "tasks" && page === "clients" ? (
        <TaskList
          refresh={refresh}
          changed={changed}
          users={directory.value?.items ?? []}
          onOpen={(id) => {
            setSelected(id);
            setCreating(false);
            window.location.hash = "/inbox";
          }}
        />
      ) : (
        <>
          <section
            className="panel p3-filters"
            aria-label="Filtros de contactos y conversaciones"
          >
            <Field
              id="p3-search"
              label="Buscar"
              value={q}
              onChange={(e) => setQuery(e.target.value)}
            />
            <SelectField
              id="p3-stage"
              label="Etapa"
              value={stage}
              options={[
                { value: "", label: "Todas" },
                ...options(cfg.config.stages.map((s) => s.label)),
              ]}
              onChange={(e) => setStage(e.target.value)}
            />
            {page === "inbox" ? (
              <>
                <SelectField
                  id="p3-queue"
                  label="Bandeja"
                  value={queue}
                  options={queues}
                  onChange={(e) => setQueue(e.target.value)}
                />
                <SelectField
                  id="p3-channel"
                  label="Canal"
                  value={channel}
                  options={[
                    { value: "", label: "Todos" },
                    { value: "local", label: "Local" },
                    { value: "whatsapp", label: "WhatsApp" },
                    { value: "messenger", label: "Messenger" },
                    { value: "instagram", label: "Instagram" },
                    { value: "tiktok", label: "TikTok" },
                  ]}
                  onChange={(e) => setChannel(e.target.value)}
                />
              </>
            ) : (
              <>
                <SelectField
                  id="p3-tag"
                  label="Etiqueta"
                  value={tag}
                  options={[
                    { value: "", label: "Todas" },
                    ...options(cfg.config.tags),
                  ]}
                  onChange={(e) => setTag(e.target.value)}
                />
                <Field
                  id="p3-city"
                  label="Ciudad"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                />
                <Field
                  id="p3-program"
                  label="Programa informado"
                  value={program}
                  onChange={(event) => setProgram(event.target.value)}
                />
                <Field
                  id="p3-type"
                  label="Tipo de contacto"
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                />
              </>
            )}
            <Button
              onClick={() => {
                setOffset(0);
                setAnchor("");
                changed();
              }}
            >
              Actualizar listado
            </Button>
            {session.actions.includes("crm.write") && (
              <Button
                disabled={
                  !cfg.ready ||
                  !cfg.config.stages.some((stage) => stage.active !== false)
                }
                onClick={() => {
                  setCreating(true);
                  setSelected("");
                }}
              >
                Nuevo contacto
              </Button>
            )}
          </section>
          {cfg.error && <Notice error>{cfg.error}</Notice>}
          {list.error && <Notice error>{list.error}</Notice>}
          <div className="p3-columns" ref={gridRef}>
            <aside
              className="panel p3-directory"
              aria-label={page === "inbox" ? "Conversaciones" : "Contactos CRM"}
            >
              {!list.value ? (
                <Notice>Cargando listado…</Notice>
              ) : (
                <>
                  <p>{list.value.total} resultados</p>
                  {list.value.items.map((row) => (
                    <button
                      className="p3-contact"
                      key={row.conversationId}
                      aria-pressed={selected === row.conversationId}
                      onClick={() => {
                        setCreating(false);
                        setSelected(row.conversationId);
                      }}
                    >
                      <strong>{row.name || row.phone}</strong>
                      <span>
                        {row.stage} · {row.assignee || "Sin asignar"}
                        {row.unread ? " · No leída" : ""}
                      </span>
                      <span>
                        {row.risk.status === "known"
                          ? `Abandono: ${{ low: "bajo", medium: "medio", high: "alto" }[row.risk.level] ?? "sin evaluación"}`
                          : "Abandono: sin evaluación"}
                      </span>
                    </button>
                  ))}
                  {!list.value.items.length && (
                    <Notice>Sin resultados para estos filtros.</Notice>
                  )}
                  <div className="p3-actions">
                    <Button
                      variant="quiet"
                      disabled={offset === 0}
                      onClick={() => setOffset((n) => Math.max(0, n - 25))}
                    >
                      Anterior
                    </Button>
                    <span>Página {Math.floor(offset / 25) + 1}</span>
                    <Button
                      variant="quiet"
                      disabled={!list.value.hasMore}
                      onClick={() => {
                        if (offset === 0 && list.value)
                          setAnchor(list.value.revision);
                        setOffset((n) => n + 25);
                      }}
                    >
                      Siguiente
                    </Button>
                  </div>
                </>
              )}
            </aside>
            {creating ? (
              <CreateContact
                config={cfg.config}
                revision={list.value?.revision ?? ""}
                changed={(conversation) => {
                  setCreating(false);
                  setSelected(conversation);
                  changed();
                }}
              />
            ) : selected ? (
              <Person
                key={selected}
                conversation={selected}
                page={page}
                refresh={refresh}
                changed={changed}
                config={cfg.config}
                drafts={drafts}
                messageDrafts={messages}
                users={directory.value?.items ?? []}
              />
            ) : (
              <section className="panel">
                <h2>
                  {page === "inbox"
                    ? "Selecciona una conversación"
                    : "Selecciona un contacto"}
                </h2>
                <p>La ficha se comparte entre CRM e Inbox.</p>
                {!cfg.config.stages.some((s) => s.active !== false) && (
                  <a href="#/settings/crm">Configurar las etapas del CRM</a>
                )}
              </section>
            )}
          </div>
        </>
      )}
    </div>
  );
}
function ContactEditor({
  client,
  revision,
  config,
  drafts,
  saved,
  create = false,
}: {
  client: Client;
  revision: string;
  config: CrmConfig;
  drafts: Map<string, Client>;
  saved: (result: Record<string, unknown>) => void;
  create?: boolean;
}) {
  const { session } = useInstitution(),
    [editing, setEditing] = useState({
      source: client,
      draft: drafts.get(client.id) ?? client,
    }),
    command = useCommand(() => {});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  if (editing.source !== client) {
    setEditing({
      source: client,
      draft:
        editing.source.id === client.id && drafts.has(client.id)
          ? editing.draft
          : (drafts.get(client.id) ?? client),
    });
  }
  const draft = editing.draft;
  const setDraft = (value: Client) =>
    setEditing({ source: client, draft: value });
  const dirty = JSON.stringify(client) !== JSON.stringify(draft);
  function edit(value: Client) {
    setFieldErrors({});
    setDraft(value);
    if (JSON.stringify(value) === JSON.stringify(client))
      drafts.delete(client.id);
    else drafts.set(client.id, value);
  }
  return (
    <form
      className="panel"
      onSubmit={(e) => {
        e.preventDefault();
        const errors = validateCrmClient(
          draft,
          config,
          create ? undefined : client,
        );
        setFieldErrors(errors);
        if (Object.keys(errors).length) return;
        void command
          .save(`clients/${client.id}`, create ? "POST" : "PUT", {
            revision,
            client: draft,
          })
          .then((result) => {
            if (result) {
              drafts.delete(client.id);
              saved(result);
            }
          });
      }}
    >
      <h2>{create ? "Nuevo contacto" : "Ficha del contacto"}</h2>
      <p className="scope-text">
        Datos declarados en CRM. El expediente académico conserva su autoridad
        en SIIE.
      </p>
      <fieldset
        disabled={!session.actions.includes("crm.write") || command.busy}
      >
        <ClientFields
          client={draft}
          setDraft={edit}
          config={config}
          programs={[]}
          catalogError=""
          tags={config.tags}
          stages={config.stages
            .filter((s) => s.active !== false || s.label === draft.stage)
            .map((s) => s.label)}
          fieldErrors={fieldErrors}
          setFeedback={() => {}}
        />
        <div className="p3-actions">
          <Button type="submit" disabled={!revision || !draft.stage}>
            {command.busy ? "Guardando…" : "Guardar ficha"}
          </Button>
          <Button
            variant="quiet"
            onClick={() => {
              if (
                !dirty ||
                window.confirm("¿Descartar los cambios de esta ficha?")
              ) {
                drafts.delete(client.id);
                setDraft(client);
              }
            }}
          >
            Restaurar versión consultada
          </Button>
        </div>
      </fieldset>
      {command.error && <Notice error>{command.error}</Notice>}
    </form>
  );
}
function CreateContact({
  config,
  revision,
  changed,
}: {
  config: CrmConfig;
  revision: string;
  changed: (conversation: string) => void;
}) {
  const cache = useCache(),
    [workspaceSession] = useWorkspaceState("institutional");
  const [client] = useState<Client>(() => {
    const identity = cache.get("new-contact") as string | undefined;
    const id = identity ?? crypto.randomUUID();
    cache.set("new-contact", id);
    return {
      id,
      name: "",
      phone: "",
      city: "",
      programId: null,
      program: "",
      schedule: "",
      stage: config.stages.find((stage) => stage.active !== false)?.label ?? "",
      tags: "",
      notes: "",
      type: "",
      interests: "",
      customValues: {},
    };
  });
  const drafts = workspaceSession.contacts;
  return (
    <ContactEditor
      client={client}
      revision={revision}
      config={config}
      drafts={drafts}
      create
      saved={(result) => {
        cache.delete("new-contact");
        changed(String(result.conversationId));
      }}
    />
  );
}
function Person({
  conversation,
  page,
  refresh,
  changed,
  config,
  drafts,
  messageDrafts,
  users,
}: {
  conversation: string;
  page: string;
  refresh: number;
  changed: () => void;
  config: CrmConfig;
  drafts: Map<string, Client>;
  messageDrafts: Map<string, string>;
  users: { id: string; name: string }[];
}) {
  const [activityOpened, setActivityOpened] = useState(false);
  const { session } = useInstitution();
  const detail = useRead<Detail>(
    page === "inbox"
      ? `inbox/${conversation}/detail`
      : `conversations/${conversation}`,
    refresh,
  );
  if (!detail.value)
    return (
      <Notice error={!!detail.error}>
        {detail.error || "Cargando ficha…"}
      </Notice>
    );
  return (
    <div className={`p3-person ${page === "inbox" ? "p3-inbox-person" : ""}`}>
      {detail.error && <Notice error>{detail.error}</Notice>}
      {page === "inbox" && (
        <Conversation
          conversation={conversation}
          detail={detail.value}
          refresh={refresh}
          changed={changed}
          drafts={messageDrafts}
          users={users}
        />
      )}
      <div className="p3-ficha">
        <RiskSummary risk={detail.value.risk} />
        {page === "inbox" && detail.value.agentOperations && (
          <section className="panel">
            <AgentConversationPanel
              institutional
              canWrite={session.actions.includes("inbox.write")}
              conversationId={conversation}
              refresh={refresh}
              onConfirmed={changed}
            />
          </section>
        )}
        {page === "inbox" && detail.value.knowledgeOperations && (
          <PrivateMemory
            conversation={conversation}
            canWrite={session.actions.includes("inbox.write")}
          />
        )}
        <ContactEditor
          client={detail.value.client}
          revision={detail.value.revision}
          config={config}
          drafts={drafts}
          saved={() => changed()}
        />
        <ManualAssessment detail={detail.value} changed={changed} />
        <Notes detail={detail.value} changed={changed} />
        <TaskList
          refresh={refresh}
          changed={changed}
          contact={detail.value.client.id}
          conversation={conversation}
          users={users}
        />
        <MergePanel detail={detail.value} changed={changed} />
        <details
          className="panel"
          onToggle={(event) => setActivityOpened(event.currentTarget.open)}
        >
          <summary>Actividad y procedencia</summary>
          {activityOpened && (
            <Activity contact={detail.value.client.id} refresh={refresh} />
          )}
          <p>
            Ficha: datos declarados CRM. Identidad académica: sin vínculo
            confirmado; no se crean alumnos ni matrículas.
          </p>
        </details>
      </div>
    </div>
  );
}
function Conversation({
  conversation,
  detail,
  refresh,
  changed,
  drafts,
  users,
}: {
  conversation: string;
  detail: Detail;
  refresh: number;
  changed: () => void;
  drafts: Map<string, string>;
  users: { id: string; name: string }[];
}) {
  const { session } = useInstitution(),
    [before, setBefore] = useState(""),
    data = useRead<{
      items: Message[];
      before: string | null;
      hasMore: boolean;
    }>(
      `conversations/${conversation}/messages${before ? `?before=${before}` : ""}`,
      refresh,
    ),
    [body, setBody] = useState(drafts.get(conversation) ?? ""),
    [attachment, setAttachment] = useState<Attachment | null>(null),
    [state, setState] = useCachedDraft(
      `conversation:${conversation}:state`,
      detail.thread.State,
    ),
    [priority, setPriority] = useCachedDraft(
      `conversation:${conversation}:priority`,
      detail.thread.Priority,
    ),
    [owner, setOwner] = useCachedDraft(
      `conversation:${conversation}:owner`,
      detail.thread.UserId ?? "",
    ),
    [mode, setMode] = useCachedDraft(
      `conversation:${conversation}:mode`,
      detail.thread.ControlMode,
    ),
    command = useCommand(changed);
  const observed = useRef("0");
  useEffect(() => {
    if (!before && data.value?.items.length)
      observed.current = data.value.items.at(-1)!.sequence;
  }, [before, data.value]);
  const update = (next: Record<string, unknown> = {}) =>
    command.save(`conversations/${conversation}`, "PUT", {
      revision: detail.revision,
      state,
      priority,
      userId: owner || null,
      mode,
      unread: detail.thread.Unread,
      readThrough: observed.current,
      ...next,
    });
  return (
    <section className="panel p3-thread" aria-label="Conversación seleccionada">
      {(detail.inFlightOrUncertain ?? 0) > 0 && (
        <Notice>
          Hay envíos iniciados o de resultado pendiente. Revisa su estado antes
          de responder.
        </Notice>
      )}
      <h2>Conversación</h2>
      <p>
        {detail.thread.ControlMode === "human"
          ? "Control humano"
          : "Control IA · automatización pendiente de habilitación"}
      </p>
      <fieldset
        disabled={!session.actions.includes("inbox.write") || command.busy}
      >
        <div className="form-grid">
          <SelectField
            id="p3-state"
            label="Estado"
            value={state}
            options={states}
            onChange={(e) => setState(e.target.value)}
          />
          <SelectField
            id="p3-priority"
            label="Prioridad"
            value={priority}
            options={priorities}
            onChange={(e) => setPriority(e.target.value)}
          />
          <AssigneePicker
            id="p3-owner"
            label="Responsable humano"
            selectedName={
              owner === detail.thread.UserId
                ? (detail.thread.Assignee ?? undefined)
                : undefined
            }
            value={owner}
            onChange={setOwner}
            users={users}
            inbox
          />
          <SelectField
            id="p3-control"
            label="Control"
            value={mode}
            options={[
              { value: "human", label: "Humano" },
              { value: "ai", label: "IA" },
            ]}
            onChange={(e) => setMode(e.target.value)}
          />
        </div>
        <div className="p3-actions">
          <Button onClick={() => void update()}>Guardar conversación</Button>
          <Button
            onClick={() => {
              setMode("human");
              setOwner(session.user.id);
              void update({ mode: "human", userId: session.user.id });
            }}
          >
            Tomar control humano
          </Button>
          <Button
            variant="quiet"
            onClick={() => void update({ unread: !detail.thread.Unread })}
          >
            {detail.thread.Unread
              ? "Marcar como leída"
              : "Marcar como no leída"}
          </Button>
        </div>
      </fieldset>
      {data.error && <Notice error>{data.error}</Notice>}
      <div className="p3-actions">
        <Button
          variant="quiet"
          disabled={!data.value?.hasMore}
          onClick={() => setBefore(data.value?.before ?? "")}
        >
          Mensajes anteriores
        </Button>
        <Button
          variant="quiet"
          disabled={!before}
          onClick={() => setBefore("")}
        >
          Más recientes
        </Button>
      </div>
      <ol className="p3-messages" aria-label="Mensajes">
        {data.value?.items.map((message) => (
          <li key={message.id} data-direction={message.direction}>
            <small>
              {message.direction === "incoming" ? "Recibido" : "Saliente"} ·{" "}
              <DateText value={message.createdAt} />
            </small>
            <p>{message.body}</p>
            {message.attachments?.map((item) => (
              <MediaDownload key={item.id} attachment={item} />
            ))}
            {message.deliveryState && (
              <small>
                {message.channelAccount} ·{" "}
                {(
                  {
                    queued: "En cola",
                    sending: "Enviando",
                    accepted: "Aceptado por el proveedor",
                    sent: "Enviado",
                    delivered: "Entregado",
                    read: "Leído",
                    uncertain: "Resultado incierto",
                    failed: "Fallido",
                    cancelled: "Cancelado",
                  } as Record<string, string>
                )[message.deliveryState] || message.deliveryState}
              </small>
            )}
          </li>
        ))}
      </ol>
      {!data.value && !data.error && <p>Cargando mensajes…</p>}
      {data.value && data.value.items.length === 0 && (
        <p>Sin mensajes registrados.</p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void command
            .save(`conversations/${conversation}/messages`, "POST", {
              revision: detail.revision,
              body: body || (attachment ? "[Adjunto]" : ""),
              ...(attachment ? { mediaId: attachment.id } : {}),
            })
            .then((result) => {
              if (result) {
                setBody("");
                setAttachment(null);
                drafts.delete(conversation);
                setBefore("");
              }
            });
        }}
      >
        <fieldset
          disabled={
            !session.actions.includes("inbox.write") ||
            detail.thread.ControlMode !== "human" ||
            detail.thread.State === "closed" ||
            command.busy
          }
        >
          <TextArea
            id="p3-message"
            label={detail.channelAccounts?.length ? "Mensaje" : "Mensaje local"}
            value={body}
            maxLength={4000}
            onChange={(e) => {
              setBody(e.target.value);
              drafts.set(conversation, e.target.value);
            }}
          />
          {detail.mediaAvailable && (
            <MediaUpload
              conversation={conversation}
              value={attachment}
              onChange={setAttachment}
            />
          )}
          <Button type="submit" disabled={!body.trim() && !attachment}>
            {detail.channelAccounts?.length
              ? "Enviar mensaje"
              : "Guardar mensaje local"}
          </Button>
        </fieldset>
      </form>
      <p className="scope-text">
        {detail.channelAccounts?.length
          ? "La respuesta se guarda en la cola de esta cuenta. Su estado indica si fue aceptada, enviada o entregada."
          : "Este mensaje se registra en la conversación local. La entrega por proveedores requiere habilitar el canal."}
      </p>
      {command.error && <Notice error>{command.error}</Notice>}
    </section>
  );
}
function AssigneePicker({
  id,
  label,
  value,
  onChange,
  users,
  inbox = false,
  selectedName,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  users: { id: string; name: string }[];
  inbox?: boolean;
  selectedName?: string;
}) {
  const [query, setQuery] = useState(""),
    [offset, setOffset] = useState(0),
    data = useRead<{ items: { id: string; name: string }[]; hasMore: boolean }>(
      `${inbox ? "inbox/" : ""}directory?` +
        new URLSearchParams({ q: query, offset: String(offset) }),
    );
  const items = data.value?.items ?? users;
  return (
    <div>
      <SelectField
        id={id}
        label={label}
        value={value}
        options={[
          { value: "", label: "Sin asignar" },
          ...(value && !items.some((item) => item.id === value)
            ? [{ value, label: selectedName || "Responsable seleccionado" }]
            : []),
          ...items.map((item) => ({ value: item.id, label: item.name })),
        ]}
        onChange={(e) => onChange(e.target.value)}
      />
      {data.error && <Notice error>{data.error}</Notice>}
      <details className="p3-assignee-search">
        <summary>Buscar otros responsables</summary>
        <Field
          id={`${id}-search`}
          label={`Buscar ${label.toLowerCase()}`}
          value={query}
          onChange={(e) => {
            setOffset(0);
            setQuery(e.target.value);
          }}
        />
      </details>
      {(offset > 0 || data.value?.hasMore) && (
        <div className="p3-actions">
          <Button
            variant="quiet"
            disabled={offset === 0}
            onClick={() => setOffset((n) => Math.max(0, n - 25))}
          >
            Responsables anteriores
          </Button>
          <Button
            variant="quiet"
            disabled={!data.value?.hasMore}
            onClick={() => setOffset((n) => n + 25)}
          >
            Más responsables
          </Button>
        </div>
      )}
    </div>
  );
}
function SlaPolicy({
  refresh,
  changed,
}: {
  refresh: number;
  changed: () => void;
}) {
  const data = useRead<{
    configured: boolean;
    enabled: boolean;
    thresholdMinutes: number | null;
    revision: string;
  }>("policy", refresh);
  if (!data.value)
    return (
      <Notice error={!!data.error}>
        {data.error || "Cargando tiempos de atención…"}
      </Notice>
    );
  return <SlaEditor initial={data.value} changed={changed} />;
}
function SlaEditor({
  initial,
  changed,
}: {
  initial: {
    configured: boolean;
    enabled: boolean;
    thresholdMinutes: number | null;
    revision: string;
  };
  changed: () => void;
}) {
  const [enabled, setEnabled] = useCachedDraft("sla:enabled", initial.enabled),
    [minutes, setMinutes] = useCachedDraft(
      "sla:minutes",
      initial.thresholdMinutes == null ? "" : String(initial.thresholdMinutes),
    ),
    { session } = useInstitution(),
    command = useCommand(changed);
  return (
    <details className="panel">
      <summary>Tiempo de atención</summary>
      <p>
        {initial.configured
          ? "Política institucional configurada."
          : "Sin configurar. No se supone un tiempo de respuesta."}
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void command.save("policy", "PUT", {
            revision: initial.revision,
            enabled,
            thresholdMinutes: Number(minutes),
          });
        }}
      >
        <fieldset
          disabled={
            !session.actions.includes("settings.crm.write") || command.busy
          }
        >
          <label>
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            Activar seguimiento del tiempo de respuesta
          </label>
          <Field
            id="p3-sla-minutes"
            label="Plazo de respuesta en minutos"
            type="number"
            min={1}
            max={525600}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
          />
          <Button type="submit" disabled={!minutes}>
            Guardar tiempo de atención
          </Button>
        </fieldset>
        {command.error && <Notice error>{command.error}</Notice>}
      </form>
    </details>
  );
}
function ManualAssessment({
  detail,
  changed,
}: {
  detail: Detail;
  changed: () => void;
}) {
  const [score, setScore] = useCachedDraft(
      `manual:${detail.thread.ConversationId}:score`,
      detail.manual?.score == null ? "" : String(detail.manual.score),
    ),
    [temperature, setTemperature] = useCachedDraft(
      `manual:${detail.thread.ConversationId}:temperature`,
      detail.manual?.temperature ?? "",
    ),
    { session } = useInstitution(),
    command = useCommand(changed);
  return (
    <details className="panel">
      <summary>Valoración manual de interés</summary>
      <p>
        Origen humano
        {detail.manual ? (
          <>
            {" "}
            · <DateText value={detail.manual.asOf} />
          </>
        ) : (
          " · Sin valoración"
        )}
        . Se conserva separada del riesgo de abandono y de futuras predicciones.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void command.save(
            `conversations/${detail.thread.ConversationId}/manual`,
            "PUT",
            {
              revision: detail.revision,
              score: score === "" ? null : Number(score),
              temperature: temperature || null,
            },
          );
        }}
      >
        <fieldset
          disabled={!session.actions.includes("crm.write") || command.busy}
        >
          <Field
            id="p3-manual-score"
            label="Puntuación manual de interés"
            type="number"
            min={0}
            max={100}
            step={1}
            value={score}
            onChange={(e) => setScore(e.target.value)}
          />
          <SelectField
            id="p3-manual-temperature"
            label="Interés observado"
            value={temperature}
            options={[
              { value: "", label: "Sin valorar" },
              { value: "cold", label: "Bajo" },
              { value: "warm", label: "Medio" },
              { value: "hot", label: "Alto" },
            ]}
            onChange={(e) => setTemperature(e.target.value)}
          />
          <Button type="submit">Guardar valoración manual</Button>
        </fieldset>
        {command.error && <Notice error>{command.error}</Notice>}
      </form>
    </details>
  );
}
function Notes({ detail, changed }: { detail: Detail; changed: () => void }) {
  const [body, setBody] = useCachedDraft(`note:${detail.client.id}`, ""),
    [offset, setOffset] = useState(0),
    command = useCommand(changed),
    { session } = useInstitution();
  const [opened, setOpened] = useState(false);
  const notes = useRead<{ items: Detail["notes"]; hasMore: boolean }>(
    `clients/${detail.client.id}/notes?offset=${offset}`,
    Number(detail.revision),
    opened,
  );
  return (
    <details
      className="panel"
      onToggle={(event) => setOpened(event.currentTarget.open)}
    >
      <summary>Notas de seguimiento · {detail.notes.length}</summary>
      <ul>
        {(notes.value?.items ?? detail.notes).map((note) => (
          <li key={note.id}>
            <p>{note.body}</p>
            <small>
              {note.author} · <DateText value={note.createdAt} />
            </small>
          </li>
        ))}
      </ul>
      <div className="p3-actions">
        <Button
          variant="quiet"
          disabled={offset === 0}
          onClick={() => setOffset((n) => Math.max(0, n - 25))}
        >
          Notas anteriores
        </Button>
        <Button
          variant="quiet"
          disabled={!notes.value?.hasMore}
          onClick={() => setOffset((n) => n + 25)}
        >
          Más notas
        </Button>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void command
            .save(`clients/${detail.client.id}/notes`, "POST", {
              revision: detail.revision,
              body,
            })
            .then((result) => {
              if (result) setBody("");
            });
        }}
      >
        <fieldset
          disabled={!session.actions.includes("crm.write") || command.busy}
        >
          <TextArea
            id="p3-note"
            label="Añadir nota de seguimiento"
            value={body}
            maxLength={2000}
            onChange={(e) => setBody(e.target.value)}
          />
          <Button type="submit" disabled={!body.trim()}>
            Guardar nota
          </Button>
        </fieldset>
      </form>
      {command.error && <Notice error>{command.error}</Notice>}
    </details>
  );
}
function TaskList({
  refresh,
  changed,
  contact = "",
  conversation = "",
  users,
  onOpen,
}: {
  onOpen?: (conversation: string) => void;
  refresh: number;
  changed: () => void;
  contact?: string;
  conversation?: string;
  users: { id: string; name: string }[];
}) {
  const [opened, setOpened] = useState(!contact);
  const entity = useEntity(`task:${conversation}`);
  const [status, setStatus] = useState("pending"),
    [offset, setOffset] = useState(0),
    [anchor, setAnchor] = useState(""),
    [query, setQuery] = useState(""),
    [title, setTitle] = useCachedDraft(`task:${conversation}:title`, ""),
    [due, setDue] = useCachedDraft(`task:${conversation}:due`, ""),
    [owner, setOwner] = useCachedDraft(`task:${conversation}:owner`, ""),
    { session } = useInstitution(),
    command = useCommand(changed);
  const tasks = useRead<Tasks>(
    "tasks?" +
      new URLSearchParams({
        status,
        offset: String(offset),
        anchor: offset ? anchor : "",
        q: query,
        contact,
      }),
    refresh,
    opened,
  );
  const filterKey = JSON.stringify([status, query, contact]);
  const [lastFilterKey, setLastFilterKey] = useState(filterKey);
  if (lastFilterKey !== filterKey) {
    setLastFilterKey(filterKey);
    setOffset(0);
    setAnchor("");
  }
  return (
    <details
      className="panel"
      open={opened}
      onToggle={(event) => setOpened(event.currentTarget.open)}
    >
      <summary>Tareas{tasks.value ? ` · ${tasks.value.total}` : ""}</summary>
      <SelectField
        id={`p3-task-filter-${contact}`}
        label="Estado de tareas"
        value={status}
        options={[{ value: "", label: "Todas" }, ...statuses]}
        onChange={(e) => setStatus(e.target.value)}
      />
      <Field
        id={`p3-task-query-${contact}`}
        label="Buscar tareas"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {tasks.error && <Notice error>{tasks.error}</Notice>}
      <Button
        variant="quiet"
        onClick={() => {
          setOffset(0);
          setAnchor("");
          changed();
        }}
      >
        Actualizar tareas
      </Button>
      <ul>
        {tasks.value?.items.map((task) => (
          <li key={task.id}>
            <strong>{task.title}</strong>
            {task.contactName && <p>{task.contactName}</p>}
            {onOpen && (
              <Button
                variant="quiet"
                onClick={() => onOpen(task.conversationId)}
              >
                Abrir conversación
              </Button>
            )}
            <p>
              {statuses.find((s) => s.value === task.status)?.label} ·{" "}
              {task.assignee || "Sin asignar"} · <DateText value={task.dueAt} />
            </p>
            <SelectField
              id={`task-${task.id}`}
              label={`Estado de ${task.title}`}
              disabled={!session.actions.includes("crm.write") || command.busy}
              value={task.status}
              options={statuses}
              onChange={(e) =>
                void command.save(`tasks/${task.id}`, "PUT", {
                  revision: tasks.value!.revision,
                  conversationId: task.conversationId,
                  title: task.title,
                  status: e.target.value,
                  priority: task.priority,
                  userId: task.userId,
                  dueAt: task.dueAt,
                })
              }
            />
          </li>
        ))}
      </ul>
      <div className="p3-actions">
        <Button
          variant="quiet"
          disabled={offset === 0}
          onClick={() => setOffset((n) => Math.max(0, n - 25))}
        >
          Tareas anteriores
        </Button>
        <Button
          variant="quiet"
          disabled={!tasks.value?.hasMore}
          onClick={() => {
            setAnchor(tasks.value?.revision ?? "");
            setOffset((n) => n + 25);
          }}
        >
          Más tareas
        </Button>
      </div>
      {conversation && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void command
              .save(`tasks/${entity.get()}`, "PUT", {
                revision: tasks.value?.revision,
                conversationId: conversation,
                title,
                status: "pending",
                priority: "normal",
                userId: owner || null,
                dueAt: due ? new Date(due).toISOString() : null,
              })
              .then((result) => {
                if (result) {
                  entity.reset();
                  setTitle("");
                  setDue("");
                  setOwner("");
                }
              });
          }}
        >
          <fieldset
            disabled={!session.actions.includes("crm.write") || command.busy}
          >
            <Field
              id="p3-task-title"
              label="Nueva tarea"
              value={title}
              maxLength={120}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Field
              id="p3-task-due"
              label="Fecha límite (hora del dispositivo)"
              type="datetime-local"
              value={due}
              onChange={(e) => setDue(e.target.value)}
            />
            <AssigneePicker
              id="p3-task-owner"
              label="Responsable de la tarea"
              value={owner}
              onChange={setOwner}
              users={users}
            />
            <Button type="submit" disabled={!title.trim() || !tasks.value}>
              Crear tarea
            </Button>
          </fieldset>
        </form>
      )}
      {command.error && <Notice error>{command.error}</Notice>}
    </details>
  );
}
function MergePanel({
  detail,
  changed,
}: {
  detail: Detail;
  changed: () => void;
}) {
  const [opened, setOpened] = useState(false);
  const entity = useEntity(`merge:${detail.client.id}`);
  const [query, setQuery] = useState(""),
    [target, setTarget] = useState<Row | null>(null),
    [confirmed, setConfirmed] = useState(false),
    { session } = useInstitution(),
    command = useCommand(changed);
  const candidates = useRead<Page>(
    "clients?" + new URLSearchParams({ q: query }),
    0,
    opened && !!query.trim(),
  );
  const groups = useRead<{
    items: {
      id: string;
      sourceContactId: string;
      sourceName?: string;
      targetContactId: string;
    }[];
  }>(`clients/${detail.client.id}/groups`, Number(detail.revision), opened);
  return (
    <details
      className="panel"
      onToggle={(event) => setOpened(event.currentTarget.open)}
    >
      <summary>Identidad y unificación reversible</summary>
      <p>
        Persona principal: {detail.client.name}. {detail.members.length}{" "}
        registros vinculados. Los originales conservan sus datos y
        conversaciones; esta acción no cambia SIIE.
      </p>
      <fieldset
        disabled={!session.actions.includes("crm.write") || command.busy}
      >
        <Field
          id="p3-merge-query"
          label="Buscar persona principal para vincular"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setTarget(null);
            setConfirmed(false);
          }}
        />
        {query.trim() &&
          candidates.value?.items
            .filter((row) => row.id !== detail.client.id)
            .map((row) => (
              <Button
                key={row.id}
                variant="quiet"
                onClick={() => setTarget(row)}
              >
                {row.name} · {row.phone}
              </Button>
            ))}
        {target && (
          <>
            <p>
              Se usará la ficha de {target.name} ({target.phone}) como
              principal. La ficha actual conserva sus datos y puede separarse
              después.
            </p>
            <label>
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              Confirmo que ambos registros corresponden a la misma persona.
            </label>
            <Button
              disabled={!confirmed}
              onClick={() =>
                void command
                  .save(`merges/${entity.get()}`, "POST", {
                    revision: detail.revision,
                    sourceContactId: detail.client.id,
                    targetContactId: target.id,
                    confirmedSamePerson: true,
                  })
                  .then((result) => {
                    if (result) {
                      entity.reset();
                      setTarget(null);
                      setQuery("");
                      setConfirmed(false);
                    }
                  })
              }
            >
              Vincular con esta ficha principal
            </Button>
          </>
        )}
        {groups.value?.items.map((group) => (
          <Button
            key={group.id}
            variant="quiet"
            onClick={() => {
              if (
                window.confirm(
                  "¿Separar este vínculo conservando sus registros originales?",
                )
              )
                void command.save(`merges/${group.id}/undo`, "POST", {
                  revision: detail.revision,
                });
            }}
          >
            Separar registro
            {group.sourceName ? ` de ${group.sourceName}` : " vinculado"}
          </Button>
        ))}
      </fieldset>
      {command.error && <Notice error>{command.error}</Notice>}
    </details>
  );
}
function Activity({ contact, refresh }: { contact: string; refresh: number }) {
  const [offset, setOffset] = useState(0),
    data = useRead<{
      items: {
        id: number;
        action: string;
        author: string | null;
        createdAt: string;
      }[];
      hasMore: boolean;
    }>(`clients/${contact}/activity?offset=${offset}`, refresh);
  const labels: Record<string, string> = {
    "workspace.create": "Contacto creado",
    "workspace.contact": "Ficha actualizada",
    "workspace.conversation": "Conversación actualizada",
    "workspace.message": "Mensaje local registrado",
    "workspace.note": "Nota añadida",
    "workspace.task": "Tarea actualizada",
    "workspace.merge": "Identidades vinculadas",
    "workspace.undo": "Vínculo separado",
    "workspace.manual": "Valoración manual actualizada",
  };
  return (
    <>
      {data.error && <Notice error>{data.error}</Notice>}
      <ul>
        {data.value?.items.map((item) => (
          <li key={item.id}>
            {labels[item.action] ?? "Actividad registrada"} ·{" "}
            {item.author || "Sistema"} · <DateText value={item.createdAt} />
          </li>
        ))}
      </ul>
      <Button
        variant="quiet"
        disabled={offset === 0}
        onClick={() => setOffset((n) => Math.max(0, n - 25))}
      >
        Actividad anterior
      </Button>
      <Button
        variant="quiet"
        disabled={!data.value?.hasMore}
        onClick={() => setOffset((n) => n + 25)}
      >
        Más actividad
      </Button>
    </>
  );
}
