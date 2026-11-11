import { useState } from "react";
import { Button, Field, Notice, SelectField } from "../shared/ui";
import { OneTime } from "./Access";
import type { Channel } from "./Channels";
import { Credentials, ResourceState, useResource } from "./Settings";
import { useInstitution, useIntent, useTask } from "./api";
import { useDraftGuard } from "./drafts";

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
  failed: "Rechazado",
  uncertain: "Resultado incierto: revisar antes de repetir",
  running: "En curso",
  pending: "Pendiente",
};

export function ChannelOperations({
  account,
  done,
}: {
  account: Channel;
  done: () => Promise<unknown>;
}) {
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const options = useResource<{ stages: { key: string; label: string }[] }>(
    "channels/routing-options",
  );
  const [pin, setPin] = useState(""),
    [stage, setStage] = useState(account.initial_stage_key || ""),
    [once, setOnce] = useState<string[]>([]),
    [diagnosis, setDiagnosis] = useState(""),
    [numbers, setNumbers] = useState<
      { id: string; display_phone_number?: string; verified_name?: string }[]
    >([]),
    [oauth, setOauth] = useState(""),
    [authUrl, setAuthUrl] = useState(""),
    [assets, setAssets] = useState<
      { id: string; name: string; external_id: string; kind: string }[]
    >([]);
  useDraftGuard(!!pin || stage !== (account.initial_stage_key || ""));
  const writable =
      session.actions.includes("settings.channels.write") &&
      !account.synthetic_demo,
    hookWritable = session.actions.includes("settings.webhooks.write");
  const ep = account.webhook;
  const perform = (action: string) =>
    void task.run(async () => {
      const payload = {
        row_version: account.row_version,
        ...(action === "register" ? { pin } : {}),
      };
      const result = await call<{
        status: string;
        code?: string;
        result: { numbers?: typeof numbers };
      }>(`channels/${account.id}/actions/${action}`, "POST", {
        ...payload,
        operation_id: intent.get({ action, ...payload }),
      });
      setPin("");
      setDiagnosis(stateLabels[result.status] || result.status);
      if (action === "numbers") setNumbers(result.result.numbers || []);
      if (
        ["verify", "health", "numbers"].includes(action) ||
        result.status === "failed"
      )
        intent.clear();
      await done();
    });
  return (
    <section className="panel">
      <h3>Conexión de esta cuenta</h3>
      {task.notices}
      {diagnosis && <Notice>{diagnosis}</Notice>}
      {numbers.length > 0 && (
        <div aria-label="Números de WhatsApp autorizados">
          {numbers.map((number) => (
            <div key={number.id}>
              <span>
                {number.display_phone_number || number.id} ·{" "}
                {number.verified_name || "Sin nombre verificado"}
              </span>
              <Button
                variant="secondary"
                disabled={
                  !writable ||
                  task.busy ||
                  !!account.fields["meta:whatsapp_phone_number_id"]
                }
                onClick={() =>
                  void task.run(async () => {
                    await call(`channels/${account.id}`, "PUT", {
                      operation_id: crypto.randomUUID(),
                      revision: account.revision,
                      row_version: account.row_version,
                      application_version: account.application_version,
                      values: { "meta:whatsapp_phone_number_id": number.id },
                    });
                    await done();
                  })
                }
              >
                Usar este número
              </Button>
            </div>
          ))}
        </div>
      )}
      <div className="institution-actions">
        <Button
          disabled={!writable || task.busy}
          onClick={() => perform("verify")}
        >
          Verificar token y cuenta
        </Button>
        <Button
          variant="secondary"
          disabled={!writable || task.busy}
          onClick={() => perform("subscribe")}
        >
          Sincronizar suscripción
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
        {account.channel === "whatsapp" && (
          <Button
            variant="secondary"
            disabled={!writable || task.busy}
            onClick={() => perform("numbers")}
          >
            Consultar números de WhatsApp
          </Button>
        )}
      </div>
      {account.channel === "whatsapp" && (
        <details>
          <summary>Registrar número en WhatsApp</summary>
          <p>
            Usa el PIN de seis dígitos de verificación en dos pasos. No es un
            código SMS.
          </p>
          <Field
            id="channel-registration-pin"
            label="PIN de seis dígitos"
            type="password"
            inputMode="numeric"
            maxLength={6}
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            autoComplete="off"
          />
          <Button
            disabled={!writable || task.busy || !/^\d{6}$/.test(pin)}
            onClick={() => perform("register")}
          >
            Registrar número
          </Button>
        </details>
      )}
      <details>
        <summary>Conectar con OAuth</summary>
        <p>
          La aplicación genera la dirección de retorno. Configura primero la URL
          pública HTTPS en Webhooks y las credenciales de esta aplicación.
        </p>
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
              const payload = { scopes: scopes[account.issuer_profile || ""] };
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
            })
          }
        >
          Preparar autorización
        </Button>
        {authUrl && (
          <p>
            <a href={authUrl} target="_blank" rel="noopener noreferrer">
              Abrir autorización del proveedor
            </a>
          </p>
        )}
        {oauth && (
          <Button
            variant="secondary"
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                const result = await call<{
                  status: string;
                  items: typeof assets;
                }>(`channels/oauth/${oauth}/assets`);
                setAssets(result.items);
                setDiagnosis(
                  result.status === "assets_ready"
                    ? "Selecciona la cuenta autorizada."
                    : "La autorización aún no está lista.",
                );
              })
            }
          >
            Consultar cuentas autorizadas
          </Button>
        )}
        {assets.map((asset) => (
          <div key={asset.id}>
            <span>
              {asset.name} · {asset.external_id}
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
                  setDiagnosis(
                    "Credencial guardada. Verifica la cuenta antes de conectarla.",
                  );
                  await done();
                })
              }
            >
              Usar esta cuenta
            </Button>
          </div>
        ))}
      </details>
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
      {ep && (
        <div>
          <h4>Webhook de esta cuenta</h4>
          <Field
            id="channel-callback"
            label={ep.callback_url ? "URL de callback" : "Ruta de callback"}
            value={ep.callback_url || ep.path}
            readOnly
          />
          <Button
            variant="secondary"
            onClick={() =>
              void navigator.clipboard.writeText(ep.callback_url || ep.path)
            }
          >
            Copiar callback
          </Button>
          {ep.public_origin_required && (
            <p>Falta configurar la URL pública HTTPS de la institución.</p>
          )}
          <p>
            Recepción: {ep.active ? "habilitada" : "pausada"}. Verificación:{" "}
            {ep.challenge_verified_at ? "confirmada" : "pendiente"}.
          </p>
          <Button
            variant="secondary"
            disabled={!hookWritable || task.busy}
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
          <Button
            variant="secondary"
            disabled={!hookWritable || task.busy}
            onClick={() =>
              void task.run(async () => {
                const result = await call<{ verify_token?: string }>(
                  `channels/${account.id}/webhook/rotate`,
                  "POST",
                  {
                    operation_id: crypto.randomUUID(),
                    row_version: ep.row_version,
                  },
                );
                if (result.verify_token) setOnce([result.verify_token]);
                await done();
              })
            }
          >
            Generar nuevo verify token
          </Button>
          {account.channel === "tiktok" && (
            <Credentials
              scope="webhook"
              owner={`endpoint:${ep.id}`}
              kinds={[
                { id: "webhook_secret", label: "Secreto de firma de TikTok" },
              ]}
            />
          )}
        </div>
      )}
      {once.length > 0 && (
        <OneTime title="Verify token" values={once} clear={() => setOnce([])} />
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
      queue: {
        id: string;
        state: string;
        attempts: number;
        row_version: string;
        body_preview?: string;
      }[];
      events: { id: string; state: string; row_version: string }[];
      operations: { id: string; action: string; status: string }[];
    }>(`channels/${identity}/history`),
    { call, session } = useInstitution(),
    task = useTask();
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
      {task.notices}
      <Button variant="secondary" onClick={() => void data.reload()}>
        Actualizar actividad
      </Button>
      {data.error && <Notice error>{data.error}</Notice>}
      {data.value && (
        <>
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
                      if (
                        window.confirm(
                          item.state === "failed"
                            ? "Se creará un nuevo intento de este envío rechazado. ¿Continuar?"
                            : "¿Autorizar este envío pendiente con tu sesión actual?",
                        )
                      )
                        recover(
                          item,
                          item.state === "failed"
                            ? "retry_send"
                            : "resume_queued",
                        );
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
                    if (
                      window.confirm(
                        "El proveedor pudo procesar este envío. Se conservará su historial y no se reenviará. ¿Cerrar su seguimiento como resultado incierto?",
                      )
                    )
                      recover(item, "abandon_uncertain");
                  }}
                >
                  Cerrar seguimiento incierto
                </Button>
              )}
            </div>
          ))}
          {data.value.events.map((item) => (
            <div key={item.id}>
              <span>Evento pendiente de revisión</span>
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
            <p>
              Hay {data.value.operations.length} operaciones que requieren
              revisión. Un resultado incierto conserva su historial y bloquea la
              repetición automática.
            </p>
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
      <a href="#/channels">Administrar webhooks por canal</a>
    </form>
  );
}
