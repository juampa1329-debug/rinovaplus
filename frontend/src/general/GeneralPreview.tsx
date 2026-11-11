import { useEffect, useState } from "react";
import { App } from "../App";
import {
  RuntimeContext,
  featureNames,
  type UiCapabilities,
} from "../shared/runtimeCapabilities";
import { useRoute } from "../shared/navigation";
import { useTheme, type ThemePreference } from "../shared/theme";
import {
  Badge,
  Button,
  EmptyState,
  Notice,
  PageHeading,
  SelectField,
} from "../shared/ui";
import { Icon } from "../shared/Icon";

type Section = {
  path: string;
  label: string;
  phase: string;
  available: boolean;
  status: string;
};
type Manifest = {
  version: string;
  profile: string;
  scope: string;
  sections: Section[];
  features: Record<string, boolean>;
};
const core = ["overview", "clients", "inbox", "settings"];
const paths = [
  "admissions",
  ...core.slice(0, 3),
  "channels",
  "assistant",
  "agents",
  "knowledge",
  "memory",
  "broadcasts",
  "campaigns",
  "ads",
  "intelligence",
  "settings",
];

export function validateGeneral(value: unknown): Manifest {
  if (!value || typeof value !== "object") throw Error("invalid_manifest");
  const m = value as Manifest;
  if (
    Object.keys(m).length !== 5 ||
    m.version !== "cbn-general-preview-c13-v1" ||
    m.profile !== "general_preview" ||
    m.scope !== "isolated_local_preview" ||
    !Array.isArray(m.sections) ||
    m.sections.length !== paths.length ||
    Object.keys(m.features ?? {})
      .sort()
      .join() !==
      ["providers", "institutional_auth", "provider_workers", "public_webhooks"]
        .sort()
        .join() ||
    Object.values(m.features).some((v) => v !== false)
  )
    throw Error("invalid_manifest");
  if (
    m.sections.some(
      (s, i) =>
        Object.keys(s).length !== 5 ||
        s.path !== paths[i] ||
        typeof s.label !== "string" ||
        !/^P\d+$/.test(s.phase) ||
        s.available !== (core.includes(s.path) || s.path === "channels") ||
        s.status !== (s.available ? "local_subset" : "pending_integration"),
    )
  )
    throw Error("invalid_sections");
  return m;
}

const foundation: UiCapabilities = {
  version: "cbn-ui-capabilities-v1",
  profile: "foundation",
  mode: "local_foundation",
  modules: core,
  scope: "restored_rehearsal_only",
  features: Object.fromEntries(
    featureNames.map((k) => [k, false]),
  ) as UiCapabilities["features"],
};

async function request(path: string, signal?: AbortSignal) {
  const response = await fetch(path, {
    headers: { "X-CRM-Local": "1" },
    cache: "no-store",
    signal: signal
      ? AbortSignal.any([signal, AbortSignal.timeout(30000)])
      : AbortSignal.timeout(30000),
  });
  if (!response.ok)
    throw Error("No se pudo cargar la información de esta copia.");
  return response.json() as Promise<unknown>;
}

