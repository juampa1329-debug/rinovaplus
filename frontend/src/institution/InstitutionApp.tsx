import { useEffect, useRef, useState } from "react";
import type { ComponentType, ReactNode } from "react";
import { Button, Field, Notice, PageHeading, SelectField } from "../shared/ui";
import { useTheme } from "../shared/theme";
import { RuntimeContext, featureNames } from "../shared/runtimeCapabilities";
import type { UiCapabilities } from "../shared/runtimeCapabilities";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import { InboxSessionProvider } from "../shared/inboxSession";
import { bindInstitutionSession } from "../shared/institutionSession";
import { useClients } from "../modules/clients/hooks/useClients";
import { Clients } from "../modules/clients/pages/Clients";
import { useCrmConfiguration } from "../modules/crm-configuration/hooks/useCrmConfiguration";
import { CrmConfiguration } from "../modules/crm-configuration/pages/CrmConfiguration";
import { Inbox } from "../modules/inbox/pages/Inbox";
import { send, SessionBoundary, useInstitution, useTask } from "./api";
import type { Contract, Session } from "./api";
import {
  ProviderKeys,
  ResourceState,
  SettingPage,
  useResource,
} from "./Settings";
import { Audit, Profile, Roles, Security, Users } from "./Access";
import { Channels, Webhooks } from "./Channels";
import { Comments } from "./Comments";
import { ChannelRuntime } from "./ChannelOperations";
import { allowNavigation } from "./drafts";
import { AgentsWorkspace } from "./AgentsWorkspace";
import { KnowledgeWorkspace } from "./KnowledgeWorkspace";
import { CampaignWorkspace } from "./CampaignWorkspace";
import { AdsWorkspace } from "./AdsWorkspace";
import { LearningWorkspace } from "./LearningWorkspace";
import { OperationsWorkspace } from "./OperationsWorkspace";
import { BroadcastWorkspace } from "./BroadcastWorkspace";
import "./knowledge.css";
import { AssistantChat as AgentAssistantChat } from "../modules/ai/pages/AgentAssistantChat";
import { BrandMark } from "../shared/BrandMark";

