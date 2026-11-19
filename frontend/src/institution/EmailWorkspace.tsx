import { useState } from "react";
import { Badge, Button, Field, Notice, SelectField } from "../shared/ui";
import { useInstitution, useTask } from "./api";
import { ResourceState, useResource } from "./Settings";
import { allowNavigation, useDraftGuard } from "./drafts";
import "./email.css";
import { ErrorFeedback } from "./ErrorFeedback";
import { explainChannelError } from "./channelErrors";

type Doc = {
  kind: string;
  id: string;
  revision: number;
  body: Record<string, unknown>;
};
type Person = {
  id: string;
  name: string;
  email: string;
  role: string;
  active: boolean;
};
type Mail = {
  id: string;
  event: string;
  recipient: string;
  state: string;
  attempts: number;
  error: string | null;
  created_at: string;
};
type Data = {
  available: boolean;
  configured: boolean;
  enabled?: boolean;
  documents: Doc[];
  events: Record<string, [string, string]>;
  users: Person[];
  history: Mail[];
  assets: { id: string; name: string }[];
  variables?: string[];
};
const defaults: Record<string, Record<string, unknown>> = {
  transport: {
    enabled: false,
    sender: "notificaciones@rinovaplus.com",
    name: "RinovaPlus · CBN",
    reply_to: "",
    daily_limit: 100,
    recovery_enabled: false,
    invitation_template: "",
    recovery_template: "",
  },
  template: {
    name: "Aviso institucional",
    subject: "{{evento}} · RinovaPlus",
    html: '<div style="font-family:Arial,Helvetica,sans-serif;background-color:#12343B;color:#F5F7F2;padding:32px;border-radius:16px"><h1>{{evento}}</h1><p>Hola {{nombre}},</p><p>{{detalle}}</p><p>{{fecha}}</p><p><a href="{{enlace}}" style="color:#C4F04D">Abrir RinovaPlus</a></p></div>',
    signature:
      '<p style="font-family:Arial,Helvetica,sans-serif;color:#52666B">Corporación Bolivariana del Norte — CBN</p>',
    published: false,
  },
  rule: {
    name: "Nueva regla",
    event: "users.create",
    enabled: false,
    users: [],
    roles: [],
    groups: [],
    template: "institucional",
    severity: "",
    channel: "",
    account: "",
    module: "",
  },
  group: { name: "Equipo de supervisión", users: [] },
  schedule: {
    name: "Informe de actividad",
    enabled: false,
    frequency: "daily",
    time: "08:00",
    zone: "America/Bogota",
    weekday: 0,
    users: [],
    roles: [],
    groups: [],
    template: "institucional",
  },
};
const labels: Record<string, string> = {
  transport: "Envío",
  template: "Plantillas y marca",
  rule: "Reglas",
  group: "Destinatarios",
  schedule: "Informes",
  history: "Historial",
};
const states: Record<string, string> = {
  queued: "En cola",
  sending: "Enviando",
  accepted: "Aceptado por Oracle",
  retry: "Reintento programado",
  failed: "Fallido",
  uncertain: "Resultado por confirmar",
  suppressed: "Suprimido",
  relayed: "Entregado al proveedor del buzón",
  bounced: "Rebotado",
  cancelled: "Cancelado",
};

export function EmailWorkspace() {
  return (
    <ErrorFeedback explain={explainChannelError}>
      <EmailWorkspaceContent />
    </ErrorFeedback>
  );
}

