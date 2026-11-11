import {
  Fragment,
  useCallback,
  useEffect,
  useState,
  type FormEvent,
} from "react";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Notice,
  SelectField,
} from "../shared/ui";
import {
  channelKeys,
  channelReferences,
  channelRequest as request,
  type ChannelAccount,
  type ChannelKey,
} from "../shared/channels";
import type { ChannelsCapabilities } from "../shared/runtimeCapabilities";

const configKeys = [
  "appId",
  "wabaId",
  "phoneNumberId",
  "pageId",
  "accountId",
  "apiVersion",
  "instagramLogin",
  "environment",
  "callbackUrl",
  "initialStage",
] as const;
const integrationTitles = {
  whatsapp: "Meta WhatsApp Cloud",
  instagram: "Instagram Business",
  messenger: "Facebook Messenger",
  facebook: "Comentarios de Facebook",
  tiktok: "TikTok",
};
const platformActions: Record<ChannelKey, string[]> = {
  whatsapp: ["Guardar integración y credenciales"],
  instagram: [
    "Conectar Instagram",
    "Diagnóstico IG",
    "Cargar cuenta",
    "Guardar conexión manual",
    "Crear endpoint Instagram",
  ],
  messenger: [
    "Conectar Facebook",
    "Diagnóstico FB",
    "Cargar páginas",
    "Guardar conexión manual",
    "Crear endpoint Facebook",
  ],
  facebook: ["Responder comentario"],
  tiktok: [
    "Conectar TikTok",
    "Diagnóstico TikTok",
    "Descubrir recursos",
    "Procesar eventos",
    "Crear endpoint TikTok",
  ],
};

function PendingConnection({
  title,
  actions,
}: {
  title: string;
  actions: string[];
}) {
  return (
    <details className="channel-ui-pending">
      <summary>
        {title} <Badge>Pendiente de portar</Badge>
      </summary>
      <p>
        Esta función de Scentra requiere completar su contrato en SQL Server. No
        está habilitada en este ensayo.
      </p>
      <div className="actions">
        {actions.map((action) => (
          <Button key={action} variant="secondary" disabled>
            {action}
          </Button>
        ))}
      </div>
    </details>
  );
}
const configurationOf = (value: Record<string, string>) =>
  Object.fromEntries(
    configKeys.map((key) => [
      key,
      value[key] ??
        (key === "instagramLogin"
          ? "facebook"
          : key === "environment"
            ? "production"
            : ""),
    ]),
  ) as Record<(typeof configKeys)[number], string>;
type Draft = {
  revision: number;
  configuration: ReturnType<typeof configurationOf>;
};
type Activity = {
  outboundRecords: number;
  receiptRecords: number;
  transportEnabled: false;
  workersEnabled: false;
};
type Comment = {
  id: string;
  channel: ChannelKey;
  body: string;
  receivedAt: string;
};
const message = (error: unknown) =>
  error instanceof Error &&
  !(error instanceof TypeError) &&
  !(error instanceof DOMException)
    ? error.message
    : "No se pudo acceder al servicio. Tu borrador se conserva; actualiza los datos antes de reintentar.";
function channelRequest<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
) {
  const timeout = AbortSignal.timeout(15000);
  return request<T>(
    path,
    method,
    body,
    signal ? AbortSignal.any([signal, timeout]) : timeout,
  );
}

function accountsOf(value: { channels: ChannelAccount[] }) {
  if (
    !Array.isArray(value.channels) ||
    value.channels.length !== channelKeys.length ||
    new Set(value.channels.map((a) => a.channel)).size !== channelKeys.length ||
    value.channels.some(
      (a) =>
        !channelKeys.includes(a.channel) ||
        !Number.isInteger(a.revision) ||
        a.revision < 0 ||
        !a.configuration ||
        Object.values(a.configuration).some((v) => typeof v !== "string"),
    )
  )
    throw new Error("La respuesta de Canales no es válida.");
  return value.channels.map((account) => accountOf(account, account.channel));
}

function accountOf(account: ChannelAccount, channel: ChannelKey) {
  if (
    !account ||
    account.channel !== channel ||
    !Number.isInteger(account.revision) ||
    account.revision < 0 ||
    !account.configuration ||
    Object.entries(account.configuration).some(
      ([key, value]) =>
        !configKeys.includes(key as (typeof configKeys)[number]) ||
        typeof value !== "string",
    ) ||
    !Array.isArray(account.credentials) ||
    account.credentials.length ||
    !account.capabilities ||
    Object.keys(account.capabilities).length ||
    account.verifiedAt !== null ||
    account.lastError !== null
  )
    throw new Error("La respuesta de Canales no es válida.");
  return account;
}