const sections = [
  ["overview", "Resumen"],
  ["admissions", "Admisiones"],
  ["inbox", "Inbox"],
  ["clients", "CRM"],
  ["channels", "Canales"],
  ["comments", "Comentarios"],
  ["assistant", "Asistente"],
  ["agents", "Agentes"],
  ["knowledge", "Conocimiento"],
  ["memory", "Memoria colectiva"],
  ["broadcasts", "Mensajería masiva"],
  ["campaigns", "Campañas"],
  ["ads", "Publicidad"],
  ["intelligence", "Inteligencia"],
  ["settings", "Ajustes"],
];
const settingsTabs = [
  ["institution", "Institución", "settings.institution.read"],
  ["profile", "Mi perfil", "self"],
  ["ai", "Inteligencia artificial", "settings.ai.read"],
  ["models", "APIs y modelos", "settings.providers.read"],
  ["channels", "Canales", "settings.channels.read"],
  ["webhooks", "Webhooks", "settings.webhooks.read"],
  ["modules", "Módulos", "settings.modules.read"],
  ["budgets", "Límites técnicos", "settings.budgets.read"],
  ["users", "Usuarios", "users.read"],
  ["roles", "Roles y permisos", "roles.read"],
  ["security", "Seguridad y sesiones", "self"],
  ["audit", "Auditoría", "audit.read"],
  ["crm", "Configuración CRM", "settings.crm.read"],
  ["operations", "Operación", "users.manage"],
];
function route() {
  const [page, tab] = window.location.hash.replace(/^#\/?/, "").split("/");
  return {
    page: sections.some((row) => row[0] === page) ? page : "overview",
    tab: tab || "profile",
  };
}
const navigate = (page: string, tab?: string) => {
  window.location.hash = `/${page}${tab ? `/${tab}` : ""}`;
};
const capabilities: UiCapabilities = {
  version: "cbn-ui-capabilities-v1",
  profile: "foundation",
  mode: "local_foundation",
  scope: "restored_rehearsal_only",
  modules: ["overview", "clients", "inbox", "settings"],
  features: Object.fromEntries(
    featureNames.map((name) => [name, false]),
  ) as UiCapabilities["features"],
};

export function InstitutionApp({
  core: CoreView = Core,
}: { core?: ComponentType<{ page: string }> } = {}) {
  const [session, setSession] = useState<Session | null>(null),
    [initialized, setInitialized] = useState<boolean | null>(null),
    [error, setError] = useState("");
  const expire = () => {
    bindInstitutionSession("");
    setSession(null);
  };
  useEffect(() => {
    let active = true;
    void send<{ initialized: boolean }>("auth/status")
      .then(async (status) => {
        if (!active) return;
        setInitialized(status.initialized);
        if (status.initialized) {
          try {
            const current = await send<Session>("auth/me");
            if (active) setSession(current);
          } catch {
            /* Login is required when no cookie remains. */
          }
        }
      })
      .catch((failure: unknown) => {
        if (active)
          setError(
            failure instanceof Error
              ? failure.message
              : "No se pudo consultar el acceso.",
          );
      });
    return () => {
      active = false;
      bindInstitutionSession("");
    };
  }, []);
  if (initialized === null)
    return (
      <AccessLayout>
        <h1 id="access-title">Acceso a RinovaPlus</h1>
        <ResourceState error={error} />
      </AccessLayout>
    );
  if (!session)
    return (
      <AccessScreen
        initialized={initialized}
        accepted={(value) => {
          setInitialized(true);
          setSession(value);
        }}
      />
    );
  return (
    <SessionBoundary key={session.session_id} initial={session} expire={expire}>
      <WorkspaceSessionProvider>
        <InboxSessionProvider>
          <Shell core={CoreView} />
        </InboxSessionProvider>
      </WorkspaceSessionProvider>
    </SessionBoundary>
  );
}
function ProductBrand() {
  return (
    <>
      <BrandMark />
      <span>
        <strong>RinovaPlus</strong>
        <small>CRM inteligente de CBN</small>
      </span>
    </>
  );
}

function AccessLayout({ children }: { children: ReactNode }) {
  const theme = useTheme();
  return (
    <main className="institution-login">
      <div className="access-brand-panel">
        <div className="institution-brand">
          <ProductBrand />
        </div>
        <div className="access-art" aria-hidden="true">
          <BrandMark width={224} />
        </div>
        <p className="access-tagline">La fuerza de conectar.</p>
      </div>
      <div className="access-content">
        <div className="access-appearance">
          <SelectField
            id="access-theme"
            label="Apariencia"
            value={theme.preference}
            options={[
              { value: "system", label: "Sistema" },
              { value: "dark", label: "Oscura" },
              { value: "light", label: "Clara" },
            ]}
            onChange={(event) =>
              theme.chooseTheme(
                event.target.value as "dark" | "light" | "system",
              )
            }
          />
        </div>
        <section className="access-form" aria-labelledby="access-title">
          {children}
        </section>
        <footer className="access-copyright">
          © 2026. Software desarrollado por la Corporación Bolivariana del Norte
          - CBN.
        </footer>
      </div>
    </main>
  );
}

function AccessScreen({
  initialized,
  accepted,
}: {
  initialized: boolean;
  accepted: (session: Session) => void;
}) {
  const task = useTask();
  const [mode, setMode] = useState(initialized ? "login" : "bootstrap"),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState(""),
    [token, setToken] = useState(""),
    [challenge, setChallenge] = useState(""),
    [code, setCode] = useState("");
  return (
    <AccessLayout>
      <h1 id="access-title">
        {challenge
          ? "Verifica tu identidad"
          : mode === "bootstrap"
            ? "Configura tu acceso"
            : mode === "redeem"
              ? "Activa o recupera tu cuenta"
              : "Inicia sesión"}
      </h1>
      <p>
        {mode === "bootstrap"
          ? "Crea la primera cuenta de administración con el código privado de configuración."
          : "Accede con tu cuenta institucional para continuar."}
      </p>
      {task.notices}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void task.run(
            async () => {
              if (mode === "redeem") {
                await send("auth/redeem", "POST", {
                  token,
                  new_password: password,
                  ...(code ? { code } : {}),
                });
                setToken("");
                setPassword("");
                setCode("");
                setMode("login");
                return;
              }
              const result = challenge
                ? await send<Session>("auth/verify", "POST", {
                    challenge_token: challenge,
                    code,
                  })
                : await send<
                    Session & {
                      mfa_required?: boolean;
                      challenge_token?: string;
                    }
                  >(
                    mode === "bootstrap" ? "auth/bootstrap" : "auth/login",
                    "POST",
                    {
                      email,
                      password,
                      ...(mode === "bootstrap"
                        ? { full_name: name, bootstrap_token: token }
                        : {}),
                    },
                  );
              if (
                "mfa_required" in result &&
                result.mfa_required &&
                "challenge_token" in result
              ) {
                setChallenge(String(result.challenge_token));
                setPassword("");
                setCode("");
              } else {
                setPassword("");
                setToken("");
                setCode("");
                accepted(result);
              }
            },
            mode === "redeem"
              ? "Contraseña guardada. Ya puedes iniciar sesión."
              : "Acceso verificado.",
          );
        }}
      >
        <fieldset disabled={task.busy}>
          {challenge ? (
            <Field
              id="login-code"
              label="Código del autenticador o de recuperación"
              autoComplete="one-time-code"
              required
              autoFocus
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
          ) : (
            <>
              {mode !== "redeem" && (
                <Field
                  id="login-email"
                  label="Correo"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              )}
              {mode === "bootstrap" && (
                <Field
                  id="login-name"
                  label="Nombre completo"
                  autoComplete="name"
                  maxLength={180}
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              )}
              {mode !== "login" && (
                <Field
                  id="login-token"
                  label={
                    mode === "bootstrap"
                      ? "Código privado de configuración"
                      : "Código de activación o recuperación"
                  }
                  type="password"
                  autoComplete="off"
                  required
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                />
              )}
              <Field
                id="login-password"
                label={mode === "redeem" ? "Nueva contraseña" : "Contraseña"}
                type="password"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                minLength={mode === "login" ? 1 : 15}
                maxLength={128}
                required
                value={password}
                hint={mode !== "login" ? "De 15 a 128 caracteres." : undefined}
                onChange={(event) => setPassword(event.target.value)}
              />
              {mode === "redeem" && (
                <Field
                  id="redeem-code"
                  label="Código del autenticador, si está activo"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                />
              )}
            </>
          )}
          <Button type="submit">
            {task.busy
              ? "Comprobando…"
              : challenge
                ? "Verificar código"
                : mode === "bootstrap"
                  ? "Crear cuenta de administración"
                  : mode === "redeem"
                    ? "Guardar contraseña"
                    : "Iniciar sesión"}
          </Button>
        </fieldset>
      </form>
      {initialized && (
        <Button
          variant="quiet"
          onClick={() => {
            setChallenge("");
            setToken("");
            setPassword("");
            setMode(mode === "redeem" ? "login" : "redeem");
          }}
        >
          {mode === "redeem"
            ? "Volver al acceso"
            : "Tengo un código de activación o recuperación"}
        </Button>
      )}
    </AccessLayout>
  );
}
function Shell({ core: CoreView }: { core: ComponentType<{ page: string }> }) {
  const { session, call, expire } = useInstitution(),
    runtime = useResource<{
      channel_operations?: boolean;
      agent_operations?: boolean;
      knowledge_operations?: boolean;
      broadcast_operations?: boolean;
      campaign_operations?: boolean;
      ads_operations?: boolean;
      learning_operations?: boolean;
      institutional_operations?: boolean;
      modules: {
        id: string;
        enabled: boolean;
        implemented: boolean;
        operational: boolean;
      }[];
    }>("runtime"),
    contract = useResource<Contract>("contracts"),
    task = useTask(),
    theme = useTheme();
  const [location, setLocation] = useState(route),
    [menu, setMenu] = useState(false);
  const routeBeforeChange = useRef(location);
  useEffect(() => {
    const change = () => {
      if (!allowNavigation()) {
        const previous = routeBeforeChange.current;
        window.history.replaceState(
          null,
          "",
          `#/${previous.page}${previous.tab ? `/${previous.tab}` : ""}`,
        );
        return;
      }
      routeBeforeChange.current = route();
      setLocation(route());
      setMenu(false);
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  const allowed = (action: string) =>
      action === "self" || session.actions.includes(action),
    currentTab = settingsTabs.find((row) => row[0] === location.tab),
    enabled = runtime.value?.modules.find(
      (row) =>
        row.id === (location.page === "comments" ? "inbox" : location.page),
    )?.enabled;
  const core =
    ["clients", "inbox"].includes(location.page) ||
    (location.page === "settings" && location.tab === "crm");
  return (
    <RuntimeContext.Provider
      value={{
        status: "ready",
        capabilities,
        reload: () => void runtime.reload(),
        actions: session.actions,
      }}
    >
      <div className="app-shell pilot-shell institution-shell">
        <aside className={`sidebar ${menu ? "is-open" : ""}`}>
          <a className="institution-brand" href="#/overview">
            <ProductBrand />
          </a>
          <nav aria-label="Navegación principal">
            {sections
              .filter(
                ([id]) =>
                  id !== "comments" || runtime.value?.channel_operations,
              )
              .map(([id, label]) => (
                <a
                  key={id}
                  href={`#/${id}`}
                  aria-current={location.page === id ? "page" : undefined}
                >
                  {label}
                </a>
              ))}
          </nav>
          <div className="institution-account">
            <strong>{session.user.full_name}</strong>
            <small>
              {(
                {
                  owner: "Propietario",
                  admin: "Administrador",
                  supervisor: "Supervisor",
                  agent: "Asesor",
                  viewer: "Consulta",
                } as Record<string, string>
              )[session.user.role] ?? session.user.role}
            </small>
            <Button
              variant="secondary"
              onClick={() => navigate("settings", "profile")}
            >
              Mi perfil
            </Button>
            <Button
              variant="quiet"
              disabled={task.busy}
              onClick={() =>
                void task.run(async () => {
                  await call("auth/logout", "POST");
                  expire();
                })
              }
            >
              Cerrar sesión
            </Button>
          </div>
        </aside>
        <main className="institution-main">
          <header className="institution-topbar">
            <Button
              variant="secondary"
              className="institution-menu"
              aria-expanded={menu}
              onClick={() => setMenu(!menu)}
            >
              Menú
            </Button>
            <span className="institution-name">
              Corporación Bolivariana del Norte
            </span>
            <span className="institution-mobile-brand">RinovaPlus</span>
            <SelectField
              id="workspace-theme"
              label="Apariencia"
              value={theme.preference}
              options={[
                { value: "system", label: "Sistema" },
                { value: "dark", label: "Oscura" },
                { value: "light", label: "Clara" },
              ]}
              onChange={(event) =>
                theme.chooseTheme(
                  event.target.value as "dark" | "light" | "system",
                )
              }
            />
          </header>
          <div className="institution-content">
            <PageHeading
              title={
                sections.find((row) => row[0] === location.page)?.[1] ??
                "RinovaPlus"
              }
              description={
                location.page === "settings"
                  ? "Configuración institucional y personalización de tu espacio de trabajo."
                  : location.page === "channels"
                    ? "Cuentas, credenciales y conexiones de mensajería."
                    : "Tu espacio de trabajo institucional."
              }
            />
            {task.notices}
            {runtime.value &&
              contract.value &&
              (runtime.error || contract.error) && (
                <Notice error>
                  {runtime.error || contract.error} Se conserva la última
                  configuración consultada. Actualiza la página antes de
                  continuar.
                </Notice>
              )}
            {!runtime.value || !contract.value ? (
              <ResourceState error={runtime.error || contract.error} />
            ) : (
              <>
                {location.page === "settings" && (
                  <nav
                    className="institution-tabs"
                    aria-label="Apartados de ajustes"
                  >
                    {settingsTabs
                      .filter(
                        (row) =>
                          allowed(row[2]) &&
                          (row[0] !== "operations" ||
                            runtime.value?.institutional_operations),
                      )
                      .map(([id, label]) => (
                        <a
                          key={id}
                          href={`#/settings/${id}`}
                          aria-current={
                            location.tab === id ? "page" : undefined
                          }
                        >
                          {label}
                        </a>
                      ))}
                  </nav>
                )}
                {enabled === false ? (
                  <Notice>
                    Este módulo está deshabilitado por la institución. Un
                    administrador puede habilitarlo en Ajustes → Módulos.
                  </Notice>
                ) : location.page === "overview" ? (
                  <section className="panel">
                    <h2>Bienvenido, {session.user.full_name}</h2>
                    <p>
                      Consulta las conversaciones, organiza contactos y
                      administra la configuración de la institución desde el
                      menú.
                    </p>
                    <div className="institution-overview">
                      {runtime.value.modules
                        .filter((m) => m.operational)
                        .map((m) => (
                          <a className="panel" key={m.id} href={`#/${m.id}`}>
                            {sections.find((row) => row[0] === m.id)?.[1] ??
                              m.id}
                          </a>
                        ))}
                    </div>
                  </section>
                ) : location.page === "comments" &&
                  runtime.value.channel_operations ? (
                  allowed("inbox.read") ? (
                    <Comments />
                  ) : (
                    <Denied />
                  )
                ) : location.page === "intelligence" &&
                  runtime.value.learning_operations ? (
                  allowed("agents.manage") && allowed("crm.read") ? (
                    <LearningWorkspace />
                  ) : (
                    <Denied />
                  )
                ) : location.page === "ads" && runtime.value.ads_operations ? (
                  allowed("ads.manage") && allowed("crm.read") ? (
                    <AdsWorkspace />
                  ) : (
                    <Denied />
                  )
                ) : location.page === "campaigns" &&
                  runtime.value.campaign_operations ? (
                  allowed("campaigns.manage") && allowed("crm.read") ? (
                    <CampaignWorkspace />
                  ) : (
                    <Denied />
                  )
                ) : location.page === "broadcasts" &&
                  runtime.value.broadcast_operations ? (
                  allowed("campaigns.manage") && allowed("crm.read") ? (
                    <BroadcastWorkspace />
                  ) : (
                    <Denied />
                  )
                ) : ["knowledge", "memory"].includes(location.page) &&
                  runtime.value.knowledge_operations ? (
                  allowed("sources.manage") ? (
                    <KnowledgeWorkspace
                      key={location.page}
                      memory={location.page === "memory"}
                    />
                  ) : (
                    <Denied />
                  )
                ) : ["agents", "assistant"].includes(location.page) &&
                  runtime.value.agent_operations ? (
                  allowed("agents.manage") ? (
                    location.page === "agents" ? (
                      <AgentsWorkspace />
                    ) : (
                      <AgentAssistantChat active selectedOnly />
                    )
                  ) : (
                    <Denied />
                  )
                ) : core ? (
                  <CoreView page={location.page} />
                ) : location.page === "channels" ? (
                  allowed("settings.channels.read") ? (
                    <Channels
                      openWebhooks={() => navigate("settings", "webhooks")}
                    />
                  ) : (
                    <Denied />
                  )
                ) : location.page === "settings" ? (
                  !currentTab || !allowed(currentTab[2]) ? (
                    <Denied />
                  ) : location.tab === "operations" ? (
                    runtime.value.institutional_operations ? (
                      <OperationsWorkspace />
                    ) : (
                      <Denied />
                    )
                  ) : location.tab === "profile" ? (
                    <Profile
                      key={session.user.revision}
                      contract={contract.value}
                    />
                  ) : location.tab === "users" ? (
                    <Users />
                  ) : location.tab === "roles" ? (
                    <Roles contract={contract.value} />
                  ) : location.tab === "security" ? (
                    <Security />
                  ) : location.tab === "audit" ? (
                    <Audit />
                  ) : location.tab === "channels" ? (
                    <Channels
                      openWebhooks={() => navigate("settings", "webhooks")}
                    />
                  ) : location.tab === "webhooks" ? (
                    runtime.value.channel_operations ? (
                      <ChannelRuntime />
                    ) : (
                      <Webhooks />
                    )
                  ) : (
                    <>
                      <SettingPage
                        key={location.tab}
                        section={location.tab}
                        contract={contract.value}
                        onSaved={
                          location.tab === "modules"
                            ? runtime.reload
                            : undefined
                        }
                      />
                      {location.tab === "models" && (
                        <ProviderKeys contract={contract.value} />
                      )}
                    </>
                  )
                ) : (
                  <section className="panel">
                    <h2>Integración pendiente</h2>
                    <p>
                      Este apartado forma parte de la adaptación institucional.
                      Sus funciones estarán disponibles cuando se complete su
                      integración.
                    </p>
                    <Button
                      variant="secondary"
                      onClick={() => navigate("overview")}
                    >
                      Volver al resumen
                    </Button>
                  </section>
                )}
              </>
            )}
          </div>
        </main>
      </div>
    </RuntimeContext.Provider>
  );
}
function Denied() {
  return (
    <Notice>
      Tu rol no permite acceder a este apartado. Solicita el permiso
      correspondiente al administrador.
    </Notice>
  );
}
function Core({ page }: { page: string }) {
  const { session } = useInstitution();
  const permission =
    page === "settings"
      ? "settings.crm.read"
      : page === "inbox"
        ? "inbox.read"
        : "crm.read";
  if (
    !session.actions.includes(permission) ||
    !session.actions.includes("settings.crm.read")
  )
    return <Denied />;
  return <CoreWorkspace page={page} />;
}
function CoreWorkspace({ page }: { page: string }) {
  const store = useClients(),
    cfg = useCrmConfiguration(),
    [selected, setSelected] = useState(""),
    [request, setRequest] = useState(0),
    { session } = useInstitution();
  if (page === "settings")
    return (
      <fieldset disabled={!session.actions.includes("settings.crm.write")}>
        <CrmConfiguration
          config={cfg.config}
          clients={store.clients}
          onChange={cfg.save}
          onReload={() => void cfg.reload()}
          revision={cfg.revision}
          loadError={cfg.error}
          ready={cfg.ready}
          openRequest={1}
        />
      </fieldset>
    );
  if (page === "inbox")
    return (
      <Inbox
        config={cfg.config}
        configReady={cfg.ready}
        configurationError={cfg.error}
        onManageConfiguration={() => navigate("settings", "crm")}
        selectedId={selected}
        threadOpenRequest={request}
        onSelect={setSelected}
        onConfirmed={() => void store.reload()}
        onClient={() => navigate("clients")}
      />
    );
  return (
    <Clients
      clients={store.clients}
      threads={store.threads}
      config={cfg.config}
      onSave={store.save}
      onInbox={(id) => {
        setSelected(id);
        setRequest((n) => n + 1);
        navigate("inbox");
      }}
      initialSelected={selected}
      openRequest={request}
      onConfigChange={cfg.save}
      onConfigReload={cfg.reload}
      configurationRevision={cfg.revision}
      configurationError={cfg.error}
      ready={store.status === "ready" && cfg.ready}
      busy={store.busy}
      serverRevision={store.revision}
      contactGroups={store.contactGroups}
      onReload={() => void store.reload()}
    />
  );
}