function ChannelSummary() {
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void request("/api/local/channels/integrations", controller.signal)
      .then((v) => setItems((v as { items: Record<string, unknown>[] }).items))
      .catch(() => {
        if (!controller.signal.aborted)
          setError("No se pudieron consultar los canales.");
      });
    return () => controller.abort();
  }, []);
  return (
    <>
      <PageHeading
        title="Canales"
        description="Cuentas y configuración conservadas en esta copia de ensayo."
      />
      <Notice>
        Los borradores están desconectados. OAuth, verificación de números y
        cambios de credenciales siguen pendientes de integración.
      </Notice>
      {error && <Notice error>{error}</Notice>}
      <div className="general-channel-grid">
        {items.map((i) => (
          <section className="panel" key={String(i.IntegrationId)}>
            <Badge>
              {i.Channel === "whatsapp"
                ? "WhatsApp"
                : i.Channel === "tiktok"
                  ? "TikTok"
                  : String(i.Channel)}
            </Badge>
            <h2>{String(i.DisplayName)}</h2>
            <dl>
              <dt>Cuenta externa</dt>
              <dd>
                {i.ExternalAccountId
                  ? String(i.ExternalAccountId)
                  : "Pendiente de configurar"}
              </dd>
              <dt>Estado solicitado</dt>
              <dd>
                {i.RequestedStatus === "connected"
                  ? "Conectado"
                  : i.RequestedStatus === "paused"
                    ? "Pausado"
                    : "Desconectado"}
              </dd>
              <dt>Verificación</dt>
              <dd>
                {i.VerifiedStatus === "unverified"
                  ? "Sin verificar"
                  : "Pendiente de revisión"}
              </dd>
              <dt>Etapa inicial</dt>
              <dd>
                {i.InitialStageKey
                  ? String(i.InitialStageLabel ?? i.InitialStageKey)
                  : "Sin etapa asignada"}
              </dd>
            </dl>
            <small>Los secretos permanecen protegidos.</small>
          </section>
        ))}
      </div>
    </>
  );
}

