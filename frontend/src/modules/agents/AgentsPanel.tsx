import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { providerNames } from "../../shared/aiSettings";
import { useWorkspaceState } from "../../shared/workspaceSession";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../../shared/ui";
import {
  api,
  blankConfiguration,
  instructionTemplates,
  labels,
  message,
  mutation,
  type Agent,
  type Catalog,
  type Source,
  type Stage,
  type ProviderOptions,
  type AgentConsole,
} from "./api";
import { AgentConfigurationExtras } from "./AgentConfigurationExtras";
import { AgentOperatingConsole } from "./AgentOperatingConsole";
import { AgentGuide } from "./AgentGuide";
import { ProgramSelector } from "./ProgramSelector";
import { useDraftGuard } from "../../institution/drafts";
import { AgentVoiceSelect } from "../../institution/AgentVoiceSelect";
import { AgentSalesSkills } from "../../institution/AgentSalesSkills";
import { ProgramSalesSetup } from "../../institution/ProgramSalesSetup";
import { OperationDialog } from "../../institution/ErrorFeedback";
import "./agents.css";

type Tab =
  | "Mis agentes"
  | "Etapas"
  | "Fuentes"
  | "Diagnóstico"
  | "Simulador"
  | "Actividad"
  | "Supervisión";
type Review = {
  agent_id: string;
  revision: number;
  ready: boolean;
  checks: string[];
  version: number;
  effective: unknown;
};
type Event = {
  id: number;
  kind: string;
  note: string;
  actor: string;
  created_at: string;
};
type Simulation = {
  agent_id: string;
  config_version: number;
  text?: string;
  handoff?: boolean;
  sources: { id: string; title: string }[];
  model?: string;
  network_called: boolean;
  messages: unknown;
  usage: unknown;
};
type Supervision = {
  items: {
    message_id: string;
    conversation_id: string;
    state: string;
    reason: string | null;
    created_at: string;
    agent: { agent_id: string; version: number } | null;
  }[];
  has_more: boolean;
  usage: {
    requests: number;
    tokens_reserved: number;
    tokens_reported: number | null;
  };
};
const emptyAgent = (): Agent => ({
  id: crypto.randomUUID(),
  name: "",
  level: "guide",
  parent_id: null,
  program_id: null,
  stage_id: null,
  state: "draft",
  version: 0,
  revision: 0,
  approved_version: null,
  configuration: blankConfiguration(),
});
const emptyStage = (): Stage => ({
  id: crypto.randomUUID(),
  program_id: 0,
  name: "",
  entry_rule: "",
  exit_rule: "",
  evidence_required: "",
  revision: 0,
  approved: false,
});
const lineList = (value: string) => value.split("\n");