function EmailWorkspaceContent() {
  const data = useResource<Data>("notifications");
  const [tab, setTab] = useState("transport");
  if (!data.value) return <ResourceState error={data.error} />;
  const view = {
    ...data.value,
    enabled:
      !!data.value.enabled &&
      data.value.documents.some(
        (doc) =>
          doc.kind === "transport" &&
          doc.id === "main" &&
          doc.body.enabled === true,
      ),
  };
  return (
    <div className="email-workspace">
      <section className="panel email-intro">
        <div>
          <Badge>P15 · Comunicación institucional</Badge>
          <h2>El aviso correcto, a la persona correcta.</h2>
          <p>
            Decide qué notificar, revisa el contenido y sigue cada envío desde
            una sola bandeja.
          </p>
        </div>
        <div className="email-health">
          <strong>
            {data.value.configured
              ? "Credenciales SMTP guardadas"
              : "Oracle pendiente"}
          </strong>
          <span>
            {view.enabled ? "Transporte habilitado" : "Salida pausada"}
          </span>
        </div>
      </section>
      {data.error && (
        <Notice error>{data.error} Se conserva la última consulta.</Notice>
      )}
      {!data.value.available ? (
        <Notice>
          La base de notificaciones necesita su instalación operativa antes de
          guardar reglas. El envío permanece pausado.
        </Notice>
      ) : (
        <>
          <nav
            className="institution-tabs"
            aria-label="Configuración de correo"
          >
            {Object.entries(labels).map(([key, label]) => (
              <button
                key={key}
                aria-current={tab === key ? "page" : undefined}
                onClick={() => {
                  if (allowNavigation()) setTab(key);
                }}
              >
                {label}
              </button>
            ))}
          </nav>
          {tab === "history" ? (
            <History data={view} reload={data.reload} />
          ) : (
            <Editor key={tab} kind={tab} data={view} reload={data.reload} />
          )}
        </>
      )}
    </div>
  );
}