function ChannelCard({
  account,
  expanded,
  onToggle,
  stages,
  disabled,
  editable,
  onSave,
}: {
  account: ChannelAccount;
  expanded: boolean;
  onToggle: () => void;
  stages: string[];
  disabled: boolean;
  editable: boolean;
  onSave: (channel: ChannelKey, draft: Draft) => Promise<ChannelAccount>;
}) {
  const [draft, setDraft] = useState<Draft>(() => ({
    revision: account.revision,
    configuration: configurationOf(account.configuration),
  }));
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const stale = draft.revision !== account.revision;
  const dirty =
    JSON.stringify(draft.configuration) !==
    JSON.stringify(configurationOf(account.configuration));
  const update = (key: keyof Draft["configuration"], value: string) => {
    setDraft((old) => ({
      ...old,
      configuration: { ...old.configuration, [key]: value },
    }));
    setSaved(false);
  };
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled || stale || !editable) return;
    setError("");
    setSaved(false);
    try {
      const current = await onSave(account.channel, draft);
      setDraft({
        revision: current.revision,
        configuration: configurationOf(current.configuration),
      });
      setSaved(true);
    } catch (reason) {
      setError(message(reason));
    }
  }
  const key = account.channel;
  const field = (
    name: keyof Draft["configuration"],
    label: string,
    options: {
      numeric?: boolean;
      max?: number;
      pattern?: string;
      url?: boolean;
    } = {},
  ) => (
    <Field
      id={`ui-${key}-${name}`}
      name={name}
      label={label}
      value={draft.configuration[name]}
      onChange={(e) => update(name, e.target.value)}
      disabled={!editable || disabled}
      maxLength={options.max ?? 128}
      pattern={options.pattern}
      inputMode={options.numeric ? "numeric" : undefined}
      type={options.url ? "url" : "text"}
    />
  );
  return (
    <section className={`panel channel-ui-card${expanded ? " expanded" : ""}`}>
      <div className="channel-ui-heading">
        <div>
          <h2>{integrationTitles[key]}</h2>
          <Badge>
            {account.revision ? "Datos guardados" : "Sin configurar"}
          </Badge>
        </div>
        <Button
          variant="secondary"
          aria-expanded={expanded}
          aria-controls={`ui-${key}-form`}
          onClick={onToggle}
        >
          {expanded ? "Cerrar" : "Ver configuración"}
        </Button>
      </div>
      <div id={`ui-${key}-form`} hidden={!expanded}>
        <form
          onSubmit={(e) => void submit(e)}
          aria-label={`Configuración de ${channelReferences[key].name}`}
        >
          <div className="form-grid">
            {field(
              "appId",
              key === "tiktok"
                ? "Client Key"
                : key === "instagram"
                  ? "Instagram App ID"
                  : key === "whatsapp"
                    ? "Meta App ID"
                    : "Facebook App ID",
              { pattern: "[A-Za-z0-9_-]*" },
            )}
            {key !== "tiktok" &&
              field("apiVersion", "Graph API", {
                max: 12,
                pattern: "(v[0-9]{1,2}\\.0)?",
              })}
            {key === "whatsapp" && (
              <>
                {field("wabaId", "WABA ID", {
                  numeric: true,
                  pattern: "[0-9]*",
                })}
                {field("phoneNumberId", "Phone Number ID", {
                  numeric: true,
                  pattern: "[0-9]*",
                })}
              </>
            )}
            {(key === "facebook" || key === "messenger") &&
              field("pageId", "Page ID", {
                numeric: true,
                pattern: "[0-9]*",
              })}
            {(key === "instagram" || key === "tiktok") &&
              field(
                "accountId",
                key === "instagram" ? "Instagram Business ID" : "Open ID",
                {
                  pattern: "[A-Za-z0-9_.:-]*",
                },
              )}
            {key === "instagram" && (
              <SelectField
                id={`ui-${key}-instagramLogin`}
                label="Acceso de Instagram"
                value={draft.configuration.instagramLogin}
                disabled={!editable || disabled}
                onChange={(e) => update("instagramLogin", e.target.value)}
                options={[
                  { value: "facebook", label: "Facebook Login" },
                  { value: "instagram", label: "Instagram Login" },
                ]}
              />
            )}
            <SelectField
              id={`ui-${key}-environment`}
              label="Perfil de cuenta"
              value={draft.configuration.environment}
              disabled={!editable || disabled}
              onChange={(e) => update("environment", e.target.value)}
              options={[
                { value: "production", label: "Principal" },
                { value: "development", label: "Pruebas" },
              ]}
            />
            {field("callbackUrl", "URL de callback (borrador)", {
              max: 2048,
              url: true,
            })}
            <SelectField
              id={`ui-${key}-initialStage`}
              label="Etapa inicial del aspirante"
              value={draft.configuration.initialStage}
              disabled={!editable || disabled}
              onChange={(e) => update("initialStage", e.target.value)}
              options={[
                { value: "", label: "Sin asignar" },
                ...new Set([
                  ...stages,
                  ...(draft.configuration.initialStage
                    ? [draft.configuration.initialStage]
                    : []),
                ]),
              ]}
            />
          </div>
          {error && <Notice error>{error}</Notice>}
          {saved && (
            <Notice>Configuración guardada en la copia de ensayo.</Notice>
          )}
          {stale && (
            <Notice>
              Hay una versión más reciente. Tu borrador se conserva; revisa los
              datos guardados antes de volver a guardar.
            </Notice>
          )}
          <div className="actions">
            {editable && (
              <Button
                type="submit"
                disabled={disabled || stale || (!dirty && account.revision > 0)}
              >
                Guardar configuración
              </Button>
            )}
            {(dirty || stale) && (
              <Button
                variant="secondary"
                disabled={disabled}
                onClick={() => {
                  setDraft({
                    revision: account.revision,
                    configuration: configurationOf(account.configuration),
                  });
                  setError("");
                  setSaved(false);
                }}
              >
                Descartar borrador y cargar datos guardados
              </Button>
            )}
          </div>
          <PendingConnection
            title="Conexión, credenciales y diagnóstico"
            actions={platformActions[key]}
          />
        </form>
      </div>
    </section>
  );
}

