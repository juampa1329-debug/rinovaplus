import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Field, Notice, SelectField } from "../shared/ui";
import type { Channel } from "./Channels";
import { Credentials, ResourceState, useResource } from "./Settings";
import { ApiError, useInstitution, useIntent, useTask } from "./api";
import { useDraftGuard } from "./drafts";
import { OperationDialog } from "./ErrorFeedback";

const scopes: Record<string, string[]> = {
  meta_whatsapp: [
    "whatsapp_business_management",
    "whatsapp_business_messaging",
    "business_management",
  ],
  facebook_login: [
    "pages_show_list",
    "pages_manage_metadata",
    "pages_read_engagement",
    "pages_manage_engagement",
    "pages_messaging",
    "instagram_basic",
    "instagram_manage_comments",
    "instagram_manage_messages",
  ],
  instagram_login: [
    "instagram_business_basic",
    "instagram_business_manage_messages",
    "instagram_business_manage_comments",
  ],
  tiktok_login_kit: ["user.info.basic"],
};
const stateLabels: Record<string, string> = {
  confirmed: "Confirmado por el proveedor",
  running: "En curso",
  pending: "Pendiente",
};

type OAuthStatus = { status: string; code?: string | null };
type OAuthAsset = { id: string; name: string; external_id: string; kind: string };
type OAuthResult = OAuthStatus & { items: OAuthAsset[] };
type OAuthNotice = {
  title: string;
  detail: string;
  nextStep?: string;
  success?: boolean;
  showChoices?: boolean;
};

function oauthMessage(result: OAuthStatus, assetPrompt: string) {
  if (result.status === "assets_ready") return assetPrompt;
  if (result.status === "completed") return "La autorización ya se aplicó a esta cuenta.";
  if (result.status === "pending")
    return "Completa el inicio de sesión en la otra pestaña. RinovaPlus está esperando la autorización.";
  if (result.status === "exchanging")
    return "RinovaPlus recibió la autorización y está consultando las cuentas.";
  if (result.status === "cancelled")
    return "El inicio de sesión terminó sin conceder acceso. Vuelve a conectar la cuenta.";
  if (result.status === "expired")
    return "La autorización venció. Inicia una conexión nueva.";
  if (result.status === "uncertain" && result.code !== "oauth_authority_or_configuration_changed")
    return "RinovaPlus no pudo confirmar el resultado de la consulta. Revisa Actividad y recuperación y vuelve a conectar si el intento sigue sin confirmarse.";
  if (result.code === "meta_app_secret_rejected")
    return "Meta rechazó el App Secret. En Meta Developers, copia el secreto vigente de esta app y guárdalo en Credenciales. Después vuelve a conectar la cuenta.";
  if (result.code === "oauth_code_exchange_rejected")
    return "Meta rechazó el código de autorización. Revisa que la URL de retorno de OAuth coincida con la registrada en la app de Meta y vuelve a conectar.";
  if (result.code === "oauth_assets_missing")
    return "El proveedor no devolvió cuentas autorizadas. Revisa que el perfil de inicio de sesión tenga acceso a la cuenta que quieres conectar y vuelve a conectar.";
  if (result.code === "oauth_provider_rejected")
    return "El proveedor rechazó la consulta de OAuth. Revisa los permisos de la app antes de volver a conectar.";
  if (result.code === "token_application_mismatch_or_invalid")
    return "Meta no pudo validar el token para esta app. Revisa el App ID y usa el perfil autorizado.";
  if (result.code === "oauth_authority_or_configuration_changed")
    return "Cambió tu sesión o la configuración de la app durante la autorización. Confirma tu identidad e inicia una conexión nueva.";
  return "RinovaPlus no pudo completar la autorización. Vuelve a conectar la cuenta.";
}