function Editor({
  kind,
  data,
  reload,
}: {
  kind: string;
  data: Data;
  reload: () => Promise<Data>;
}) {
  const { call } = useInstitution(),
    task = useTask();
  const initialId =
    kind === "transport"
      ? "main"
      : kind === "template"
        ? "institucional"
        : "nuevo";
  const blank = {
    ...defaults[kind],
    ...(["rule", "schedule"].includes(kind)
      ? {
          template:
            data.documents.find(
              (x) => x.kind === "template" && x.body.published,
            )?.id ?? "",
        }
      : {}),
  };
  const [identity, setIdentity] = useState(initialId);
  const current = data.documents.find(
    (x) => x.kind === kind && x.id === identity,
  );
  const [revision, setRevision] = useState(current?.revision ?? 0);
  const [draft, setDraft] = useState<Record<string, unknown>>(
    current?.body ?? blank,
  );
  const [base, setBase] = useState(JSON.stringify(current?.body ?? blank));
  const [preview, setPreview] = useState("");
  const [audience, setAudience] = useState<
    { name: string; email: string }[] | null
  >(null);
  const [recipient, setRecipient] = useState("");
  const [testId, setTestId] = useState(() => crypto.randomUUID());
  const [versions, setVersions] = useState<
    { revision: number; body: Record<string, unknown> }[]
  >([]);
  const dirty = JSON.stringify(draft) !== base;
  useDraftGuard(dirty);
  const change = (key: string, value: unknown) => {
    setAudience(null);
    setDraft((old) => ({ ...old, [key]: value }));
  };
  const switchDoc = (id: string) => {
    setRevision(
      data.documents.find((x) => x.kind === kind && x.id === id)?.revision ?? 0,
    );
    const next =
      data.documents.find((x) => x.kind === kind && x.id === id)?.body ?? blank;
    setIdentity(id);
    setDraft(next);
    setBase(JSON.stringify(next));
    setPreview("");
    setVersions([]);
  };
  const str = (key: string) => String(draft[key] ?? "");
  const selected = (key: string) =>
    Array.isArray(draft[key]) ? (draft[key] as string[]) : [];
  const pick = (key: string, value: string, checked: boolean) =>
    change(
      key,
      checked
        ? [...selected(key), value]
        : selected(key).filter((x) => x !== value),
    );
  return (
    <div className="email-editor-grid">
      <form
        className="panel"
        onSubmit={(e) => {
          e.preventDefault();
          void task.run(async () => {
            const saved = await call<{ revision: number }>(
              `notifications/documents/${kind}/${identity}`,
              "PUT",
              {
                revision,
                body: draft,
              },
            );
            setRevision(saved.revision);
            setBase(JSON.stringify(draft));
            await reload();
          }, "Configuración guardada. Revisa el estado de salida antes de activar reglas.");
        }}
      >
        <div className="institution-section-head">
          <h3>{labels[kind]}</h3>
          <Badge>Versión {revision}</Badge>
        </div>
        {task.notices}
        <fieldset disabled={task.busy}>
          {kind !== "transport" && (
            <>
              <SelectField
                id="mail-document"
                label="Registro"
                value={current ? identity : "__new__"}
                disabled={dirty}
                onChange={(e) =>
                  switchDoc(
                    e.target.value === "__new__"
                      ? crypto.randomUUID()
                      : e.target.value,
                  )
                }
                options={[
                  { value: "__new__", label: "Nuevo registro" },
                  ...data.documents
                    .filter((x) => x.kind === kind)
                    .map((x) => ({
                      value: x.id,
                      label: String(x.body.name ?? x.id),
                    })),
                ]}
              />
              <Field
                id="mail-id"
                label="Identificador"
                pattern="[a-zA-Z0-9_-]{1,80}"
                value={identity}
                readOnly={!!current}
                onChange={(e) => setIdentity(e.target.value)}
                required
                hint="Un identificador estable; por ejemplo: institucional o supervisores."
              />
            </>
          )}
          <Field
            id="mail-name"
            label={kind === "transport" ? "Nombre del remitente" : "Nombre"}
            value={str("name")}
            onChange={(e) => change("name", e.target.value)}
            required
          />
          {kind === "transport" && (
            <>
              <Field
                id="mail-from"
                label="Remitente aprobado en Oracle"
                type="email"
                value={str("sender")}
                onChange={(e) => change("sender", e.target.value)}
                required
              />
              <Field
                id="mail-reply"
                label="Responder a (opcional)"
                type="email"
                value={str("reply_to")}
                onChange={(e) => change("reply_to", e.target.value)}
              />
              <Field
                id="mail-limit"
                label="Máximo diario de seguridad"
                type="number"
                min={1}
                max={10000}
                value={str("daily_limit")}
                onChange={(e) => change("daily_limit", Number(e.target.value))}
              />
              <label className="email-check">
                <input
                  type="checkbox"
                  checked={!!draft.enabled}
                  onChange={(e) => change("enabled", e.target.checked)}
                />
                Habilitar salida de correo
              </label>
              <label className="email-check">
                <input
                  type="checkbox"
                  checked={!!draft.recovery_enabled}
                  onChange={(e) => change("recovery_enabled", e.target.checked)}
                />
                Permitir recuperación de contraseña por correo
              </label>
              {(
                [
                  ["invitation_template", "Plantilla de invitación"],
                  ["recovery_template", "Plantilla de recuperación"],
                ] as const
              ).map(([field, label]) => (
                <SelectField
                  key={field}
                  id={`mail-${field}`}
                  label={label}
                  value={str(field)}
                  onChange={(e) => change(field, e.target.value)}
                  options={[
                    { value: "", label: "Diseño de RinovaPlus (respaldo)" },
                    ...data.documents
                      .filter(
                        (doc) => doc.kind === "template" && doc.body.published,
                      )
                      .map((doc) => ({
                        value: doc.id,
                        label: String(doc.body.name ?? doc.id),
                      })),
                  ]}
                />
              ))}
              <Notice>
                Estas plantillas necesitan la variable {"{{enlace}}"}. Si una
                versión deja de estar publicada, el acceso usa el diseño seguro
                de respaldo.
              </Notice>
              <Notice>
                La contraseña SMTP se guarda sólo en las variables de producción
                de Coolify. La conexión usa TLS en el puerto 587. El máximo
                diario también protege ante una regla mal configurada.
              </Notice>
            </>
          )}
          {kind === "template" && (
            <>
              <Field
                id="mail-subject"
                label="Asunto"
                value={str("subject")}
                onChange={(e) => change("subject", e.target.value)}
                required
              />
              <label htmlFor="mail-html">HTML del correo</label>
              <textarea
                id="mail-html"
                className="email-code"
                rows={13}
                value={str("html")}
                onChange={(e) => change("html", e.target.value)}
              />
              <label className="email-upload">
                Importar HTML
                <input
                  type="file"
                  accept=".html,.htm,text/html"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f)
                      void task.run(async () => {
                        if (f.size > 100000)
                          throw new Error(
                            "El HTML debe ocupar como máximo 100 KB.",
                          );
                        change("html", await f.text());
                      }, "HTML cargado como borrador. Revisa su vista previa.");
                  }}
                />
              </label>
              <label htmlFor="mail-signature">Firma visual (HTML)</label>
              <textarea
                id="mail-signature"
                rows={3}
                value={str("signature")}
                onChange={(e) => change("signature", e.target.value)}
              />
              <label className="email-check">
                <input
                  type="checkbox"
                  checked={!!draft.published}
                  onChange={(e) => change("published", e.target.checked)}
                />
                Publicar esta versión para reglas e informes
              </label>
              <Button
                variant="secondary"
                onClick={() =>
                  void task.run(async () => {
                    const result = await call<{ html: string }>(
                      "notifications/preview",
                      "POST",
                      {
                        html: str("html") + str("signature"),
                        values: {
                          nombre: "Equipo CBN",
                          evento: "Vista previa de notificación",
                          detalle:
                            "Ejemplo de contenido institucional. Los datos se completan según el evento.",
                          fecha: new Date().toLocaleString("es-CO"),
                          enlace: "https://app.rinovaplus.com/",
                          institucion:
                            "Corporación Bolivariana del Norte — CBN",
                          periodo: "Último período completo",
                        },
                      },
                    );
                    setPreview(result.html);
                  }, "Vista previa validada.")
                }
              >
                Validar y previsualizar
              </Button>
            </>
          )}
          {kind === "rule" && (
            <>
              <SelectField
                id="mail-event"
                label="Evento"
                value={str("event")}
                options={Object.entries(data.events)
                  .filter(
                    ([id]) =>
                      ![
                        "mail.test",
                        "password.reset",
                        "user.invited",
                        "report.daily",
                        "report.weekly",
                      ].includes(id),
                  )
                  .map(([value, [label]]) => ({ value, label }))}
                onChange={(e) => change("event", e.target.value)}
              />
              {[
                ["severity", "Severidad (opcional)"],
                ["channel", "Canal (opcional)"],
                ["account", "ID de cuenta (opcional)"],
                ["module", "Módulo (opcional)"],
              ].map(([key, label]) => (
                <Field
                  key={key}
                  id={`mail-${key}`}
                  label={label}
                  value={str(key)}
                  onChange={(e) => change(key, e.target.value)}
                />
              ))}
            </>
          )}
          {["rule", "schedule"].includes(kind) && (
            <>
              <SelectField
                id="mail-template"
                label="Plantilla"
                value={str("template")}
                options={[
                  { value: "", label: "Seleccionar plantilla publicada" },
                  ...data.documents
                    .filter((x) => x.kind === "template" && x.body.published)
                    .map((x) => ({ value: x.id, label: String(x.body.name) })),
                ]}
                onChange={(e) => change("template", e.target.value)}
              />
              <label className="email-check">
                <input
                  type="checkbox"
                  checked={!!draft.enabled}
                  onChange={(e) => change("enabled", e.target.checked)}
                />
                Activar {kind === "rule" ? "regla" : "informe"} con estos
                destinatarios
              </label>
            </>
          )}
          {kind === "schedule" && (
            <>
              <SelectField
                id="mail-frequency"
                label="Frecuencia"
                value={str("frequency")}
                options={[
                  { value: "daily", label: "Diaria" },
                  { value: "weekly", label: "Semanal" },
                ]}
                onChange={(e) => change("frequency", e.target.value)}
              />
              <Field
                id="mail-time"
                label="Hora local"
                type="time"
                value={str("time")}
                onChange={(e) => change("time", e.target.value)}
                required
              />
              <Field
                id="mail-zone"
                label="Zona horaria IANA"
                value={str("zone")}
                onChange={(e) => change("zone", e.target.value)}
                required
              />
              {draft.frequency === "weekly" && (
                <SelectField
                  id="mail-weekday"
                  label="Día"
                  value={str("weekday")}
                  options={[
                    "Lunes",
                    "Martes",
                    "Miércoles",
                    "Jueves",
                    "Viernes",
                    "Sábado",
                    "Domingo",
                  ].map((label, value) => ({ label, value: String(value) }))}
                  onChange={(e) => change("weekday", Number(e.target.value))}
                />
              )}
              <Notice>
                Incluye el total de eventos de auditoría del período completo.
                Sólo se envía a administradores con permiso de gestión. No
                incluye textos de conversaciones ni datos de estudiantes.
              </Notice>
            </>
          )}
          {["rule", "schedule", "group"].includes(kind) && (
            <fieldset className="email-recipients">
              <legend>Personas destinatarias</legend>
              {data.users
                .filter((x) => x.active)
                .map((person) => (
                  <label className="email-check" key={person.id}>
                    <input
                      type="checkbox"
                      checked={selected("users").includes(person.id)}
                      onChange={(e) =>
                        pick("users", person.id, e.target.checked)
                      }
                    />
                    <span>
                      {person.name}
                      <small>{person.email}</small>
                    </span>
                  </label>
                ))}
              {kind !== "group" && (
                <>
                  <legend>Roles</legend>
                  {[...new Set(data.users.map((x) => x.role))].map((role) => (
                    <label className="email-check" key={role}>
                      <input
                        type="checkbox"
                        checked={selected("roles").includes(role)}
                        onChange={(e) => pick("roles", role, e.target.checked)}
                      />
                      {role}
                    </label>
                  ))}
                  <legend>Grupos</legend>
                  {data.documents
                    .filter((x) => x.kind === "group")
                    .map((group) => (
                      <label className="email-check" key={group.id}>
                        <input
                          type="checkbox"
                          checked={selected("groups").includes(group.id)}
                          onChange={(e) =>
                            pick("groups", group.id, e.target.checked)
                          }
                        />
                        {String(group.body.name)}
                      </label>
                    ))}
                </>
              )}
              <small>
                Antes de enviar se vuelven a comprobar el acceso del usuario, su
                correo actual y sus preferencias. Seleccionar un rol o grupo no
                concede permisos nuevos.
              </small>
            </fieldset>
          )}
          <div className="email-actions">
            <Button type="submit">
              Guardar {kind === "template" ? "versión" : "configuración"}
            </Button>
            {kind === "rule" && (
              <Button
                variant="secondary"
                onClick={() =>
                  void task.run(async () => {
                    const result = await call<{
                      items: { name: string; email: string }[];
                    }>("notifications/audience", "POST", { rule: draft });
                    setAudience(result.items);
                  }, "Destinatarios comprobados con sus permisos actuales.")
                }
              >
                Revisar destinatarios efectivos
              </Button>
            )}
            {current && (
              <Button
                variant="secondary"
                onClick={() =>
                  void task.run(async () => {
                    setVersions(
                      (
                        await call<{ items: typeof versions }>(
                          `notifications/documents/${kind}/${identity}/history`,
                        )
                      ).items,
                    );
                  }, "Versiones consultadas.")
                }
              >
                Ver versiones
              </Button>
            )}
          </div>
          {audience && (
            <Notice>
              {audience.length} destinatarios autorizados:{" "}
              {audience.map((v) => `${v.name} (${v.email})`).join(", ") ||
                "ninguno; revisa personas, roles, grupos y permisos antes de activar."}
            </Notice>
          )}
          {versions.map((v) => (
            <div className="email-version" key={v.revision}>
              <span>Versión {v.revision}</span>
              <Button
                variant="quiet"
                onClick={() => {
                  setDraft({
                    ...v.body,
                    ...(kind === "template" ? { published: false } : {}),
                    ...(["transport", "rule", "schedule"].includes(kind)
                      ? { enabled: false }
                      : {}),
                  });
                  setPreview("");
                }}
              >
                Recuperar como borrador
              </Button>
            </div>
          ))}
        </fieldset>
      </form>
      <aside className="email-side">
        {kind === "template" ? (
          <>
            <section className="panel">
              <h3>Vista previa</h3>
              {preview ? (
                <iframe
                  title="Vista previa de correo"
                  sandbox=""
                  referrerPolicy="no-referrer"
                  srcDoc={preview}
                  className="email-preview"
                />
              ) : (
                <p>
                  Valida el HTML para ver cómo se presentará. Los scripts,
                  formularios e imágenes externas están bloqueados.
                </p>
              )}
              <small>
                Variables: {data.variables?.map((x) => `{{${x}}}`).join(", ")}
              </small>
            </section>
            <section className="panel">
              <h3>Logos y firmas</h3>
              <p>
                PNG, JPEG o WebP estático, hasta 1 MB y 2048 píxeles. Se
                incrustan en el correo.
              </p>
              <input
                aria-label="Subir logo o firma"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f)
                    void task.run(async () => {
                      if (f.size > 1000000)
                        throw new Error(
                          "La imagen debe ocupar como máximo 1 MB.",
                        );
                      const buffer = new Uint8Array(await f.arrayBuffer());
                      let binary = "";
                      for (const byte of buffer)
                        binary += String.fromCharCode(byte);
                      await call("notifications/assets", "POST", {
                        name: f.name,
                        content: btoa(binary),
                      });
                      await reload();
                    }, "Recurso inspeccionado y guardado.");
                }}
              />
              {data.assets.map((a) => (
                <div key={a.id}>
                  <strong>{a.name}</strong>
                  <Button
                    variant="quiet"
                    onClick={() =>
                      change(
                        "html",
                        str("html") +
                          `<img src="cid:${a.id}" alt="CBN" width="160">`,
                      )
                    }
                  >
                    Insertar imagen
                  </Button>
                </div>
              ))}
            </section>
          </>
        ) : (
          <section className="panel">
            <h3>Antes de activar</h3>
            <p>
              Verifica Oracle, publica una plantilla y revisa destinatarios. Una
              regla nueva empieza con eventos futuros.
            </p>
            <p>
              Las invitaciones y la recuperación se envían sólo al usuario
              afectado. Los avisos operativos se filtran por sus permisos.
            </p>
          </section>
        )}
        <section className="panel">
          <h3>Prueba controlada</h3>
          <Field
            id="mail-test-recipient"
            label="Correo destinatario"
            type="email"
            value={recipient}
            onChange={(e) => {
              setRecipient(e.target.value);
              setTestId(crypto.randomUUID());
            }}
          />
          <p>
            Usa sólo un destinatario autorizado. Se enviará una muestra sin
            datos personales del CRM.
          </p>
          <Button
            disabled={
              task.busy ||
              !data.configured ||
              !data.enabled ||
              !recipient.trim() ||
              (kind === "template" && dirty)
            }
            variant="secondary"
            onClick={() =>
              void task.run(async () => {
                await call("notifications/test", "POST", {
                  operation_id: testId,
                  recipient,
                  template: kind === "template" && current ? identity : "",
                });
                setTestId(crypto.randomUUID());
                await reload();
              }, "Prueba en cola. Consulta el historial para ver el resultado del transporte.")
            }
          >
            Enviar correo de prueba
          </Button>
        </section>
      </aside>
    </div>
  );
}

