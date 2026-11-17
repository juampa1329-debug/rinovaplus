import { useState } from "react";
import { Badge, Button, Field, Notice, SelectField } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import type { Document } from "./api";
import { Credentials, ResourceState, useResource } from "./Settings";
import { OneTime } from "./Access";
import { allowNavigation, useDraftGuard } from "./drafts";
import { ChannelOperations, ChannelWebhook } from "./ChannelOperations";
import type { IssuedWebhook } from "./ChannelOperations";
import { ErrorFeedback, OperationDialog } from "./ErrorFeedback";
import { explainChannelError } from "./channelErrors";

export type Channel = {
  id: string;
  application_id: string;
  display_name: string;
  channel: string;
  revision: number;
  row_version: string;
  application_version: string;
  verified_status: string;
  fields: Document;
  provider_operations_available?: boolean;
  issuer_profile?: string;
  oauth_callback?: string;
  oauth_ready?: boolean;
  synthetic_demo?: boolean;
  initial_stage_key?: string;
  requested_status?: string;
  webhook?: {
    id: string;
    path: string;
    callback_url: string;
    public_origin_required: boolean;
    active: boolean;
    row_version: string;
    challenge_verified_at: string | null;
    last_seen_at: string | null;
  } | null;
  verify_token?: string;
};
type ChannelField = {
  id: string;
  group: string;
  label: string;
  config_key: string;
  input_type: string;
  options: { value: string; label: string }[] | null;
  field_kind: string;
  editable_in_p2: boolean;
  value_type: string;
  max_length?: number;
  range?: { minimum: number; maximum: number };
  requires_provider_action: boolean;
};
type Catalog = {
  provider_operations_available?: boolean;
  groups: { id: string; label: string; applies_to_channels: string[] }[];
  fields: ChannelField[];
};
const whatsappMetaFields: Partial<
  Record<string, { label: string; hint: string }>
> = {
  "meta:whatsapp_business_account_id": {
    label: "ID de la cuenta de WhatsApp (WABA ID)",
    hint: "En la configuración de Meta Business, abre la cuenta de WhatsApp y copia el ID de esa cuenta.",
  },
  "meta:whatsapp_phone_number_id": {
    label: "ID del número de teléfono en Meta",
    hint: "En el Administrador de WhatsApp, copia el ID que Meta asigna al número que quieres conectar.",
  },
};
export const channelNames: Record<string, string> = {
  whatsapp: "WhatsApp",
  instagram: "Instagram",
  facebook: "Facebook",
  messenger: "Messenger",
  tiktok: "TikTok",
};

const oauthReturnErrors = {
  confirm: {
    title: "Vuelve a confirmar tu identidad",
    detail: "La sesión o la confirmación de identidad venció durante la autorización.",
    nextStep: "Abre el canal, vuelve a conectar la cuenta y confirma tu identidad cuando se solicite.",
  },
  "invalid-attempt": {
    title: "La autorización ya no está disponible",
    detail: "El intento de conexión venció, ya se usó o pertenece a otra sesión.",
    nextStep: "Abre el canal e inicia una conexión nueva en la misma sesión de RinovaPlus.",
  },
  "configuration-changed": {
    title: "Cambió la configuración del inicio de sesión",
    detail: "La aplicación o su credencial cambió durante la autorización.",
    nextStep: "Abre el canal e inicia una conexión nueva con la configuración guardada.",
  },
};

function oauthReturn() {
  const [prefix, section, action, account, session, extra] =
    window.location.hash.split("/");
  const uuid = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
  if (prefix !== "#" || section !== "channels" || action !== "oauth")
    return null;
  if (!session && Object.hasOwn(oauthReturnErrors, account))
    return { error: oauthReturnErrors[account as keyof typeof oauthReturnErrors] };
  if (!extra && uuid.test(account ?? "") && uuid.test(session ?? ""))
    return { account, session };
  return null;
}

export function Channels({ openWebhooks }: { openWebhooks: () => void }) {
  return (
    <ErrorFeedback explain={explainChannelError}>
      <ChannelAccounts openWebhooks={openWebhooks} />
    </ErrorFeedback>
  );
}