export function ChannelOperations({
  account,
  done,
  returnedOAuth,
  initialWebhook,
}: {
  account: Channel;
  done: () => Promise<unknown>;
  returnedOAuth?: string;
  initialWebhook?: IssuedWebhook;
}) {
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const options = useResource<{ stages: { key: string; label: string }[] }>(
    "channels/routing-options",
  );
  const [pin, setPin] = useState(""),
    [stage, setStage] = useState(account.initial_stage_key || ""),
    [diagnosis, setDiagnosis] = useState(""),
    [synced, setSynced] = useState<{
      wabaId: unknown;
      numbers: { id: string; display_phone_number?: string; verified_name?: string }[];
      hasMoreNumbers?: boolean;
    } | null>(null),
    [oauth, setOauth] = useState(returnedOAuth || ""),
    [authUrl, setAuthUrl] = useState(""),
    [assets, setAssets] = useState<OAuthAsset[]>([]),
    [oauthNotice, setOAuthNotice] = useState<OAuthNotice | null>(null);
  const lastNotice = useRef("");
  const choices = useRef<HTMLDivElement>(null);
  const oauthSection = useRef<HTMLDetailsElement>(null);
  useDraftGuard(!!pin || stage !== (account.initial_stage_key || ""));
  const writable =
      session.actions.includes("settings.channels.write") &&
      !account.synthetic_demo,
    hookReadable = session.actions.includes("settings.webhooks.read");
  const pageOAuth =
    account.issuer_profile === "facebook_login" &&
    ["facebook", "messenger"].includes(account.channel);
  const oauthProvider =
    account.issuer_profile === "facebook_login"
      ? "Facebook"
      : account.issuer_profile === "instagram_login"
        ? "Instagram"
        : account.issuer_profile === "meta_whatsapp"
          ? "Meta"
          : null;
  const assetPrompt = pageOAuth
    ? "Selecciona la página autorizada."
    : account.channel === "whatsapp"
      ? "Selecciona el número institucional autorizado."
      : "Selecciona la cuenta autorizada.";
  const whatsapp = account.channel === "whatsapp";
  const wabaId = account.fields["meta:whatsapp_business_account_id"];
  const phoneId = account.fields["meta:whatsapp_phone_number_id"];
  const syncResult = synced && synced.wabaId === wabaId ? synced : null;
  const confirmSaved = (name: string) => {
    setOAuthNotice({
      title: whatsapp ? "Número agregado a RinovaPlus" : "Cuenta agregada a RinovaPlus",
      detail: `Canal ${account.display_name} actualizado con ${name}.`,
      nextStep: "Pulsa «Verificar token y cuenta» para comprobar la conexión con el proveedor.",
      success: true,
    });
  };
  const applyOAuthResult = useCallback((result: OAuthResult) => {
    setAssets(result.items);
    const detail = oauthMessage(result, assetPrompt);
    setDiagnosis(detail);
    if (["pending", "exchanging"].includes(result.status)) return;
    setAuthUrl("");
    const key = `${oauth}:${result.status}:${result.code ?? ""}`;
    if (lastNotice.current === key) return;
    lastNotice.current = key;
    if (result.status === "assets_ready") {
      setOAuthNotice({
        title: whatsapp ? "Números de WhatsApp disponibles" : "Autorización completada",
        detail: "El proveedor autorizó el acceso. Elige qué quieres agregar a este canal.",
        nextStep: whatsapp
          ? "Pulsa «Usar este número» junto al número que quieres guardar."
          : pageOAuth
            ? "Pulsa «Usar esta página» junto a la página que quieres guardar."
            : "Pulsa «Usar esta cuenta» junto a la cuenta que quieres guardar.",
        success: true,
        showChoices: true,
      });
    } else {
      setOAuthNotice({
        title: result.status === "completed"
          ? "Autorización guardada"
          : result.status === "cancelled"
            ? "Autorización cancelada"
            : result.status === "expired"
              ? "Autorización vencida"
              : "No se pudo completar la autorización",
        detail,
        success: result.status === "completed",
      });
    }
  }, [assetPrompt, oauth, pageOAuth, whatsapp]);
  useEffect(() => {
    if (!oauth) return;
    const returned = oauth === returnedOAuth;
    if (!returned && (!oauthProvider || !authUrl)) return;
    let active = true;
    let loading = false;
    const onReturn = async () => {
      if (loading || (!returned && document.hidden)) return;
      loading = true;
      try {
        const result = await call<OAuthResult>(
          `channels/oauth/${oauth}/assets`,
        );
        if (!active) return;
        applyOAuthResult(result);
      } catch {
        if (active && returned && lastNotice.current !== `${oauth}:load-error`) {
          lastNotice.current = `${oauth}:load-error`;
          setOAuthNotice({
            title: "No se pudo consultar la autorización",
            detail: "RinovaPlus no pudo leer el resultado del inicio de sesión.",
            nextStep: "Pulsa «Consultar cuentas autorizadas» o inicia una conexión nueva.",
          });
        }
      } finally {
        loading = false;
      }
    };
    if (returned) void onReturn();
    else {
      window.addEventListener("focus", onReturn);
      document.addEventListener("visibilitychange", onReturn);
    }
    return () => {
      active = false;
      window.removeEventListener("focus", onReturn);
      document.removeEventListener("visibilitychange", onReturn);
    };
  }, [applyOAuthResult, oauthProvider, oauth, authUrl, call, returnedOAuth]);
  const perform = (action: string) =>
    void task.run(async () => {
      if (action === "numbers") setSynced(null);
      const payload = {
        row_version: account.row_version,
        ...(action === "register" ? { pin } : {}),
      };
      const result = await call<{
        status: string;
        code?: string;
        result: {
          numbers?: NonNullable<typeof synced>["numbers"];
          hasMoreNumbers?: boolean;
        };
      }>(`channels/${account.id}/actions/${action}`, "POST", {
        ...payload,
        operation_id: intent.get({ action, ...payload }),
      });
      setPin("");
      if (
        ["verify", "health", "numbers"].includes(action) ||
        (action === "subscribe" && account.channel === "whatsapp" && result.status === "confirmed") ||
        result.status === "failed"
      )
        intent.clear();
      if (result.status === "failed" || result.status === "uncertain") {
        setDiagnosis("");
        throw new ApiError(
          409,
          result.status === "uncertain"
            ? "provider_outcome_unknown"
            : result.code || "provider_operation_failed",
        );
      }
      if (action === "numbers" && result.status === "confirmed") {
        setDiagnosis("");
        setSynced({
          wabaId,
          numbers: result.result.numbers || [],
          hasMoreNumbers: result.result.hasMoreNumbers,
        });
        return;
      }
      if (action === "register" && result.status === "confirmed") {
        setOAuthNotice({
          title: "Número registrado en WhatsApp",
          detail: "Meta confirmó el registro del número en WhatsApp Cloud API.",
          nextStep: "Pulsa «Verificar token y cuenta» para comprobar el canal.",
          success: true,
        });
      }
      setDiagnosis(
        action === "subscribe" && account.channel === "whatsapp" && result.status === "confirmed"
          ? "Meta confirmó la URL de RinovaPlus para los mensajes de esta cuenta."
          : stateLabels[result.status] || result.status,
      );
      await done();
    }, "");
  return (
    <section className="panel">
      <h3>Conexión de esta cuenta</h3>
      {oauthNotice && (
        <OperationDialog
          guidance={oauthNotice}
          success={oauthNotice.success}
          dismissLabel={oauthNotice.showChoices
            ? whatsapp ? "Ver números" : "Ver opciones"
            : undefined}
          dismiss={() => {
            setOAuthNotice(null);
            if (!oauthNotice.showChoices) return;
            if (oauthSection.current) oauthSection.current.open = true;
            const choice = choices.current?.querySelector<HTMLButtonElement>("button:not(:disabled)");
            (choice ?? oauthSection.current?.querySelector("summary"))?.focus();
          }}
        />
      )}
      {task.notices}
      {diagnosis && <Notice>{diagnosis}</Notice>}
      <div className="institution-actions">
        <Button
          disabled={!writable || task.busy}
          onClick={() => perform("verify")}
        >
          Verificar token y cuenta
        </Button>
        <Button
          variant="secondary"
          disabled={
            !writable || task.busy ||
            (account.channel === "whatsapp" && !session.actions.includes("settings.webhooks.write"))
          }
          onClick={() => perform("subscribe")}
        >
          {account.channel === "whatsapp" ? "Configurar recepción en Meta" : "Sincronizar suscripción"}
        </Button>
        <Button
          variant="secondary"
          disabled={!writable || task.busy}
          onClick={() => perform("health")}
        >
          Salud del token
        </Button>
        {account.channel !== "whatsapp" && (
          <Button
            variant="secondary"
            disabled={
              !writable ||
              task.busy ||
              account.issuer_profile === "tiktok_business"
            }
            onClick={() => perform("refresh")}
          >
            Renovar token
          </Button>
        )}
      </div>
      <details ref={oauthSection} open={oauthProvider ? true : undefined}>
        <summary>
          {oauthProvider
            ? `Inicio de sesión con ${oauthProvider}`
            : "Conectar con OAuth"}
        </summary>
        <p>
          La aplicación genera la dirección de retorno. Configura primero la URL
          pública HTTPS en Webhooks y las credenciales de esta aplicación.
        </p>
        {account.channel === "whatsapp" && (
          <p>
            Inicia sesión con Facebook y elige un número de WhatsApp de las
            cuentas que autorices en Meta.
          </p>
        )}
        {account.oauth_ready && account.oauth_callback && (
          <Field
            id="channel-oauth-callback"
            label="URL de retorno de OAuth"
            value={account.oauth_callback}
            readOnly
          />
        )}
        {account.issuer_profile === "tiktok_business" && (
          <Notice>
            TikTok Business requiere su aplicación y autorización de Accounts
            API. Login Kit acredita la identidad y tiene permisos distintos.
          </Notice>
        )}
        <Button
          disabled={
            !writable || task.busy || !scopes[account.issuer_profile || ""]
          }
          onClick={() =>
            void task.run(async () => {
              const allowed = scopes[account.issuer_profile || ""];
              const payload = {
                scopes: pageOAuth
                  ? allowed.filter((scope) => scope.startsWith("pages_"))
                  : allowed,
              };
              const result = await call<{
                authorization_url: string;
                oauth_session_id: string;
              }>(`channels/${account.id}/oauth`, "POST", {
                ...payload,
                operation_id: crypto.randomUUID(),
              });
              setOauth(result.oauth_session_id);
              setAuthUrl(result.authorization_url);
              setAssets([]);
              setDiagnosis(oauthMessage({ status: "pending" }, assetPrompt));
              if (oauthProvider)
                window.open(
                  result.authorization_url,
                  "_blank",
                  "noopener,noreferrer",
                );
            }, "")
          }
        >
          {oauthProvider
            ? `Conectar con ${oauthProvider}`
            : "Preparar autorización"}
        </Button>
        {authUrl && (
          <p>
            <a href={authUrl} target="_blank" rel="noopener noreferrer">
              {oauthProvider
                ? `Abrir ${oauthProvider} en otra pestaña`
                : "Abrir autorización del proveedor"}
            </a>
          </p>
        )}
        {oauth && (
          <Button
            variant="secondary"
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                applyOAuthResult(await call<OAuthResult>(`channels/oauth/${oauth}/assets`));
              }, "")
            }
          >
            {pageOAuth
              ? "Cargar páginas autorizadas"
              : "Consultar cuentas autorizadas"}
          </Button>
        )}
        <div className="channel-number-list" ref={choices}>
        {assets.map((asset) => (
          <div className="channel-number-row" key={asset.id}>
            <span>
              <strong>{asset.name}</strong>
              <small>ID {asset.external_id}</small>
            </span>
            <Button
              disabled={!writable || task.busy}
              onClick={() =>
                void task.run(async () => {
                  await call(`channels/oauth/${oauth}/select`, "POST", {
                    asset_id: asset.id,
                    operation_id: crypto.randomUUID(),
                  });
                  setAssets([]);
                  setAuthUrl("");
                  setOauth("");
                  confirmSaved(asset.name);
                  setDiagnosis(
                    "Cuenta guardada. Verifica la conexión con el proveedor.",
                  );
                  await done();
                }, "")
              }
            >
              {pageOAuth ? "Usar esta página" : account.channel === "whatsapp" ? "Usar este número" : "Usar esta cuenta"}
            </Button>
          </div>
        ))}
        </div>
      </details>
      {whatsapp && (
        <section aria-label="Números de WhatsApp">
          <h4>Números de WhatsApp</h4>
          <p>
            Usa «Conectar con Meta» para encontrar tus cuentas y guardar su WABA ID y el ID
            del número. Para configurarlo manualmente, busca el WABA ID en Meta Business →
            Configuración → Cuentas de WhatsApp. En Administrador de WhatsApp → Números de
            teléfono, encontrarás el ID del número.
          </p>
          <p>
            La sincronización consulta los números de la cuenta guardada en este canal.
            Para agregar otro número, crea un canal de WhatsApp para ese número.
          </p>
          {!wabaId && (
            <p>Guarda un WABA ID o elige un número desde el inicio de sesión con Meta para poder sincronizar.</p>
          )}
          <Button
            variant="secondary"
            disabled={!writable || task.busy || !wabaId}
            onClick={() => perform("numbers")}
          >
            Sincronizar números de WhatsApp
          </Button>
          {syncResult && (
            <>
              <Notice>
                {syncResult.numbers.length === 0
                  ? "Meta no devolvió números para esta cuenta. Revisa el WABA ID y el acceso del token en Meta."
                  : `Meta devolvió ${syncResult.numbers.length} ${syncResult.numbers.length === 1 ? "número" : "números"} para esta cuenta.`}
                {syncResult.hasMoreNumbers && " Meta tiene más números para esta cuenta."}
              </Notice>
              <div className="channel-number-list">
                {syncResult.numbers.map((number) => (
                  <div className="channel-number-row" key={number.id}>
                    <span>
                      <strong>{number.display_phone_number || number.id}</strong>
                      <small>{number.verified_name || "Sin nombre verificado"} · ID {number.id}</small>
                    </span>
                    {number.id === phoneId ? <span>Guardado en este canal</span> : (
                      <Button
                        variant="secondary"
                        disabled={!writable || task.busy || !!phoneId}
                        onClick={() =>
                          void task.run(async () => {
                            await call(`channels/${account.id}`, "PUT", {
                              operation_id: crypto.randomUUID(),
                              revision: account.revision,
                              row_version: account.row_version,
                              application_version: account.application_version,
                              values: { "meta:whatsapp_phone_number_id": number.id },
                            });
                            confirmSaved(number.display_phone_number || number.id);
                            await done();
                          }, "")
                        }
                      >
                        Usar este número
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
          <details>
            <summary>Registrar número en WhatsApp Cloud API</summary>
            <p>
              Registra el número solo si Meta indica que el registro está pendiente. Primero
              guárdalo en este canal. Usa el PIN de seis dígitos de verificación en dos pasos
              de WhatsApp Business, distinto del código de verificación por SMS.
            </p>
            <Field
              id="channel-registration-pin"
              label="PIN de seis dígitos"
              type="password"
              inputMode="numeric"
              maxLength={6}
              value={pin}
              disabled={!phoneId || !wabaId}
              onChange={(e) => setPin(e.target.value)}
              autoComplete="off"
            />
            <Button
              disabled={!writable || task.busy || !phoneId || !wabaId || !/^\d{6}$/.test(pin)}
              onClick={() => perform("register")}
            >
              Registrar número
            </Button>
          </details>
        </section>
      )}
      <div className="institution-fields">
        <SelectField
          id="channel-initial-stage"
          label="Etapa inicial del CRM"
          value={stage}
          onChange={(e) => setStage(e.target.value)}
          options={[
            { value: "", label: "Selecciona una etapa" },
            ...(options.value?.stages || []).map((s) => ({
              value: s.key,
              label: s.label,
            })),
          ]}
        />
        <Button
          disabled={!writable || task.busy || !stage}
          onClick={() =>
            void task.run(async () => {
              await call(`channels/${account.id}/routing`, "PUT", {
                operation_id: crypto.randomUUID(),
                row_version: account.row_version,
                initial_stage_key: stage,
                status: "connected",
              });
              await done();
            })
          }
        >
          Conectar cuenta verificada
        </Button>
        <Button
          variant="secondary"
          disabled={!writable || task.busy || !stage}
          onClick={() =>
            void task.run(async () => {
              await call(`channels/${account.id}/routing`, "PUT", {
                operation_id: crypto.randomUUID(),
                row_version: account.row_version,
                initial_stage_key: stage,
                status: "paused",
              });
              await done();
            })
          }
        >
          Pausar cuenta
        </Button>
      </div>
      {(hookReadable || account.webhook || initialWebhook) && (
        <ChannelWebhook
          account={account}
          done={done}
          initial={initialWebhook}
        />
      )}
      {session.actions.includes("settings.ai.write") && (
        <CommentAiPricing identity={account.id} />
      )}
      <ChannelHistory identity={account.id} />
      <Button
        variant="quiet"
        disabled={!writable || task.busy}
        onClick={() => {
          const action =
            account.verified_status === "retired" ? "restore" : "retire";
          if (
            window.confirm(
              action === "retire"
                ? "Se desconectará esta cuenta, se revocarán sus credenciales y se cancelarán sus envíos pendientes. Se conservará el historial del CRM. ¿Retirar la cuenta?"
                : "La cuenta conservará su identidad y necesitará nuevas credenciales y verificación. ¿Restaurarla?",
            )
          )
            void task.run(async () => {
              await call(`channels/${account.id}/lifecycle/${action}`, "POST", {
                operation_id: crypto.randomUUID(),
                row_version: account.row_version,
              });
              await done();
            });
        }}
      >
        {account.verified_status === "retired"
          ? "Restaurar cuenta"
          : "Retirar cuenta"}
      </Button>
    </section>
  );
}

export type IssuedWebhook = {
  webhook: NonNullable<Channel["webhook"]>;
  verify_token: string;
};

export function ChannelWebhook({
  account,
  done,
  initial,
}: {
  account: Channel;
  done: () => Promise<unknown>;
  initial?: IssuedWebhook;
}) {
  const { call, session } = useInstitution();
  const task = useTask();
  const intent = useIntent();
  const [issued, setIssued] = useState(initial);
  useDraftGuard(!!issued);
  const ep = account.webhook ?? issued?.webhook;
  const values = issued?.webhook.id === ep?.id ? issued : undefined;
  const writable =
    session.actions.includes("settings.webhooks.write") &&
    !account.synthetic_demo;
  const isMeta = account.channel !== "tiktok";
  const copy = (value: string, token = false) =>
    void task.run(
      async () => {
        try {
          await navigator.clipboard.writeText(value);
        } catch {
          throw new ApiError(
            409,
            token ? "webhook_token_copy_failed" : "callback_copy_failed",
          );
        }
      },
      token ? "Token de verificación copiado." : "URL de callback copiada.",
    );

  return (
    <div className="institution-webhook">
      <h4>Webhook de esta cuenta</h4>
      {task.notices}
      <p>
        {isMeta
          ? "La firma de eventos se valida con el App Secret de Meta."
          : "La firma de eventos se valida con el secreto de firma de TikTok."}
      </p>
      {ep && (
        <p>
          Último evento recibido{" "}
          {ep.last_seen_at ? (
            <time dateTime={ep.last_seen_at}>
              {new Date(ep.last_seen_at).toLocaleString("es-CO")}
            </time>
          ) : "sin eventos registrados"}
        </p>
      )}
      {(account.channel === "facebook" || account.channel === "messenger") && (
        <p>
          Facebook y Messenger comparten estos valores cuando usan la misma app
          de Meta.
        </p>
      )}
      {ep?.public_origin_required && (
        <p>Configura la URL pública HTTPS de la institución.</p>
      )}
      {ep && (
        <p>
          Recepción: {ep.active ? "habilitada" : "pausada"}.
          {isMeta &&
            ` Verificación: ${ep.challenge_verified_at ? "confirmada" : "pendiente"}.`}
        </p>
      )}
      <div className="institution-actions">
        {isMeta && (
          <Button
            variant="primary"
            disabled={!writable || task.busy || ep?.public_origin_required}
            onClick={() => {
              if (
                ep?.challenge_verified_at &&
                !window.confirm(
                  "Se emitirá un token nuevo para esta URL. Deberás guardarlo en Meta y confirmar el webhook otra vez. ¿Continuar?",
                )
              )
                return;
              void task.run(async () => {
                const body = { row_version: ep?.row_version ?? null };
                const result = await call<Partial<IssuedWebhook>>(
                  `channels/${account.id}/webhook/rotate`,
                  "POST",
                  { ...body, operation_id: intent.get(body) },
                );
                intent.clear();
                setIssued(
                  result.webhook && result.verify_token
                    ? {
                        webhook: result.webhook,
                        verify_token: result.verify_token,
                      }
                    : undefined,
                );
                await done();
                if (!result.verify_token)
                  throw new ApiError(409, "webhook_values_already_issued");
              }, "");
            }}
          >
            Generar webhook
          </Button>
        )}
        {ep && (
          <Button
            variant="secondary"
            disabled={!writable || task.busy}
            onClick={() =>
              void task.run(async () => {
                await call(`channels/${account.id}/webhook`, "POST", {
                  operation_id: crypto.randomUUID(),
                  row_version: ep.row_version,
                  active: !ep.active,
                });
                await done();
              })
            }
          >
            {ep.active ? "Pausar recepción" : "Habilitar recepción firmada"}
          </Button>
        )}
      </div>
      {ep && (
        <div className="panel institution-webhook">
          {values && (
            <>
              <h4>Valores para Meta</h4>
              <p>
                Reemplaza ambos campos en Meta y pulsa «Verificar y guardar». El
                token se muestra una sola vez.
              </p>
            </>
          )}
          <Field
            id={`channel-callback-${account.id}`}
            label={ep.callback_url ? "URL de callback" : "Ruta de callback"}
            value={values?.webhook.callback_url || ep.callback_url || ep.path}
            readOnly
          />
          <Button
            variant="secondary"
            onClick={() =>
              copy(values?.webhook.callback_url || ep.callback_url || ep.path)
            }
          >
            Copiar URL de callback
          </Button>
          {values && (
            <>
              <Field
                id={`channel-verify-token-${account.id}`}
                label="Token de verificación"
                value={values.verify_token}
                readOnly
                autoComplete="off"
                spellCheck={false}
                onFocus={(event) => event.currentTarget.select()}
              />
              <div className="institution-actions">
                <Button
                  variant="secondary"
                  onClick={() => copy(values.verify_token, true)}
                >
                  Copiar token de verificación
                </Button>
                <Button variant="quiet" onClick={() => setIssued(undefined)}>
                  Ocultar token
                </Button>
              </div>
            </>
          )}
        </div>
      )}
      {ep && !isMeta && (
        <Credentials
          scope="webhook"
          owner={`endpoint:${ep.id}`}
          kinds={[
            { id: "webhook_secret", label: "Secreto de firma de TikTok" },
          ]}
        />
      )}
    </div>
  );
}

function CommentAiPricing({ identity }: { identity: string }) {
  const [input, setInput] = useState(""),
    [output, setOutput] = useState(""),
    [source, setSource] = useState(""),
    [daily, setDaily] = useState(10),
    { call } = useInstitution(),
    task = useTask();
  useDraftGuard(!!input || !!output || !!source);
  return (
    <details>
      <summary>Asistencia de IA para comentarios</summary>
      {task.notices}
      <p>
        Selecciona el modelo en Proveedores, habilita IA y define los límites
        técnicos. Confirma aquí sus tarifas máximas; la revisión caduca en siete
        días. Las reservas de presupuesto son conservadoras y no representan una
        factura.
      </p>
      <div className="institution-fields">
        <Field
          id="comment-ai-input-price"
          label="Máximo USD por millón de tokens de entrada"
          type="number"
          min={0}
          max={1000}
          step="0.000001"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <Field
          id="comment-ai-output-price"
          label="Máximo USD por millón de tokens de salida"
          type="number"
          min={0}
          max={1000}
          step="0.000001"
          value={output}
          onChange={(e) => setOutput(e.target.value)}
        />
        <Field
          id="comment-ai-price-source"
          label="Fuente HTTPS de las tarifas revisadas"
          type="url"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        />
        <Field
          id="comment-ai-daily"
          label="Máximo de borradores por día"
          type="number"
          min={1}
          max={10000}
          value={daily}
          onChange={(e) => setDaily(Number(e.target.value))}
        />
      </div>
      <Button
        disabled={
          task.busy ||
          input === "" ||
          output === "" ||
          !source ||
          !Number.isFinite(Number(input)) ||
          !Number.isFinite(Number(output))
        }
        onClick={() =>
          void task.run(async () => {
            await call(`channels/${identity}/comment-ai-policy`, "PUT", {
              operation_id: crypto.randomUUID(),
              input_micros_per_million: Math.ceil(Number(input) * 1_000_000),
              output_micros_per_million: Math.ceil(Number(output) * 1_000_000),
              source_url: source,
              daily_requests: daily,
            });
            setInput("");
            setOutput("");
            setSource("");
          })
        }
      >
        Confirmar límites de tarifa del modelo seleccionado
      </Button>
    </details>
  );
}

function ChannelHistory({ identity }: { identity: string }) {
  const data = useResource<{
      oauth?: (OAuthStatus & { started_at: string }) | null;
      queue: {
        id: string;
        state: string;
        attempts: number;
        row_version: string;
        body_preview?: string;
      }[];
      events: {
        id: string;
        state: string;
        code?: string | null;
        row_version: string;
        kind?: string;
        created_at?: string;
        body_preview?: string | null;
      }[];
      operations: { id: string; action: string; status: string; code?: string | null }[];
    }>(`channels/${identity}/history`),
    { call, session } = useInstitution(),
    task = useTask();
  const [recoveryConfirmation, setRecoveryConfirmation] = useState<{
    resource: { id: string; row_version: string };
    action: string;
    detail: string;
    trigger: Element | null;
  } | null>(null);
  const recover = (
    resource: { id: string; row_version: string },
    action: string,
  ) =>
    void task.run(async () => {
      await call(`channels/${identity}/recover`, "POST", {
        operation_id: crypto.randomUUID(),
        resource_id: resource.id,
        row_version: resource.row_version,
        action,
      });
      await data.reload();
    });
  return (
    <details>
      <summary>Actividad y recuperación</summary>
      {recoveryConfirmation && <OperationDialog
        guidance={{title: "Confirmar recuperación", detail: recoveryConfirmation.detail}}
        trigger={recoveryConfirmation.trigger}
        dismiss={() => setRecoveryConfirmation(null)}
        dismissLabel="Cancelar"
        confirm={{label: "Confirmar recuperación", run: () => recover(recoveryConfirmation.resource, recoveryConfirmation.action)}}
      />}
      {task.notices}
      <Button variant="secondary" onClick={() => void data.reload()}>
        Actualizar actividad
      </Button>
      {data.error && <Notice error>{data.error}</Notice>}
      {data.value && (
        <>
          {data.value.oauth && (
            <p>
              <strong>Último intento de OAuth</strong>{" · "}
              <time dateTime={data.value.oauth.started_at}>
                {new Date(data.value.oauth.started_at).toLocaleString("es-CO")}
              </time>{" · "}
              {oauthMessage(
                data.value.oauth,
                "El proveedor devolvió cuentas. Puedes elegir una desde el resultado de esa autorización.",
              )}
            </p>
          )}
          <p>
            {data.value.queue.length} envíos recientes ·{" "}
            {data.value.events.length} eventos que requieren revisión.
          </p>
          {data.value.queue.map((item) => (
            <div key={item.id}>
              <span>
                {(
                  {
                    queued: "En cola",
                    sending: "Enviando",
                    accepted: "Aceptado",
                    sent: "Enviado",
                    delivered: "Entregado",
                    read: "Leído",
                    uncertain: "Resultado incierto",
                    failed: "Fallido",
                    cancelled: "Cancelado",
                    retried: "Reintentado con un nuevo registro",
                  } as Record<string, string>
                )[item.state] || item.state}{" "}
                · {item.attempts} intentos
              </span>
              {item.body_preview && (
                <blockquote>{item.body_preview}</blockquote>
              )}
              {["queued", "failed"].includes(item.state) &&
                item.body_preview && (
                  <Button
                    variant="secondary"
                    disabled={
                      task.busy ||
                      !session.actions.includes("settings.channels.write") ||
                      !session.actions.includes("inbox.write")
                    }
                    onClick={() => {
                      setRecoveryConfirmation({resource: item,
                        action: item.state === "failed" ? "retry_send" : "resume_queued",
                        trigger: document.activeElement,
                        detail: item.state === "failed"
                            ? "Se creará un nuevo intento de este envío rechazado. ¿Continuar?"
                            : "¿Autorizar este envío pendiente con tu sesión actual?"});
                    }}
                  >
                    {item.state === "failed"
                      ? "Reintentar envío rechazado"
                      : "Autorizar envío pendiente"}
                  </Button>
                )}
              {item.state === "uncertain" && (
                <Button
                  variant="secondary"
                  disabled={
                    task.busy ||
                    !session.actions.includes("settings.channels.write")
                  }
                  onClick={() => {
                    setRecoveryConfirmation({resource: item, action: "abandon_uncertain",
                      trigger: document.activeElement,
                      detail: "El proveedor pudo procesar este envío. Se conservará su historial y no se reenviará. ¿Cerrar su seguimiento como resultado incierto?"});
                  }}
                >
                  Cerrar seguimiento incierto
                </Button>
              )}
            </div>
          ))}
          {data.value.events.map((item) => (
            <div key={item.id} role="group" aria-label={`Evento ${item.id}`}>
              <p>
                <strong>
                  {(
                    {
                      message: "Mensaje",
                      comment: "Comentario",
                      comment_deleted: "Comentario eliminado",
                      status: "Recibo de estado",
                    } as Record<string, string>
                  )[item.kind || ""] || "Evento"}
                </strong>
                {" · "}
                <code>{item.id}</code>
                {item.created_at && (
                  <>
                    {" · "}
                    <time dateTime={item.created_at}>
                      {new Date(item.created_at).toLocaleString("es-CO")}
                    </time>
                  </>
                )}
              </p>
              {item.body_preview && (
                <blockquote>{item.body_preview}</blockquote>
              )}
              <span>
                {item.code === "initial_stage_review_required"
                  ? "El chat nuevo necesita una etapa inicial activa. Selecciona la etapa, guarda el enrutamiento y reprocesa el evento."
                  : item.code === "provider_author_missing"
                    ? "Meta envió el evento sin un remitente que se pueda identificar."
                    : "Evento pendiente de revisión"}
              </span>
              {item.code && <small>{item.code}</small>}
              <Button
                variant="secondary"
                disabled={
                  task.busy ||
                  !session.actions.includes("settings.channels.write")
                }
                onClick={() => recover(item, "reprocess_event")}
              >
                Reprocesar con la configuración actual
              </Button>
            </div>
          ))}
          {data.value.operations.length > 0 && (
            <section aria-label="Operaciones que requieren revisión">
              <h4>Operaciones que requieren revisión</h4>
              <p>Un resultado incierto conserva su historial y bloquea la repetición automática.</p>
              {data.value.operations.map((operation) => (
                <article key={operation.id}>
                  <strong>{operation.action === "whatsapp_gemini_intro" ? "Respuesta automática de Gemini" : operation.action}</strong>
                  <p>{operation.status === "running" ? "En proceso" : operation.status === "uncertain" ? "Resultado sin confirmar; no se repite automáticamente." : "La operación se detuvo antes de completarse."}</p>
                  {operation.code && <p><code>{operation.code}</code></p>}
                  {operation.code?.includes("budget") && <p>Revisa el consumo y los topes de IA en Ajustes → Presupuesto. No reenvíes el mensaje del cliente mientras se revisa este intento.</p>}
                  {operation.code?.startsWith("voice_input_") && <p>No se pudo usar la nota de voz. Comprueba que el archivo se pueda reproducir en el Inbox y revisa su descarga antes de repetir.</p>}
                  <small>Referencia: {operation.id}</small>
                </article>
              ))}
            </section>
          )}
        </>
      )}
    </details>
  );
}

type Runtime = {
  revision: number;
  public_base_url: string;
  ingress_enabled: boolean;
  outbound_enabled: boolean;
  receipt_retention_days: number;
};
export function ChannelRuntime() {
  const data = useResource<Runtime>("channels/runtime");
  if (!data.value) return <ResourceState error={data.error} />;
  return (
    <RuntimeEditor
      key={data.value.revision}
      value={data.value}
      done={data.reload}
    />
  );
}
function RuntimeEditor({
  value,
  done,
}: {
  value: Runtime;
  done: () => Promise<unknown>;
}) {
  const [draft, setDraft] = useState(value),
    { call, session } = useInstitution(),
    task = useTask();
  useDraftGuard(JSON.stringify(value) !== JSON.stringify(draft));
  return (
    <form
      className="panel"
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          await call("channels/runtime", "PUT", {
            ...draft,
            operation_id: crypto.randomUUID(),
          });
          await done();
        });
      }}
    >
      <h3>Recepción y salida de canales</h3>
      {task.notices}
      <p>
        Los callbacks y retornos OAuth de cada cuenta se generan desde esta
        dirección.
      </p>
      <fieldset
        disabled={
          task.busy || !session.actions.includes("settings.webhooks.write")
        }
      >
        <Field
          id="public-channel-origin"
          label="URL pública HTTPS"
          type="url"
          placeholder="https://crm.institucion.edu"
          value={draft.public_base_url}
          onChange={(e) =>
            setDraft({ ...draft, public_base_url: e.target.value })
          }
        />
        <label>
          <input
            type="checkbox"
            checked={draft.ingress_enabled}
            onChange={(e) =>
              setDraft({ ...draft, ingress_enabled: e.target.checked })
            }
          />{" "}
          Permitir recepción firmada
        </label>
        <label>
          <input
            type="checkbox"
            checked={draft.outbound_enabled}
            onChange={(e) =>
              setDraft({ ...draft, outbound_enabled: e.target.checked })
            }
          />{" "}
          Permitir salida de cuentas verificadas
        </label>
        <Field
          id="receipt-retention"
          label="Conservar recibos cifrados (días)"
          type="number"
          min={1}
          max={90}
          value={draft.receipt_retention_days}
          onChange={(e) =>
            setDraft({
              ...draft,
              receipt_retention_days: Number(e.target.value),
            })
          }
        />
        <Button type="submit">Guardar</Button>
      </fieldset>
      <p>
        Las cuentas mantienen sus propios permisos, pausas y límites. Una
        respuesta aceptada por el proveedor aún no acredita entrega.
      </p>
    </form>
  );
}
