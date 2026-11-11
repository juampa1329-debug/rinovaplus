import { useEffect, useState, type FormEvent } from "react";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../shared/ui";
import {
  channelKeys,
  channelReferences,
  channelRequest,
  channelStates,
  type ChannelAccount,
  type ChannelKey,
} from "../shared/channels";

type SocialComment = {
  id: string;
  channel: ChannelKey;
  body: string;
  receivedAt: string;
};
type TransportStatus = {
  queued: number;
  failed: number;
  uncertain: number;
  receiptsFailed: number;
  lastError: string | null;
};
const emptyAccount = (channel: ChannelKey): ChannelAccount => ({
  channel,
  configuration: {},
  state: "unconfigured",
  revision: 0,
  capabilities: {},
  credentials: [],
  lastError: null,
  verifiedAt: null,
});

export function ChannelSettings({
  focusedChannel,
}: { focusedChannel?: ChannelKey } = {}) {
  const [accounts, setAccounts] = useState<ChannelAccount[]>([]);
  const [expanded, setExpanded] = useState<ChannelKey | null>(
    focusedChannel ?? null,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [stages, setStages] = useState<string[]>([]);
  const [comments, setComments] = useState<SocialComment[]>([]);
  const [transport, setTransport] = useState<TransportStatus | null>(null);
  const [replying, setReplying] = useState<string | null>(null);

  async function load(signal?: AbortSignal) {
    const result = await channelRequest<{ channels: ChannelAccount[] }>(
      "/api/v1/channels",
      "GET",
      undefined,
      signal,
    );
    setAccounts(result.channels);
    const [config, social, status] = await Promise.allSettled([
      channelRequest<{
        config: { stages: { label: string; active: boolean }[] };
      }>("/api/local/crm/configuration", "GET", undefined, signal),
      channelRequest<{ comments: SocialComment[] }>(
        "/api/v1/social-comments",
        "GET",
        undefined,
        signal,
      ),
      channelRequest<TransportStatus>(
        "/api/v1/channels/transport/status",
        "GET",
        undefined,
        signal,
      ),
    ]);
    if (config.status === "fulfilled")
      setStages(
        config.value.config.stages.filter((s) => s.active).map((s) => s.label),
      );
    if (social.status === "fulfilled") setComments(social.value.comments);
    if (status.status === "fulfilled") setTransport(status.value);
  }
  useEffect(() => {
    const controller = new AbortController();
    setBusy("load");
    load(controller.signal)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(null);
      });
    return () => controller.abort();
  }, []);

  async function run(key: string, action: () => Promise<void>) {
    setBusy(key);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No se pudo completar la operación.",
      );
    } finally {
      setBusy(null);
    }
  }
  function update(account: ChannelAccount) {
    setAccounts((rows) => [
      ...rows.filter((r) => r.channel !== account.channel),
      account,
    ]);
  }
  async function save(
    form: HTMLFormElement,
    account: ChannelAccount,
    connect = false,
  ) {
    if (!form.reportValidity()) return;
    await run(account.channel, async () => {
      const data = new FormData(form);
      const configuration = Object.fromEntries(
        [
          "appId",
          "wabaId",
          "phoneNumberId",
          "pageId",
          "accountId",
          "apiVersion",
          "instagramLogin",
          "callbackUrl",
          "initialStage",
          "environment",
        ].map((name) => [
          name,
          String(
            data.get(name) ||
              (name === "instagramLogin"
                ? "facebook"
                : name === "environment"
                  ? "production"
                  : ""),
          ),
        ]),
      );
      const secrets = Object.fromEntries(
        ["accessToken", "appSecret", "verifyToken", "refreshToken"].map(
          (name) => [name, String(data.get(name) || "")],
        ),
      );
      const stored = await channelRequest<ChannelAccount>(
        `/api/v1/channels/${account.channel}/draft`,
        "PUT",
        { revision: account.revision, configuration, ...secrets },
      );
      for (const name of Object.keys(secrets)) {
        const input = form.elements.namedItem(name);
        if (input instanceof HTMLInputElement) input.value = "";
      }
      update(stored);
      if (connect) {
        update(
          await channelRequest<ChannelAccount>(
            `/api/v1/channels/${account.channel}/activation`,
            "POST",
          ),
        );
        setNotice(
          "La plataforma confirmó el acceso y la suscripción. Registra también los campos del webhook en su panel; la recepción se confirmará con el primer evento firmado.",
        );
      } else
        setNotice(
          "Configuración guardada correctamente.",
        );
    });
  }
  function submit(event: FormEvent<HTMLFormElement>, account: ChannelAccount) {
    event.preventDefault();
    void save(event.currentTarget, account);
  }
  function generateToken(form: HTMLFormElement | null, name: string) {
    const input = form?.elements.namedItem(name);
    if (input instanceof HTMLInputElement) {
      input.value = Array.from(
        crypto.getRandomValues(new Uint8Array(32)),
        (n) => n.toString(16).padStart(2, "0"),
      ).join("");
      input.type = "text";
      input.focus();
      input.select();
    }
  }
  async function copyToken(form: HTMLFormElement | null) {
    const input = form?.elements.namedItem("verifyToken");
    if (!(input instanceof HTMLInputElement) || !input.value) {
      setError(
        "Genera o ingresa el token antes de copiarlo. Los valores guardados no se vuelven a mostrar.",
      );
      return;
    }
    try {
      await navigator.clipboard.writeText(input.value);
      setNotice("Token copiado. Pégalo en el panel de Meta antes de guardar.");
    } catch {
      input.type = "text";
      input.focus();
      input.select();
      setNotice(
        "El navegador bloqueó el portapapeles. Copia el token seleccionado con Ctrl+C.",
      );
    }
  }
  async function numberAction(
    form: HTMLFormElement | null,
    action: "request" | "verify" | "register",
  ) {
    if (!form) return;
    const values = new FormData(form);
    await run("whatsapp", async () => {
      const code = String(
        values.get(
          action === "register" ? "registrationPin" : "verificationCode",
        ) || "",
      );
      if (action !== "request" && !/^[0-9]{6}$/.test(code))
        throw new Error("Ingresa un código de seis dígitos.");
      const result =
        action === "register"
          ? await channelRequest<{ registered: boolean }>(
              "/api/v1/channels/whatsapp/number-registration",
              "POST",
              { pin: code },
            )
          : await channelRequest<{ success: boolean }>(
              "/api/v1/channels/whatsapp/number-verification",
              "POST",
              {
                action,
                method: String(values.get("verificationMethod") || "SMS"),
                locale: "es_CO",
                code: action === "verify" ? code : "",
              },
            );
      if (!("registered" in result ? result.registered : result.success))
        throw new Error(
          "Meta no confirmó la operación. Revisa el estado del número en WhatsApp Manager.",
        );
      const field = form.elements.namedItem(
        action === "register" ? "registrationPin" : "verificationCode",
      );
      if (field instanceof HTMLInputElement) field.value = "";
      setNotice(
        action === "request"
          ? "Meta aceptó la solicitud del código de verificación."
          : action === "verify"
            ? "Meta confirmó la verificación del número."
            : "Meta confirmó el registro del número en Cloud API.",
      );
    });
  }
  return (
    <div className="channel-settings">
      {!focusedChannel && (
        <div className="configuration-row">
          <div>
            <h3>Conecta los canales de admisiones</h3>
            <p>
              Carga las credenciales y administra las conexiones desde esta
              aplicación.
            </p>
          </div>
          <Button
            variant="secondary"
            disabled={!!busy}
            onClick={() => void run("load", () => load())}
          >
            {busy === "load" ? "Actualizando…" : "Actualizar estado"}
          </Button>
        </div>
      )}
      {error && <Notice error>{error}</Notice>}
      {notice && <Notice>{notice}</Notice>}
      {channelKeys
        .filter((key) => !focusedChannel || key === focusedChannel)
        .map((key) => {
          const account =
            accounts.find((a) => a.channel === key) || emptyAccount(key);
          const config = account.configuration;
          const opened = expanded === key;
          const callbackPath = `/api/v1/webhooks/${key === "tiktok" ? "tiktok" : "meta"}`;
          return (
            <section
              className="channel-section"
              key={key}
              aria-labelledby={`channel-heading-${key}`}
            >
              <div className="configuration-row">
                <div>
                  <h3 id={`channel-heading-${key}`}>
                    {channelReferences[key].name}
                  </h3>
                  <p>{channelReferences[key].purpose}</p>
                  <Badge>{channelStates[account.state] || account.state}</Badge>
                </div>
                <Button
                  variant={opened ? "secondary" : "primary"}
                  aria-expanded={opened}
                  aria-controls={`channel-form-${key}`}
                  onClick={() => {
                    setExpanded(opened ? null : key);
                    setNotice("");
                  }}
                >
                  {opened
                    ? "Cerrar configuración"
                    : account.revision
                      ? "Administrar"
                      : "Conectar"}
                </Button>
              </div>
              {opened && (
                <form
                  id={`channel-form-${key}`}
                  key={`${key}-${account.revision}`}
                  onSubmit={(e) => submit(e, account)}
                  className="channel-connection-form"
                  autoComplete="off"
                >
                  <div className="form-grid">
                    <Field
                      id={`${key}-appId`}
                      name="appId"
                      label={
                        key === "tiktok"
                          ? "TikTok App ID / Client Key"
                          : "Meta App ID"
                      }
                      defaultValue={config.appId || ""}
                      maxLength={128}
                      required={key !== "whatsapp"}
                      hint={
                        key === "whatsapp"
                          ? "Opcional para guardar y validar el token. Obligatorio para activar webhooks."
                          : undefined
                      }
                    />
                    {key !== "tiktok" && (
                      <Field
                        id={`${key}-apiVersion`}
                        name="apiVersion"
                        label="Versión Graph API"
                        defaultValue={config.apiVersion || ""}
                        placeholder="vXX.0"
                        pattern="v[0-9]{1,2}\.0"
                        required={key !== "whatsapp"}
                        hint={
                          key === "whatsapp"
                            ? "Opcional: al validar se guardará la versión informada por Meta, si está disponible. También puedes ingresar la versión indicada en tu panel."
                            : "Usa la versión habilitada en tu aplicación de Meta."
                        }
                      />
                    )}
                    {key === "whatsapp" && (
                      <>
                        <SelectField
                          id="whatsapp-environment"
                          name="environment"
                          label="Entorno de la conexión"
                          defaultValue={config.environment || "production"}
                          options={[
                            { value: "production", label: "Producción" },
                            {
                              value: "development",
                              label: "Alterno",
                            },
                          ]}
                        />
                        <Field
                          id={`${key}-wabaId`}
                          name="wabaId"
                          label="WhatsApp Business Account ID (WABA)"
                          defaultValue={config.wabaId || ""}
                          inputMode="numeric"
                          pattern="[0-9]+"
                          required
                        />
                        <Field
                          id={`${key}-phoneNumberId`}
                          name="phoneNumberId"
                          label="Phone Number ID"
                          defaultValue={config.phoneNumberId || ""}
                          inputMode="numeric"
                          pattern="[0-9]+"
                          required
                        />
                      </>
                    )}
                    {(key === "facebook" || key === "messenger") && (
                      <Field
                        id={`${key}-pageId`}
                        name="pageId"
                        label="Facebook Page ID"
                        defaultValue={config.pageId || ""}
                        inputMode="numeric"
                        pattern="[0-9]+"
                        required
                      />
                    )}
                    {(key === "instagram" || key === "tiktok") && (
                      <Field
                        id={`${key}-accountId`}
                        name="accountId"
                        label={
                          key === "instagram"
                            ? "Instagram Professional Account ID"
                            : "Business ID (Open ID de la cuenta autorizada)"
                        }
                        defaultValue={config.accountId || ""}
                        required
                        maxLength={128}
                      />
                    )}
                    {key === "instagram" && (
                      <SelectField
                        id={`${key}-instagramLogin`}
                        name="instagramLogin"
                        label="Producto de autenticación"
                        defaultValue={config.instagramLogin || "facebook"}
                        options={[
                          {
                            value: "facebook",
                            label: "Instagram API con Facebook Login",
                          },
                          {
                            value: "instagram",
                            label: "Instagram API con Instagram Login",
                          },
                        ]}
                      />
                    )}
                    <Field
                      id={`${key}-accessToken`}
                      name="accessToken"
                      type="password"
                      autoComplete="new-password"
                      label={
                        key === "facebook" || key === "messenger"
                          ? "Page Access Token"
                          : "Access Token"
                      }
                      placeholder={
                        account.credentials.includes("accessToken")
                          ? "Guardado · deja vacío para conservarlo"
                          : "Pega el token de la plataforma"
                      }
                      maxLength={12000}
                    />
                    <Field
                      id={`${key}-appSecret`}
                      name="appSecret"
                      type="password"
                      autoComplete="new-password"
                      label="App Secret"
                      placeholder={
                        account.credentials.includes("appSecret")
                          ? "Guardado · deja vacío para conservarlo"
                          : "Secreto de la aplicación"
                      }
                      maxLength={4096}
                    />
                    {key !== "tiktok" && (
                      <>
                        <Field
                          id={`${key}-verifyToken`}
                          name="verifyToken"
                          type="password"
                          autoComplete="new-password"
                          label="Token de verificación del webhook"
                          placeholder={
                            account.credentials.includes("verifyToken")
                              ? "Guardado · deja vacío para conservarlo"
                              : "Crea un token y regístralo en la plataforma"
                          }
                          maxLength={4096}
                          hint="Copia este token al panel de Meta antes de guardar; no se volverá a mostrar."
                        />
                        <div className="actions">
                          <Button
                            variant="secondary"
                            onClick={(e) =>
                              generateToken(e.currentTarget.form, "verifyToken")
                            }
                          >
                            Generar token de verificación
                          </Button>
                          <Button
                            variant="secondary"
                            onClick={(e) =>
                              void copyToken(e.currentTarget.form)
                            }
                          >
                            Copiar token
                          </Button>
                        </div>
                      </>
                    )}
                    <Field
                      id={`${key}-callbackUrl`}
                      name="callbackUrl"
                      type="url"
                      label="Callback HTTPS público"
                      defaultValue={config.callbackUrl || ""}
                      placeholder={`https://tu-dominio${callbackPath}`}
                      maxLength={2048}
                      hint={`Ruta de callback: ${callbackPath}.`}
                    />
                    <SelectField
                      id={`${key}-initialStage`}
                      name="initialStage"
                      label="Etapa inicial del aspirante"
                      defaultValue={config.initialStage || ""}
                      options={[
                        {
                          value: "",
                          label: "Selecciona una etapa activa del CRM",
                        },
                        ...stages,
                      ]}
                    />
                  </div>
                  {!stages.length && (
                    <Notice>
                      Crea una etapa activa en la configuración del CRM para que
                      los eventos recibidos puedan crear aspirantes.
                    </Notice>
                  )}
                  {key === "whatsapp" && (
                    <Notice>
                      Para comenzar, guarda el Access Token, WABA ID y Phone
                      Number ID y pulsa Validar acceso. App ID, App Secret,
                      token de verificación y callback HTTPS se necesitan
                      después para activar webhooks.
                    </Notice>
                  )}
                  {key === "whatsapp" &&
                    config.environment === "development" && (
                      <p>
                        Perfil alterno seleccionado por el operador.
                      </p>
                    )}
                  <p>
                    {key === "tiktok"
                      ? "Autoriza la cuenta en TikTok for Business y pega aquí su token. La conexión registra las suscripciones de mensajes y comentarios mediante la API Business."
                      : `En Meta for Developers, registra el callback HTTPS y el mismo token de verificación. Suscribe los campos ${key === "whatsapp" ? "messages de WhatsApp Business Account" : key === "facebook" ? "feed de la página" : key === "messenger" ? "messages, messaging_postbacks, message_deliveries y message_reads de la página" : "messages, messaging_postbacks y comments de Instagram"}. Después guarda y conecta el canal.`}
                  </p>
                  <p>
                    <a
                      href={
                        key === "tiktok"
                          ? "https://business-api.tiktok.com/portal/"
                          : "https://developers.facebook.com/apps/"
                      }
                      target="_blank"
                      rel="noreferrer"
                    >
                      Abrir panel de{" "}
                      {key === "tiktok"
                        ? "TikTok for Business"
                        : "Meta for Developers"}
                    </a>
                  </p>
                  {key === "tiktok" && (
                    <p>
                      Requiere acceso aprobado a TikTok Business Messaging.
                      Login Kit o una cuenta de anuncios por sí solos no
                      habilitan mensajes.
                    </p>
                  )}
                  <p>
                    Los campos secretos vacíos conservan los valores guardados.
                    Para cambiar las credenciales, ingresa sus nuevos valores y
                    guarda.
                  </p>
                  <div className="actions">
                    <Button type="submit" variant="secondary" disabled={!!busy}>
                      {busy === key ? "Procesando…" : "Guardar datos"}
                    </Button>
                    <Button
                      disabled={!!busy}
                      onClick={(e) => {
                        if (e.currentTarget.form)
                          void save(e.currentTarget.form, account, true);
                      }}
                    >
                      Guardar y conectar
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={!!busy || !account.revision}
                      onClick={() =>
                        void run(key, async () => {
                          update(
                            await channelRequest<ChannelAccount>(
                              `/api/v1/channels/${key}/discovery`,
                              "POST",
                            ),
                          );
                          setNotice(
                            "La plataforma confirmó el acceso al recurso configurado.",
                          );
                        })
                      }
                    >
                      Validar acceso
                    </Button>
                    {account.revision > 0 && (
                      <Button
                        variant="quiet"
                        disabled={!!busy}
                        onClick={() =>
                          void run(key, async () => {
                            update(
                              await channelRequest<ChannelAccount>(
                                `/api/v1/channels/${key}/pause`,
                                "POST",
                              ),
                            );
                            setNotice(
                              "Canal pausado. Los mensajes pendientes se conservan sin enviar.",
                            );
                          })
                        }
                      >
                        Pausar
                      </Button>
                    )}
                  </div>
                  {account.capabilities.asset && (
                    <p>
                      Recurso confirmado:{" "}
                      {account.capabilities.asset.name ||
                        account.capabilities.asset.username ||
                        account.capabilities.asset.verified_name ||
                        account.capabilities.asset.id}
                      {account.capabilities.asset.display_phone_number
                        ? ` · ${account.capabilities.asset.display_phone_number}`
                        : ""}
                    </p>
                  )}
                  {account.verifiedAt && (
                    <p>
                      Última validación:{" "}
                      {new Date(account.verifiedAt).toLocaleString("es-CO")}
                    </p>
                  )}
                  {key === "whatsapp" && (
                    <details>
                      <summary>Verificar o registrar un número nuevo</summary>
                      <p>
                        Usa estas acciones únicamente si WhatsApp Manager indica
                        que el número necesita verificación o registro. Guarda
                        primero sus identificadores y credenciales.
                      </p>
                      <div className="form-grid">
                        <SelectField
                          id="whatsapp-verification-method"
                          name="verificationMethod"
                          label="Recibir código por"
                          options={["SMS", "VOICE"]}
                        />
                        <Field
                          id="whatsapp-verification-code"
                          name="verificationCode"
                          label="Código recibido"
                          autoComplete="one-time-code"
                          inputMode="numeric"
                          pattern="[0-9]{6}"
                          maxLength={6}
                        />
                        <Field
                          id="whatsapp-registration-pin"
                          name="registrationPin"
                          label="PIN de verificación en dos pasos"
                          type="password"
                          autoComplete="new-password"
                          inputMode="numeric"
                          pattern="[0-9]{6}"
                          maxLength={6}
                          hint="Se transmite únicamente a Meta durante el registro; no se guarda."
                        />
                      </div>
                      <div className="actions">
                        <Button
                          variant="secondary"
                          disabled={!!busy || !account.revision}
                          onClick={(e) =>
                            void numberAction(e.currentTarget.form, "request")
                          }
                        >
                          Solicitar código
                        </Button>
                        <Button
                          variant="secondary"
                          disabled={!!busy || !account.revision}
                          onClick={(e) =>
                            void numberAction(e.currentTarget.form, "verify")
                          }
                        >
                          Verificar código
                        </Button>
                        <Button
                          variant="secondary"
                          disabled={!!busy || !account.revision}
                          onClick={(e) =>
                            void numberAction(e.currentTarget.form, "register")
                          }
                        >
                          Registrar número
                        </Button>
                      </div>
                    </details>
                  )}
                </form>
              )}
            </section>
          );
        })}
      {!focusedChannel && (
        <>
          <section className="channel-section">
            <h3>Recepción y envíos</h3>
            {transport ? (
              <>
                <p>
                  En cola: {transport.queued} · Fallidos: {transport.failed} ·
                  Resultado incierto: {transport.uncertain} · Recibos pendientes
                  de atención: {transport.receiptsFailed}
                </p>
                {transport.lastError && (
                  <Notice error>
                    {transport.lastError === "initial_crm_stage_required"
                      ? "Configura la etapa inicial del canal y reprocesa los recibos."
                      : "Hay eventos o envíos que requieren atención. Revisa los permisos y la configuración del canal."}
                  </Notice>
                )}
                {transport.receiptsFailed > 0 && (
                  <Button
                    disabled={!!busy}
                    variant="secondary"
                    onClick={() =>
                      void run("receipts", async () => {
                        await channelRequest(
                          "/api/v1/channels/transport/retry-receipts",
                          "POST",
                        );
                        await load();
                        setNotice(
                          "Recibos fallidos devueltos a la cola de ingesta.",
                        );
                      })
                    }
                  >
                    Reprocesar recibos
                  </Button>
                )}
              </>
            ) : (
              <p>Actualice el estado para consultar las colas.</p>
            )}
          </section>
          <section className="channel-section">
            <h3>Comentarios sociales</h3>
            {comments.length === 0 ? (
              <p>
                Los comentarios recibidos de las cuentas conectadas aparecerán
                aquí.
              </p>
            ) : (
              comments.map((comment) => (
                <article className="channel-comment" key={comment.id}>
                  <Badge>{channelReferences[comment.channel].name}</Badge>
                  <p>{comment.body}</p>
                  <Button
                    variant="secondary"
                    onClick={() =>
                      setReplying(replying === comment.id ? null : comment.id)
                    }
                  >
                    {replying === comment.id ? "Cerrar respuesta" : "Responder"}
                  </Button>
                  {replying === comment.id && (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        const form = e.currentTarget;
                        const data = new FormData(form);
                        void run(comment.id, async () => {
                          await channelRequest(
                            `/api/v1/social-comments/${comment.id}/reply`,
                            "POST",
                            {
                              operationId: crypto.randomUUID(),
                              body: String(data.get("body") || ""),
                              mode: String(data.get("mode") || "public"),
                            },
                          );
                          form.reset();
                          setReplying(null);
                          setNotice(
                            "Respuesta encolada. El despachador enviará el mensaje y registrará el resultado.",
                          );
                          await load();
                        });
                      }}
                    >
                      <TextArea
                        id={`reply-${comment.id}`}
                        name="body"
                        label="Respuesta"
                        required
                        maxLength={4000}
                      />
                      <SelectField
                        id={`reply-mode-${comment.id}`}
                        name="mode"
                        label="Tipo de respuesta"
                        options={[
                          { value: "public", label: "Comentario público" },
                          ...(comment.channel === "instagram"
                            ? [
                                {
                                  value: "private",
                                  label: "Invitación por mensaje privado",
                                },
                              ]
                            : []),
                        ]}
                      />
                      <Button type="submit" disabled={!!busy}>
                        Encolar respuesta
                      </Button>
                    </form>
                  )}
                </article>
              ))
            )}
          </section>
        </>
      )}
    </div>
  );
}
