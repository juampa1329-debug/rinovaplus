import { useEffect, useState } from "react";
import { Button, Field, Notice, SelectField } from "../shared/ui";

type Connection = {
  server: string;
  port: number;
  username: string;
  password: string;
  certificate_hostname: string;
  database: string;
};
type Review = {
  database: string;
  engine_major: number;
  edition: string;
  compatibility_level: number;
  table_count: number;
  column_count: number;
  relation_count: number;
  missing_academic_tables: string[];
  missing_crm_tables: string[];
  sql2019_engine: boolean;
  metadata_visibility?: string;
};
type Snapshot = {
  revision: number;
  connection: Omit<Connection, "password">;
  has_password: boolean;
  source: "saved" | "environment";
  review: Review | null;
};
type Schema = {
  review: Review;
  tables: string[][];
  columns: (string | number | boolean | null)[][];
  relations: (string | number | boolean | null)[][];
};
const errors: Record<string, string> = {
  sql_connection_failed:
    "No se pudo conectar. Revisa servidor, puerto y certificado TLS; la validación de seguridad permanece activa.",
  sql_login_or_database_denied:
    "SQL Server rechazó el acceso. Revisa las credenciales y el permiso sobre la base seleccionada.",
  sql_credentials_required:
    "Introduce la contraseña para este servidor y usuario.",
  sql_database_required: "Selecciona una base de datos.",
  sql_identity_unavailable: "No se pudo verificar la identidad de la base.",
  sql_profile_changed:
    "La selección cambió en otra sesión. Recarga antes de guardar.",
  sql_connection_busy: "Hay otra comprobación en curso. Espera a que termine.",
  sql_profile_storage_unavailable:
    "No se puede abrir el almacén cifrado. Conserva el volumen y su clave; no vuelvas a guardar hasta recuperarlos.",
  sql_metadata_limit: "El esquema supera el límite de esta vista de metadatos.",
  local_access_required:
    "Esta configuración requiere acceso desde la aplicación local.",
  invalid_request: "Revisa el formato de los campos.",
};

