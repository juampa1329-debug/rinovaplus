import { InboxOperationPanel } from "../components/InboxOperationPanel";
import { InboxOperationSettings } from "../components/InboxOperationSettings";
import { InboxDirectory } from "../components/InboxDirectory";
import { InboxPanelResize } from "../components/InboxPanelResize";
import { slaLabels } from "../api/inboxOperations";
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { useInboxDrafts, useInboxView } from "../../../shared/inboxSession";
import { channelKeys, channelReferences } from "../../../shared/channels";
import type { Thread } from "../../../shared/demo";
import { InboxMediaComposer, InboxMediaView } from "../components/InboxMedia";
import {
  inboxApi,
  channelNames,
  deliveryLabels,
  type DeliveryIntent,
  type InboxPage,
} from "../api/inboxApi";
import { useInbox } from "../hooks/useInbox";
import type { CrmConfig } from "../../../shared/crm";
import { ThreadOperation } from "../../../features/ThreadWorkflow";
import {
  changeControl,
  recordOperation,
  workflowOf,
} from "../../../shared/workflow";
import { InboxContactEditor } from "../components/InboxContactEditor";
import { MiniCrm } from "../../../features/MiniCrm";
import { InboxAssessment } from "../components/InboxAssessment";
import { ContactMerge } from "../../contacts/components/ContactMerge";
import { useRuntime, usePermission } from "../../../shared/runtimeCapabilities";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../../../shared/ui";