function OracleReceipt({
  mail,
  reload,
}: {
  mail: Mail;
  reload: () => Promise<Data>;
}) {
  const { call } = useInstitution(),
    task = useTask();
  const [reference, setReference] = useState(""),
    [observed, setObserved] = useState(""),
    [action, setAction] = useState("relayed");
  return (
    <details>
      <summary>Registrar recibo de Oracle</summary>
      <p>
        Observación manual del administrador. Contrasta el Message-ID {mail.id}
        @rinovaplus.com en el log de Oracle. La aceptación SMTP no acredita
        entrega; un rebote suprime nuevos envíos a esa dirección.
      </p>
      {task.notices}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void task.run(async () => {
            await call("notifications/receipts", "POST", {
              id: reference,
              mail_id: mail.id,
              action,
              observed_at: observed,
            });
            await reload();
          }, "Recibo registrado como observación manual del administrador.");
        }}
      >
        <fieldset disabled={task.busy}>
          <Field
            id={`receipt-id-${mail.id}`}
            label="ID del evento en Oracle"
            value={reference}
            maxLength={200}
            required
            onChange={(e) => setReference(e.target.value)}
          />
          <Field
            id={`receipt-time-${mail.id}`}
            label="Fecha del evento (ISO con zona horaria)"
            value={observed}
            placeholder="2026-11-18T22:51:41.436Z"
            required
            onChange={(e) => setObserved(e.target.value)}
          />
          <SelectField
            id={`receipt-action-${mail.id}`}
            label="Resultado observado"
            value={action}
            options={[
              {
                value: "relayed",
                label: "Aceptado por el proveedor del buzón",
              },
              { value: "bounced", label: "Rebote permanente confirmado" },
            ]}
            onChange={(e) => setAction(e.target.value)}
          />
          <label>
            <input type="checkbox" required /> He verificado que el recibo
            corresponde a este correo y destinatario.
          </label>
          <Button type="submit">Guardar recibo observado</Button>
        </fieldset>
      </form>
    </details>
  );
}

