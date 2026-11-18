import { useState } from "react";
import { OperationDialog } from "./ErrorFeedback";
import { Button, Field, Notice, SelectField } from "../shared/ui";
import { TypedFields } from "./Fields";
import { useInstitution, useIntent, useTask } from "./api";
import type { Contract, Document, User } from "./api";
import { ResourceState, useResource } from "./Settings";
import { useDraftGuard } from "./drafts";

type Role = {
  key: string;
  name: string;
  actions: string[];
  revision: number;
  active: boolean;
  protected: boolean;
};
const roleLabels: Record<string, string> = {
  owner: "Propietario",
  admin: "Administrador",
  supervisor: "Supervisor",
  agent: "Asesor",
  viewer: "Consulta",
};
export function OneTime({
  title,
  values,
  clear,
}: {
  title: string;
  values: string[];
  clear: () => void;
}) {
  useDraftGuard(values.length > 0);
  return (
    <section className="notice">
      <h3>{title}</h3>
      <p>
        Guarda esta información en un lugar seguro. Se muestra una sola vez y no
        se envía por correo.
      </p>
      {values.map((value, index) => (
        <div className="institution-once" key={index}>
          <code>{value}</code>
          <Button
            variant="secondary"
            onClick={() => void navigator.clipboard.writeText(value)}
          >
            Copiar
          </Button>
        </div>
      ))}
      <Button variant="secondary" onClick={clear}>
        Ya la guardé
      </Button>
    </section>
  );
}
export function Profile({ contract }: { contract: Contract }) {
  const { session, call, refresh, expire } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [draft, setDraft] = useState<Document>(session.user.profile),
    [email, setEmail] = useState(session.user.email),
    [password, setPassword] = useState("");
  useDraftGuard(
    JSON.stringify(draft) !== JSON.stringify(session.user.profile) ||
      email !== session.user.email ||
      !!password,
  );
  return (
    <form
      className="panel"
      onSubmit={(event) => {
        event.preventDefault();
        void task.run(async () => {
          const body = {
            revision: session.user.revision,
            email,
            profile: draft,
          };
          const result = await call<{ signed_out: boolean }>("profile", "PUT", {
            ...body,
            operation_id: intent.get(body),
            ...(password ? { current_password: password } : {}),
          });
          setPassword("");
          if (result.signed_out) expire();
          else await refresh();
        });
      }}
    >
      <h3>Mi perfil</h3>
      <p>
        Tu cuenta es personal. Los empleados de SIIE y los agentes de IA se
        administran por separado.
      </p>
      {task.notices}
      <fieldset disabled={task.busy}>
        <Field
          id="profile-email"
          label="Correo de acceso"
          type="email"
          maxLength={254}
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <TypedFields
          prefix="profile"
          specs={contract.fields.profile}
          value={draft}
          onChange={setDraft}
        />
        {email !== session.user.email && (
          <Field
            id="profile-password"
            label="Contraseña actual para cambiar el correo"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        )}
        <Button type="submit">Guardar perfil</Button>
      </fieldset>
    </form>
  );
}
export function Users({ emailAvailable = false }: { emailAvailable?: boolean } = {}) {
  const { call, session } = useInstitution(),
    data = useResource<{ items: User[]; next: string | null }>("users"),
    roles = useResource<{ items: Role[] }>("roles"),
    task = useTask(),
    intent = useIntent();
  const [email, setEmail] = useState(""),
    [name, setName] = useState(""),
    [password, setPassword] = useState(""),
    [role, setRole] = useState("agent"),
    [once, setOnce] = useState<string[]>([]),
    [more, setMore] = useState<User[]>([]),
    [next, setNext] = useState<string | null>(null),
    [end, setEnd] = useState(false);
  const writable =
    session.actions.includes("users.manage") && roles.value !== null;
  useDraftGuard(!!email || !!name || !!password);
  if (!data.value) return <ResourceState error={data.error} />;
  const options = (roles.value?.items ?? [])
    .filter((row) => row.active)
    .map((row) => ({ value: row.key, label: roleLabels[row.key] ?? row.name }));
  return (
    <>
      {task.notices}
      {roles.error && (
        <Notice>
          La lista de usuarios está disponible. Para asignar roles necesitas
          también permiso para consultarlos.
        </Notice>
      )}
      {once.length > 0 && (
        <OneTime
          title="Activación de cuenta"
          values={once}
          clear={() => setOnce([])}
        />
      )}
      <form
        className="panel"
        onSubmit={(event) => {
          event.preventDefault();
          void task.run(async () => {
            const body = {
              email,
              full_name: name,
              role,
              ...(password ? { password } : {}),
            };
            const result = await call<{ activation_token?: string }>(
              "users",
              "POST",
              { ...body, operation_id: intent.get(body) },
            );
            setPassword("");
            setEmail("");
            setName("");
            if (result.activation_token) setOnce([result.activation_token]);
            intent.clear();
            await data.reload();
            setMore([]);
            setNext(null);
          });
        }}
      >
        <h3>Crear usuario</h3>
        <fieldset disabled={!writable || task.busy}>
          <div className="institution-fields">
            <Field
              id="user-name"
              label="Nombre completo"
              maxLength={180}
              value={name}
              required
              onChange={(event) => setName(event.target.value)}
            />
            <Field
              id="user-email"
              label="Correo"
              type="email"
              maxLength={254}
              value={email}
              required
              onChange={(event) => setEmail(event.target.value)}
            />
            <SelectField
              id="user-role"
              label="Rol"
              options={options}
              value={role}
              onChange={(event) => setRole(event.target.value)}
            />
            <Field
              id="user-password"
              label="Contraseña inicial, opcional"
              hint="Mínimo 15 caracteres. Vacía: generar código de activación de un solo uso."
              type="password"
              autoComplete="new-password"
              minLength={15}
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <Button type="submit">Crear usuario</Button>
        </fieldset>
      </form>
      <section className="panel">
        <h3>Usuarios humanos</h3>
        {[...data.value.items, ...more].map((user) => (
          <UserRow
            key={`${user.id}-${user.revision}`}
            user={user}
            options={options}
            writable={writable}
            emailAvailable={emailAvailable}
            onDone={async () => {
              await data.reload();
              setMore([]);
              setNext(null);
            }}
            onToken={(token) => setOnce([token])}
          />
        ))}
        {!end && (next ?? data.value.next) && (
          <Button
            variant="secondary"
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                const page = await call<{ items: User[]; next: string | null }>(
                  `users?after=${encodeURIComponent(next ?? data.value!.next!)}&limit=50`,
                );
                setMore([...more, ...page.items]);
                setNext(page.next);
                setEnd(page.next === null);
              }, "Usuarios cargados.")
            }
          >
            Cargar más usuarios
          </Button>
        )}
      </section>
    </>
  );
}
function UserRow({
  user,
  options,
  writable,
  emailAvailable,
  onDone,
  onToken,
}: {
  user: User;
  options: { value: string; label: string }[];
  writable: boolean;
  emailAvailable: boolean;
  onDone: () => Promise<void>;
  onToken: (token: string) => void;
}) {
  const { call } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [name, setName] = useState(user.full_name),
    [role, setRole] = useState(user.role),
    [active, setActive] = useState(user.active);
  const [emailReview, setEmailReview] = useState(false);
  useDraftGuard(
    name !== user.full_name || role !== user.role || active !== user.active,
  );
  return (
    <details className="institution-user">
      <summary>
        {user.full_name} · {user.email} · {roleLabels[user.role] ?? user.role} ·{" "}
        {user.active ? "Activo" : "Inactivo"}
      </summary>
      {task.notices}
      {emailReview && <OperationDialog guidance={{title:"Enviar activación por correo",detail:`Se enviará un enlace de un solo uso a ${user.email}, válido durante una hora. Reemplazará el código de activación anterior.`}} dismiss={()=>setEmailReview(false)} confirm={{label:"Enviar activación",run:()=>{setEmailReview(false);void task.run(async()=>{await call(`notifications/users/${user.id}/invite`,"POST",{operation_id:intent.get({user:user.id,action:"email-invite"})});intent.clear();},"Activación en cola. Revisa su envío en Correos y notificaciones.");}}} />}
      <fieldset disabled={!writable || task.busy}>
        <div className="institution-fields">
          <Field
            id={`user-name-${user.id}`}
            label="Nombre"
            maxLength={180}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <SelectField
            id={`user-role-${user.id}`}
            label="Rol"
            options={options}
            value={role}
            onChange={(event) => setRole(event.target.value)}
          />
          <label className="institution-check">
            <input
              type="checkbox"
              checked={active}
              onChange={(event) => setActive(event.target.checked)}
            />
            Cuenta activa
          </label>
        </div>
        <div className="institution-actions">
          <Button
            onClick={() =>
              void task.run(async () => {
                const body = {
                  revision: user.revision,
                  role,
                  active,
                  full_name: name,
                };
                await call(`users/${user.id}`, "PUT", {
                  ...body,
                  operation_id: intent.get(body),
                });
                await onDone();
              })
            }
          >
            Guardar usuario
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              if (
                window.confirm(
                  "¿Generar un código para restablecer la contraseña de esta cuenta?",
                )
              )
                void task.run(async () => {
                  const result = await call<{ reset_token: string }>(
                    `users/${user.id}/reset`,
                    "POST",
                  );
                  onToken(result.reset_token);
                });
            }}
          >
            Restablecer acceso
          </Button>
          {emailAvailable && user.active && user.activation_pending && <Button variant="secondary" onClick={()=>setEmailReview(true)}>Enviar activación por correo</Button>}
        </div>
      </fieldset>
    </details>
  );
}
export function Roles({ contract }: { contract: Contract }) {
  const data = useResource<{ items: Role[] }>("roles");
  const [fresh, setFresh] = useState("");
  if (!data.value) return <ResourceState error={data.error} />;
  return (
    <>
      <Notice>
        Los permisos se comprueban en cada solicitud. La administración de
        usuarios es independiente de la creación de agentes de IA. El
        propietario conserva todos los permisos.
      </Notice>
      {data.value.items.map((role) => (
        <RoleEditor
          key={`${role.key}-${role.revision}`}
          role={role}
          contract={contract}
          done={data.reload}
        />
      ))}
      <section className="panel">
        <Field
          id="new-role"
          label="Identificador del nuevo rol"
          hint="Letras minúsculas, números y guion bajo; empieza por letra."
          pattern="[a-z][a-z0-9_]*"
          maxLength={64}
          value={fresh}
          onChange={(event) => setFresh(event.target.value)}
        />
        {fresh &&
          /^[a-z][a-z0-9_]*$/.test(fresh) &&
          !data.value.items.some((r) => r.key === fresh) && (
            <RoleEditor
              key={fresh}
              role={{
                key: fresh,
                name: fresh,
                revision: 0,
                active: true,
                protected: false,
                actions: [],
              }}
              contract={contract}
              done={async () => {
                await data.reload();
                setFresh("");
              }}
            />
          )}
      </section>
    </>
  );
}
function RoleEditor({
  role,
  contract,
  done,
}: {
  role: Role;
  contract: Contract;
  done: () => Promise<unknown>;
}) {
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  const [name, setName] = useState(roleLabels[role.key] ?? role.name),
    [active, setActive] = useState(role.active),
    [actions, setActions] = useState(role.actions);
  useDraftGuard(
    name !== (roleLabels[role.key] ?? role.name) ||
      active !== role.active ||
      JSON.stringify(actions) !== JSON.stringify(role.actions),
  );
  return (
    <details className="panel">
      <summary>
        {name} · {actions.length} permisos
      </summary>
      {task.notices}
      <fieldset
        disabled={
          !session.actions.includes("roles.manage") ||
          role.protected ||
          task.busy
        }
      >
        <Field
          id={`role-name-${role.key}`}
          label="Nombre del rol"
          maxLength={100}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <label className="institution-check">
          <input
            type="checkbox"
            checked={active}
            onChange={(event) => setActive(event.target.checked)}
          />
          Rol activo
        </label>
        <div className="institution-fields">
          {contract.actions.map((action) => (
            <label key={action.id} className="institution-check">
              <input
                type="checkbox"
                checked={actions.includes(action.id)}
                onChange={(event) =>
                  setActions(
                    event.target.checked
                      ? [...actions, action.id]
                      : actions.filter((v) => v !== action.id),
                  )
                }
              />
              {action.label}
            </label>
          ))}
        </div>
        <Button
          onClick={() =>
            void task.run(async () => {
              const body = { name, active, actions, revision: role.revision };
              await call(`roles/${role.key}`, "PUT", {
                ...body,
                operation_id: intent.get(body),
              });
              await done();
            })
          }
        >
          Guardar permisos
        </Button>
      </fieldset>
      {role.protected && <small>Rol protegido por el sistema.</small>}
    </details>
  );
}
export function Security() {
  const { call, session, expire, refresh } = useInstitution(),
    data = useResource<{
      items: {
        id: string;
        user_id: string;
        issued_at: string;
        expires_at: string;
        current: boolean;
        revoked: boolean;
      }[];
    }>("sessions"),
    task = useTask();
  const [password, setPassword] = useState(""),
    [newPassword, setNewPassword] = useState(""),
    [confirmPassword, setConfirmPassword] = useState(""),
    [code, setCode] = useState(""),
    [setup, setSetup] = useState<{
      setup_id: string;
      secret: string;
      otpauth_uri: string;
    } | null>(null),
    [once, setOnce] = useState<string[]>([]);
  useDraftGuard(
    !!password ||
      !!newPassword ||
      !!confirmPassword ||
      !!code ||
      setup !== null,
  );
  const credentials = { current_password: password, ...(code ? { code } : {}) };
  return (
    <>
      {task.notices}
      <section className="panel">
        <h3>Contraseña y autenticación</h3>
        <Field
          id="security-password"
          label="Contraseña actual"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Field
          id="security-code"
          label="Código de autenticación o recuperación"
          autoComplete="one-time-code"
          value={code}
          onChange={(event) => setCode(event.target.value)}
        />
        <Field
          id="security-new-password"
          label="Nueva contraseña"
          type="password"
          autoComplete="new-password"
          minLength={15}
          maxLength={128}
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          hint="De 15 a 128 caracteres. Cambiarla cierra todas tus sesiones."
        />
        <Field
          id="security-confirm-password"
          label="Confirmar nueva contraseña"
          type="password"
          autoComplete="new-password"
          maxLength={128}
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
        />
        <div className="institution-actions">
          <Button
            disabled={
              task.busy ||
              !password ||
              newPassword.length < 15 ||
              confirmPassword !== newPassword
            }
            onClick={() =>
              void task.run(async () => {
                await call("security/password", "POST", {
                  ...credentials,
                  new_password: newPassword,
                });
                expire();
              })
            }
          >
            Cambiar contraseña
          </Button>
          <Button
            variant="secondary"
            disabled={task.busy || !password || session.mfa_enabled}
            onClick={() =>
              void task.run(async () => {
                setSetup(
                  await call("security/totp/setup", "POST", credentials),
                );
                setPassword("");
                setCode("");
              }, "Configuración de autenticación preparada.")
            }
          >
            Configurar autenticador
          </Button>
          <Button
            variant="secondary"
            disabled={task.busy || !password || !session.mfa_enabled}
            onClick={() => {
              if (window.confirm("¿Desactivar la autenticación en dos pasos?"))
                void task.run(async () => {
                  await call("security/totp/disable", "POST", credentials);
                  setPassword("");
                  setCode("");
                  await refresh();
                });
            }}
          >
            Desactivar autenticador
          </Button>
        </div>
        <p>
          Estado:{" "}
          {session.mfa_enabled
            ? "Autenticación en dos pasos activada"
            : "Autenticación en dos pasos desactivada"}
          .
        </p>
      </section>
      {setup && (
        <section className="panel">
          <h3>Vincular tu autenticador</h3>
          <p>
            Introduce esta clave en tu aplicación de autenticación y confirma
            con su código actual.
          </p>
          {setup.secret && (
            <OneTime
              title="Clave del autenticador"
              values={[setup.secret, setup.otpauth_uri]}
              clear={() => setSetup({ ...setup, secret: "", otpauth_uri: "" })}
            />
          )}
          <Field
            id="setup-code"
            label="Código de seis dígitos"
            inputMode="numeric"
            pattern="[0-9]{6}"
            maxLength={6}
            autoComplete="one-time-code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          />
          <Button
            disabled={task.busy || code.length !== 6}
            onClick={() =>
              void task.run(async () => {
                const result = await call<{ recovery_codes: string[] }>(
                  "security/totp/verify",
                  "POST",
                  { setup_id: setup.setup_id, code },
                );
                setSetup(null);
                setCode("");
                setOnce(result.recovery_codes);
                await refresh();
              })
            }
          >
            Activar autenticador
          </Button>
        </section>
      )}
      {once.length > 0 && (
        <OneTime
          title="Códigos de recuperación"
          values={once}
          clear={() => setOnce([])}
        />
      )}
      <section className="panel">
        <h3>Sesiones</h3>
        <Button
          variant="secondary"
          onClick={() =>
            void task.run(async () => {
              await data.reload();
            }, "Sesiones actualizadas.")
          }
        >
          Actualizar sesiones
        </Button>
        {data.error && <Notice error>{data.error}</Notice>}
        {data.value?.items.map((row) => (
          <div className="institution-list-row" key={row.id}>
            <div>
              <strong>
                {row.current
                  ? "Sesión actual"
                  : row.user_id === session.user.id
                    ? "Otra sesión tuya"
                    : `Usuario ${row.user_id}`}
              </strong>
              <p>
                {new Date(row.issued_at).toLocaleString("es-CO", {
                  timeZone: session.user.profile.timezone || "America/Bogota",
                })}{" "}
                · {row.revoked ? "Revocada" : "Vigente"}
              </p>
            </div>
            <Button
              variant="secondary"
              disabled={task.busy || row.revoked}
              onClick={() =>
                void task.run(async () => {
                  await call(`sessions/${row.id}/revoke`, "POST");
                  if (row.current) expire();
                  else await data.reload();
                }, "Sesión revocada.")
              }
            >
              Revocar sesión
            </Button>
          </div>
        ))}
      </section>
    </>
  );
}
export function Audit() {
  type Event = {
    id: number;
    actor_id: string;
    action: string;
    resource: string;
    outcome: string;
    occurred_at: string;
  };
  const data = useResource<{ items: Event[]; next: number | null }>(
      "audit?limit=50",
    ),
    { call, session } = useInstitution(),
    task = useTask();
  const [older, setOlder] = useState<Event[]>([]),
    [next, setNext] = useState<number | null>(null),
    [end, setEnd] = useState(false);
  if (!data.value) return <ResourceState error={data.error} />;
  return (
    <section className="panel">
      <h3>Registro de actividad</h3>
      <p>
        Historial de acciones y accesos. No contiene contraseñas, claves ni
        cuerpos de mensajes.
      </p>
      {task.notices}
      <div className="institution-table">
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Acción</th>
              <th>Resultado</th>
              <th>Usuario</th>
            </tr>
          </thead>
          <tbody>
            {[...data.value.items, ...older].map((row) => (
              <tr key={row.id}>
                <td>
                  {new Date(row.occurred_at).toLocaleString("es-CO", {
                    timeZone: session.user.profile.timezone || "America/Bogota",
                  })}
                </td>
                <td>{row.action}</td>
                <td>
                  {row.outcome === "accepted"
                    ? "Aceptada"
                    : row.outcome === "denied"
                      ? "Denegada"
                      : "Fallida"}
                </td>
                <td>{row.actor_id ?? "Acceso sin sesión"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!end && (next ?? data.value.next) && (
        <Button
          variant="secondary"
          disabled={task.busy}
          onClick={() =>
            void task.run(async () => {
              const page = await call<{ items: Event[]; next: number | null }>(
                `audit?after=${next ?? data.value!.next}&limit=50`,
              );
              setOlder([...older, ...page.items]);
              setNext(page.next);
              setEnd(page.next === null);
            }, "Más actividad cargada.")
          }
        >
          Cargar más actividad
        </Button>
      )}
    </section>
  );
}