export function Inbox({
  selectedId,
  threadOpenRequest,
  onSelect,
  onConfirmed,
  onClient,
  config,
  configReady = true,
  configurationError = "",
  onManageConfiguration,
}: {
  selectedId: string;
  threadOpenRequest: number;
  onSelect: (id: string) => void;
  onConfirmed: () => void;
  onClient: () => void;
  config: CrmConfig;
  configReady?: boolean;
  configurationError?: string;
  onManageConfiguration?: () => void;
}) {
  const { features, profile } = useRuntime().capabilities;
  const canWrite = usePermission("inbox.write");
  const gridRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const element = gridRef.current;
    if (!element) return;
    const update = () => {
      // Document coordinates keep panel height stable when focus scrolls the page.
      const top = element.getBoundingClientRect().top + window.scrollY;
      const height = `${Math.max(360, window.innerHeight - top - 24)}px`;
      if (element.style.getPropertyValue("--inbox-height") !== height)
        element.style.setProperty("--inbox-height", height);
    };
    update();
    const observer =
      typeof ResizeObserver !== "undefined" ? new ResizeObserver(update) : null;
    if (element.parentElement) observer?.observe(element.parentElement);
    const main = element.closest("main");
    if (main) observer?.observe(main);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("resize", update);
      observer?.disconnect();
    };
  }, []);
  const [query, setQuery] = useInboxView("query");
  const [storedMode, setStoredMode] = useInboxView("mode");
  const [openedThreadRequest, setOpenedThreadRequest] = useInboxView(
    "openedThreadRequest",
  );
  const mode =
    !features.comments && !features.inboxOperations
      ? "Mensajes"
      : openedThreadRequest === threadOpenRequest
        ? storedMode
        : "Mensajes";
  function setMode(value: string) {
    setOpenedThreadRequest(threadOpenRequest);
    setStoredMode(value);
  }
  const [channel, setChannel] = useInboxView("channel");
  const [filter, setFilter] = useInboxView("filter");
  const [drafts, setDrafts] = useInboxDrafts("messages");
  const [stateFilter, setStateFilter] = useInboxView("stateFilter");
  const [stage, setStage] = useInboxView("stage");
  const [showContext, setShowContext] = useInboxView("showContext");
  const [assignee, setAssignee] = useInboxView("assignee");
  const [humanId, setHumanId] = useInboxView("humanId");
  const [aiId, setAiId] = useInboxView("aiId");
  const [sla, setSla] = useInboxView("sla");
  const [assignment, setAssignment] = useInboxView("assignment");
  const [offset, setOffset] = useInboxView("offset");
  const store = useInbox(selectedId, onConfirmed);
  const busy = store.busy;
  const [list, setList] = useState<{ key: string; page: InboxPage } | null>(
    null,
  );
  const [listFailure, setListFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const [listRefresh, setListRefresh] = useState(0);
  const [, setOptions] = useState<{
    channels: string[];
    assignees: string[];
  }>({ channels: [], assignees: [] });
  const [optionsError, setOptionsError] = useState(false);
  useEffect(() => {
    if (mode !== "Mensajes") return;
    const timer = window.setInterval(() => setListRefresh((n) => n + 1), 60000);
    return () => clearInterval(timer);
  }, [mode]);
  function operationConfirmed() {
    setListRefresh((n) => n + 1);
    store.reload();
    onConfirmed();
  }
  const selection = useRef(selectedId);
  useLayoutEffect(() => {
    selection.current = selectedId;
  }, [selectedId]);
  const listKey = JSON.stringify([
    query,
    channel,
    filter,
    stateFilter,
    stage,
    assignee,
    humanId,
    aiId,
    sla,
    assignment,
    offset,
    listRefresh,
    store.refresh,
  ]);
  useEffect(() => {
    const controller = new AbortController();
    void inboxApi
      .options(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setOptions(result);
          setOptionsError(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setOptionsError(true);
      });
    return () => controller.abort();
  }, [listRefresh, store.refresh]);
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(
      () => {
        void inboxApi
          .list(
            {
              q: query.trim(),
              channel:
                channel === "CRM"
                  ? "Local"
                  : channel === "Todos" || !features.externalDelivery
                    ? ""
                    : channel,
              stage,
              state:
                (
                  {
                    Abierta: "open",
                    "En espera": "waiting",
                    Cerrada: "closed",
                  } as Record<string, string>
                )[stateFilter] ?? "",
              mode:
                filter === "Humano"
                  ? "human"
                  : filter === "IA" && features.automation
                    ? "ai"
                    : "",
              unread: filter === "Sin leer",
              assignment: features.inboxOperations
                ? filter === "Sin asignar"
                  ? "unassigned"
                  : assignment
                : "",
              assignee: features.inboxOperations ? assignee : "",
              humanId: features.inboxOperations ? humanId : undefined,
              aiId: features.inboxOperations ? aiId : undefined,
              sla: features.inboxOperations ? sla : undefined,
              offset,
            },
            controller.signal,
          )
          .then((page) => {
            if (!controller.signal.aborted) {
              setList({ key: listKey, page });
              setListFailure(null);
              if (!selection.current && page.items[0])
                onSelect(page.items[0].clientId);
            }
          })
          .catch(() => {
            if (!controller.signal.aborted)
              setListFailure({
                key: listKey,
                message: "No se pudo consultar la bandeja. Reintente.",
              });
          });
      },
      query.trim() ? 300 : 0,
    );
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    query,
    channel,
    filter,
    stateFilter,
    stage,
    assignee,
    humanId,
    aiId,
    sla,
    assignment,
    offset,
    listKey,
    onSelect,
    features.externalDelivery,
    features.automation,
    features.inboxOperations,
  ]);
  const listReady = list?.key === listKey;
  const listError = listFailure?.key === listKey ? listFailure.message : "";
  const visible = listReady ? list.page.items : [];
  const mobile = useSyncExternalStore(
    subscribeMobile,
    () => window.matchMedia?.("(max-width: 1100px)").matches ?? false,
  );
  const [feedback, setFeedback] = useState("");
  const [mobilePane, setMobilePane] = useState<"list" | "thread" | "context">(
    "thread",
  );
  const contextRef = useRef<HTMLHeadingElement>(null);
  const contextButton = useRef<HTMLButtonElement>(null);
  const threadRef = useRef<HTMLHeadingElement>(null);
  const listRef = useRef<HTMLHeadingElement>(null);
  const focusTarget = useRef<"context" | "thread" | "list" | "button" | null>(
    null,
  );
  useLayoutEffect(() => {
    const target = focusTarget.current;
    if (!target) return;
    focusTarget.current = null;
    const element =
      target === "context"
        ? contextRef.current
        : target === "thread"
          ? threadRef.current
          : target === "list"
            ? listRef.current
            : contextButton.current;
    element?.focus({ preventScroll: true });
    const box = element?.getBoundingClientRect();
    if (box && (box.top < 0 || box.bottom > window.innerHeight))
      element?.scrollIntoView?.({ block: "center", behavior: "instant" });
  });
  function closeContext() {
    setShowContext(false);
    setMobilePane("thread");
    focusTarget.current = "button";
  }

  const thread =
    store.detail && store.page
      ? { ...store.detail.thread, messages: store.page.items }
      : undefined;
  const client = store.detail?.client;
  const draftKey = thread?.id ?? selectedId;
  const draft = drafts[draftKey]?.body ?? "";
  const [pending, setPending] = useState(false);
  const [mediaBusy, setMediaBusy] = useState(false);
  const draftMedia = drafts[draftKey]?.media;
  const draftDestination = store.detail?.destinations.find(
    (item) => item.id === drafts[draftKey]?.identityId,
  );
  const externalMediaBlocked =
    !!draftMedia &&
    drafts[draftKey]?.delivery === "external" &&
    (!draftDestination?.mediaKinds.includes(draftMedia.kind ?? "") ||
      (draftDestination.channel === "tiktok" &&
        (draftMedia.size ?? 0) > 3_000_000) ||
      (draftDestination.channel === "instagram" &&
        draftMedia.kind === "document" &&
        draftMedia.mime !== "application/pdf"));
  const captionBlocked =
    !!draftMedia &&
    !!draft.trim() &&
    drafts[draftKey]?.delivery === "external" &&
    (draftMedia.kind === "audio" ||
      ["messenger", "instagram", "tiktok"].includes(
        draftDestination?.channel ?? "",
      ));
  async function updateThread(value: Thread, route?: DeliveryIntent) {
    if (pending || busy) return false;
    setPending(true);
    try {
      await store.change(value, route);
      setFeedback("Cambio confirmado.");
      return true;
    } catch (error) {
      setFeedback(
        error instanceof Error
          ? error.message
          : "No se pudo guardar; el borrador se conserva.",
      );
      return false;
    } finally {
      setPending(false);
    }
  }
  async function compose(event: React.FormEvent) {
    event.preventDefault();
    if (
      !thread ||
      pending ||
      busy ||
      mediaBusy ||
      (!draft.trim() && !draftMedia) ||
      (draftMedia && draftMedia.state !== "ready") ||
      externalMediaBlocked ||
      captionBlocked
    )
      return;
    const submitted = draft;
    const delivery = drafts[draftKey]?.delivery ?? "local";
    const identityId = drafts[draftKey]?.identityId;
    if (delivery === "external" && !identityId) {
      setFeedback("Seleccione el destino externo antes de encolar el mensaje.");
      return;
    }
    setPending(true);
    try {
      await store.send(submitted.trim(), {
        delivery,
        ...(delivery === "external" ? { identityId } : {}),
        ...(draftMedia ? { mediaId: draftMedia.id } : {}),
      });
      setDrafts((items) =>
        items[draftKey]?.body === submitted
          ? {
              ...items,
              [draftKey]: { ...items[draftKey], body: "", media: undefined },
            }
          : items,
      );
      setFeedback(
        delivery === "external"
          ? "Mensaje programado correctamente."
          : "Mensaje guardado correctamente.",
      );
    } catch (reason) {
      setFeedback((reason as Error).message);
    } finally {
      setPending(false);
    }
  }
  const operationControls = thread ? (
    <fieldset disabled={busy || pending || !canWrite}>
      <ThreadOperation
        key={`${thread.id}:${thread.workflow?.assignee}`}
        thread={thread}
        showAssignee={false}
        onChange={(value) => {
          void updateThread(value);
        }}
      />
    </fieldset>
  ) : null;
  return (
    <>
      <nav className="horizontal-tabs" aria-label="Subsecciones de Inbox">
        {["Mensajes", "Comentarios", "Configurar operación"]
          .filter(
            (item) =>
              item === "Mensajes" ||
              (item === "Comentarios"
                ? features.comments
                : features.inboxOperations),
          )
          .map((item) => (
            <button
              key={item}
              aria-current={mode === item ? "page" : undefined}
              onClick={() => setMode(item)}
            >
              {item}
            </button>
          ))}
      </nav>
      <div hidden={mode !== "Mensajes"} className="inbox-workspace">
        <div
          ref={gridRef}
          className={`inbox-grid paginated-inbox${showContext ? "" : " without-context"}`}
          data-mobile-pane={mobilePane}
        >
          <section
            className="panel inbox-list"
            aria-labelledby="inbox-list-title"
          >
            <div className="panel-heading">
              <h2 id="inbox-list-title" ref={listRef} tabIndex={-1}>
                Bandeja <span className="count">{visible.length}</span>
              </h2>
            </div>
            <div className="filter-stack">
              <Field
                id="inbox-search"
                label="Buscar conversaciones"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setOffset(0);
                }}
                placeholder="Nombre, teléfono o último mensaje"
                maxLength={200}
              />
              <SelectField
                id="inbox-filter"
                label="Vista rápida"
                options={
                  features.inboxOperations
                    ? ["Todos", "Sin leer", "Sin asignar", "Humano", "IA"]
                    : ["Todos", "Sin leer", "Humano"]
                }
                value={filter}
                onChange={(event) => {
                  setFilter(event.target.value);
                  setOffset(0);
                }}
              />
              <details className="inbox-secondary-filters">
                <summary>Más filtros</summary>
                <SelectField
                  id="inbox-stage"
                  label="Etapa de admisión"
                  value={stage}
                  options={[
                    { value: "", label: "Todas las etapas" },
                    ...config.stages.map((item) => ({
                      value: item.label,
                      label: item.label,
                    })),
                  ]}
                  onChange={(event) => {
                    setStage(event.target.value);
                    setOffset(0);
                  }}
                />
                <SelectField
                  id="inbox-channel"
                  label="Canal de mensajes"
                  options={[
                    "Todos",
                    "CRM",
                    ...(features.externalDelivery
                      ? channelKeys.map((key) => channelReferences[key].name)
                      : []),
                  ]}
                  value={channel}
                  onChange={(event) => {
                    setChannel(event.target.value);
                    setOffset(0);
                  }}
                />
                <SelectField
                  id="inbox-state-filter"
                  label="Estado operativo"
                  options={["Todos", "Abierta", "En espera", "Cerrada"]}
                  value={stateFilter}
                  onChange={(event) => {
                    setStateFilter(event.target.value);
                    setOffset(0);
                  }}
                />
                {features.inboxOperations && (
                  <>
                    <SelectField
                      id="inbox-assignment"
                      label="Asignación"
                      value={assignment}
                      options={[
                        { value: "", label: "Todas" },
                        { value: "assigned", label: "Con responsable" },
                        { value: "unassigned", label: "Sin responsable" },
                      ]}
                      onChange={(event) => {
                        setAssignment(event.target.value);
                        setOffset(0);
                        setFilter(filter === "Sin asignar" ? "Todos" : filter);
                      }}
                    />
                    <InboxDirectory
                      scope="members"
                      label="Filtrar responsable humano"
                      value={humanId}
                      eligible={false}
                      refresh={listRefresh}
                      onChange={(value) => {
                        setHumanId(value);
                        setAssignee("");
                        setOffset(0);
                      }}
                    />
                    <InboxDirectory
                      scope="agents"
                      label="Filtrar agente IA"
                      value={aiId}
                      eligible={false}
                      refresh={listRefresh}
                      onChange={(value) => {
                        setAiId(value);
                        setOffset(0);
                      }}
                    />
                    <SelectField
                      id="inbox-sla"
                      label="Filtrar SLA de respuesta"
                      value={sla}
                      options={[
                        { value: "", label: "Todos los SLA" },
                        ...Object.entries(slaLabels).map(([value, label]) => ({
                          value,
                          label,
                        })),
                      ]}
                      onChange={(event) => {
                        setSla(event.target.value);
                        setOffset(0);
                      }}
                    />
                    <p className="scope-text">
                      Responsables por identidad y agentes registrados. SLA
                      según la política configurada; se actualiza cada minuto.
                      Los filtros no envían mensajes.
                    </p>
                  </>
                )}
              </details>
              {optionsError && (
                <Notice error>
                  No se pudieron cargar las opciones.{" "}
                  <Button
                    variant="quiet"
                    onClick={() => setListRefresh((n) => n + 1)}
                  >
                    Reintentar opciones
                  </Button>
                </Notice>
              )}
              <Button
                variant="quiet"
                onClick={() => {
                  setStateFilter("Todos");
                  setQuery("");
                  setFilter("Todos");
                  setChannel("Todos");
                  setAssignee("");
                  setAssignment("");
                  setHumanId("");
                  setAiId("");
                  setSla("");
                  setOffset(0);
                }}
              >
                Restablecer filtros
              </Button>
            </div>
            <ul className="record-list">
              {visible.map((item) => {
                return (
                  <li key={item.clientId}>
                    <button
                      className={`record thread-record${selectedId === item.clientId ? " selected" : ""}`}
                      aria-pressed={selectedId === item.clientId}
                      onClick={() => {
                        onSelect(item.clientId);
                        setMobilePane("thread");
                        focusTarget.current = "thread";
                        setFeedback("");
                      }}
                    >
                      <span className="record-copy">
                        <strong>
                          {item.name || item.phone || "Contacto"}
                          {item.unread && (
                            <span
                              className="unread-dot"
                              aria-label="Sin leer"
                            />
                          )}
                        </strong>
                        <span>{item.preview || "Sin mensajes"}</span>
                        <small>
                          {dateLabel(item.lastMessageAt || item.updatedAt)}
                        </small>
                        <small>
                          {item.channel} ·{" "}
                          {item.mode === "human"
                            ? "Control humano"
                            : "Asistencia IA"}
                        </small>
                        <small>
                          {workflowOf(item).state} · {workflowOf(item).assignee}{" "}
                          · {workflowOf(item).priority}
                        </small>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            {!listReady && !listError && <Notice>Consultando bandeja…</Notice>}
            {listError && (
              <Notice error>
                {listError}{" "}
                <Button
                  variant="quiet"
                  onClick={() => setListRefresh((n) => n + 1)}
                >
                  Reintentar bandeja
                </Button>
              </Notice>
            )}
            {listReady && !listError && !visible.length && (
              <EmptyState title="Bandeja sin coincidencias">
                Cambie o restablezca los filtros. Las conversaciones existentes
                se conservan.
              </EmptyState>
            )}
            {listReady && !listError && (
              <nav
                className="inbox-pagination"
                aria-label="Páginas de conversaciones"
              >
                <Button
                  variant="quiet"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - 25))}
                >
                  Anterior
                </Button>
                <span>Página {Math.floor(offset / 25) + 1}</span>
                <Button
                  variant="quiet"
                  disabled={!list.page.hasMore}
                  onClick={() => setOffset(offset + 25)}
                >
                  Siguiente
                </Button>
              </nav>
            )}
            <p className="panel-footer">
              Conversaciones y seguimiento en un solo lugar.
            </p>
          </section>
          <section
            className="panel conversation"
            aria-labelledby="conversation-title"
          >
            {thread && client ? (
              <>
                <Button
                  variant="quiet"
                  className="mobile-pane-back"
                  onClick={() => {
                    setMobilePane("list");
                    focusTarget.current = "list";
                  }}
                >
                  Volver a la bandeja
                </Button>
                <div className="conversation-heading">
                  <div>
                    <h2 id="conversation-title" ref={threadRef} tabIndex={-1}>
                      {client.name || client.phone}
                    </h2>
                    {thread.channel.toLowerCase() !== "local" && (
                      <p>{thread.channel}</p>
                    )}
                  </div>
                  <Badge>
                    {thread.mode === "human"
                      ? "Control humano"
                      : "Asistencia IA"}
                  </Badge>
                </div>
                <div className="conversation-tools">
                  {features.automation && (
                    <Button
                      variant={thread.mode === "ai" ? "primary" : "secondary"}
                      disabled={busy || pending || !canWrite}
                      onClick={() => void updateThread(changeControl(thread))}
                    >
                      {thread.mode === "ai"
                        ? "Tomar control"
                        : "Reservar para IA"}
                    </Button>
                  )}
                  <Button
                    variant="quiet"
                    disabled={!thread.unread || busy || pending || !canWrite}
                    onClick={() =>
                      void updateThread(
                        recordOperation(
                          { ...thread, unread: false },
                          "Hilo marcado como leído",
                        ),
                      )
                    }
                  >
                    Marcar leído
                  </Button>
                  <button
                    type="button"
                    className="button quiet"
                    ref={contextButton}
                    aria-expanded={
                      showContext && (!mobile || mobilePane === "context")
                    }
                    aria-controls="inbox-context"
                    onClick={() => {
                      if (showContext && (!mobile || mobilePane === "context"))
                        closeContext();
                      else {
                        setShowContext(true);
                        setMobilePane("context");
                        focusTarget.current = "context";
                      }
                    }}
                  >
                    {showContext && !mobile
                      ? "Ocultar ficha CRM"
                      : "Mostrar ficha CRM"}
                  </button>
                </div>
                <div
                  className="message-log"
                  role="log"
                  aria-label="Historial unificado de mensajes"
                >
                  {store.loading && <Notice>Actualizando conversación…</Notice>}
                  {store.page?.hasMore && (
                    <Button
                      variant="secondary"
                      disabled={store.olderBusy || busy}
                      onClick={() => void store.older()}
                    >
                      {store.olderBusy
                        ? "Cargando anteriores…"
                        : "Cargar mensajes anteriores"}
                    </Button>
                  )}
                  {store.error && <Notice error>{store.error}</Notice>}
                  {thread.messages.map((message) => (
                    <div
                      key={message.id}
                      className={`message ${message.direction}`}
                    >
                      <p>{message.body}</p>
                      {message.attachment && (
                        <InboxMediaView
                          key={`message-media:${message.id}:${message.attachment.id}`}
                          conversation={thread.id}
                          asset={message.attachment}
                        />
                      )}
                      <small>
                        {channelNames[message.channel] ??
                          "Origen sin identificar"}{" "}
                        ·{" "}
                        {deliveryLabels[message.deliveryState] ??
                          "Estado no disponible"}
                        {message.deliveryState === "failed" &&
                          " · Revise el canal y sus permisos; no se reenvía automáticamente."}
                        {message.createdAt && (
                          <>
                            {" "}
                            ·{" "}
                            <time dateTime={message.createdAt}>
                              {dateLabel(message.createdAt)}
                            </time>
                          </>
                        )}
                      </small>
                    </div>
                  ))}
                </div>
                <div className="composer">
                  {feedback && <Notice>{feedback}</Notice>}
                  {workflowOf(thread).state === "Cerrada" && (
                    <Notice>
                      Conversación cerrada. Reábrala para guardar o encolar
                      mensajes.
                    </Notice>
                  )}
                  <p id="inbox-draft-help" className="draft-session-note">
                    Redacte y confirme su mensaje cuando esté listo.
                  </p>
                  <form onSubmit={compose}>
                    {features.media && (
                      <InboxMediaComposer
                        key={`composer-media:${thread.id}`}
                        conversation={thread.id}
                        asset={draftMedia}
                        disabled={
                          !canWrite ||
                          busy ||
                          pending ||
                          thread.mode !== "human" ||
                          workflowOf(thread).state === "Cerrada"
                        }
                        onBusy={setMediaBusy}
                        onChange={(asset) =>
                          setDrafts((items) => ({
                            ...items,
                            [draftKey]: {
                              ...items[draftKey],
                              body: items[draftKey]?.body ?? "",
                              media: asset,
                            },
                          }))
                        }
                      />
                    )}
                    {externalMediaBlocked && (
                      <Notice>
                        La subida de adjuntos no está habilitada para este
                        canal.
                      </Notice>
                    )}
                    {captionBlocked && (
                      <Notice>
                        Este canal requiere enviar el adjunto sin texto
                        adicional; puede escribirlo en otro mensaje. No se
                        descartará texto silenciosamente.
                      </Notice>
                    )}
                    {features.externalDelivery && (
                      <SelectField
                        id="inbox-delivery"
                        label="Destino del mensaje"
                        value={drafts[draftKey]?.delivery ?? "local"}
                        options={[
                          {
                            value: "local",
                            label: "Guardar mensaje",
                          },
                          {
                            value: "external",
                            label: "Encolar envío externo",
                          },
                        ]}
                        onChange={(event) =>
                          setDrafts((items) => ({
                            ...items,
                            [draftKey]: {
                              ...items[draftKey],
                              body: draft,
                              delivery: event.target.value as
                                "local" | "external",
                            },
                          }))
                        }
                      />
                    )}
                    {features.externalDelivery &&
                      drafts[draftKey]?.delivery === "external" && (
                        <>
                          <SelectField
                            id="inbox-destination"
                            label="Canal y destinatario vinculados"
                            value={drafts[draftKey]?.identityId ?? ""}
                            options={[
                              { value: "", label: "Seleccione un destino" },
                              ...(store.detail?.destinations ?? []).map(
                                (item) => ({
                                  value: item.id,
                                  label: `${channelNames[item.channel] ?? item.channel} · ${item.externalId} · ${["connected", "awaiting_webhook"].includes(item.state) ? "Activo" : "Canal no activo"}`,
                                }),
                              ),
                            ]}
                            onChange={(event) =>
                              setDrafts((items) => ({
                                ...items,
                                [draftKey]: {
                                  ...items[draftKey],
                                  body: draft,
                                  identityId: event.target.value,
                                },
                              }))
                            }
                          />
                          {!store.detail?.destinations.length && (
                            <Notice>
                              No hay identidades vinculadas a esta conversación.
                            </Notice>
                          )}
                          <Notice>
                            El mensaje se programa para el destino seleccionado
                            cuando el canal y su ventana lo permitan. Un
                            resultado incierto requiere revisión antes de
                            reenviar.
                          </Notice>
                        </>
                      )}
                    <TextArea
                      id="message-draft"
                      aria-describedby="inbox-draft-help"
                      label="Borrador del mensaje"
                      placeholder="Escriba el mensaje…"
                      maxLength={4000}
                      rows={2}
                      value={draft}
                      onChange={(event) =>
                        setDrafts((items) => ({
                          ...items,
                          [draftKey]: {
                            ...items[draftKey],
                            body: event.target.value,
                          },
                        }))
                      }
                    />
                    <div className="composer-footer">
                      <small
                        className={
                          thread.mode !== "ai" &&
                          drafts[draftKey]?.delivery !== "external"
                            ? "composer-local-help"
                            : undefined
                        }
                      >
                        {thread.mode === "ai"
                          ? "Tome control humano para guardar mensajes. La IA no responde."
                          : drafts[draftKey]?.delivery === "external"
                            ? "Se programará para el destino elegido."
                            : "El mensaje quedará guardado."}
                      </small>
                      <Button
                        type="submit"
                        disabled={
                          !canWrite ||
                          busy ||
                          pending ||
                          (!draft.trim() && !draftMedia) ||
                          mediaBusy ||
                          (!!draftMedia && draftMedia.state !== "ready") ||
                          externalMediaBlocked ||
                          captionBlocked ||
                          draft.trim().length > 4000 ||
                          thread.mode !== "human" ||
                          workflowOf(thread).state === "Cerrada" ||
                          (drafts[draftKey]?.delivery === "external" &&
                            !(store.detail?.destinations ?? []).some(
                              (item) =>
                                item.id === drafts[draftKey]?.identityId &&
                                ["connected", "awaiting_webhook"].includes(
                                  item.state,
                                ),
                            ))
                        }
                      >
                        {drafts[draftKey]?.delivery === "external"
                          ? "Guardar y encolar envío"
                          : "Guardar mensaje"}
                      </Button>
                    </div>
                  </form>
                </div>
              </>
            ) : (
              <EmptyState
                title={
                  store.loading
                    ? "Cargando conversación…"
                    : store.error
                      ? "Conversación no disponible"
                      : "Seleccione una conversación"
                }
              >
                {store.error && (
                  <>
                    <p>{store.error}</p>
                    <Button variant="secondary" onClick={store.reload}>
                      Reintentar conversación
                    </Button>
                  </>
                )}
                Seleccione una conversación de la bandeja para ver su detalle.
              </EmptyState>
            )}
          </section>
          {showContext && (
            <aside
              id="inbox-context"
              className="panel contact-context"
              aria-labelledby="context-title"
            >
              <div className="panel-heading">
                <h2 id="context-title" ref={contextRef} tabIndex={-1}>
                  {profile === "foundation" ? "Ficha CRM" : "Contexto CRM"}
                </h2>
                <Button variant="quiet" onClick={closeContext}>
                  Cerrar ficha
                </Button>
              </div>
              {client && thread ? (
                <>
                  {profile !== "foundation" && (
                    <div className="identity-block">
                      <span className="avatar large" aria-hidden="true">
                        {client.name.slice(-1) || "D"}
                      </span>
                      <h3>{client.name || client.phone}</h3>
                      <Badge>{client.stage}</Badge>
                    </div>
                  )}
                  {profile !== "foundation" && (
                    <dl className="detail-list">
                      <dt>Teléfono</dt>
                      <dd>{client.phone || "Sin teléfono"}</dd>
                      <dt>Canal de conversación</dt>
                      <dd>{thread.channel}</dd>
                      <dt>Programa</dt>
                      <dd>{client.program}</dd>
                      <dt>Jornada</dt>
                      <dd>{client.schedule}</dd>
                      <dt>Etiqueta</dt>
                      <dd>{client.tags || "Sin etiquetas"}</dd>
                      <dt>Tipo</dt>
                      <dd>{client.type || "Sin definir"}</dd>
                      <dt>Intereses</dt>
                      <dd>{client.interests || "Sin definir"}</dd>
                      {config.fields
                        .filter((field) => field.active)
                        .map((field) => (
                          <div className="detail-pair" key={field.key}>
                            <dt>{field.label}</dt>
                            <dd>
                              {field.type === "Boolean"
                                ? client.customValues[field.key] === "true"
                                  ? "Sí"
                                  : client.customValues[field.key] === "false"
                                    ? "No"
                                    : "Sin definir"
                                : client.customValues[field.key] ||
                                  "Sin definir"}
                            </dd>
                          </div>
                        ))}
                      <dt>Notas</dt>
                      <dd>{client.notes || "Sin notas locales"}</dd>
                    </dl>
                  )}
                  {configurationError && (
                    <Notice error>{configurationError}</Notice>
                  )}
                  {!configReady && <Notice>Cargando catálogo CRM…</Notice>}
                  <Button
                    variant="quiet"
                    onClick={onManageConfiguration ?? onClient}
                  >
                    {profile === "foundation"
                      ? "Configurar CRM"
                      : "Administrar etapas, etiquetas y campos"}
                  </Button>
                  <MiniCrm thread={thread} refresh={store.refresh} />
                  {features.assessment && store.detail && (
                    <InboxAssessment
                      key={`assessment:${thread.id}`}
                      detail={store.detail}
                      busy={busy || pending}
                      onSave={store.assess}
                    />
                  )}
                  {features.advancedCrm && (
                    <ContactMerge
                      contactId={client.id}
                      refresh={store.refresh}
                      onConfirmed={operationConfirmed}
                      onOpenContact={onSelect}
                    />
                  )}
                  {profile !== "foundation" && (
                    <div className="inbox-operation-details">
                      <h3>
                        {features.inboxOperations
                          ? "Estado, responsable y prioridad"
                          : "Estado y prioridad"}
                      </h3>
                      {operationControls}
                    </div>
                  )}

                  <details className="scope-note" open>
                    <summary>
                      {profile === "foundation"
                        ? "Ficha del contacto"
                        : "Ficha compartida y campos del contacto"}
                    </summary>
                    <InboxContactEditor
                      key={
                        store.detail?.contactGroup?.primaryContactId ??
                        client.id
                      }
                      saved={
                        store.detail?.contactGroup?.primaryContact ?? client
                      }
                      config={config}
                      busy={busy || !configReady}
                      onSave={store.saveContact}
                      onOpenContact={onSelect}
                    />
                  </details>
                  {profile === "foundation" && (
                    <details className="scope-note">
                      <summary>Estado y prioridad</summary>
                      {operationControls}
                    </details>
                  )}
                  {features.inboxOperations && (
                    <InboxOperationPanel
                      key={`operations:${thread.id}`}
                      id={thread.id}
                      refresh={listRefresh + store.refresh}
                      onConfirmed={operationConfirmed}
                    />
                  )}
                  <Button variant="secondary" onClick={onClient}>
                    Ver Clientes
                  </Button>
                  {profile !== "foundation" && (
                    <p className="scope-text">
                      Ficha CRM compartida con Clientes.
                    </p>
                  )}
                </>
              ) : (
                <p>Seleccione un contacto.</p>
              )}
            </aside>
          )}
          <InboxPanelResize container={gridRef} contextVisible={showContext} />
        </div>
      </div>
      {features.inboxOperations && mode === "Configurar operación" && (
        <InboxOperationSettings
          refresh={listRefresh}
          onConfirmed={operationConfirmed}
        />
      )}
      {features.comments && mode === "Comentarios" && (
        <section className="panel">
          <EmptyState title="Comentarios no conectados">
            Los comentarios sociales estarán disponibles cuando se implemente su
            integración.
          </EmptyState>
        </section>
      )}
    </>
  );
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? date.toLocaleString("es-CO", {
        timeZone: "America/Bogota",
        dateStyle: "short",
        timeStyle: "short",
      })
    : "Fecha no disponible";
}

function subscribeMobile(callback: () => void) {
  const media = window.matchMedia?.("(max-width: 1100px)");
  media?.addEventListener("change", callback);
  return () => media?.removeEventListener("change", callback);
}