function History({
  data,
  reload,
}: {
  data: Data;
  reload: () => Promise<Data>;
}) {
  const { call } = useInstitution(),
    task = useTask();
  return (
    <section className="panel">
      <div className="institution-section-head">
        <h3>Historial de correo</h3>
        <Button
          variant="secondary"
          onClick={() =>
            void task.run(async () => {
              await reload();
            }, "Historial actualizado.")
          }
        >
          Actualizar
        </Button>
      </div>
      {task.notices}
      <Notice>
        «Aceptado por Oracle» confirma la recepción SMTP. La entrega al
        proveedor del buzón requiere un recibo de Oracle. Un resultado incierto
        se conserva sin reenviarlo automáticamente.
      </Notice>
      {!data.history.length ? (
        <p>No hay envíos registrados.</p>
      ) : (
        <div className="email-table">
          <table>
            <thead>
              <tr>
                <th>Evento y fecha</th>
                <th>Destinatario</th>
                <th>Estado</th>
                <th>Intentos</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {data.history.map((mail) => (
                <tr key={mail.id}>
                  <td>
                    {data.events[mail.event]?.[0] ?? mail.event}
                    <small>
                      {new Date(mail.created_at).toLocaleString("es-CO")}
                    </small>
                  </td>
                  <td>{mail.recipient}</td>
                  <td>
                    <Badge>{states[mail.state] ?? mail.state}</Badge>
                    {mail.error && (
                      <small>
                        {mail.error === "smtp_connection_failed"
                          ? "No se pudo conectar. Revisa host, credenciales y salida de red en Coolify."
                          : mail.error === "smtp_result_unknown"
                            ? "Oracle pudo recibir el correo. Consulta sus registros antes de cualquier nuevo envío."
                            : mail.error}
                      </small>
                    )}
                  </td>
                  <td>{mail.attempts}</td>
                  <td>
                    {["accepted", "uncertain"].includes(mail.state) && (
                      <OracleReceipt mail={mail} reload={reload} />
                    )}
                    {["queued", "retry"].includes(mail.state) && (
                      <Button
                        variant="quiet"
                        onClick={() =>
                          void task.run(async () => {
                            await call(
                              `notifications/outbox/${mail.id}/cancel`,
                              "POST",
                              {},
                            );
                            await reload();
                          }, "Envío cancelado.")
                        }
                      >
                        Cancelar envío
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function EmailPreferences() {
  const data = useResource<{
    available: boolean;
    revision: number;
    body: { disabled_events?: string[] };
    events: Record<string, string>;
  }>("notifications/preferences");
  if (!data.value) return <ResourceState error={data.error} />;
  if (!data.value.available) return null;
  return (
    <PreferenceEditor
      key={data.value.revision}
      value={data.value}
      reload={data.reload}
    />
  );
}

function PreferenceEditor({
  value,
  reload,
}: {
  value: {
    revision: number;
    body: { disabled_events?: string[] };
    events: Record<string, string>;
  };
  reload: () => Promise<unknown>;
}) {
  const { session, call } = useInstitution(),
    task = useTask();
  const [disabled, setDisabled] = useState(value.body.disabled_events ?? []);
  useDraftGuard(
    JSON.stringify(disabled) !==
      JSON.stringify(value.body.disabled_events ?? []),
  );
  return (
    <form
      className="panel email-workspace"
      onSubmit={(e) => {
        e.preventDefault();
        void task.run(async () => {
          await call(
            `notifications/documents/preference/${session.user.id}`,
            "PUT",
            { revision: value.revision, body: { disabled_events: disabled } },
          );
          await reload();
        }, "Preferencias guardadas.");
      }}
    >
      <h3>Mis avisos por correo</h3>
      <p>
        Estos avisos dependen de las reglas institucionales y de tus permisos.
        La recuperación de contraseña y las invitaciones que solicites conservan
        su envío de seguridad.
      </p>
      {task.notices}
      <fieldset disabled={task.busy}>
        {Object.entries(value.events).map(([id, label]) => (
          <label className="email-check" key={id}>
            <input
              type="checkbox"
              checked={!disabled.includes(id)}
              onChange={(e) =>
                setDisabled((old) =>
                  e.target.checked ? old.filter((x) => x !== id) : [...old, id],
                )
              }
            />
            {label}
          </label>
        ))}
      </fieldset>
      <Button type="submit" disabled={task.busy}>
        Guardar mis preferencias
      </Button>
    </form>
  );
}