function ChannelAccounts({ openWebhooks }: { openWebhooks: () => void }) {
  const data = useResource<{ items: Channel[] }>("channels"),
    catalog = useResource<Catalog>("channels/catalog"),
    { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [returnContext] = useState(oauthReturn);
  const [returnError, setReturnError] = useState(returnContext?.error);
  const [selected, setSelected] = useState(returnContext?.account ?? ""),
    [channel, setChannel] = useState("whatsapp"),
    [name, setName] = useState(""),
    [client, setClient] = useState(""),
    [graphVersion, setGraphVersion] = useState(""),
    [issuer, setIssuer] = useState("meta_whatsapp"),
    [app, setApp] = useState("");
  const [initialWebhook, setInitialWebhook] = useState<IssuedWebhook>();
  const selectAccount = (id: string) => {
    if (!allowNavigation()) return;
    if (id !== selected) setInitialWebhook(undefined);
    setSelected(id);
  };
  useDraftGuard(!!name || !!client || !!graphVersion);
  const writable = session.actions.includes("settings.channels.write");
  if (!data.value || !catalog.value)
    return <ResourceState error={data.error || catalog.error} />;
  const account = data.value.items.find((row) => row.id === selected);
  return (
    <>
      {returnError && (
        <OperationDialog guidance={returnError} dismiss={() => setReturnError(undefined)} />
      )}
      {!catalog.value.provider_operations_available && (
        <Notice>
          Configura tus canales y administra varias cuentas de mensajería. Las
          verificaciones de número y token, OAuth, sincronización y envíos
          externos estarán disponibles al habilitar su integración. Una
          configuración guardada aún no acredita conexión con el proveedor.
        </Notice>
      )}
      {task.notices}
      <div className="institution-channel-layout">
        <aside className="panel">
          <h3>Cuentas</h3>
          {data.value.items.map((row) => (
            <Button
              key={row.id}
              variant={row.id === selected ? "primary" : "quiet"}
              onClick={() => selectAccount(row.id)}
            >
              {row.display_name}
              <small>{channelNames[row.channel]}</small>
            </Button>
          ))}
          {!data.value.items.length && <p>No hay cuentas configuradas.</p>}
          <Button variant="secondary" onClick={() => selectAccount("")}>
            Nueva cuenta
          </Button>
        </aside>
        <div>
          {account ? (
            <ChannelEditor
              key={account.id}
              account={account}
              catalog={catalog.value}
              writable={writable}
              done={data.reload}
              openWebhooks={openWebhooks}
              initialWebhook={initialWebhook}
              returnedOAuth={
                returnContext?.account === account.id
                  ? returnContext.session
                  : undefined
              }
            />
          ) : (
            <form
              className="panel"
              onSubmit={(event) => {
                event.preventDefault();
                void task.run(async () => {
                  const body = {
                    channel,
                    display_name: name,
                    issuer_profile: issuer,
                    ...(channel !== "tiktok" && graphVersion
                      ? { api_version: graphVersion }
                      : {}),
                    ...(app ? { application_id: app } : { client_id: client }),
                  };
                  const result = await call<Channel>("channels", "POST", {
                    ...body,
                    operation_id: intent.get(body),
                  });
                  setName("");
                  setClient("");
                  setGraphVersion("");
                  if (
                    result.verify_token &&
                    result.webhook &&
                    channel !== "tiktok"
                  ) {
                    setInitialWebhook({
                      webhook: result.webhook,
                      verify_token: result.verify_token,
                    });
                  }
                  await data.reload();
                  setSelected(result.id);
                });
              }}
            >
              <h3>Nueva cuenta de canal</h3>
              <fieldset disabled={!writable || task.busy}>
                <SelectField
                  id="channel-type"
                  label="Canal"
                  options={Object.entries(channelNames).map(
                    ([value, label]) => ({ value, label }),
                  )}
                  value={channel}
                  onChange={(event) => {
                    const next = event.target.value;
                    setChannel(next);
                    setIssuer(
                      next === "whatsapp"
                        ? "meta_whatsapp"
                        : next === "instagram"
                          ? "instagram_login"
                          : next === "tiktok"
                            ? catalog.value?.provider_operations_available
                              ? "tiktok_login_kit"
                              : "tiktok_business"
                            : "facebook_login",
                    );
                    setApp("");
                  }}
                />
                <Field
                  id="channel-name"
                  label="Nombre de la cuenta"
                  required
                  maxLength={160}
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
                <SelectField
                  id="channel-issuer"
                  label="Inicio de sesión del proveedor"
                  value={issuer}
                  options={
                    channel === "whatsapp"
                      ? ["meta_whatsapp"]
                      : channel === "instagram"
                        ? ["instagram_login", "facebook_login"]
                        : channel === "tiktok"
                          ? catalog.value.provider_operations_available
                            ? ["tiktok_login_kit", "tiktok_business"]
                            : ["tiktok_business"]
                          : ["facebook_login"]
                  }
                  onChange={(event) => {
                    setIssuer(event.target.value);
                    setApp("");
                  }}
                />
                <SelectField
                  id="channel-application"
                  label="Aplicación"
                  value={app}
                  options={[
                    { value: "", label: "Configurar una aplicación" },
                    ...Array.from(
                      new Map(
                        data.value.items
                          .filter((row) =>
                            row.issuer_profile
                              ? row.issuer_profile === issuer
                              : row.channel === channel,
                          )
                          .map((row) => [
                            row.application_id,
                            {
                              value: row.application_id,
                              label: row.display_name,
                            },
                          ]),
                      ).values(),
                    ),
                  ]}
                  onChange={(event) => setApp(event.target.value)}
                />
                {!app && (
                  <Field
                    id="channel-client-id"
                    label={channel === "tiktok" ? "Client Key" : "App ID"}
                    required
                    maxLength={128}
                    value={client}
                    onChange={(event) => setClient(event.target.value)}
                  />
                )}
                {channel !== "tiktok" && (
                  <Field
                    id="channel-graph-version"
                    label="Versión de Graph API"
                    placeholder="v25.0"
                    hint="Consulta la versión en Meta, en Configuración de la app → Avanzada."
                    pattern="v[0-9]{1,2}[.][0-9]{1,2}"
                    maxLength={6}
                    value={graphVersion}
                    onChange={(event) => setGraphVersion(event.target.value)}
                  />
                )}
                <Button type="submit">Crear cuenta</Button>
              </fieldset>
            </form>
          )}
        </div>
      </div>
    </>
  );
}
function ChannelEditor({
  account,
  catalog,
  writable,
  done,
  openWebhooks,
  returnedOAuth,
  initialWebhook,
}: {
  account: Channel;
  catalog: Catalog;
  writable: boolean;
  done: () => Promise<unknown>;
  openWebhooks: () => void;
  returnedOAuth?: string;
  initialWebhook?: IssuedWebhook;
}) {
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [draft, setDraft] = useState({ base: account, values: account.fields });
  const dirty =
    JSON.stringify(draft.values) !== JSON.stringify(draft.base.fields);
  const values = dirty ? draft.values : account.fields;
  const base = dirty ? draft.base : account;
  const setValues = (values: Document) => setDraft({ base, values });
  useDraftGuard(dirty);
  const groups = catalog.groups.filter((g) =>
    g.applies_to_channels.includes(account.channel),
  );
  const editable = catalog.fields.filter(
    (f) =>
      groups.some((g) => g.id === f.group) &&
      f.group !== "webhooks" &&
      f.field_kind === "input" &&
      f.editable_in_p2,
  );
  return (
    <>
      <h2>{account.display_name}</h2>
      {account.synthetic_demo && (
        <Notice>
          Cuenta ficticia para explorar la interfaz. Agrega otra cuenta con los
          datos de tu institución para conectarla.
        </Notice>
      )}
      <Badge>
        {channelNames[account.channel]} ·{" "}
        {account.verified_status === "unverified"
          ? "Sin verificar"
          : account.verified_status === "retired"
            ? "Retirada"
            : account.verified_status === "identity_only"
              ? "Identidad verificada · sin permisos de Business API"
              : account.verified_status}
      </Badge>
      {task.notices}
      {dirty && base.row_version !== account.row_version && (
        <Notice>
          Tu borrador se conserva y hay una versión más reciente.{" "}
          <Button
            variant="secondary"
            onClick={() => {
              if (
                window.confirm(
                  "¿Reemplazar este borrador por la configuración guardada?",
                )
              )
                setDraft({ base: account, values: account.fields });
            }}
          >
            Cargar configuración guardada
          </Button>
        </Notice>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void task.run(async () => {
            const body = {
              revision: base.revision,
              row_version: base.row_version,
              application_version: base.application_version,
              values: Object.fromEntries(
                editable
                  .filter(
                    (f) =>
                      values[f.id] !== undefined &&
                      values[f.id] !== null &&
                      !Object.is(values[f.id], base.fields[f.id]),
                  )
                  .map((f) => [f.id, values[f.id]]),
              ),
            };
            const result = await call<Channel>(
              `channels/${account.id}`,
              "PUT",
              {
                ...body,
                operation_id: intent.get(body),
              },
            );
            await done();
            setDraft({ base: result, values: result.fields });
          });
        }}
      >
        <fieldset disabled={task.busy || !writable}>
          {groups
            .filter(
              (g) => g.id !== "webhooks" && g.id !== "meta_secret_rotation",
            )
            .map((group) => (
              <section className="panel" key={group.id}>
                <h3>{group.label}</h3>
                <div className="institution-fields">
                  {catalog.fields
                    .filter(
                      (f) => f.group === group.id && f.field_kind !== "secret",
                    )
                    .map((field) => {
                      const id = `channel-${field.id}`,
                        current = values[field.id],
                        metaField = whatsappMetaFields[field.id],
                        disabled =
                          !field.editable_in_p2 ||
                          field.requires_provider_action ||
                          field.field_kind === "transient",
                        change = (value: unknown) =>
                          setValues({ ...values, [field.id]: value });
                      if (
                        field.field_kind === "display" ||
                        field.field_kind === "metadata"
                      )
                        return (
                          <div className="field" key={id}>
                            <span>{field.label}</span>
                            <strong>
                              {current == null || current === ""
                                ? "Sin información del proveedor"
                                : String(current)}
                            </strong>
                          </div>
                        );
                      if (field.value_type === "boolean")
                        return (
                          <label key={id} className="institution-check">
                            <input
                              type="checkbox"
                              checked={current === true}
                              disabled={disabled}
                              onChange={(event) => change(event.target.checked)}
                            />
                            {field.label}
                          </label>
                        );
                      if (field.options?.length)
                        return (
                          <SelectField
                            key={id}
                            id={id}
                            label={field.label}
                            options={field.options}
                            value={String(current ?? field.options[0].value)}
                            disabled={disabled}
                            onChange={(event) => change(event.target.value)}
                          />
                        );
                      return (
                        <Field
                          key={id}
                          id={id}
                          label={metaField?.label ?? field.label}
                          value={
                            Array.isArray(current)
                              ? current.join(", ")
                              : current == null
                                ? ""
                                : String(current)
                          }
                          type={
                            field.field_kind === "transient"
                              ? "password"
                              : field.value_type === "integer"
                                ? "number"
                                : "text"
                          }
                          autoComplete={
                            field.field_kind === "transient" ? "off" : undefined
                          }
                          inputMode={metaField ? "numeric" : undefined}
                          min={field.range?.minimum}
                          max={field.range?.maximum}
                          maxLength={field.max_length}
                          disabled={disabled}
                          hint={
                            field.requires_provider_action
                              ? "Disponible al conectar el proveedor."
                              : field.id.endsWith("_login_configuration_id")
                                ? "Cópialo de Inicio de sesión con Facebook para empresas → Configuraciones en Meta."
                                : metaField?.hint
                          }
                          onChange={(event) =>
                            change(
                              field.value_type === "integer"
                                ? Number(event.target.value)
                                : field.value_type === "string_array"
                                  ? event.target.value
                                      .split(",")
                                      .map((v) => v.trim())
                                      .filter(Boolean)
                                  : event.target.value,
                            )
                          }
                        />
                      );
                    })}
                </div>
              </section>
            ))}
          <Button type="submit">Guardar cuenta</Button>
        </fieldset>
      </form>
      <Credentials
        scope="channel"
        owner={`application:${account.application_id}`}
        onChanged={done}
        kinds={[
          {
            id: account.channel === "tiktok" ? "client_secret" : "app_secret",
            label:
              account.channel === "tiktok" ? "Client Secret" : "App Secret",
          },
        ]}
      />
      <Credentials
        scope="channel"
        owner={`integration:${account.id}`}
        onChanged={done}
        kinds={[
          {
            id:
              ["instagram", "facebook", "messenger"].includes(
                account.channel,
              ) && account.issuer_profile !== "instagram_login"
                ? "page_access_token"
                : "access_token",
            label:
              ["instagram", "facebook", "messenger"].includes(
                account.channel,
              ) && account.issuer_profile !== "instagram_login"
                ? "Page Access Token"
                : "Access Token",
          },
          ...(account.provider_operations_available &&
          account.issuer_profile === "facebook_login"
            ? [{ id: "access_token", label: "User Access Token" }]
            : []),
          ...(account.provider_operations_available &&
          account.channel === "tiktok"
            ? [{ id: "refresh_token", label: "Refresh Token" }]
            : []),
        ]}
      />
      {account.provider_operations_available ? (
        <>
          <Notice>
            {dirty
              ? "Guarda la configuración antes de ejecutar acciones de conexión."
              : "Las acciones utilizan la configuración guardada de esta cuenta."}
          </Notice>
          <fieldset disabled={dirty || task.busy}>
            <ChannelOperations
              account={account}
              done={done}
              returnedOAuth={returnedOAuth}
              initialWebhook={initialWebhook}
            />
          </fieldset>
        </>
      ) : (
        <section className="panel">
          <h3>Verificación y conexión</h3>
          <p>
            Estas acciones consultan al proveedor y requieren la integración
            operativa del canal.
          </p>
          <div className="institution-actions">
            {[
              "Conectar con OAuth",
              "Verificar token",
              ...(account.channel === "whatsapp"
                ? ["Verificar número", "Registrar número"]
                : []),
              "Sincronizar cuenta",
            ].map((label) => (
              <Button
                key={label}
                disabled
                title="La integración del proveedor todavía no está habilitada."
              >
                {label}
              </Button>
            ))}
          </div>
        </section>
      )}
      <section className="panel">
        <h3>Webhooks</h3>
        <p>
          Los canales y Ajustes utilizan el mismo endpoint y las mismas claves
          de verificación.
        </p>
        <Button
          variant="secondary"
          disabled={!session.actions.includes("settings.webhooks.read")}
          onClick={openWebhooks}
        >
          Administrar webhooks
        </Button>
      </section>
    </>
  );
}
type Endpoint = {
  id: string;
  key: string;
  provider: string;
  callback_url: string;
  requested_active: boolean;
  signature_required: boolean;
  actual_active: boolean;
  integration_ids: string[];
};

export function ChannelWebhooks() {
  const { session } = useInstitution();
  if (!session.actions.includes("settings.channels.read"))
    return <Notice>Para generar un webhook necesitas acceso a Canales.</Notice>;
  return (
    <ErrorFeedback explain={explainChannelError}>
      <ChannelWebhookChooser />
    </ErrorFeedback>
  );
}

function ChannelWebhookChooser() {
  const data = useResource<{ items: Channel[] }>("channels");
  const [selected, setSelected] = useState("");
  if (!data.value) return <ResourceState error={data.error} />;
  const accounts = data.value.items.filter(
    (row) => row.verified_status !== "retired" && !row.synthetic_demo,
  );
  const account = accounts.find((row) => row.id === selected);
  return (
    <section className="panel institution-webhook">
      <h3>Webhooks por cuenta</h3>
      <SelectField
        id="webhook-channel-account"
        label="Cuenta para el webhook"
        value={selected}
        options={[
          { value: "", label: "Selecciona una cuenta" },
          ...accounts.map((row) => {
            const channel = channelNames[row.channel];
            const name = row.display_name;
            return {
              value: row.id,
              label: name.toLowerCase().startsWith(channel.toLowerCase())
                ? name
                : `${channel} · ${name}`,
            };
          }),
        ]}
        onChange={(e) => {
          if (allowNavigation()) setSelected(e.target.value);
        }}
      />
      {data.error && <Notice error>{data.error}</Notice>}
      {account && (
        <ChannelWebhook key={account.id} account={account} done={data.reload} />
      )}
    </section>
  );
}

export function Webhooks() {
  const { session, call } = useInstitution(),
    data = useResource<{ items: Endpoint[]; revision: number }>("webhooks"),
    channels = useResource<{ items: Channel[] }>("channels"),
    task = useTask(),
    intent = useIntent();
  const [account, setAccount] = useState(""),
    [url, setUrl] = useState(""),
    [once, setOnce] = useState<string[]>([]);
  useDraftGuard(!!account || !!url);
  if (!data.value) return <ResourceState error={data.error} />;
  const accounts = channels.value?.items ?? [];
  const selected = accounts.find((row) => row.id === account),
    writable = session.actions.includes("settings.webhooks.write");
  return (
    <>
      <Notice>
        El endpoint conserva una identidad única y firma obligatoria. La
        recepción pública de eventos permanece deshabilitada hasta habilitar la
        integración de canales.
      </Notice>
      {task.notices}
      {once.length > 0 && (
        <OneTime
          title="Claves de webhook"
          values={once}
          clear={() => setOnce([])}
        />
      )}
      {channels.error && (
        <Notice>
          Para crear endpoints o cambiar sus cuentas vinculadas necesitas
          permiso para consultar Canales. Puedes consultar los webhooks
          existentes.
        </Notice>
      )}
      <form
        className="panel"
        onSubmit={(event) => {
          event.preventDefault();
          if (!selected) return;
          void task.run(async () => {
            const body = {
              provider: selected.channel === "tiktok" ? "tiktok" : "meta",
              integration_ids: [selected.id],
              callback_url: url,
              signature_required: true,
            };
            const result = await call<{
              verify_token_once?: string;
              signature_secret_once?: string;
              secrets_already_issued?: boolean;
            }>("webhooks", "POST", { ...body, operation_id: intent.get(body) });
            intent.clear();
            if (result.secrets_already_issued) {
              await data.reload();
              throw new Error(
                "El endpoint ya se creó. Por seguridad, las claves no vuelven a mostrarse; puedes generar otras con Rotar claves.",
              );
            }
            setOnce(
              [result.verify_token_once, result.signature_secret_once].filter(
                (v): v is string => !!v,
              ),
            );
            setUrl("");
            setAccount("");
            await data.reload();
          });
        }}
      >
        <h3>Crear webhook</h3>
        <fieldset disabled={!writable || task.busy}>
          <SelectField
            id="endpoint-account"
            label="Cuenta del canal"
            options={[
              { value: "", label: "Selecciona una cuenta" },
              ...accounts.map((row) => ({
                value: row.id,
                label: `${row.display_name} · ${channelNames[row.channel]}`,
              })),
            ]}
            value={account}
            required
            onChange={(event) => setAccount(event.target.value)}
          />
          <Field
            id="endpoint-url"
            label="URL de callback"
            type="url"
            placeholder="https://"
            maxLength={2048}
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <Button type="submit" disabled={!selected}>
            Crear endpoint y claves
          </Button>
        </fieldset>
      </form>
      {data.value.items.map((endpoint) => (
        <EndpointEditor
          key={`${endpoint.id}-${data.value!.revision}`}
          endpoint={endpoint}
          all={data.value!}
          accounts={accounts}
          writable={writable}
          done={data.reload}
          onSecrets={setOnce}
        />
      ))}
    </>
  );
}
function EndpointEditor({
  endpoint,
  all,
  accounts,
  writable,
  done,
  onSecrets,
}: {
  endpoint: Endpoint;
  all: { items: Endpoint[]; revision: number };
  accounts: Channel[];
  writable: boolean;
  done: () => Promise<unknown>;
  onSecrets: (values: string[]) => void;
}) {
  const { call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [url, setUrl] = useState(endpoint.callback_url),
    [requested, setRequested] = useState(endpoint.requested_active),
    [ids, setIds] = useState(endpoint.integration_ids);
  useDraftGuard(
    url !== endpoint.callback_url ||
      requested !== endpoint.requested_active ||
      JSON.stringify(ids) !== JSON.stringify(endpoint.integration_ids),
  );
  return (
    <section className="panel">
      <h3>
        {endpoint.provider} · {endpoint.key}
      </h3>
      <Badge>
        {endpoint.actual_active ? "Activo" : "Recepción deshabilitada"}
      </Badge>
      {task.notices}
      <fieldset disabled={!writable || task.busy}>
        <Field
          id={`endpoint-url-${endpoint.id}`}
          label="URL de callback"
          type="url"
          maxLength={2048}
          value={url}
          onChange={(event) => setUrl(event.target.value)}
        />
        <label className="institution-check">
          <input
            type="checkbox"
            checked={requested}
            onChange={(event) => setRequested(event.target.checked)}
          />
          Solicitar activación al habilitar la integración
        </label>
        <p>Validación de firma: obligatoria.</p>
        {accounts
          .filter((row) =>
            endpoint.provider === "tiktok"
              ? row.channel === "tiktok"
              : row.channel !== "tiktok",
          )
          .map((row) => (
            <label className="institution-check" key={row.id}>
              <input
                type="checkbox"
                checked={ids.includes(row.id)}
                onChange={(event) =>
                  setIds(
                    event.target.checked
                      ? [...ids, row.id]
                      : ids.filter((id) => id !== row.id),
                  )
                }
              />
              {row.display_name}
            </label>
          ))}
        <div className="institution-actions">
          <Button
            onClick={() =>
              void task.run(async () => {
                const endpoints = all.items.map((item) => ({
                  key: item.key,
                  provider: item.provider,
                  callback_url:
                    item.id === endpoint.id ? url : item.callback_url,
                  requested_active:
                    item.id === endpoint.id ? requested : item.requested_active,
                  signature_required: true,
                  integration_ids:
                    item.id === endpoint.id ? ids : item.integration_ids,
                }));
                const body = {
                  revision: all.revision,
                  document: { endpoints },
                };
                await call("settings/webhooks", "PUT", {
                  ...body,
                  operation_id: intent.get(body),
                });
                await done();
              })
            }
          >
            Guardar webhook
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              if (
                window.confirm(
                  "¿Generar nuevas claves? Las anteriores dejarán de ser válidas.",
                )
              )
                void task.run(async () => {
                  const result = await call<{
                    verify_token_once?: string;
                    signature_secret_once?: string;
                    secrets_already_issued?: boolean;
                  }>(`webhooks/${endpoint.id}/rotate`, "POST", {
                    operation_id: intent.get({
                      rotate: endpoint.id,
                      revision: all.revision,
                    }),
                  });
                  intent.clear();
                  if (result.secrets_already_issued)
                    throw new Error(
                      "Estas claves ya se generaron. Si no pudiste guardarlas, vuelve a solicitar Rotar claves para reemplazarlas.",
                    );
                  onSecrets(
                    [
                      result.verify_token_once,
                      result.signature_secret_once,
                    ].filter((v): v is string => !!v),
                  );
                  await done();
                });
            }}
          >
            Rotar claves
          </Button>
        </div>
      </fieldset>
      <Credentials
        scope="webhook"
        owner={`endpoint:${endpoint.id}`}
        kinds={[
          { id: "verify_token", label: "Token de verificación" },
          { id: "webhook_secret", label: "Secreto de firma" },
        ]}
      />
    </section>
  );
}
