import { Button, Notice } from "../shared/ui";
import { useResource, ResourceState } from "./Settings";
import { useTask } from "./api";

type Status = {
  scope: "local" | "postgres_deployment" | "postgres_rehearsal";
  sql: {
    state: string;
    engine: number;
    product?: string;
    version?: string;
    tables: number;
    academic_access: boolean;
  };
  workers: {
    alive: boolean;
    ready: boolean;
    stages: {
      stage: string;
      state: string;
      last_success_age_seconds: number | null;
      consecutive_failures: number;
    }[];
  };
  queues: Record<string, Record<string, number>>;
  backup: {
    state: string;
    verified_at?: number;
    age_seconds?: number;
    ready_blobs?: number;
    restore_verified: boolean;
  };
  local_ready: boolean;
  online: { state: string; phase: string; public_origin?: string | null };
  infrastructure?: { queue_backend: string; redis: string };
  observed_at: number;
};
const stages: Record<string, string> = {
  events: "Recepción de eventos",
  projection: "Conversaciones y comentarios",
  media: "Archivos",
  campaigns: "Campañas y flujos",
  broadcasts: "Mensajería masiva",
  dispatch: "Cola de salida",
  maintenance: "Mantenimiento de canales",
  agents: "Solicitudes de agentes",
};
const states: Record<string, string> = {
  ready: "Al día",
  starting: "Iniciando",
  stale: "Requiere actualización",
  failed: "Necesita revisión",
  verified: "Verificado",
  missing: "Sin verificación registrada",
  unverified: "Restauración aún no verificada",
  rehearsal: "Entorno de ensayo",
  invalid: "Verificación inválida",
};
const groups: Record<string, string> = {
  webhook_receipts: "Recepciones de webhooks",
  webhook_events: "Eventos de canales",
  outbound: "Mensajes de salida",
  provider_operations: "Operaciones de canal",
  media: "Archivos",
  agent_requests: "Solicitudes de agentes",
  broadcasts: "Campañas masivas",
  campaign_enrollments: "Seguimientos",
};

export function OperationsWorkspace() {
  const data = useResource<Status>("operations"),
    task = useTask();
  return (
    <>
      <div className="institution-section-head">
        <h2>Estado de operación</h2>
        <Button
          variant="secondary"
          disabled={task.busy}
          onClick={() =>
            void task.run(async () => {
              await data.reload();
            }, "Estado actualizado.")
          }
        >
          Actualizar estado
        </Button>
      </div>
      {task.notices}
      {!data.value ? (
        <ResourceState error={data.error} />
      ) : (
        <>
          {data.error && (
            <Notice error>
              {data.error} Se conserva la última consulta; actualiza antes de
              tomar decisiones.
            </Notice>
          )}
          <p>
            Última consulta:{" "}
            {new Date(data.value.observed_at * 1000).toLocaleString("es-CO")}
          </p>
          <Notice error={!data.value.local_ready}>
            {data.value.local_ready
              ? "La base de datos y los procesos responden."
              : "La operación necesita revisión. Consulta los procesos pendientes."}
          </Notice>
          <section className="panel">
            <h3>Base de datos</h3>
            <p>
              {data.value.sql.product ?? "SQL Server"}{" "}
              {data.value.sql.version ?? data.value.sql.engine} ·{" "}
              {data.value.sql.tables} tablas verificadas.
            </p>
            <p>
              {data.value.scope === "postgres_deployment"
                ? "Esta base contiene el CRM. La integración académica SIIE está separada y no se accede a ella desde este panel."
                : "Las tablas académicas permanecen protegidas. La aplicación no tiene permisos para modificarlas."}
            </p>
            {data.value.infrastructure && (
              <p>
                Colas persistentes en{" "}
                {data.value.infrastructure.queue_backend === "postgresql"
                  ? "PostgreSQL"
                  : "SQL Server"}
                . Redis no se utiliza en este recorrido.
              </p>
            )}
          </section>
          <section className="panel">
            <h3>Procesos</h3>
            {!data.value.workers.alive && (
              <Notice error>El proceso de trabajo no responde.</Notice>
            )}
            <ul>
              {data.value.workers.stages.map((item) => (
                <li key={item.stage}>
                  <strong>{stages[item.stage] ?? item.stage}:</strong>{" "}
                  {states[item.state] ?? item.state}
                  {item.last_success_age_seconds !== null &&
                    ` · última comprobación hace ${Math.round(item.last_success_age_seconds)} s`}
                  {item.consecutive_failures > 0 &&
                    ` · ${item.consecutive_failures} fallo(s) consecutivo(s)`}
                </li>
              ))}
            </ul>
          </section>
          <section className="panel">
            <h3>Respaldo y recuperación</h3>
            <p>{states[data.value.backup.state] ?? data.value.backup.state}</p>
            {data.value.backup.verified_at && (
              <p>
                Restauración comprobada:{" "}
                {new Date(data.value.backup.verified_at * 1000).toLocaleString(
                  "es-CO",
                )}{" "}
                · {data.value.backup.ready_blobs} archivos conservados.
              </p>
            )}
            <p>
              El operador realiza y verifica los respaldos. Una verificación con
              más de 24 horas requiere actualización.
            </p>
            <p>
              Este recibo acredita una restauración fechada; no verifica
              continuamente los archivos ni sustituye una copia externa y la
              custodia de claves.
            </p>
          </section>
          <section className="panel">
            <h3>Actividad pendiente</h3>
            <p>
              Los totales incluyen todos los registros de cada cola. Un efecto
              incierto requiere revisión; no debe enviarse de nuevo
              automáticamente.
            </p>
            {Object.entries(data.value.queues).map(([group, values]) => (
              <div key={group}>
                <h4>{groups[group] ?? group}</h4>
                {Object.keys(values).length === 0 ? (
                  <p>Sin registros.</p>
                ) : (
                  <ul>
                    {Object.entries(values).map(([state, count]) => (
                      <li key={state}>
                        {state}: {count}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </section>
          <section className="panel">
            <h3>Disponibilidad online</h3>
            <p>
              {data.value.online.state === "configured"
                ? `URL HTTPS configurada: ${data.value.online.public_origin}. La aceptación institucional se documenta por separado.`
                : `La publicación institucional se configurará en ${data.value.online.phase} cuando estén disponibles el servidor y la URL HTTPS.`}
            </p>
          </section>
        </>
      )}
    </>
  );
}
