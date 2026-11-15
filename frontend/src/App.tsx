import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { AssistantChat } from "./modules/ai";
import { ChannelsWorkspace } from "./features/ChannelsWorkspace";
import {
  KnowledgePanel,
  MemoryPanel,
} from "./modules/ai/components/AdmissionsPanel";
import { Admissions } from "./modules/admissions";
import { CampaignsPanel } from "./modules/campaigns/CampaignsPanel";
import { AgentsPanel } from "./modules/agents/AgentsPanel";
import { PeriodCatalog } from "./modules/catalog";
import { Clients } from "./modules/clients";
import { Inbox } from "./modules/inbox";
import { CreatorReference, PlannedModule } from "./features/PlannedModule";
import { Settings, settingsSections } from "./features/Settings";
import { useClients } from "./modules/clients";
import type { Client } from "./shared/demo";
import { useCrmConfiguration } from "./modules/crm-configuration";
import { modules, navigate, useRoute } from "./shared/navigation";
import { Badge, Button, EmptyState, Notice, PageHeading } from "./shared/ui";
import { Icon } from "./shared/Icon";
import { BrandMark } from "./shared/BrandMark";
import { useRuntime } from "./shared/runtimeCapabilities";
import { CrmConfiguration } from "./modules/crm-configuration/pages/CrmConfiguration";
import { useTheme } from "./shared/theme";
import {
  readBooleanPreference,
  writeBooleanPreference,
  sidebarCollapsedKey,
} from "./shared/viewPreferences";
import {
  WorkspaceSessionProvider,
  useWorkspaceState,
} from "./shared/workspaceSession";
import { InboxSessionProvider, useInboxView } from "./shared/inboxSession";
import "./shared/shell-navigation.css";
import { overviewData } from "./shared/overview";
import {
  OverviewCharts,
  OverviewMetrics,
  OverviewQueue,
} from "./features/Overview";

function InboxNavigation({
  threadOpenRequest,
  onNavigate,
}: {
  threadOpenRequest: number;
  onNavigate: () => void;
}) {
  const { capabilities } = useRuntime();
  const [storedMode, setMode] = useInboxView("mode");
  const [openedThreadRequest, setOpenedThreadRequest] = useInboxView(
    "openedThreadRequest",
  );
  const mode =
    openedThreadRequest === threadOpenRequest ? storedMode : "Mensajes";

  return (
    <div
      id="inbox-subnavigation"
      className="inbox-subnavigation"
      role="group"
      aria-label="Subsecciones de Inbox"
    >
      {[
        { label: "Mensajes", value: "Mensajes", icon: "inbox" },
        { label: "Comentarios", value: "Comentarios", icon: "application" },
        {
          label: "Configuración",
          value: "Configurar operación",
          icon: "settings",
        },
      ]
        .filter(
          (item) =>
            item.value === "Mensajes" ||
            (item.value === "Comentarios"
              ? capabilities.features.comments
              : capabilities.features.inboxOperations),
        )
        .map((item) => (
          <button
            key={item.value}
            type="button"
            aria-label={item.label}
            title={item.label}
            aria-current={mode === item.value ? "page" : undefined}
            onClick={() => {
              setOpenedThreadRequest(threadOpenRequest);
              setMode(item.value);
              onNavigate();
            }}
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </button>
        ))}
    </div>
  );
}

function SettingsNavigation({ onNavigate }: { onNavigate: () => void }) {
  const { capabilities } = useRuntime();
  const [section, setSection] = useWorkspaceState("settingsSection");
  if (capabilities.profile === "foundation")
    return (
      <div
        id="settings-subnavigation"
        className="settings-subnavigation"
        role="group"
        aria-label="Secciones de Ajustes e integraciones"
      >
        <button type="button" aria-current="page" onClick={onNavigate}>
          <Icon name="settings" />
          <span>CRM</span>
        </button>
      </div>
    );
  const icons: Record<(typeof settingsSections)[number], string> = {
    IA: "assistant",
    Canales: "inbox",
    "Base de datos": "settings",
    APIs: "settings",
    Diagnóstico: "overview",
    Usuarios: "clients",
    Perfil: "clients",
    Seguridad: "access",
  };

  return (
    <div
      id="settings-subnavigation"
      className="settings-subnavigation"
      role="group"
      aria-label="Secciones de Ajustes e integraciones"
    >
      {settingsSections.map((item) => (
        <button
          key={item}
          type="button"
          aria-current={section === item ? "page" : undefined}
          onClick={() => {
            setSection(item);
            onNavigate();
          }}
        >
          <Icon name={icons[item]} />
          <span>{item}</span>
        </button>
      ))}
    </div>
  );
}

