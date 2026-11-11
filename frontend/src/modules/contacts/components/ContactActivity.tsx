import { useEffect, useRef, useState } from "react";
import {
  contactActivityApi,
  activityLabel,
  type ActivityFilters,
  type ContactActivityPage,
} from "../api/contactActivity";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import { operationDate, slaLabels } from "../../inbox/api/inboxOperations";
import { Badge, Button, Field, Notice, SelectField } from "../../../shared/ui";

export function ContactActivity({
  contactId,
  refresh,
}: {
  contactId: string;
  refresh?: string | number;
}) {
  const [filtersByContact, setFilters] = useWorkspaceField(
    "clients",
    "activityFilters",
  );
  const filters = filtersByContact[contactId] ?? {
    kind: "all",
    fromDate: "",
    toDate: "",
  };
  const [reload, setReload] = useState(0);
  const base = JSON.stringify([contactId, filters, refresh, reload]);
  const [navigation, setNavigation] = useState<{
    base: string;
    cursors: (string | null)[];
  }>({ base: "", cursors: [] });
  const cursors = navigation.base === base ? navigation.cursors : [];
  const cursor = cursors.at(-1) ?? null;
  const key = JSON.stringify([base, cursor]);
  const [result, setResult] = useState<{
    key: string;
    contactId: string;
    page: ContactActivityPage;
  } | null>(null);
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const sequence = useRef(0);
  const invalidDates =
    !!filters.fromDate && !!filters.toDate && filters.fromDate > filters.toDate;
  useEffect(() => {
    if (invalidDates) return;
    const controller = new AbortController();
    const token = ++sequence.current;
    const timer = window.setTimeout(() => {
      const [binding, before] = JSON.parse(key) as [string, string | null];
      const [id, selected] = JSON.parse(binding) as [string, ActivityFilters];
      void contactActivityApi
        .read(id, selected, before, controller.signal)
        .then((page) => {
          if (!controller.signal.aborted && token === sequence.current) {
            setResult({ key, contactId: id, page });
            setFailure(null);
          }
        })
        .catch(() => {
          if (!controller.signal.aborted && token === sequence.current)
            setFailure({
              key,
              message:
                "No se pudo consultar la actividad real. Reintente o vuelva al historial reciente; sus borradores se conservan.",
            });
        });
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [key, invalidDates]);
  const page = result?.key === key ? result.page : null;
  const error = failure?.key === key ? failure.message : "";
  function change(update: Partial<ActivityFilters>) {
    setFilters((previous) => ({
      ...previous,
      [contactId]: { ...filters, ...update },
    }));
  }
  const metrics = result?.contactId === contactId ? result.page.metrics : null;
  return (
    <details className="scope-note" open>
      <summary>Actividad y métricas del contacto</summary>
      {metrics && (
        <section aria-label="Métricas actuales del contacto">
          <h3>Resumen actual del contacto completo</h3>
          {metrics.scope === "current_group_all_messages_current_tasks" && (
            <p>
              Mensajes y tareas de las {metrics.memberCount} fichas del grupo
              actual. El SLA corresponde únicamente a la conversación
              seleccionada.
            </p>
          )}
          <p className="scope-text">
            Todos los mensajes disponibles y estado actual de tareas, sin
            limitar por filtros o página del historial. Calculado:{" "}
            {operationDate(metrics.calculatedAt)} · America/Bogota.
          </p>
          <dl className="detail-list">
            <div>
              <dt>Mensajes registrados</dt>
              <dd>
                {metrics.messages.messages} · {metrics.messages.incoming}{" "}
                entrantes · {metrics.messages.outgoing} salientes locales
              </dd>
            </div>
            <div>
              <dt>Último mensaje registrado</dt>
              <dd>
                {metrics.messages.lastMessageAt
                  ? operationDate(metrics.messages.lastMessageAt)
                  : "Sin mensajes registrados"}
              </dd>
            </div>
            <div>
              <dt>Tareas actuales</dt>
              <dd>
                {metrics.tasks
                  ? `${metrics.tasks.pendingTasks} pendientes · ${metrics.tasks.completedTasks} completadas · ${metrics.tasks.cancelledTasks} canceladas · ${metrics.tasks.overdueTasks} vencidas`
                  : "No disponibles: fuente de tareas no instalada"}
              </dd>
            </div>
            <div>
              <dt>SLA de próxima respuesta local</dt>
              <dd>{slaLabels[metrics.sla.status] ?? "No disponible"}</dd>
            </div>
            <div>
              <dt>Tiempo de respuesta</dt>
              <dd>
                {metrics.messages.incoming
                  ? "No medido en este corte"
                  : "No disponible: no hay registros entrantes"}
              </dd>
            </div>
          </dl>
        </section>
      )}
      <div className="form-grid">
        <SelectField
          id="activity-kind"
          label="Clase de actividad"
          value={filters.kind}
          options={[
            { value: "all", label: "Toda la actividad" },
            { value: "contact", label: "Ficha del contacto" },
            { value: "conversation", label: "Operaciones de conversación" },
            { value: "message", label: "Registros de mensajes" },
            { value: "assignment", label: "Asignación de responsables" },
            { value: "task", label: "Tareas de seguimiento" },
          ]}
          onChange={(event) =>
            change({ kind: event.target.value as ActivityFilters["kind"] })
          }
        />
        <Field
          id="activity-from"
          label="Actividad desde (Bogotá)"
          type="date"
          value={filters.fromDate}
          onChange={(event) => change({ fromDate: event.target.value })}
        />
        <Field
          id="activity-to"
          label="Actividad hasta (Bogotá, inclusive)"
          type="date"
          value={filters.toDate}
          onChange={(event) => change({ toDate: event.target.value })}
        />
      </div>
      <div className="actions">
        <Button variant="secondary" onClick={() => setReload((n) => n + 1)}>
          Actualizar actividad reciente
        </Button>
        <Button
          variant="quiet"
          onClick={() => change({ kind: "all", fromDate: "", toDate: "" })}
        >
          Limpiar filtros de actividad
        </Button>
      </div>
      <p className="scope-text">
        Estos filtros afectan únicamente al historial. Fechas visibles en
        America/Bogota; origen SQL UTC. Las confirmaciones no detallan valores
        anteriores/posteriores ni identidad autenticada del operador. Mensajes
        registrados no acreditan entrega externa. Preparaciones técnicas de IA y
        configuración global no se cuentan como actividad del contacto.
      </p>
      {invalidDates && (
        <Notice error>
          La fecha inicial debe ser anterior o igual a la final.
        </Notice>
      )}
      {error && (
        <Notice error>
          {error}
          <Button variant="secondary" onClick={() => setReload((n) => n + 1)}>
            Reintentar actividad
          </Button>
        </Notice>
      )}
      {!invalidDates && !page && !error && (
        <p role="status">Cargando actividad…</p>
      )}
      {page && (
        <>
          {!page.historyScope.inboxAvailable && (
            <Notice>
              Historial de tareas/asignaciones no disponible; se conservan los
              registros CRM y mensajes.
            </Notice>
          )}
          {!page.items.length && (
            <p>
              Sin registros para estos filtros. La ficha y sus métricas
              completas se conservan.
            </p>
          )}
          <ol className="workflow-list">
            {page.items.map((item) => (
              <li key={item.id}>
                <strong>{activityLabel(item)}</strong>
                <small>
                  <time dateTime={item.occurredAt}>
                    {operationDate(item.occurredAt)}
                  </time>{" "}
                  · America/Bogota
                </small>
                <small>
                  {item.actor === "automation"
                    ? "Automatización IA · tarea interna"
                    : item.actor
                      ? "Operador local"
                      : "Autor no registrado"}
                </small>
                {metrics &&
                  metrics.scope ===
                    "current_group_all_messages_current_tasks" &&
                  item.sourceContactId && (
                    <small>
                      Ficha de origen: {item.sourceContactId} · Conversación:{" "}
                      {item.conversationId}
                    </small>
                  )}
              </li>
            ))}
          </ol>
          <div className="actions" aria-label="Páginas de actividad">
            <Button
              variant="quiet"
              disabled={!cursors.length}
              onClick={() =>
                setNavigation({ base, cursors: cursors.slice(0, -1) })
              }
            >
              Actividad más reciente
            </Button>
            <Badge>Página {cursors.length + 1}</Badge>
            <Button
              variant="quiet"
              disabled={!page.hasMore || !page.nextCursor}
              onClick={() =>
                setNavigation({ base, cursors: [...cursors, page.nextCursor] })
              }
            >
              Actividad anterior
            </Button>
          </div>
        </>
      )}
    </details>
  );
}