type Phase = {
  id: string;
  title: string;
  accepted: number;
  total: number;
  percent_display: string;
  partial: number;
};
function Progress() {
  const [phases, setPhases] = useState<Phase[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void request("/api/local/progress", controller.signal)
      .then((v) => setPhases((v as { phases: Phase[] }).phases))
      .catch(() => {
        if (!controller.signal.aborted)
          setError("No se pudo consultar el progreso.");
      });
    return () => controller.abort();
  }, []);
  return (
    <>
      <PageHeading
        title="Avance de la adaptación"
        description="Criterios completos aceptados por fase; los avances parciales conservan su evidencia."
      />
      {error && <Notice error>{error}</Notice>}
      <section className="panel general-progress">
        <table>
          <caption>Roadmap de la institución</caption>
          <thead>
            <tr>
              <th>Fase</th>
              <th>Criterios aceptados</th>
              <th>Porcentaje</th>
              <th>Criterios parciales</th>
            </tr>
          </thead>
          <tbody>
            {phases.map((p) => (
              <tr key={p.id}>
                <th scope="row">
                  {p.id} · {p.title}
                </th>
                <td>
                  {p.accepted}/{p.total}
                </td>
                <td>{p.percent_display}</td>
                <td>{p.partial}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

const remaining: Record<string, string> = {
  admissions:
    "Falta integrar el catálogo académico completo y aceptar sus recorridos con SIIE.",
  assistant:
    "Faltan la ejecución integrada y las pruebas de los agentes educativos.",
  agents:
    "Se conserva la jerarquía orientador → programa → etapa. Falta aceptar su ejecución en esta composición.",
  knowledge:
    "Faltan las fuentes publicadas, su aislamiento y recuperación sobre el contrato integrado.",
  memory:
    "Faltan la memoria colectiva y el ADN institucional con versiones y evidencia.",
  broadcasts:
    "Faltan audiencias, consentimiento, cadencia y transporte aceptados.",
  campaigns:
    "Faltan activadores, audiencias, flujos persistentes y remarketing conectado.",
  ads: "Faltan cuentas, permisos, captación y atribución aceptadas.",
  intelligence:
    "Faltan datasets, evaluación por segmento y promoción o reversión de modelos.",
};

export function GeneralPreview() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [menu, setMenu] = useState(false);
  const route = useRoute();
  const { preference, chooseTheme } = useTheme();
  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/local/session", {
      method: "POST",
      headers: { "X-CRM-Local": "1" },
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(30000)]),
    })
      .then((r) => {
        if (!r.ok) throw Error("session");
        return request("/api/local/runtime", controller.signal);
      })
      .then((v) => {
        if (!controller.signal.aborted) {
          setManifest(validateGeneral(v));
          setError(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    document.title = "CRM CBN · Vista general";
  }, [route, manifest]);
  if (!manifest)
    return (
      <main className="public-main">
        <section className="panel">
          <Notice error={error}>
            {error
              ? "No se pudo comprobar la disponibilidad de esta copia."
              : "Comprobando funciones disponibles…"}
          </Notice>
          {error && (
            <Button
              onClick={() => {
                setError(false);
                setAttempt((n) => n + 1);
              }}
            >
              Reintentar
            </Button>
          )}
        </section>
      </main>
    );
  const selected = manifest.sections.find((s) => s.path === route);
  return (
    <RuntimeContext.Provider
      value={{
        status: "ready",
        capabilities: foundation,
        reload: () => window.location.reload(),
      }}
    >
      <div className="app-shell pilot-shell general-preview">
        <a className="skip-link" href="#general-main">
          Saltar al contenido
        </a>
        <aside className="sidebar">
          <button
            className="sidebar-logo-toggle"
            aria-label="Menú CRM CBN"
            aria-expanded={menu}
            aria-controls="general-navigation"
            onClick={() => setMenu(!menu)}
          >
            <Icon name="menu" />
            <span>CRM CBN</span>
          </button>
          <nav
            id="general-navigation"
            aria-label="Navegación principal"
            className={menu ? "mobile-open" : ""}
          >
            {manifest.sections.map((s) => (
              <a
                key={s.path}
                href={`#/${s.path}`}
                onClick={() => setMenu(false)}
                className="nav-link"
                aria-current={s.path === route ? "page" : undefined}
                aria-label={
                  s.available ? s.label : `${s.label}, integración pendiente`
                }
              >
                <Icon name={s.path === "channels" ? "settings" : s.path} />
                <span>{s.label}</span>
                {!s.available && (
                  <small className="general-pending" aria-hidden="true">
                    Pendiente
                  </small>
                )}
              </a>
            ))}
            <a
              href="#/progress"
              onClick={() => setMenu(false)}
              className="nav-link"
              aria-current={route === "progress" ? "page" : undefined}
            >
              <Icon name="overview" />
              <span>Avance general</span>
            </a>
          </nav>
          <div className="sidebar-footer">
            <strong>Institución educativa</strong>
            <small>Vista general · copia de ensayo</small>
          </div>
        </aside>
        <div className="workspace">
          <header className="topbar">
            <Badge>Vista de avances</Badge>
            <SelectField
              id="general-theme"
              label="Apariencia"
              value={preference}
              onChange={(e) => chooseTheme(e.target.value as ThemePreference)}
              options={[
                { value: "system", label: "Sistema" },
                { value: "light", label: "Claro" },
                { value: "dark", label: "Oscuro" },
              ]}
            />
          </header>
          <div
            id="general-main"
            role={core.includes(route) ? undefined : "main"}
            tabIndex={-1}
          >
            <div className="general-core" hidden={!core.includes(route)}>
              <App />
            </div>
            {core.includes(route) ? null : route === "channels" ? (
              <ChannelSummary />
            ) : route === "progress" ? (
              <Progress />
            ) : selected ? (
              <>
                <PageHeading
                  title={selected.label}
                  description="Adaptación educativa de las funciones de Scentra."
                />
                <section className="panel">
                  <Badge>{selected.phase} · Integración pendiente</Badge>
                  <h2>Avance de esta sección</h2>
                  <p>{remaining[route]}</p>
                  <p>
                    Su estructura y el trabajo anterior se conservan. Esta vista
                    muestra el estado de adaptación de la sección.
                  </p>
                  <Button
                    onClick={() => {
                      window.location.hash = "/progress";
                    }}
                  >
                    Ver progreso por fase
                  </Button>
                </section>
              </>
            ) : (
              <EmptyState title="Sección no encontrada">
                Selecciona una sección del menú.
              </EmptyState>
            )}
          </div>
        </div>
      </div>
    </RuntimeContext.Provider>
  );
}