function SidebarSubnavigation({
  open,
  children,
}: {
  open: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className="sidebar-subnavigation"
      data-open={open}
      aria-hidden={!open}
      inert={!open}
    >
      <div className="sidebar-subnavigation-content">{children}</div>
    </div>
  );
}

function ThemeControl({
  theme,
  chooseTheme,
}: Pick<ReturnType<typeof useTheme>, "theme" | "chooseTheme">) {
  const nextTheme = theme === "dark" ? "light" : "dark";
  const label = nextTheme === "light" ? "Modo claro" : "Modo oscuro";
  const action =
    nextTheme === "light" ? "Cambiar a modo claro" : "Cambiar a modo oscuro";
  return (
    <fieldset className="theme-control" aria-label="Apariencia">
      <legend className="visually-hidden">Apariencia</legend>
      <button
        type="button"
        aria-label={action}
        title={action}
        onClick={() => chooseTheme(nextTheme)}
        className="theme-option motion-safe:transition-colors duration-150 ease-feedback"
      >
        <Icon name={nextTheme === "light" ? "sun" : "moon"} />
        <span>{label}</span>
      </button>
    </fieldset>
  );
}

function CoreApp() {
  const runtime = useRuntime();
  const { capabilities } = runtime;
  const available = (path: string) =>
    runtime.status === "ready" &&
    (capabilities.modules === null ||
      (capabilities.modules as string[]).includes(path));
  const route = useRoute();
  const { theme, chooseTheme } = useTheme();
  const clientStore = useClients();
  const clients = clientStore.clients;
  const threads = clientStore.threads;
  const configuration = useCrmConfiguration();
  const crmConfig = configuration.config;
  const [configurationOpenRequest, setConfigurationOpenRequest] = useState(0);
  const [selectedThread, setSelectedThread] = useState("");
  const [threadOpenRequest, setThreadOpenRequest] = useState(0);
  const [clientOpenRequest, setClientOpenRequest] = useState(0);
  const [mobileNav, setMobileNav] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() =>
    readBooleanPreference(sidebarCollapsedKey, false),
  );
  const [inboxNavigationOpen, setInboxNavigationOpen] = useState(true);
  const [settingsNavigationOpen, setSettingsNavigationOpen] = useState(true);
  const [feedback, setFeedback] = useState("");
  const headingRef = useRef<HTMLDivElement>(null);
  const module = modules.find((item) => item.path === route);
  const title =
    module?.title ??
    (route === "creators"
      ? "CRM de creadores · Referencia"
      : "Ruta no disponible");

  useEffect(() => {
    document.title = `${title} · RinovaPlus`;
    headingRef.current?.focus();
  }, [title]);

  async function saveClient(client: Client, create: boolean) {
    const saved = await clientStore.save(client, create);
    return saved;
  }
  function link(path: string) {
    if (path === "inbox") setInboxNavigationOpen(true);
    if (path === "settings") setSettingsNavigationOpen(true);
    navigate(path);
    setMobileNav(false);
    setFeedback("");
  }
  const publicForm = route === "application";
  const pilot = [
    "overview",
    "inbox",
    "clients",
    "admissions",
    "assistant",
    "campaigns",
    "agents",
    "settings",
  ].includes(route);
  const dashboard = overviewData(clients, threads, crmConfig);

  return (
    <InboxSessionProvider>
      <WorkspaceSessionProvider>
        <div
          className={`app-shell bg-canvas text-ink ${publicForm ? "public-shell" : ""} ${pilot ? "pilot-shell" : ""}`}
          data-theme={theme}
          data-route={route}
          data-sidebar-collapsed={!publicForm && sidebarCollapsed}
        >
          <a
            href="#main"
            className="skip-link"
            onClick={(event) => {
              event.preventDefault();
              document.getElementById("main")?.focus();
            }}
          >
            Saltar al contenido
          </a>
          {!publicForm && (
            <aside className="sidebar" aria-label="Menú RinovaPlus">
              <button
                type="button"
                className="sidebar-logo-toggle desktop-logo-toggle"
                aria-expanded={!sidebarCollapsed}
                aria-controls="main-navigation"
                aria-label={
                  sidebarCollapsed
                    ? "Abrir menú RinovaPlus"
                    : "Cerrar menú RinovaPlus"
                }
                title={
                  sidebarCollapsed
                    ? "Abrir menú RinovaPlus"
                    : "Cerrar menú RinovaPlus"
                }
                onClick={() => {
                  const next = !sidebarCollapsed;
                  setSidebarCollapsed(next);
                  writeBooleanPreference(sidebarCollapsedKey, next);
                }}
              >
                <Icon name="menu" />
                <span className="sidebar-project-name brand-wordmark">
                  <BrandMark width={24} />
                  RinovaPlus
                </span>
              </button>
              <button
                type="button"
                className="sidebar-logo-toggle mobile-logo-toggle"
                aria-expanded={mobileNav}
                aria-controls="main-navigation"
                aria-label={
                  mobileNav ? "Cerrar menú RinovaPlus" : "Abrir menú RinovaPlus"
                }
                title={
                  mobileNav ? "Cerrar menú RinovaPlus" : "Abrir menú RinovaPlus"
                }
                onClick={() => setMobileNav(!mobileNav)}
              >
                <Icon name="menu" />
                <span className="sidebar-project-name brand-wordmark">
                  <BrandMark width={24} />
                  RinovaPlus
                </span>
              </button>
              <nav
                id="main-navigation"
                className={mobileNav ? "mobile-open" : ""}
                aria-label="Navegación principal"
              >
                <div className="nav-group primary-navigation">
                  {modules
                    .filter((item) =>
                      ["overview", "inbox", "admissions"].includes(item.path),
                    )
                    .map((item) => (
                      <Fragment key={item.path}>
                        <a
                          href={`#/${item.path}`}
                          aria-disabled={!available(item.path) || undefined}
                          tabIndex={available(item.path) ? undefined : -1}
                          className="nav-link"
                          aria-label={item.label}
                          title={item.label}
                          aria-expanded={
                            item.path === "inbox"
                              ? route === "inbox" && inboxNavigationOpen
                              : undefined
                          }
                          aria-controls={
                            item.path === "inbox" &&
                            route === "inbox" &&
                            inboxNavigationOpen
                              ? "inbox-subnavigation"
                              : undefined
                          }
                          aria-current={
                            route === item.path ? "page" : undefined
                          }
                          onClick={(event) => {
                            if (!available(item.path)) {
                              event.preventDefault();
                              return;
                            }
                            if (item.path === "inbox") {
                              if (route === "inbox") {
                                event.preventDefault();
                                setInboxNavigationOpen((value) => !value);
                              } else {
                                setInboxNavigationOpen(true);
                              }
                            } else {
                              setMobileNav(false);
                            }
                            setFeedback("");
                          }}
                        >
                          <Icon name={item.path} />
                          <span className="nav-label">{item.label}</span>
                        </a>
                        {item.path === "inbox" && route === "inbox" && (
                          <SidebarSubnavigation open={inboxNavigationOpen}>
                            <InboxNavigation
                              threadOpenRequest={threadOpenRequest}
                              onNavigate={() => {
                                setMobileNav(false);
                                setFeedback("");
                              }}
                            />
                          </SidebarSubnavigation>
                        )}
                      </Fragment>
                    ))}
                </div>
                <section className="other-modules" aria-label="Otros módulos">
                  <h2 className="other-modules-title">Otros módulos</h2>
                  {["Operación", "Gestión"].map((group) => (
                    <div className="nav-group" key={group}>
                      <h2>{group}</h2>
                      {modules
                        .filter(
                          (item) =>
                            item.group === group &&
                            !["overview", "inbox", "admissions"].includes(
                              item.path,
                            ),
                        )
                        .map((item) => (
                          <Fragment key={item.path}>
                            <a
                              href={`#/${item.path}`}
                              aria-disabled={!available(item.path) || undefined}
                              tabIndex={available(item.path) ? undefined : -1}
                              className="nav-link"
                              aria-label={item.label}
                              title={item.label}
                              aria-current={
                                route === item.path ? "page" : undefined
                              }
                              aria-expanded={
                                item.path === "settings"
                                  ? route === "settings" &&
                                    settingsNavigationOpen
                                  : undefined
                              }
                              aria-controls={
                                item.path === "settings"
                                  ? "settings-subnavigation"
                                  : undefined
                              }
                              onClick={(event) => {
                                if (!available(item.path)) {
                                  event.preventDefault();
                                  return;
                                }
                                if (item.path === "settings") {
                                  if (route === "settings") {
                                    event.preventDefault();
                                    setSettingsNavigationOpen(
                                      (value) => !value,
                                    );
                                  } else {
                                    setSettingsNavigationOpen(true);
                                  }
                                }
                                setMobileNav(false);
                                setFeedback("");
                              }}
                            >
                              <Icon name={item.path} />
                              <span className="nav-label">{item.label}</span>
                            </a>
                            {item.path === "settings" &&
                              route === "settings" && (
                                <SidebarSubnavigation
                                  open={settingsNavigationOpen}
                                >
                                  <SettingsNavigation
                                    onNavigate={() => {
                                      setMobileNav(false);
                                      setFeedback("");
                                    }}
                                  />
                                </SidebarSubnavigation>
                              )}
                          </Fragment>
                        ))}
                    </div>
                  ))}
                </section>
              </nav>
              <div
                className={`sidebar-footer sidebar-preferences${mobileNav ? " mobile-open" : ""}`}
              >
                <div className="sidebar-user" title="Espacio de trabajo">
                  <span className="avatar" aria-hidden="true">
                    C
                  </span>
                  <div>
                    <strong>Espacio de trabajo</strong>
                  </div>
                </div>
                <ThemeControl theme={theme} chooseTheme={chooseTheme} />
              </div>
            </aside>
          )}
          <div className="workspace">
            {publicForm && (
              <header className="topbar public-toolbar">
                <a className="public-brand brand-wordmark" href="#/overview">
                  <BrandMark width={28} />
                  RinovaPlus
                </a>
                <div className="topbar-actions">
                  <ThemeControl theme={theme} chooseTheme={chooseTheme} />
                </div>
              </header>
            )}
            <main
              id="main"
              tabIndex={-1}
              className={publicForm ? "public-main" : ""}
            >
              {feedback && <Notice>{feedback}</Notice>}
              {route !== "inbox" &&
                route !== "settings" &&
                clientStore.status === "loading" && (
                  <Notice>Cargando información…</Notice>
                )}
              {route !== "inbox" &&
                route !== "settings" &&
                clientStore.status === "error" && (
                  <Notice error>
                    {clientStore.error}{" "}
                    <Button
                      variant="secondary"
                      onClick={() => void clientStore.reload()}
                    >
                      Reintentar carga de clientes
                    </Button>
                  </Notice>
                )}
              <div ref={headingRef} tabIndex={-1} className="heading-focus">
                <PageHeading
                  title={title}
                  description={
                    module?.description ??
                    (route === "creators"
                      ? "Estructura separada del CRM de Clientes; expansión no implementada."
                      : "Este enlace no está disponible.")
                  }
                >
                  <Badge>
                    {capabilities.profile === "foundation"
                      ? "Copia de ensayo"
                      : (module?.phase ??
                        (route === "creators"
                          ? "Fase 7F · Condicionada"
                          : "Sin ruta"))}
                  </Badge>
                </PageHeading>
              </div>
              {available(route) &&
                route === "overview" &&
                clientStore.status === "ready" && (
                  <OverviewMetrics data={dashboard} />
                )}
              <OverviewCharts
                active={
                  available(route) &&
                  route === "overview" &&
                  clientStore.status === "ready"
                }
                data={dashboard}
              />
              <div key={route}>
                {runtime.status !== "ready" ? (
                  <section className="panel">
                    <Notice error={runtime.status === "error"}>
                      {runtime.status === "error"
                        ? "No se pudo comprobar la disponibilidad de las funciones."
                        : "Comprobando funciones disponibles…"}
                    </Notice>
                    {runtime.status === "error" && (
                      <Button variant="secondary" onClick={runtime.reload}>
                        Reintentar disponibilidad
                      </Button>
                    )}
                  </section>
                ) : !available(route) ? (
                  <section className="panel">
                    <EmptyState title="Función pendiente en esta copia">
                      Puede trabajar con contactos, conversaciones y
                      configuración CRM. Esta función requiere una integración
                      posterior.
                    </EmptyState>
                    <Button variant="secondary" onClick={() => link("clients")}>
                      Ir a contactos
                    </Button>
                  </section>
                ) : (
                  <>
                    {route === "admissions" && <Admissions />}
                    {route === "overview" && clientStore.status === "ready" && (
                      <OverviewQueue
                        clients={clients}
                        threads={threads}
                        onOpen={(id) => {
                          setSelectedThread(id);
                          setThreadOpenRequest((value) => value + 1);
                          link("inbox");
                        }}
                        onNavigate={link}
                      />
                    )}
                    {route === "clients" && (
                      <Clients
                        clients={clients}
                        contactGroups={clientStore.contactGroups}
                        onReload={() => {
                          void clientStore.reload();
                        }}
                        threads={threads}
                        config={crmConfig}
                        onConfigChange={configuration.save}
                        onConfigReload={configuration.reload}
                        configurationRevision={configuration.revision}
                        configurationError={configuration.error}
                        configurationOpenRequest={configurationOpenRequest}
                        onConfigurationOpened={() =>
                          setConfigurationOpenRequest(0)
                        }
                        initialSelected={selectedThread}
                        openRequest={clientOpenRequest}
                        onSave={saveClient}
                        ready={
                          clientStore.status === "ready" && configuration.ready
                        }
                        busy={clientStore.busy}
                        serverRevision={clientStore.revision}
                        onInbox={(id) => {
                          setSelectedThread(id);
                          setThreadOpenRequest((value) => value + 1);
                          link("inbox");
                        }}
                      />
                    )}
                    {route === "inbox" && (
                      <Inbox
                        config={crmConfig}
                        configReady={configuration.ready}
                        configurationError={configuration.error}
                        onManageConfiguration={() => {
                          if (capabilities.profile === "foundation") {
                            link("settings");
                            return;
                          }
                          setConfigurationOpenRequest((value) => value + 1);
                          setClientOpenRequest((value) => value + 1);
                          link("clients");
                        }}
                        selectedId={selectedThread}
                        threadOpenRequest={threadOpenRequest}
                        onSelect={setSelectedThread}
                        onConfirmed={() => {
                          void clientStore.reload();
                        }}
                        onClient={() => {
                          setClientOpenRequest((value) => value + 1);
                          link("clients");
                        }}
                      />
                    )}
                    {["application", "review"].includes(route) && (
                      <section className="panel">
                        <EmptyState title="Integración académica pendiente">
                          No hay solicitudes conectadas. El registro académico y
                          sus confirmaciones estarán disponibles cuando se
                          implemente su contrato.
                        </EmptyState>
                      </section>
                    )}
                    {capabilities.features.automation && (
                      <AssistantChat active={route === "assistant"} />
                    )}
                    {route === "settings" &&
                      (capabilities.profile === "foundation" ? (
                        <section className="panel">
                          <CrmConfiguration
                            config={crmConfig}
                            clients={clients}
                            onChange={configuration.save}
                            onReload={configuration.reload}
                            revision={configuration.revision}
                            loadError={configuration.error}
                            ready={configuration.ready}
                            openRequest={1}
                          />
                        </section>
                      ) : (
                        <Settings />
                      ))}
                    {route === "campaigns" && <CampaignsPanel />}
                    {route === "agents" && <AgentsPanel />}
                    {["review", "access", "retention", "corporate"].includes(
                      route,
                    ) && <PlannedModule path={route} />}
                    {route === "knowledge" && (
                      <>
                        <KnowledgePanel />
                        <PeriodCatalog />
                      </>
                    )}
                    {route === "memory" && <MemoryPanel />}
                    {route === "creators" && <CreatorReference />}
                    {!module && route !== "creators" && (
                      <section className="panel">
                        <EmptyState title="Elija una sección del diseño">
                          La navegación contiene las rutas disponibles. No hay
                          API o recurso remoto detrás de este enlace.
                        </EmptyState>
                        <Button onClick={() => link("overview")}>
                          Volver al resumen
                        </Button>
                      </section>
                    )}
                  </>
                )}
              </div>
              <footer className="workspace-footer">RinovaPlus</footer>
            </main>
          </div>
        </div>
      </WorkspaceSessionProvider>
    </InboxSessionProvider>
  );
}

export function App() {
  const { capabilities } = useRuntime();
  return capabilities.profile === "channels" ? (
    <ChannelsWorkspace />
  ) : (
    <CoreApp />
  );
}
