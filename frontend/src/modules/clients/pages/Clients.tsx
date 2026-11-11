import { fetchCatalog } from "../../catalog/api/catalog";
import type { Program } from "../../catalog/model";
import { useEffect, useRef, useState } from "react";
import { clientsApi } from "../api/clientsApi";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import { usePanelEntrance } from "../../../shared/usePanelEntrance";
import type { Client, Thread } from "../../../shared/demo";
import type { CrmConfig } from "../../../shared/crm";
import { allTags, validateCrmClient } from "../../../shared/crm";
import { CrmConfiguration } from "../../crm-configuration/pages/CrmConfiguration";
import { ClientFields } from "../components/ClientFields";
import { MiniCrm } from "../../../features/MiniCrm";
import { ContactMerge } from "../../contacts/components/ContactMerge";
import type { ContactLink } from "../../contacts/api/contactMergeApi";
import { emptyClient } from "../../../shared/demo";
import { useRuntime, usePermission } from "../../../shared/runtimeCapabilities";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Notice,
  SelectField,
} from "../../../shared/ui";

export function Clients({
  clients,
  onSave,
  onInbox,
  initialSelected,
  openRequest,
  config,
  threads,
  onConfigChange,
  onConfigReload,
  configurationRevision,
  configurationError,
  configurationOpenRequest,
  onConfigurationOpened,
  ready,
  busy,
  serverRevision,
  contactGroups = [],
  onReload,
}: {
  clients: Client[];
  onSave: (client: Client, create: boolean) => Promise<Client>;
  onInbox: (id: string) => void;
  initialSelected?: string;
  openRequest: number;
  config: CrmConfig;
  threads: Thread[];
  onConfigChange: (config: CrmConfig) => void | Promise<void>;
  onConfigReload?: () => void;
  configurationRevision?: string;
  configurationError?: string;
  configurationOpenRequest?: number;
  onConfigurationOpened?: () => void;
  ready: boolean;
  busy: boolean;
  serverRevision: string;
  contactGroups?: ContactLink[];
  onReload?: () => void;
}) {
  const { features } = useRuntime().capabilities;
  const canWrite = usePermission("crm.write");
  const entranceRef = usePanelEntrance("clients");
  const draftFormRef = useRef<HTMLFormElement>(null);
  const focusTargetRef = useRef("#client-name");
  const [focusRequest, setFocusRequest] = useState(0);
  useEffect(() => {
    if (focusRequest)
      draftFormRef.current
        ?.querySelector<HTMLElement>(focusTargetRef.current)
        ?.focus();
  }, [focusRequest]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [catalogError, setCatalogError] = useState("");
  useEffect(() => {
    if (!features.academic) return;
    const controller = new AbortController();
    async function load() {
      const values: Program[] = [];
      try {
        for (let offset = 0; offset <= 10000; offset += 25) {
          const page = await fetchCatalog(
            "programs",
            "",
            offset,
            controller.signal,
          );
          values.push(...(page.items as Program[]));
          if (!page.page.hasMore) break;
        }
        if (!controller.signal.aborted) setPrograms(values);
      } catch {
        if (!controller.signal.aborted)
          setCatalogError(
            "El catálogo de programas no está disponible. Puede guardar la ficha sin programa.",
          );
      }
    }
    if (ready && features.academic) void load();
    return () => controller.abort();
  }, [ready, features.academic]);
  const [query, setQuery] = useWorkspaceField("clients", "query");
  const [stage, setStage] = useWorkspaceField("clients", "stage");
  const [tag, setTag] = useWorkspaceField("clients", "tag");
  const [city, setCity] = useWorkspaceField("clients", "city");
  const [contactType, setContactType] = useWorkspaceField(
    "clients",
    "contactType",
  );
  const [program, setProgram] = useWorkspaceField("clients", "program");
  const [storedSelected, selectStored] = useWorkspaceField(
    "clients",
    "selected",
  );
  const [openedRequest, setOpenedRequest] = useWorkspaceField(
    "clients",
    "openedRequest",
  );
  const [drafts, setDrafts] = useWorkspaceField("clients", "drafts");
  const physicalSelected =
    openedRequest !== openRequest
      ? (initialSelected ?? clients[0]?.id ?? "__new")
      : storedSelected || initialSelected || clients[0]?.id || "__new";
  const selected =
    contactGroups.find((link) => link.sourceContactId === physicalSelected)
      ?.targetContactId ?? physicalSelected;
  const draft = drafts[selected] ?? null;
  function setSelected(id: string) {
    setOpenedRequest(openRequest);
    selectStored(id);
  }
  function setDraft(value: Client | null) {
    if (value) {
      setOpenedRequest(openRequest);
      selectStored(selected);
    }
    setDrafts((previous) => {
      const next = { ...previous };
      if (value) next[selected] = value;
      else delete next[selected];
      return next;
    });
  }
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState("");
  const client = draft ??
    clients.find((item) => item.id === selected) ?? {
      ...emptyClient(),
      stage: "",
    };
  const tags = allTags(config, clients);
  const normalize = (value: string) => value.trim().toLowerCase();
  const persistedOptions = (key: "city" | "type") =>
    [
      ...new Map(
        clients
          .filter((item) => normalize(item[key]))
          .map((item) => [normalize(item[key]), item[key].trim()]),
      ).entries(),
    ]
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label));
  const programOptions = [
    ...new Map<string, { value: string; label: string; name: string }>([
      ...clients
        .filter((item) => item.programId != null)
        .map(
          (item) =>
            [
              `id:${item.programId}`,
              {
                value: `id:${item.programId}`,
                label: item.program || `Programa #${item.programId}`,
                name: item.program,
              },
            ] as const,
        ),
      ...programs.map(
        (item) =>
          [
            `id:${item.id}`,
            {
              value: `id:${item.id}`,
              label: item.label || `Programa #${item.id}`,
              name: item.label ?? "",
            },
          ] as const,
      ),
      ...clients
        .filter((item) => item.programId == null && normalize(item.program))
        .map(
          (item) =>
            [
              `text:${normalize(item.program)}`,
              {
                value: `text:${normalize(item.program)}`,
                label: `${item.program.trim()} · texto guardado`,
                name: item.program.trim(),
              },
            ] as const,
        ),
    ]).values(),
  ].sort((a, b) => a.label.localeCompare(b.label));
  const programName =
    programOptions.find((item) => item.value === program)?.name ??
    (program.startsWith("text:") ? program.slice(5) : "");
  if (program && !programOptions.some((item) => item.value === program))
    programOptions.push({
      value: program,
      name: programName,
      label: programName || `Programa #${program.slice(3)}`,
    });
  const stages = [
    ...new Set([
      ...config.stages.map((item) => item.label),
      ...clients.map((item) => item.stage),
    ]),
  ];
  const [searchResult, setSearchResult] = useState<{
    key: string;
    ids: string[];
  }>({ key: "", ids: [] });
  const [searchFailure, setSearchFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const [searchAttempt, setSearchAttempt] = useState(0);
  const searchKey = JSON.stringify([
    query,
    stage,
    tag,
    city,
    contactType,
    program,
    programName,
    serverRevision,
    searchAttempt,
  ]);
  const searchError =
    searchFailure?.key === searchKey ? searchFailure.message : "";
  const searching = ready && searchResult.key !== searchKey && !searchError;
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, [features.academic]);
  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    let active = true;
    const timer = window.setTimeout(
      () => {
        void clientsApi
          .list(query, stage, tag, controller.signal, {
            city,
            contactType,
            program: programName,
            ...(program.startsWith("id:")
              ? { programId: Number(program.slice(3)) }
              : {}),
          })
          .then((result) => {
            if (active) {
              setSearchResult({
                key: searchKey,
                ids: result.clients.map((item) => item.id),
              });
              setSearchFailure(null);
            }
          })
          .catch((failure) => {
            if (active)
              setSearchFailure({
                key: searchKey,
                message:
                  failure instanceof Error
                    ? failure.message
                    : "No se pudo buscar.",
              });
          });
      },
      query.trim() ? 300 : 0,
    );
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    query,
    stage,
    tag,
    city,
    contactType,
    program,
    programName,
    searchKey,
    ready,
  ]);
  // A filtered response controls membership only; Inbox keeps the complete owner list.
  const visible =
    searchResult.key === searchKey
      ? clients.filter((item) => searchResult.ids.includes(item.id))
      : [];
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!ready || busy) return;
    const problems = validateCrmClient(
      client,
      config,
      clients.find((item) => item.id === client.id),
    );
    setFieldErrors(problems);
    setError(Object.values(problems)[0] ?? "");
    if (Object.keys(problems).length) {
      focusTargetRef.current = '[aria-invalid="true"]';
      setFocusRequest((request) => request + 1);
      return;
    }
    const submitted = {
      ...client,
      id: client.id || crypto.randomUUID(),
      name: client.name.trim(),
      phone: client.phone.trim(),
    };
    setDraft(submitted);
    try {
      const saved = await onSave(submitted, selected === "__new");
      setDrafts((previous) => {
        if (JSON.stringify(previous[selected]) !== JSON.stringify(submitted))
          return previous;
        const next = { ...previous };
        delete next[selected];
        return next;
      });
      if (mounted.current) {
        setSelected(saved.id);
        setFeedback("Ficha guardada correctamente.");
      }
    } catch (failure) {
      if (mounted.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "No se pudo guardar. El borrador se conserva.",
        );
    }
  }
  return (
    <div ref={entranceRef} className="clients-workspace">
      <div className="module-intro">
        <span className="section-eyebrow">RELACIÓN Y SEGUIMIENTO</span>
        <Badge>
          {clients.length} contactos · {Object.keys(drafts).length} borradores
          sin guardar
        </Badge>
      </div>
      <p className="draft-session-note">
        Confirme los cambios cuando la ficha esté lista.
      </p>
      <CrmConfiguration
        config={config}
        clients={clients}
        onChange={onConfigChange}
        onReload={onConfigReload}
        revision={configurationRevision}
        loadError={configurationError}
        ready={ready}
        openRequest={configurationOpenRequest}
        onOpened={onConfigurationOpened}
      />
      <div className="clients-grid">
        <section
          className="panel client-list"
          aria-labelledby="client-list-title"
        >
          <div className="panel-heading">
            <h2 id="client-list-title">
              Base de clientes <span className="count">{clients.length}</span>
            </h2>
            <Button
              disabled={!ready || busy || !canWrite}
              onClick={() => {
                setSelected("__new");
                setDrafts((items) => ({
                  ...items,
                  __new: items.__new ?? { ...emptyClient(), stage: "" },
                }));
                setError("");
                setFieldErrors({});
                setFeedback("");
                focusTargetRef.current = "#client-name";
                setFocusRequest((request) => request + 1);
              }}
            >
              Nuevo
            </Button>
          </div>
          <div className="filter-stack">
            <Field
              id="client-search"
              label="Buscar clientes"
              placeholder="Nombre o teléfono"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <SelectField
              id="client-stage-filter"
              label="Filtrar etapa"
              options={["Todas", ...stages]}
              value={stage}
              onChange={(event) => setStage(event.target.value)}
            />
            <SelectField
              id="client-tag-filter"
              label="Filtrar etiqueta"
              options={["Todas", ...tags]}
              value={tag}
              onChange={(event) => setTag(event.target.value)}
            />
            <SelectField
              id="client-city-filter"
              label="Filtrar ciudad"
              value={city}
              options={[
                { value: "", label: "Todas las ciudades" },
                ...persistedOptions("city"),
              ]}
              onChange={(event) => setCity(event.target.value)}
            />
            <SelectField
              id="client-type-filter"
              label="Filtrar tipo de contacto"
              value={contactType}
              options={[
                { value: "", label: "Todos los tipos" },
                ...persistedOptions("type"),
              ]}
              onChange={(event) => setContactType(event.target.value)}
            />
            {features.academic && (
              <SelectField
                id="client-program-filter"
                label="Filtrar programa de interés"
                value={program}
                options={[
                  { value: "", label: "Todos los programas" },
                  ...programOptions,
                ]}
                onChange={(event) => setProgram(event.target.value)}
              />
            )}
            <Button
              variant="quiet"
              onClick={() => {
                setQuery("");
                setStage("Todas");
                setTag("Todas");
                setCity("");
                setContactType("");
                setProgram("");
              }}
            >
              Restablecer filtros de clientes
            </Button>
          </div>
          <ul className="record-list">
            {visible.map((item) => (
              <li key={item.id}>
                <button
                  className={`record${selected === item.id ? " selected" : ""}`}
                  disabled={busy}
                  aria-pressed={selected === item.id}
                  onClick={() => {
                    setSelected(item.id);
                    setError("");
                    setFieldErrors({});
                    setFeedback("");
                  }}
                >
                  <span className="avatar" aria-hidden="true">
                    {item.name.slice(-1) || "D"}
                  </span>
                  <span className="record-copy">
                    <strong>{item.name || item.phone}</strong>
                    <span>{item.program}</span>
                    <small>{item.tags || "Sin etiquetas"}</small>
                    {drafts[item.id] && (
                      <small className="draft-marker">
                        Borrador sin guardar
                      </small>
                    )}
                  </span>
                  <Badge>{item.stage}</Badge>
                </button>
              </li>
            ))}
          </ul>
          {searching && <Notice>Buscando fichas locales…</Notice>}
          {searchError && (
            <Notice error>
              {searchError}{" "}
              <Button
                variant="secondary"
                onClick={() => {
                  setSearchFailure(null);
                  setSearchAttempt((value) => value + 1);
                }}
              >
                Reintentar búsqueda
              </Button>
            </Notice>
          )}
          {ready && !searching && !searchError && !visible.length && (
            <EmptyState title="Sin coincidencias">
              Cambie la búsqueda o seleccione otra etapa.
            </EmptyState>
          )}
          <p className="panel-footer">
            {visible.length} de {clients.length} fichas
          </p>
        </section>
        <section
          className="panel client-detail"
          aria-labelledby="client-detail-title"
        >
          <div className="panel-heading">
            <div>
              <h2 id="client-detail-title">
                {selected !== "__new" ? "Ficha CRM" : "Nueva ficha"}
              </h2>
              <p>Contacto CRM independiente de la identidad académica.</p>
            </div>
            <Badge>
              {draft
                ? "Cambios sin guardar"
                : ready
                  ? "Ficha guardada"
                  : "Pendiente de cargar"}
            </Badge>
          </div>
          <p className="draft-session-note">
            Los borradores de cada ficha se conservan al navegar en esta
            pestaña. Recargar los descarta; guardar requiere una acción
            explícita.
          </p>
          <form ref={draftFormRef} onSubmit={save} noValidate>
            {error && <Notice error>{error}</Notice>}
            {feedback && <Notice>{feedback}</Notice>}
            <fieldset
              className="client-editor-fields"
              disabled={!ready || busy || !canWrite}
            >
              <ClientFields
                client={client}
                setDraft={setDraft}
                config={config}
                programs={programs}
                catalogError={catalogError}
                tags={tags}
                stages={[
                  "",
                  ...new Set([
                    ...config.stages
                      .filter((item) => item.active !== false)
                      .map((item) => item.label),
                    ...(selected === "__new" ? [] : [client.stage]),
                  ]),
                ]}
                fieldErrors={fieldErrors}
                setFeedback={setFeedback}
                onOpenContact={onInbox}
              />
              <div className="actions">
                <Button type="submit">
                  {busy
                    ? "Guardando ficha…"
                    : selected !== "__new"
                      ? "Guardar ficha"
                      : "Crear ficha"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setDraft(null);
                    if (selected === "__new")
                      setSelected(initialSelected || clients[0]?.id || "__new");
                    setError("");
                    setFieldErrors({});
                    setFeedback("Borrador descartado.");
                  }}
                >
                  Cancelar
                </Button>
                {selected !== "__new" && client.id && (
                  <Button variant="quiet" onClick={() => onInbox(client.id)}>
                    Abrir en Inbox
                  </Button>
                )}
              </div>
            </fieldset>
          </form>
          <details className="scope-note">
            <summary>Qué falta para la funcionalidad completa</summary>
            <p>
              Permisos empresariales, baja auditada y registro académico aún no
              están disponibles. La comparación de posibles duplicados es solo
              lectura. Guardar un contacto no crea un aspirante ni un estudiante
              en el core.
            </p>
          </details>
          {features.advancedCrm && selected !== "__new" && client.id && (
            <ContactMerge
              key={client.id}
              contactId={client.id}
              refresh={serverRevision}
              onConfirmed={onReload}
              onOpenContact={onInbox}
            />
          )}
          <MiniCrm
            thread={threads.find((item) => item.clientId === client.id)}
            refresh={serverRevision}
          />
        </section>
      </div>
    </div>
  );
}