function Comments() {
  const [offset, setOffset] = useState(0);
  const [attempt, setAttempt] = useState(0);
  const [data, setData] = useState<{ offset: number; rows: Comment[] } | null>(
    null,
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    void channelRequest<{ comments: Comment[] }>(
      `/api/v1/social-comments?offset=${offset}&limit=25`,
      "GET",
      undefined,
      controller.signal,
    )
      .then((result) => {
        if (
          !Array.isArray(result.comments) ||
          result.comments.length > 25 ||
          result.comments.some(
            (c) =>
              typeof c.body !== "string" ||
              !channelKeys.includes(c.channel) ||
              !Number.isFinite(Date.parse(c.receivedAt)),
          )
        )
          throw new Error("La respuesta de comentarios no es válida.");
        if (!controller.signal.aborted) {
          setData({ offset, rows: result.comments });
          setError("");
        }
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(message(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [offset, attempt]);
  const rows = data?.offset === offset ? data.rows : [];
  return (
    <section className="panel">
      <h2>Comentarios sociales</h2>
      {busy && <p role="status">Consultando comentarios…</p>}
      {error && (
        <Notice error>
          {error}
          <Button
            variant="secondary"
            onClick={() => {
              setBusy(true);
              setAttempt((n) => n + 1);
            }}
          >
            Reintentar comentarios
          </Button>
        </Notice>
      )}
      {!busy && !error && !rows.length && (
        <p>No hay comentarios en esta página.</p>
      )}
      {rows.map((row) => (
        <article className="channel-ui-comment" key={row.id}>
          <div>
            <Badge>{channelReferences[row.channel].name}</Badge>
            <time dateTime={row.receivedAt}>
              {new Intl.DateTimeFormat("es-CO", {
                dateStyle: "medium",
                timeStyle: "short",
              }).format(new Date(row.receivedAt))}
            </time>
          </div>
          <p>{row.body}</p>
        </article>
      ))}
      <div className="actions">
        <Button
          variant="secondary"
          disabled={busy || offset === 0}
          onClick={() => {
            setBusy(true);
            setError("");
            setOffset((n) => Math.max(0, n - 25));
          }}
        >
          Anterior
        </Button>
        <Button
          variant="secondary"
          disabled={busy || !!error || rows.length < 25}
          onClick={() => {
            setBusy(true);
            setError("");
            setOffset((n) => n + 25);
          }}
        >
          Siguiente
        </Button>
      </div>
    </section>
  );
}

export function ChannelsUiPanel({
  capabilities,
}: {
  capabilities: ChannelsCapabilities["channels"];
}) {
  const [accounts, setAccounts] = useState<ChannelAccount[]>([]);
  const [expanded, setExpanded] = useState<ChannelKey | null>(null);
  const [stages, setStages] = useState<string[]>([]);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [error, setError] = useState("");
  const [stageError, setStageError] = useState("");
  const [statusError, setStatusError] = useState("");
  const [busy, setBusy] = useState(true);
  const load = useCallback(
    async (signal?: AbortSignal) => {
      const [accountResult, stageResult, statusResult] =
        await Promise.allSettled([
          channelRequest<{ channels: ChannelAccount[] }>(
            "/api/v1/channels",
            "GET",
            undefined,
            signal,
          ).then(accountsOf),
          capabilities.stageOptions
            ? channelRequest<{ stages: string[] }>(
                "/api/local/channels/stages",
                "GET",
                undefined,
                signal,
              )
            : Promise.resolve(null),
          capabilities.status
            ? channelRequest<Activity>(
                "/api/v1/channels/transport/status",
                "GET",
                undefined,
                signal,
              )
            : Promise.resolve(null),
        ]);
      if (signal?.aborted) return;
      if (accountResult.status === "fulfilled") {
        setAccounts(accountResult.value);
        setError("");
      } else setError(message(accountResult.reason));
      if (
        stageResult.status === "fulfilled" &&
        (!stageResult.value ||
          (Array.isArray(stageResult.value.stages) &&
            stageResult.value.stages.every((s) => typeof s === "string")))
      ) {
        setStages(stageResult.value?.stages ?? []);
        setStageError("");
      } else setStageError("No se pudieron consultar las etapas activas.");
      if (
        statusResult.status === "fulfilled" &&
        (!statusResult.value ||
          (Number.isInteger(statusResult.value.outboundRecords) &&
            Number.isInteger(statusResult.value.receiptRecords) &&
            statusResult.value.outboundRecords >= 0 &&
            statusResult.value.receiptRecords >= 0 &&
            statusResult.value.transportEnabled === false &&
            statusResult.value.workersEnabled === false))
      ) {
        setActivity(statusResult.value);
        setStatusError("");
      } else setStatusError("No se pudo consultar la actividad local.");
      setBusy(false);
    },
    [capabilities.stageOptions, capabilities.status],
  );
  useEffect(() => {
    const controller = new AbortController();
    void Promise.resolve().then(() => {
      if (!controller.signal.aborted) return load(controller.signal);
    });
    return () => controller.abort();
  }, [load]);
  const update = (account: ChannelAccount) =>
    setAccounts((rows) =>
      rows.map((row) => (row.channel === account.channel ? account : row)),
    );
  async function save(channel: ChannelKey, draft: Draft) {
    setBusy(true);
    try {
      const stored = await channelRequest<ChannelAccount>(
        `/api/v1/channels/${channel}/draft`,
        "PUT",
        draft,
      );
      accountOf(stored, channel);
      update(stored);
      return stored;
    } catch (reason) {
      try {
        const current = await channelRequest<ChannelAccount>(
          `/api/v1/channels/${channel}`,
        );
        accountOf(current, channel);
        update(current);
        setError("");
      } catch {
        setError(
          "No se pudo confirmar la versión guardada. Consulta los datos antes de volver a guardar.",
        );
      }
      throw reason;
    } finally {
      setBusy(false);
    }
  }
  const card = (key: ChannelKey) => {
    const account = accounts.find((a) => a.channel === key);
    return account ? (
      <ChannelCard
        account={account}
        expanded={expanded === key}
        onToggle={() => setExpanded((old) => (old === key ? null : key))}
        stages={stages}
        disabled={busy || !!error || !!stageError}
        editable={capabilities.configuration}
        onSave={save}
      />
    ) : null;
  };
  return (
    <div className="channel-ui-content">
      <Notice>
        Los datos se guardan en esta copia. La conexión a plataformas y los
        envíos están pendientes.
      </Notice>
      <div className="actions">
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            void load();
          }}
        >
          Actualizar datos
        </Button>
      </div>
      {error && <Notice error>{error}</Notice>}
      {stageError && <Notice error>{stageError}</Notice>}
      {busy && !accounts.length && <p role="status">Consultando canales…</p>}
      {!busy && !accounts.length && !error && (
        <EmptyState title="Sin canales disponibles">
          Actualiza la consulta para revisar la configuración.
        </EmptyState>
      )}
      <div className="channel-ui-list">
        {channelKeys
          .filter((key) => key !== "facebook")
          .map((key) => (
            <Fragment key={key}>
              {card(key)}
              {key === "whatsapp" && (
                <section className="panel">
                  <PendingConnection
                    title="Verificar número WhatsApp"
                    actions={["Sincronizar números", "Registrar/verificar"]}
                  />
                </section>
              )}
              {key === "messenger" && (
                <div
                  className="channel-ui-facebook-comments"
                  hidden={expanded !== "messenger" && expanded !== "facebook"}
                >
                  {card("facebook")}
                </div>
              )}
            </Fragment>
          ))}
        <section className="panel">
          <PendingConnection
            title="Webhooks"
            actions={[
              "Crear / actualizar endpoint",
              "Procesar eventos pendientes",
            ]}
          />
        </section>
      </div>
      {capabilities.status && (
        <section className="panel">
          <h2>Actividad local</h2>
          {statusError ? (
            <Notice error>{statusError}</Notice>
          ) : activity ? (
            <p>
              Recibos almacenados: {activity.receiptRecords}. Registros de cola
              de ensayo: {activity.outboundRecords}.
            </p>
          ) : (
            <p role="status">Consultando actividad…</p>
          )}
          <Badge>Transporte pendiente</Badge>
        </section>
      )}
      {capabilities.comments && <Comments />}
    </div>
  );
}