async function request<T>(
  method = "GET",
  action = "",
  body?: unknown,
  signal?: AbortSignal,
) {
  const response = await fetch(`/api/local/database${action}`, {
    method,
    signal,
    cache: "no-store",
    credentials: "same-origin",
    headers: {
      "X-CRM-Local": "1",
      ...(method !== "GET" ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new Error(
      errors[result.detail ?? result.code] ??
        "No se pudo completar la operación.",
    );
  return result as T;
}

export function DatabaseSettings() {
  const [connection, setConnection] = useState<Connection>({
    server: "host.docker.internal",
    port: 1433,
    username: "",
    password: "",
    certificate_hostname: "localhost",
    database: "",
  });
  const [revision, setRevision] = useState(0);
  const [hasPassword, setHasPassword] = useState(false);
  const [databases, setDatabases] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>("load");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [review, setReview] = useState<Review | null>(null);
  const [schema, setSchema] = useState<Schema | null>(null);
  const [table, setTable] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void request<Snapshot>("GET", "", undefined, controller.signal)
      .then((value) => {
        if (controller.signal.aborted) return;
        setConnection({ ...value.connection, password: "" });
        setRevision(value.revision);
        setHasPassword(value.has_password);
        setReview(value.review);
        if (value.connection.database)
          setDatabases([value.connection.database]);
        if (value.source === "saved")
          setNotice("Conexión seleccionada y guardada en este backend.");
      })
      .catch((reason: Error) => {
        if (!controller.signal.aborted) setError(reason.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(null);
      });
    return () => controller.abort();
  }, []);

  function change<K extends keyof Connection>(key: K, value: Connection[K]) {
    const endpointChanged = [
      "server",
      "port",
      "username",
      "certificate_hostname",
    ].includes(key);
    setConnection((current) => ({
      ...current,
      [key]: value,
      ...(key !== "database" ? { database: "" } : {}),
      ...(endpointChanged ? { password: "" } : {}),
    }));
    if (endpointChanged) setHasPassword(false);
    setReview(null);
    setSchema(null);
    setNotice("");
    setError("");
    if (key !== "database") setDatabases([]);
  }

  async function run(action: "discover" | "test" | "save" | "schema") {
    setBusy(action);
    setError("");
    setNotice("");
    try {
      const body = { ...connection, revision };
      if (action === "discover") {
        const result = await request<{ databases: string[] }>(
          "POST",
          "/discover",
          body,
        );
        setDatabases(result.databases);
        if (!result.databases.includes(connection.database))
          setConnection((current) => ({ ...current, database: "" }));
        setReview(null);
        setSchema(null);
        setNotice(
          result.databases.length
            ? "Elige una base de la lista."
            : "Este usuario no tiene bases disponibles.",
        );
      } else {
        const result = await request<Schema & { revision?: number }>(
          action === "save" ? "PUT" : "POST",
          action === "save" ? "" : `/${action}`,
          body,
        );
        setReview(result.review);
        if (action === "schema") {
          setSchema(result);
          setTable("");
        } else {
          setSchema(null);
          setTable("");
        }
        if (action === "save" && result.revision !== undefined) {
          setRevision(result.revision);
          setHasPassword(true);
          setConnection((current) => ({ ...current, password: "" }));
          setNotice(
            "Selección verificada y guardada con credenciales cifradas.",
          );
        } else if (action === "test")
          setNotice("Conexión verificada con TLS y acceso de lectura.");
      }
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "No se pudo completar la operación.",
      );
    } finally {
      setBusy(null);
    }
  }

  const selectedColumns =
    schema?.columns.filter((row) => `${row[0]}.${row[1]}` === table) ?? [];
  const selectedRelations =
    schema?.relations.filter(
      (row) =>
        `${row[1]}.${row[2]}` === table || `${row[4]}.${row[5]}` === table,
    ) ?? [];
  return (
    <div>
      <p>
        Elige una conexión para inspeccionar su estructura. Las credenciales se
        guardan cifradas; esta selección no cambia una conexión CRM activa.
      </p>
      {error && <Notice error>{error}</Notice>}
      {notice && <Notice>{notice}</Notice>}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void run("discover");
        }}
      >
        <fieldset disabled={busy !== null}>
          <legend>Conexión SQL Server</legend>
          <div className="form-grid">
            <Field
              id="db-server"
              label="Servidor o IP"
              value={connection.server}
              onChange={(event) => change("server", event.target.value)}
              autoComplete="off"
              required
              maxLength={253}
            />
            <Field
              id="db-port"
              label="Puerto TCP"
              type="number"
              min={1}
              max={65535}
              value={connection.port}
              onChange={(event) => change("port", Number(event.target.value))}
              required
            />
            <Field
              id="db-user"
              label="Usuario SQL"
              value={connection.username}
              onChange={(event) => change("username", event.target.value)}
              autoComplete="username"
              required
              maxLength={128}
            />
            <Field
              id="db-password"
              label="Contraseña"
              type="password"
              value={connection.password}
              onChange={(event) => change("password", event.target.value)}
              placeholder={
                hasPassword ? "Contraseña guardada" : "Introduce la contraseña"
              }
              autoComplete="current-password"
              maxLength={4096}
            />
            <Field
              id="db-certificate"
              label="Nombre del certificado TLS"
              value={connection.certificate_hostname}
              onChange={(event) =>
                change("certificate_hostname", event.target.value)
              }
              required
              maxLength={253}
              hint="Debe coincidir con el certificado del servidor. En esta copia local: localhost."
            />
          </div>
          <div className="actions">
            <Button type="submit">
              {busy === "discover" ? "Consultando…" : "Listar bases"}
            </Button>
          </div>
          <SelectField
            id="db-database"
            label="Base de datos"
            value={connection.database}
            onChange={(event) => change("database", event.target.value)}
            options={[
              { value: "", label: "Selecciona una base" },
              ...databases,
            ]}
          />
          <div className="actions">
            <Button
              variant="secondary"
              disabled={!connection.database}
              onClick={() => void run("test")}
            >
              Probar conexión
            </Button>
            <Button
              disabled={!connection.database}
              onClick={() => void run("save")}
            >
              Guardar selección
            </Button>
            <Button
              variant="quiet"
              disabled={!connection.database}
              onClick={() => void run("schema")}
            >
              Ver estructura
            </Button>
          </div>
        </fieldset>
      </form>
      {busy && (
        <p role="status">
          {busy === "load"
            ? "Cargando configuración…"
            : "Comprobando conexión…"}
        </p>
      )}
      {review && (
        <section aria-label="Resultado de conexión">
          <h3>{review.database}</h3>
          <p>
            {review.table_count} tablas visibles · {review.column_count}{" "}
            columnas · {review.relation_count} relaciones
          </p>
          {review.metadata_visibility !== "database" && (
            <Notice>
              Los permisos de este usuario no permiten confirmar el esquema
              completo. Los totales mostrados pueden ser parciales.
            </Notice>
          )}
          <p>
            {review.edition} · Motor {review.engine_major} · Compatibilidad{" "}
            {review.compatibility_level}
          </p>
          {review.missing_academic_tables.length > 0 ||
          review.missing_crm_tables.length > 0 ? (
            <Notice>
              La conexión funciona, pero no están visibles todas las tablas
              académicas y CRM conocidas. Puede ser un fragmento o requerir más
              permisos de lectura. Seleccionarla no activa CRM ni crea tablas.
            </Notice>
          ) : (
            <Notice>
              La conexión está seleccionada para revisar sus metadatos. La
              activación CRM requiere validar su esquema completo; no cambia las
              conexiones de operaciones que ya estén en curso.
            </Notice>
          )}
        </section>
      )}
      {schema && (
        <section aria-label="Estructura de la base">
          <SelectField
            id="db-table"
            label="Tabla"
            value={table}
            onChange={(event) => setTable(event.target.value)}
            options={[
              { value: "", label: "Selecciona una tabla" },
              ...schema.tables.map((row) => row.join(".")),
            ]}
          />
          {table && (
            <>
              <h3>Columnas</h3>
              <ul>
                {selectedColumns.map((row) => (
                  <li key={String(row[2])}>
                    {String(row[2])} · {String(row[3])}
                    {row[7] ? " · Admite nulos" : " · Requerida"}
                  </li>
                ))}
              </ul>
              <h3>Relaciones declaradas</h3>
              {selectedRelations.length ? (
                <ul>
                  {selectedRelations.map((row, index) => (
                    <li
                      key={`${row[0]}-${index}`}
                    >{`${row[1]}.${row[2]}.${row[3]} → ${row[4]}.${row[5]}.${row[6]}`}</li>
                  ))}
                </ul>
              ) : (
                <p>Sin claves foráneas declaradas para esta tabla.</p>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