export function AgentsPanel() {
  const [, setSettingsSection] = useWorkspaceState("settingsSection");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [providers, setProviders] = useState<ProviderOptions | null>(null);
  const [tab, setTab] = useState<Tab>("Mis agentes");
  const [draft, setDraft] = useState<Agent | null>(null);
  const [variablesText, setVariablesText] = useState("{}");
  const [variablesError, setVariablesError] = useState("");
  const initialSelection = useRef(false);
  const draftFormRef = useRef<HTMLFormElement>(null);
  const [createFocusRequest, setCreateFocusRequest] = useState(0);
  useEffect(() => {
    if (createFocusRequest)
      draftFormRef.current
        ?.querySelector<HTMLInputElement>("#agent-name")
        ?.focus();
  }, [createFocusRequest]);
  const [stage, setStage] = useState<Stage>(emptyStage);
  const [source, setSource] = useState<Source | null>(null);
  const [sourceOwner, setSourceOwner] = useState("");
  const [until, setUntil] = useState("");
  const [sourceProgram, setSourceProgram] = useState("");
  const [sourceStage, setSourceStage] = useState("");
  const [search, setSearch] = useState("");
  const [programFilter, setProgramFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [note, setNote] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [review, setReview] = useState<Review | null>(null);
  const [question, setQuestion] = useState("");
  const [channel, setChannel] = useState("local");
  const [consoleData, setConsoleData] = useState<AgentConsole | null>(null);
  const [guideOpen, setGuideOpen] = useState(false);
  const [simulationVariant, setSimulationVariant] = useState("current");
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [eventOffset, setEventOffset] = useState(0);
  const [eventMore, setEventMore] = useState(false);
  const [supervision, setSupervision] = useState<Supervision | null>(null);
  const [jobOffset, setJobOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");

  async function refresh() {
    const [value, options] = await Promise.all([
      api<Catalog>(),
      api<ProviderOptions>("/providers"),
    ]);
    setCatalog(value);
    setProviders(options);
    return value;
  }
  useEffect(() => {
    let live = true;
    void Promise.all([api<Catalog>(), api<ProviderOptions>("/providers")])
      .then(([value, options]) => {
        if (live) {
          setCatalog(value);
          setProviders(options);
        }
      })
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, []);
  async function act(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setFeedback("");
    try {
      await work();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No se pudo completar la operación.",
      );
    } finally {
      setBusy(false);
    }
  }
  const programs = catalog?.programs?.items ?? [];
  const programOptions = programs.map((p) => ({
    value: String(p.program_id),
    label: `${p.name}${p.schedule ? " · " + p.schedule : ""}`,
  }));
  const saved = catalog?.agents.find((a) => a.id === draft?.id);
  const archived = saved?.state === "archived";
  useEffect(() => {
    let live = true;
    void Promise.resolve().then(async () => {
      if (!live) return;
      setConsoleData(null);
      if (saved)
        await api<AgentConsole>(`/profiles/${saved.id}/console`)
          .then((value) => {
            if (live) setConsoleData(value);
          })
          .catch((failure: Error) => {
            if (live) setError(failure.message);
          });
    });
    return () => {
      live = false;
    };
  }, [saved]);
  async function loadConsole() {
    if (saved)
      setConsoleData(await api<AgentConsole>(`/profiles/${saved.id}/console`));
  }
  const diagnosisBinding = useRef("");
  useLayoutEffect(() => {
    diagnosisBinding.current = saved
      ? JSON.stringify([saved.id, saved.version, saved.revision])
      : "";
  }, [saved]);
  async function diagnose() {
    if (!saved) return;
    const binding = diagnosisBinding.current;
    const result = await api<Review>(`/profiles/${saved.id}/preflight`);
    if (
      diagnosisBinding.current !== binding ||
      result.version !== saved.version
    ) {
      setReview(null);
      setError(
        "El diagnóstico no corresponde al perfil o versión actual. Actualice antes de consultarlo.",
      );
      return;
    }
    setReview({ ...result, agent_id: saved.id, revision: saved.revision });
  }
  const draftChanged =
    !!saved &&
    !!draft &&
    (!!variablesError ||
      draft.name !== saved.name ||
      JSON.stringify(draft.configuration) !==
        JSON.stringify({
          ...blankConfiguration(),
          ...saved.configuration,
          provider: saved.configuration.provider ?? "openrouter",
        }));
  useDraftGuard(draftChanged || (!!draft && !saved && !!draft.name.trim()));
  const selectedProvider = providers?.providers.find(
    (p) => p.id === draft?.configuration.provider,
  );
  const modelOptions =
    selectedProvider?.models.map((m) => ({
      value: m.id,
      label:
        m.name + (m.origin === "saved_configuration" ? " · configurado" : ""),
    })) ?? [];
  const fallbackOptions =
    providers?.providers
      .find(
        (provider) =>
          provider.id ===
          (draft?.configuration.fallback_provider ||
            draft?.configuration.provider),
      )
      ?.models.map((model) => ({ value: model.id, label: model.name })) ?? [];
  if (
    draft?.configuration.fallback_model &&
    !fallbackOptions.some(
      (model) => model.value === draft.configuration.fallback_model,
    )
  )
    fallbackOptions.push({
      value: draft.configuration.fallback_model,
      label: draft.configuration.fallback_model + " · guardado",
    });
  for (const value of [
    draft?.configuration.primary_model,
    draft?.configuration.fallback_model,
  ]) {
    if (value && !modelOptions.some((m) => m.value === value))
      modelOptions.push({ value, label: value + " · guardado en el perfil" });
  }
  const programName = (id: number | null) =>
    programs.find((p) => p.program_id === id)?.name ?? "Programa no disponible";
  function select(agent: Agent) {
    setDraft(
      structuredClone({
        ...agent,
        configuration: {
          ...blankConfiguration(),
          ...agent.configuration,
          provider: agent.configuration.provider ?? "openrouter",
        },
      }),
    );
    setVariablesText(
      JSON.stringify(agent.configuration.template_variables ?? {}, null, 2),
    );
    setVariablesError("");
    setReview(null);
    setSimulation(null);
    setConfirmed(false);
    setNote("");
  }
  useEffect(() => {
    if (!catalog || initialSelection.current) return;
    initialSelection.current = true;
    const first =
      catalog.agents.find((agent) => agent.state !== "archived") ??
      catalog.agents[0];
    void Promise.resolve().then(() => {
      if (first && !draft) select(first);
    });
  }, [catalog, draft]);
  function patch(p: Partial<Agent>) {
    setDraft((current) => (current ? { ...current, ...p } : current));
    setReview(null);
    setSimulation(null);
    setConfirmed(false);
  }
  function configure(p: Partial<Agent["configuration"]>) {
    if (draft) patch({ configuration: { ...draft.configuration, ...p } });
  }
  function updateVariables(value: string) {
    setVariablesText(value);
    try {
      const parsed: unknown = JSON.parse(value);
      if (
        !parsed ||
        Array.isArray(parsed) ||
        typeof parsed !== "object" ||
        Object.entries(parsed).some(
          ([key, item]) =>
            !/^[A-Za-z_][A-Za-z0-9_]*$/.test(key) ||
            typeof item !== "string" ||
            [
              "agent_name",
              "agent_description",
              "agent_specialty",
              "program_id",
            ].includes(key),
        )
      ) {
        throw new Error("invalid_variables");
      }
      setVariablesError("");
      configure({ template_variables: parsed as Record<string, string> });
    } catch {
      setVariablesError(
        "Use un objeto JSON con nombres de variable y valores de texto. Los nombres automáticos del agente y programa están reservados.",
      );
    }
  }
  function toggle(
    field: "channels" | "capabilities" | "document_ids",
    value: string,
  ) {
    if (!draft) return;
    const values = draft.configuration[field];
    configure({
      [field]: values.includes(value)
        ? values.filter((v) => v !== value)
        : [...values, value],
    });
  }
  async function save() {
    if (!draft || archived || variablesError) return;
    await api(`/profiles/${draft.id}`, "PUT", {
      ...mutation(draft.revision),
      name: draft.name,
      level: draft.level,
      parent_id: draft.parent_id,
      program_id: draft.program_id,
      stage_id: draft.stage_id,
      configuration: draft.configuration,
    });
    const next = await refresh();
    const item = next.agents.find((a) => a.id === draft.id);
    if (item) select(item);
    setFeedback(
      item?.state === "paused"
        ? "Configuración guardada. El agente continúa pausado."
        : "Configuración guardada. El agente está disponible; las conexiones y el control humano conservan sus ajustes.",
    );
  }
  async function change(state: string) {
    if (!saved) return;
    await api(`/profiles/${saved.id}/state`, "POST", {
      ...mutation(saved.revision),
      state,
    });
    const next = await refresh();
    const item = next.agents.find((a) => a.id === saved.id);
    if (item) select(item);
    setFeedback(
      state === "draft"
        ? "Agente restaurado para editar. Complete su configuración y pulse Guardar configuración para dejarlo disponible."
        : "Estado actualizado.",
    );
  }
  async function loadEvents(offset: number) {
    const data = await api<{ items: Event[]; has_more: boolean }>(
      `/history?offset=${offset}${saved ? "&entity_id=" + saved.id : ""}`,
    );
    setEvents(data.items);
    setEventMore(data.has_more);
    setEventOffset(offset);
  }
  async function loadSupervision(offset: number) {
    setSupervision(await api<Supervision>(`/supervision?offset=${offset}`));
    setJobOffset(offset);
  }
  async function simulate(call: boolean) {
    if (!saved) return;
    setSimulation(
      await api<Simulation>("/simulate", "POST", {
        agent_id: saved.id,
        config_version: saved.version,
        program_id: saved.program_id,
        stage_id: saved.stage_id,
        question,
        channel,
        call_provider: call,
        acknowledge_consumption: call,
        variant: simulationVariant,
        request_id: crypto.randomUUID(),
      }),
    );
    await loadConsole();
  }
  const filteredAgents =
    catalog?.agents.filter(
      (agent) =>
        (!search ||
          (
            agent.name +
            " " +
            (agent.configuration.description ?? "") +
            " " +
            (agent.program_id
              ? programName(agent.program_id)
              : labels[agent.level])
          )
            .toLocaleLowerCase()
            .includes(search.toLocaleLowerCase())) &&
        (!programFilter || String(agent.program_id) === programFilter) &&
        (!stateFilter || agent.state === stateFilter),
    ) ?? [];

  const approval = approvalFields();
  return (
    <section className="agents-workspace" aria-label="Agentes de admisiones">
      <div className="panel-heading">
        <div>
          <h2>Agentes IA de admisiones</h2>
          <p>
            Personalice la atención de cada programa, con contexto institucional
            y supervisión humana.
          </p>
        </div>
        <div className="form-actions">
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() =>
              void act(async () => {
                await refresh();
              })
            }
          >
            Actualizar
          </Button>
          <Button
            disabled={busy || !catalog?.installed}
            onClick={() => {
              const next = emptyAgent();
              next.configuration = {
                ...next.configuration,
                ...providers?.defaults,
                provider:
                  providers?.current_provider ?? next.configuration.provider,
                monthly_token_limit: 250000,
                allow_reply: true,
                capabilities: [
                  "program.read",
                  "sources.read",
                  "conversation.reply",
                  "human.handoff",
                ],
                instruction_template: "admissions",
                instructions: instructionTemplates.admissions,
              };
              setDraft(next);
              setConsoleData(null);
              setVariablesText("{}");
              setVariablesError("");
              setTab("Mis agentes");
              setReview(null);
              setSimulation(null);
              setNote("");
              setConfirmed(false);
              setCreateFocusRequest((request) => request + 1);
            }}
          >
            Crear agente personalizado
          </Button>
          <a className="button quiet" href="#/assistant">
            Abrir asistente
          </a>
          <Button
            variant="quiet"
            aria-expanded={guideOpen}
            onClick={() => setGuideOpen((open) => !open)}
          >
            Guía completa
          </Button>
        </div>
      </div>
      {guideOpen && <AgentGuide />}
      {error && (
        <OperationDialog
          guidance={{
            title: "No se pudo completar la operación del agente",
            detail: error,
            nextStep:
              "Conserva tu borrador y revisa Actividad para conocer el resultado y el consumo. Corrige la causa indicada antes de volver a intentarlo; no se repetirá la operación automáticamente.",
          }}
          dismiss={() => setError("")}
        />
      )}
      {feedback && <Notice>{feedback}</Notice>}
      {catalog?.institutional && (
        <ProgramSalesSetup
          catalog={catalog}
          disabled={
            busy || draftChanged || (!!draft && !saved && !!draft.name.trim())
          }
          onSaved={async () => {
            const value = await refresh();
            const current = value.agents.find(
              (agent) => agent.id === draft?.id,
            );
            if (current) select(current);
          }}
        />
      )}
      {!catalog && !error && <Notice>Cargando agentes…</Notice>}
      {catalog && !catalog.installed && (
        <Notice>
          La configuración de agentes está pendiente de habilitación. Los flujos
          actuales continúan disponibles.
        </Notice>
      )}
      {catalog?.installed && (
        <>
          <dl className="agents-summary">
            <div>
              <dt>Agentes</dt>
              <dd>{catalog.counts.total}</dd>
            </div>
            <div>
              <dt>Programas cubiertos</dt>
              <dd>{catalog.counts.programs}</dd>
            </div>
            <div>
              <dt>Activos</dt>
              <dd>{catalog.counts.active}</dd>
            </div>
            <div>
              <dt>Pausados</dt>
              <dd>{catalog.counts.paused ?? 0}</dd>
            </div>
            <div>
              <dt>Calidad académica</dt>
              <dd>No evaluada</dd>
            </div>
          </dl>
          <nav className="agents-tabs" aria-label="Secciones de agentes">
            {(
              [
                "Mis agentes",
                "Etapas",
                "Fuentes",
                "Diagnóstico",
                "Simulador",
                "Actividad",
                "Supervisión",
              ] as Tab[]
            ).map((item) => (
              <Button
                key={item}
                variant={tab === item ? "secondary" : "quiet"}
                aria-pressed={tab === item}
                disabled={busy}
                onClick={() => {
                  setTab(item);
                  if (item === "Actividad") void act(() => loadEvents(0));
                  if (item === "Supervisión")
                    void act(() => loadSupervision(0));
                }}
              >
                {item}
              </Button>
            ))}
          </nav>
          <div className="agents-layout">
            <aside
              className="agents-tree"
              aria-label="Mis agentes configurados"
            >
              <div className="agents-list-heading">
                <h3>Agentes configurados</h3>
                <small>
                  {filteredAgents.length} de {catalog.agents.length} agentes
                </small>
              </div>
              <Field
                id="agents-search"
                label="Buscar agentes"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <SelectField
                id="agents-filter-program"
                label="Programa"
                options={[
                  { value: "", label: "Todos los programas" },
                  ...programOptions,
                ]}
                value={programFilter}
                onChange={(e) => setProgramFilter(e.target.value)}
              />
              <SelectField
                id="agents-filter-state"
                label="Estado"
                options={[
                  { value: "", label: "Todos los estados" },
                  ...["draft", "active", "paused", "archived"].map((value) => ({
                    value,
                    label: labels[value],
                  })),
                ]}
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
              />
              <div className="agents-list">
                {filteredAgents.map((agent) => (
                  <Button
                    key={agent.id}
                    className="agents-agent-card"
                    variant={draft?.id === agent.id ? "secondary" : "quiet"}
                    aria-pressed={draft?.id === agent.id}
                    onClick={() => select(agent)}
                  >
                    <span className="agents-card-heading">
                      <span className="badge">{labels[agent.state]}</span>
                      <small>Versión {agent.version}</small>
                    </span>
                    <strong>{agent.name}</strong>
                    <small>{labels[agent.level]}</small>
                    {agent.program_id && (
                      <span>{programName(agent.program_id)}</span>
                    )}
                    <span className="agents-card-description">
                      {agent.configuration.description ||
                        "Sin descripción operativa"}
                    </span>
                    <span className="agents-card-channels">
                      {agent.configuration.channels.map((value) => (
                        <span className="badge" key={value}>
                          {labels[value]}
                        </span>
                      ))}
                    </span>
                    <small>
                      {agent.configuration.capabilities.length} herramientas
                      habilitadas
                    </small>
                  </Button>
                ))}
              </div>
              {catalog.agents.length > 0 && !filteredAgents.length && (
                <p>No hay agentes que coincidan con los filtros.</p>
              )}
              {!catalog.agents.length && (
                <p>
                  No hay agentes configurados. Cree un orientador para comenzar.
                </p>
              )}
              {catalog.legacy_agents.length > 0 && (
                <details>
                  <summary>Registros anteriores</summary>
                  {catalog.legacy_agents.map((item) => (
                    <div key={item.id}>
                      <Button
                        variant="quiet"
                        onClick={() => {
                          setDraft({
                            ...emptyAgent(),
                            id: item.id,
                            name: item.name,
                          });
                          setVariablesText("{}");
                          setVariablesError("");
                          setTab("Mis agentes");
                        }}
                      >
                        Configurar {item.name}
                      </Button>
                    </div>
                  ))}
                </details>
              )}
              <a href="#/memory">
                {catalog.knowledge_scope_editor
                  ? "Memoria colectiva y ADN"
                  : "Consultar memoria del aspirante"}
              </a>
              <a href="#/knowledge">Administrar conocimiento</a>
            </aside>
            <div className="agents-content">
              {tab === "Mis agentes" &&
                (draft ? (
                  <form
                    ref={draftFormRef}
                    className="panel"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void act(save);
                    }}
                  >
                    <div className="agents-editor-heading">
                      <div>
                        <h3>Constructor del agente</h3>
                        <p>{draft.name || "Nuevo agente personalizado"}</p>
                      </div>
                      <Badge>
                        {labels[draft.state]} · versión{" "}
                        {draft.version || "sin guardar"}
                      </Badge>
                    </div>
                    {archived && (
                      <Notice>
                        Este agente está archivado. Restaurarlo habilita la
                        edición; guardar una configuración válida lo deja
                        disponible, sin otra aprobación.
                        <Button
                          variant="quiet"
                          disabled={busy}
                          onClick={() => void act(() => change("draft"))}
                        >
                          Restaurar agente
                        </Button>
                      </Notice>
                    )}
                    <fieldset disabled={busy || archived}>
                      <section
                        className="agents-editor-section"
                        aria-labelledby="agent-identity-heading"
                      >
                        <h4 id="agent-identity-heading">
                          Identidad y personalidad
                        </h4>
                        <div className="agents-form-grid">
                          <Field
                            id="agent-name"
                            label="Nombre del agente"
                            value={draft.name}
                            onChange={(e) => patch({ name: e.target.value })}
                            required
                            maxLength={100}
                          />
                          <Field
                            id="agent-description"
                            label="Descripción operativa"
                            value={draft.configuration.description ?? ""}
                            onChange={(e) =>
                              configure({ description: e.target.value })
                            }
                          />
                          <SelectField
                            id="agent-level"
                            label="Responsabilidad"
                            disabled={draft.version > 0}
                            value={draft.level}
                            options={["guide", "program", "stage"].map(
                              (value) => ({ value, label: labels[value] }),
                            )}
                            onChange={(e) =>
                              patch({
                                level: e.target.value,
                                parent_id:
                                  e.target.value === "guide"
                                    ? null
                                    : (catalog.agents.find(
                                        (agent) =>
                                          agent.level ===
                                            (e.target.value === "program"
                                              ? "guide"
                                              : "program") &&
                                          agent.state !== "archived",
                                      )?.id ?? null),
                                program_id:
                                  e.target.value === "stage"
                                    ? (catalog.agents.find(
                                        (agent) =>
                                          agent.level === "program" &&
                                          agent.state !== "archived",
                                      )?.program_id ?? null)
                                    : null,
                                stage_id: null,
                              })
                            }
                          />
                          {draft.level === "guide" && (
                            <SelectField
                              id="agent-parent-root"
                              label="Agente supervisor (opcional)"
                              value=""
                              disabled
                              options={[
                                {
                                  value: "",
                                  label:
                                    "Sin supervisor · orientador institucional",
                                },
                              ]}
                            />
                          )}
                          {draft.level !== "guide" && (
                            <>
                              <SelectField
                                id="agent-parent"
                                label="Agente supervisor (obligatorio)"
                                required
                                value={draft.parent_id ?? ""}
                                disabled={draft.version > 0}
                                options={[
                                  { value: "", label: "Seleccione un padre" },
                                  ...catalog.agents
                                    .filter(
                                      (a) =>
                                        a.level ===
                                          (draft.level === "program"
                                            ? "guide"
                                            : "program") &&
                                        a.state !== "archived",
                                    )
                                    .map((a) => ({
                                      value: a.id,
                                      label: a.name,
                                    })),
                                ]}
                                onChange={(e) => {
                                  const parent = catalog.agents.find(
                                    (a) => a.id === e.target.value,
                                  );
                                  patch({
                                    parent_id: e.target.value || null,
                                    program_id:
                                      draft.level === "stage"
                                        ? (parent?.program_id ?? null)
                                        : draft.program_id,
                                    stage_id: null,
                                  });
                                }}
                              />
                              {!catalog.agents.some(
                                (agent) =>
                                  agent.level ===
                                    (draft.level === "program"
                                      ? "guide"
                                      : "program") &&
                                  agent.state !== "archived",
                              ) && (
                                <p className="agents-scope-help">
                                  {draft.level === "program"
                                    ? "Primero cree un orientador institucional o restaure uno archivado. El agente de programa necesita ese supervisor."
                                    : "Primero configure el agente del programa para poder crear su subagente de etapa."}
                                </p>
                              )}
                              <ProgramSelector
                                id="agent-program"
                                label="Programa vigente"
                                value={
                                  draft.program_id
                                    ? String(draft.program_id)
                                    : ""
                                }
                                programs={programs}
                                disabled={
                                  draft.version > 0 || draft.level === "stage"
                                }
                                onChange={(value) =>
                                  patch({
                                    program_id: Number(value) || null,
                                    stage_id: null,
                                  })
                                }
                              />
                            </>
                          )}
                          {draft.level === "stage" && (
                            <SelectField
                              id="agent-stage"
                              label="Etapa del programa"
                              value={draft.stage_id ?? ""}
                              disabled={draft.version > 0}
                              options={[
                                { value: "", label: "Seleccione una etapa" },
                                ...catalog.stages
                                  .filter(
                                    (s) => s.program_id === draft.program_id,
                                  )
                                  .map((s) => ({
                                    value: s.id,
                                    label:
                                      s.name +
                                      (s.approved
                                        ? ""
                                        : " · pendiente de aprobación"),
                                  })),
                              ]}
                              onChange={(e) =>
                                patch({ stage_id: e.target.value || null })
                              }
                            />
                          )}
                        </div>
                        <div className="agents-form-grid">
                          <Field
                            id="agent-tone"
                            label="Tono y personalidad"
                            value={draft.configuration.tone}
                            onChange={(e) =>
                              configure({ tone: e.target.value })
                            }
                          />
                          <SelectField
                            id="agent-risk"
                            label="Postura de riesgo"
                            value={
                              draft.configuration.risk_posture ?? "balanced"
                            }
                            options={[
                              {
                                value: "balanced",
                                label: "Automática · orientar con evidencia",
                              },
                              {
                                value: "cautious",
                                label:
                                  "Cautelosa · aclarar antes de recomendar",
                              },
                            ]}
                            onChange={(e) =>
                              configure({
                                risk_posture: e.target.value as
                                  "balanced" | "cautious",
                              })
                            }
                          />
                          <Field
                            id="agent-operating-style"
                            label="Estilo operativo"
                            value={draft.configuration.operating_style ?? ""}
                            onChange={(e) =>
                              configure({ operating_style: e.target.value })
                            }
                          />
                          <Field
                            id="agent-escalation"
                            label="Política de derivación humana"
                            value={draft.configuration.escalation_policy ?? ""}
                            onChange={(e) =>
                              configure({ escalation_policy: e.target.value })
                            }
                            hint="Criterios adicionales; se conservan la solicitud de asesor y los controles humanos existentes."
                          />
                        </div>
                      </section>
                      <section
                        className="agents-editor-section"
                        aria-labelledby="agent-behavior-heading"
                      >
                        <h4 id="agent-behavior-heading">
                          Objetivos y reglas de comportamiento
                        </h4>
                        <TextArea
                          id="agent-objectives"
                          label="Objetivos, uno por línea"
                          value={draft.configuration.objectives.join("\n")}
                          onChange={(e) =>
                            configure({ objectives: lineList(e.target.value) })
                          }
                          rows={3}
                        />
                        <TextArea
                          id="agent-rules"
                          label="Reglas, una por línea"
                          value={draft.configuration.rules.join("\n")}
                          onChange={(e) =>
                            configure({ rules: lineList(e.target.value) })
                          }
                          rows={3}
                        />
                      </section>
                      <section
                        className="agents-editor-section"
                        aria-labelledby="agent-instructions-heading"
                      >
                        <h4 id="agent-instructions-heading">
                          Instrucciones rellenables
                        </h4>
                        <label>
                          <input
                            type="checkbox"
                            checked={draft.configuration.customized ?? true}
                            onChange={(e) =>
                              configure({ customized: e.target.checked })
                            }
                          />
                          Agente personalizado · usar mis instrucciones
                        </label>
                        <p>
                          Personalice las instrucciones del agente y los valores
                          de su plantilla.
                        </p>
                        <div className="agents-template-actions">
                          <SelectField
                            id="agent-template"
                            label="Plantilla base"
                            value={
                              draft.configuration.instruction_template ??
                              "custom"
                            }
                            options={[
                              {
                                value: "custom",
                                label:
                                  "Personalizada · conservar instrucciones",
                              },
                              {
                                value: "admissions",
                                label: "Orientación institucional",
                              },
                              {
                                value: "program",
                                label: "Especialista de programa",
                              },
                            ]}
                            onChange={(e) =>
                              configure({
                                instruction_template: e.target.value as
                                  "custom" | "admissions" | "program",
                              })
                            }
                          />
                          <Button
                            variant="secondary"
                            disabled={
                              !draft.configuration.instruction_template ||
                              draft.configuration.instruction_template ===
                                "custom"
                            }
                            onClick={() => {
                              const template =
                                draft.configuration.instruction_template;
                              if (template && template !== "custom")
                                configure({
                                  instructions: instructionTemplates[template],
                                });
                            }}
                          >
                            Reemplazar instrucciones por plantilla
                          </Button>
                        </div>
                        <TextArea
                          id="agent-instructions"
                          label="Instrucciones operativas"
                          value={draft.configuration.instructions}
                          onChange={(e) =>
                            configure({ instructions: e.target.value })
                          }
                          rows={9}
                          disabled={draft.configuration.customized === false}
                        />
                        <p className="agents-variable-help">
                          Marcadores automáticos: <code>{"{agent_name}"}</code>,{" "}
                          <code>{"{agent_description}"}</code>,{" "}
                          <code>{"{agent_specialty}"}</code> y{" "}
                          <code>{"{program_id}"}</code>. Para otros marcadores,
                          agregue sus valores como texto en Variables JSON.
                        </p>
                        <TextArea
                          id="agent-variables"
                          label="Variables JSON"
                          value={variablesText}
                          rows={5}
                          spellCheck={false}
                          aria-invalid={!!variablesError}
                          aria-describedby={
                            variablesError ? "agent-variables-error" : undefined
                          }
                          onChange={(e) => updateVariables(e.target.value)}
                        />
                        {variablesError && (
                          <p
                            className="field-error"
                            role="alert"
                            id="agent-variables-error"
                          >
                            {variablesError}
                          </p>
                        )}
                      </section>
                      <section
                        className="agents-editor-section"
                        aria-labelledby="agent-channels-heading"
                      >
                        <h4 id="agent-channels-heading">Canales de atención</h4>
                        <label>
                          <input
                            type="checkbox"
                            checked={
                              draft.configuration.global_enabled ?? false
                            }
                            onChange={(e) =>
                              configure({ global_enabled: e.target.checked })
                            }
                          />
                          Global · análisis y documentos internos sin
                          conversación
                        </label>
                        <p>
                          Seleccione dónde puede atender este agente. Las
                          conexiones se administran en Ajustes → Canales.
                        </p>
                        <div className="agents-checks">
                          {[
                            "local",
                            "whatsapp",
                            "instagram",
                            "facebook",
                            "tiktok",
                          ].map((value) => (
                            <label key={value}>
                              <input
                                type="checkbox"
                                checked={draft.configuration.channels.includes(
                                  value,
                                )}
                                onChange={() => toggle("channels", value)}
                              />
                              {labels[value]}
                            </label>
                          ))}
                        </div>
                      </section>
                      <section
                        className="agents-editor-section"
                        aria-labelledby="agent-models-heading"
                      >
                        <h4 id="agent-models-heading">
                          Política de modelo y presupuesto
                        </h4>
                        <SelectField
                          id="agent-route"
                          label="Ruta operativa"
                          value={draft.configuration.route ?? "admissions"}
                          options={[
                            {
                              value: "admissions",
                              label: "Admisiones por programa",
                            },
                            {
                              value: "institutional",
                              label: "Orientación institucional",
                            },
                            { value: "followup", label: "Seguimiento" },
                            { value: "analytics", label: "Analítica agregada" },
                          ]}
                          onChange={(e) =>
                            configure({
                              route: e.target
                                .value as Agent["configuration"]["route"],
                            })
                          }
                        />
                        <p>
                          Las credenciales se administran en Ajustes → APIs. El
                          presupuesto del orientador cubre todos sus programas y
                          subagentes.
                        </p>
                        <SelectField
                          id="agent-provider"
                          label="Proveedor de IA"
                          value={draft.configuration.provider}
                          options={
                            providers?.providers.map((p) => ({
                              value: p.id,
                              label:
                                providerNames[p.id] +
                                (p.configured && p.endpoint_ready
                                  ? " · configurado"
                                  : " · sin configurar"),
                            })) ?? []
                          }
                          onChange={(e) =>
                            configure({
                              provider: e.target
                                .value as Agent["configuration"]["provider"],
                              primary_model: "",
                              fallback_model: "",
                            })
                          }
                        />
                        <p>
                          {selectedProvider?.catalog_loaded
                            ? "Modelos del catálogo ya consultado en esta sesión."
                            : "Se muestran selecciones guardadas. Para consultar otros modelos utilice Ajustes → APIs."}
                        </p>
                        <Button
                          variant="quiet"
                          disabled={busy}
                          onClick={() =>
                            void act(async () =>
                              setProviders(
                                await api<ProviderOptions>("/providers"),
                              ),
                            )
                          }
                        >
                          Actualizar opciones guardadas
                        </Button>
                        <div className="agents-form-grid">
                          <SelectField
                            id="agent-fallback-provider"
                            label="Proveedor de respaldo"
                            value={draft.configuration.fallback_provider ?? ""}
                            options={[
                              { value: "", label: "Mismo proveedor principal" },
                              ...(providers?.providers.map((provider) => ({
                                value: provider.id,
                                label: providerNames[provider.id],
                              })) ?? []),
                            ]}
                            onChange={(e) =>
                              configure({
                                fallback_provider:
                                  (e.target
                                    .value as Agent["configuration"]["fallback_provider"]) ||
                                  null,
                                fallback_model: "",
                              })
                            }
                          />
                          <SelectField
                            id="agent-model"
                            label="Modelo principal"
                            options={[
                              {
                                value: "",
                                label: "Seleccione un modelo del proveedor",
                              },
                              ...modelOptions,
                            ]}
                            value={draft.configuration.primary_model}
                            onChange={(e) =>
                              configure({ primary_model: e.target.value })
                            }
                          />
                          <SelectField
                            id="agent-fallback"
                            label="Modelo alternativo"
                            options={[
                              { value: "", label: "Sin modelo alternativo" },
                              ...fallbackOptions.filter(
                                (m) =>
                                  m.value !==
                                    draft.configuration.primary_model ||
                                  (draft.configuration.fallback_provider &&
                                    draft.configuration.fallback_provider !==
                                      draft.configuration.provider),
                              ),
                            ]}
                            value={draft.configuration.fallback_model}
                            onChange={(e) =>
                              configure({ fallback_model: e.target.value })
                            }
                          />
                          <Field
                            id="agent-output"
                            label="Máximo de tokens de salida"
                            type="number"
                            min={128}
                            max={2000}
                            value={draft.configuration.max_tokens}
                            onChange={(e) =>
                              configure({ max_tokens: Number(e.target.value) })
                            }
                          />
                          <Field
                            id="agent-budget"
                            label="Límite mensual de tokens"
                            type="number"
                            min={0}
                            max={100000000}
                            value={draft.configuration.monthly_token_limit}
                            onChange={(e) =>
                              configure({
                                monthly_token_limit: Number(e.target.value),
                              })
                            }
                          />
                        </div>
                        <p>
                          Las reservas incluyen reintentos; cero impide el
                          consumo. No representan facturación.
                        </p>
                      </section>
                      <AgentConfigurationExtras
                        draft={draft}
                        configure={configure}
                        versions={consoleData?.versions ?? []}
                      />
                      {catalog.institutional && (
                        <AgentVoiceSelect
                          value={draft.configuration.voice_profile_id ?? ""}
                          onChange={(value) =>
                            configure({ voice_profile_id: value })
                          }
                        />
                      )}
                      {catalog.institutional && (
                        <AgentSalesSkills
                          configuration={draft.configuration}
                          guide={draft.level === "guide"}
                          onChange={configure}
                        />
                      )}
                      <section
                        className="agents-editor-section"
                        aria-labelledby="agent-sources-heading"
                      >
                        <h4 id="agent-sources-heading">
                          Fuentes complementarias
                        </h4>
                        {catalog.sources.map((item) => (
                          <label className="agents-source-option" key={item.id}>
                            <input
                              type="checkbox"
                              checked={draft.configuration.document_ids.includes(
                                item.id,
                              )}
                              onChange={() => toggle("document_ids", item.id)}
                            />
                            {item.title} ·{" "}
                            {item.owner
                              ? "alcance revisado"
                              : "sin alcance aprobado"}
                          </label>
                        ))}
                        {!catalog.sources.length && (
                          <p>
                            No hay documentos. La oferta institucional se
                            consulta directamente del catálogo vigente.
                          </p>
                        )}
                      </section>
                      <div className="form-actions">
                        <Button type="submit" disabled={!!variablesError}>
                          Guardar configuración
                        </Button>
                        <Button
                          variant="quiet"
                          onClick={() =>
                            saved ? select(saved) : setDraft(null)
                          }
                        >
                          Descartar cambios
                        </Button>
                      </div>
                    </fieldset>
                    <div
                      className="agents-editor-links"
                      aria-label="Acciones de la configuración"
                    >
                      <a
                        className="button quiet"
                        href="#/settings"
                        onClick={() => setSettingsSection("APIs")}
                      >
                        Configurar APIs y modelos
                      </a>
                      {saved && (
                        <>
                          {archived ? (
                            <Button
                              disabled={busy}
                              onClick={() => void act(() => change("draft"))}
                            >
                              Restaurar agente
                            </Button>
                          ) : (
                            <>
                              <Button
                                variant="secondary"
                                disabled={busy || draftChanged}
                                onClick={() =>
                                  void act(() =>
                                    change(
                                      saved.state === "active"
                                        ? "paused"
                                        : "active",
                                    ),
                                  )
                                }
                              >
                                {saved.state === "active"
                                  ? "Pausar"
                                  : "Reanudar"}
                              </Button>
                              {catalog.knowledge_reindex_available !== false ? (
                                <Button
                                  variant="secondary"
                                  disabled={busy || draftChanged}
                                  onClick={() =>
                                    void act(async () => {
                                      const result = await api<{
                                        chunks: number;
                                        documents: number;
                                      }>(
                                        `/profiles/${saved.id}/reindex`,
                                        "POST",
                                        mutation(saved.revision),
                                      );
                                      setFeedback(
                                        `Conocimiento actualizado: ${result.documents} documentos, ${result.chunks} fragmentos.`,
                                      );
                                      await loadConsole();
                                    })
                                  }
                                >
                                  Reindexar conocimiento
                                </Button>
                              ) : (
                                <p>
                                  La administración del índice estará disponible
                                  en Conocimiento. Aquí puede revisar las
                                  fuentes publicadas y su alcance.
                                </p>
                              )}
                              <Button
                                variant="quiet"
                                disabled={busy || draftChanged}
                                onClick={() =>
                                  void act(() => change("archived"))
                                }
                              >
                                Archivar agente
                              </Button>
                            </>
                          )}
                          <Button
                            variant="quiet"
                            disabled={busy}
                            onClick={() => {
                              setTab("Actividad");
                              void act(() => loadEvents(0));
                            }}
                          >
                            Ver actividad
                          </Button>
                        </>
                      )}
                    </div>
                    {saved && (
                      <AgentOperatingConsole
                        key={saved.id}
                        agent={saved}
                        data={consoleData}
                        refresh={loadConsole}
                        busy={busy}
                        act={act}
                        changed={draftChanged}
                        question={question}
                        setQuestion={setQuestion}
                        simulate={simulate}
                        simulation={simulation}
                        diagnose={() => {
                          setTab("Diagnóstico");
                          void act(diagnose);
                        }}
                      />
                    )}
                  </form>
                ) : (
                  <Notice>
                    Seleccione un agente de la lista o cree el orientador
                    institucional.
                  </Notice>
                ))}
              {tab === "Etapas" && (
                <section className="panel">
                  <h3>Etapas configurables por programa</h3>
                  <p>
                    Los estados oficiales del SIIE se mantienen independientes.
                    Cada revisión requiere aprobación humana.
                  </p>
                  <SelectField
                    id="stage-edit"
                    label="Etapa a editar"
                    value={
                      catalog.stages.some((s) => s.id === stage.id)
                        ? stage.id
                        : ""
                    }
                    options={[
                      { value: "", label: "Crear una etapa" },
                      ...catalog.stages.map((s) => ({
                        value: s.id,
                        label: programName(s.program_id) + " · " + s.name,
                      })),
                    ]}
                    onChange={(e) => {
                      setStage(
                        structuredClone(
                          catalog.stages.find((s) => s.id === e.target.value) ??
                            emptyStage(),
                        ),
                      );
                      setConfirmed(false);
                    }}
                  />
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      void act(async () => {
                        await api(`/stages/${stage.id}`, "PUT", {
                          ...mutation(stage.revision),
                          program_id: stage.program_id,
                          name: stage.name,
                          entry_rule: stage.entry_rule,
                          exit_rule: stage.exit_rule,
                          evidence_required: stage.evidence_required,
                        });
                        const next = await refresh();
                        const current = next.stages.find(
                          (s) => s.id === stage.id,
                        );
                        if (current) setStage(current);
                        setFeedback(
                          "Etapa guardada. Revise sus condiciones antes de aprobarla.",
                        );
                      });
                    }}
                  >
                    <fieldset disabled={busy}>
                      <ProgramSelector
                        id="stage-program"
                        label="Programa"
                        value={stage.program_id ? String(stage.program_id) : ""}
                        programs={programs}
                        disabled={stage.revision > 0}
                        onChange={(value) =>
                          setStage({
                            ...stage,
                            program_id: Number(value),
                          })
                        }
                      />
                      <Field
                        id="stage-name"
                        label="Nombre de la etapa"
                        value={stage.name}
                        required
                        maxLength={100}
                        onChange={(e) =>
                          setStage({ ...stage, name: e.target.value })
                        }
                      />
                      <TextArea
                        id="stage-entry"
                        label="Condición de entrada"
                        value={stage.entry_rule}
                        required
                        rows={3}
                        maxLength={1000}
                        onChange={(e) =>
                          setStage({ ...stage, entry_rule: e.target.value })
                        }
                      />
                      <TextArea
                        id="stage-exit"
                        label="Condición de salida"
                        value={stage.exit_rule}
                        required
                        rows={3}
                        maxLength={1000}
                        onChange={(e) =>
                          setStage({ ...stage, exit_rule: e.target.value })
                        }
                      />
                      <TextArea
                        id="stage-evidence"
                        label="Evidencia que debe revisar la persona responsable"
                        value={stage.evidence_required}
                        required
                        rows={3}
                        maxLength={1000}
                        onChange={(e) =>
                          setStage({
                            ...stage,
                            evidence_required: e.target.value,
                          })
                        }
                      />
                      <Button type="submit">Guardar etapa pendiente</Button>
                    </fieldset>
                  </form>
                  {stage.revision > 0 && (
                    <>
                      <Badge>
                        {stage.approved
                          ? "Versión aprobada"
                          : "Revisión pendiente"}{" "}
                        · {stage.revision}
                      </Badge>
                      {approval}
                      <Button
                        disabled={busy || !confirmed || !note.trim()}
                        onClick={() =>
                          void act(async () => {
                            await api(`/stages/${stage.id}/approve`, "POST", {
                              ...mutation(stage.revision),
                              note,
                              confirmed,
                            });
                            const next = await refresh();
                            const current = next.stages.find(
                              (s) => s.id === stage.id,
                            );
                            if (current) setStage(current);
                            setConfirmed(false);
                            setFeedback(
                              "Etapa aprobada. El cambio de etapa de una conversación requiere su propia confirmación.",
                            );
                          })
                        }
                      >
                        Aprobar versión de la etapa
                      </Button>
                    </>
                  )}
                </section>
              )}
              {tab === "Fuentes" && (
                <section className="panel">
                  <h3>Alcance y vigencia de fuentes</h3>
                  <p>
                    {catalog.knowledge_scope_editor ? (
                      <>
                        Revisa contenido, ámbito y vigencia en{" "}
                        <a href="#/knowledge">Conocimiento</a>. Cada cambio
                        conserva una nueva versión.
                      </>
                    ) : (
                      <>
                        Publique documentos en{" "}
                        <a href="#/knowledge">Conocimiento</a> y apruebe aquí su
                        alcance antes de utilizarlos.
                      </>
                    )}
                  </p>
                  <SelectField
                    id="source-select"
                    label="Fuente"
                    value={source?.id ?? ""}
                    options={[
                      { value: "", label: "Seleccione un documento" },
                      ...catalog.sources.map((s) => ({
                        value: s.id,
                        label: s.title,
                      })),
                    ]}
                    onChange={(e) => {
                      const selected =
                        catalog.sources.find((s) => s.id === e.target.value) ??
                        null;
                      setSource(selected);
                      setSourceOwner(selected?.owner ?? "");
                      setUntil(selected?.valid_until ?? "");
                      setSourceProgram(
                        selected?.program_id ? String(selected.program_id) : "",
                      );
                      setSourceStage(selected?.stage_id ?? "");
                      setConfirmed(false);
                    }}
                  />
                  {source && (
                    <fieldset disabled={busy || catalog.knowledge_scope_editor}>
                      <ProgramSelector
                        id="source-program"
                        label="Ámbito"
                        programs={programs}
                        value={sourceProgram}
                        emptyLabel="Institucional público"
                        onChange={(value) => {
                          setSourceProgram(value);
                          setSourceStage("");
                        }}
                      />
                      <SelectField
                        id="source-stage"
                        label="Etapa"
                        value={sourceStage}
                        options={[
                          { value: "", label: "Todo el ámbito seleccionado" },
                          ...catalog.stages
                            .filter(
                              (s) =>
                                s.program_id === Number(sourceProgram) &&
                                s.approved,
                            )
                            .map((s) => ({ value: s.id, label: s.name })),
                        ]}
                        onChange={(e) => setSourceStage(e.target.value)}
                      />
                      <Field
                        id="source-owner"
                        label="Responsable de la fuente"
                        value={sourceOwner}
                        maxLength={100}
                        onChange={(e) => setSourceOwner(e.target.value)}
                      />
                      <Field
                        id="source-until"
                        label="Vigente hasta"
                        type="date"
                        value={until}
                        onChange={(e) => setUntil(e.target.value)}
                      />
                      {approval}
                      <Button
                        disabled={
                          !confirmed ||
                          !note.trim() ||
                          !until ||
                          !sourceOwner.trim()
                        }
                        onClick={() =>
                          void act(async () => {
                            await api(`/sources/${source.id}/scope`, "PUT", {
                              ...mutation(source.scope_revision ?? 0),
                              confirmed,
                              note,
                              owner: sourceOwner,
                              valid_until: until,
                              program_id: Number(sourceProgram) || null,
                              stage_id: sourceStage || null,
                            });
                            await refresh();
                            setSource(null);
                            setConfirmed(false);
                            setFeedback("Alcance de la fuente aprobado.");
                          })
                        }
                      >
                        Aprobar alcance y vigencia
                      </Button>
                    </fieldset>
                  )}
                  {!catalog.sources.length && (
                    <p>No hay documentos publicados para configurar.</p>
                  )}
                </section>
              )}
              {tab === "Diagnóstico" && (
                <section className="panel">
                  <h3>Diagnóstico opcional</h3>
                  <p>
                    Esta consulta no aprueba ni activa el perfil y no consume
                    IA. Guardar una configuración válida la deja disponible.
                  </p>
                  <Button
                    disabled={busy || !saved || draftChanged}
                    onClick={() => void act(diagnose)}
                  >
                    Ejecutar diagnóstico
                  </Button>
                  {review && (
                    <>
                      <Notice error={!review.ready}>
                        {review.ready
                          ? "Configuración válida para su ámbito."
                          : "Revise las condiciones indicadas."}
                      </Notice>
                      {review.checks.map((code) => (
                        <p key={code}>{message(code)}</p>
                      ))}
                      <details>
                        <summary>Configuración efectiva</summary>
                        <pre>{JSON.stringify(review.effective, null, 2)}</pre>
                      </details>
                    </>
                  )}
                </section>
              )}
              {tab === "Simulador" && (
                <section className="panel">
                  <h3>Simular configuración guardada</h3>
                  {saved ? (
                    <>
                      <p>
                        Agente: {saved.name} · versión {saved.version}.{" "}
                        {saved.program_id
                          ? programName(saved.program_id)
                          : "Orientación sin programa confirmado"}
                        {saved.stage_id
                          ? " · " +
                            catalog.stages.find((s) => s.id === saved.stage_id)
                              ?.name
                          : ""}
                        .
                      </p>
                      <p>
                        La simulación usa un contexto vacío y aislado, sin
                        mensajes ni expedientes reales.
                      </p>
                      <TextArea
                        id="simulation-question"
                        label="Mensaje de prueba"
                        value={question}
                        maxLength={2000}
                        rows={4}
                        onChange={(e) => setQuestion(e.target.value)}
                      />
                      <SelectField
                        id="simulation-channel"
                        label="Canal a simular"
                        value={channel}
                        options={[
                          "local",
                          "whatsapp",
                          "instagram",
                          "facebook",
                          "tiktok",
                        ].map((value) => ({ value, label: labels[value] }))}
                        onChange={(e) => setChannel(e.target.value)}
                      />
                      <Button
                        disabled={busy || !question.trim()}
                        onClick={() => void act(() => simulate(false))}
                      >
                        Ver contexto sin consumir IA
                      </Button>
                      <SelectField
                        id="simulation-variant"
                        label="Variante a probar"
                        value={simulationVariant}
                        options={[
                          { value: "current", label: "Versión actual" },
                          ...(saved.configuration.ab_enabled
                            ? [
                                {
                                  value: "comparison",
                                  label: "Versión comparativa configurada",
                                },
                              ]
                            : []),
                        ]}
                        onChange={(e) => setSimulationVariant(e.target.value)}
                      />
                      <p>
                        Pulsar Probar respuesta autoriza esta consulta y su
                        consumo. No se envía ningún mensaje al aspirante.
                      </p>
                      <Button
                        disabled={
                          busy || !question.trim() || draftChanged || archived
                        }
                        onClick={() => void act(() => simulate(true))}
                      >
                        Probar respuesta
                      </Button>
                      {simulation && (
                        <section aria-label="Resultado de simulación">
                          <Badge>
                            {simulation.network_called
                              ? "Proveedor consultado"
                              : "Vista previa sin consumo"}
                          </Badge>
                          {simulation.text && <p>{simulation.text}</p>}
                          {simulation.handoff !== undefined && (
                            <p>
                              {simulation.handoff
                                ? "Decisión: derivar a una persona"
                                : "Decisión: respuesta con fuentes"}
                            </p>
                          )}
                          {simulation.sources.map((s) => (
                            <p key={s.id}>{s.title}</p>
                          ))}
                          <details>
                            <summary>Versión, fuentes y uso</summary>
                            <pre>{JSON.stringify(simulation, null, 2)}</pre>
                          </details>
                        </section>
                      )}
                    </>
                  ) : (
                    <Notice>
                      Seleccione una versión guardada. Los cambios sin guardar
                      no se simulan.
                    </Notice>
                  )}
                </section>
              )}
              {tab === "Actividad" && (
                <section className="panel">
                  <h3>Historial de configuración y actividad</h3>
                  {events.map((event) => (
                    <article className="agents-event" key={event.id}>
                      <strong>{labels[event.kind] ?? "Actividad"}</strong>
                      <p>{event.note || "Configuración guardada"}</p>
                      <small>{event.created_at} · Operador local</small>
                    </article>
                  ))}
                  {!events.length && (
                    <p>No hay actividad registrada para la selección.</p>
                  )}
                  <div className="form-actions">
                    <Button
                      variant="secondary"
                      disabled={busy || !eventOffset}
                      onClick={() =>
                        void act(() =>
                          loadEvents(Math.max(0, eventOffset - 25)),
                        )
                      }
                    >
                      Anteriores
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={busy || !eventMore}
                      onClick={() =>
                        void act(() => loadEvents(eventOffset + 25))
                      }
                    >
                      Siguientes
                    </Button>
                  </div>
                </section>
              )}
              {tab === "Supervisión" && (
                <section className="panel">
                  <h3>Derivaciones y ejecución</h3>
                  {supervision && (
                    <>
                      <p>
                        {supervision.usage.requests} solicitudes este mes ·{" "}
                        {supervision.usage.tokens_reserved.toLocaleString(
                          "es-CO",
                        )}{" "}
                        tokens reservados ·{" "}
                        {supervision.usage.tokens_reported === null
                          ? "sin uso informado por proveedor"
                          : supervision.usage.tokens_reported.toLocaleString(
                              "es-CO",
                            ) + " tokens informados"}
                        .
                      </p>
                      <p>
                        La reserva no es una factura ni una medición de calidad.
                      </p>
                      {supervision.items.map((job) => (
                        <article className="agents-event" key={job.message_id}>
                          <strong>
                            {(
                              {
                                queued: "Pendiente",
                                processing: "En curso",
                                completed: "Completado",
                                cancelled: "Cancelado",
                                failed: "Fallido",
                                handoff: "Derivación humana",
                              } as Record<string, string>
                            )[job.state] ?? "Estado no disponible"}
                          </strong>
                          <p>
                            {job.reason
                              ? message(job.reason)
                              : "Sin incidencia registrada"}
                          </p>
                          {job.agent && (
                            <p>
                              {catalog.agents.find(
                                (a) => a.id === job.agent?.agent_id,
                              )?.name ?? "Agente registrado"}{" "}
                              · versión {job.agent.version}
                            </p>
                          )}
                          <small>{job.created_at}</small>
                        </article>
                      ))}
                      {!supervision.items.length && (
                        <p>No hay ejecuciones registradas.</p>
                      )}
                      <div className="form-actions">
                        <Button
                          variant="secondary"
                          disabled={busy || !jobOffset}
                          onClick={() =>
                            void act(() =>
                              loadSupervision(Math.max(0, jobOffset - 25)),
                            )
                          }
                        >
                          Anteriores
                        </Button>
                        <Button
                          variant="secondary"
                          disabled={busy || !supervision.has_more}
                          onClick={() =>
                            void act(() => loadSupervision(jobOffset + 25))
                          }
                        >
                          Siguientes
                        </Button>
                      </div>
                    </>
                  )}
                </section>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );

  function approvalFields() {
    return (
      <div className="agents-approval">
        <TextArea
          id={`agent-approval-${tab}`}
          label="Motivo y evidencia de la revisión"
          required
          aria-required="true"
          value={note}
          rows={3}
          maxLength={1000}
          onChange={(e) => {
            setNote(e.target.value);
            setConfirmed(false);
          }}
        />
        <p>
          Obligatorio para aprobar, activar o cambiar el estado. Al modificar el
          motivo se solicita confirmar de nuevo.
        </p>
        <label>
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          Confirmo que revisé la versión guardada y su evidencia.
        </label>
      </div>
    );
  }
  // JSX consumes the shared approval fields through the getter below.
}
