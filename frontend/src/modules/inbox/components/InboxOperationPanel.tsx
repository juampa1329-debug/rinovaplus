import { useState } from "react";
import { AgentConversationPanel } from "../../agents/AgentConversationPanel";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import {
  operationDate,
  priorityOptions,
  slaLabels,
  taskInputDate,
  useOperations,
  type OperationDetail,
  type TaskDraft,
} from "../api/inboxOperations";
import { InboxDirectory } from "./InboxDirectory";
import { Badge, Button, Field, Notice, SelectField } from "../../../shared/ui";
const emptyTask = (): TaskDraft => ({
  id: "",
  revision: "",
  title: "",
  priority: "",
  human: "",
  humanName: "",
  due: "",
  status: "pending",
  editing: false,
});
export function InboxOperationPanel({
  id,
  refresh,
  onConfirmed,
}: {
  id: string;
  refresh: number;
  onConfirmed: () => void;
}) {
  const [offset, setOffset] = useState(0);
  const store = useOperations<OperationDetail>(
    `/conversations/${id}?offset=${offset}`,
    refresh,
    onConfirmed,
  );
  const [assignments, setAssignments] = useWorkspaceField(
    "inboxOperations",
    "assignments",
  );
  const [drafts, setDrafts] = useWorkspaceField("inboxOperations", "tasks");
  const [validation, setValidation] = useState("");
  const saved = store.data?.assignment;
  const assignment = assignments[id] ?? {
    revision: store.data?.revision ?? "",
    human: saved?.humanEmployeeId == null ? "" : String(saved.humanEmployeeId),
    humanName: saved?.humanName ?? "",
    ai: saved?.aiAgentId ?? "",
    aiName: saved?.aiName ?? "",
  };
  const draft = drafts[id] ?? emptyTask();
  function changeTask(patch: Partial<TaskDraft>) {
    setDrafts((previous) => ({
      ...previous,
      [id]: {
        ...draft,
        ...patch,
        id: draft.id || crypto.randomUUID(),
        revision: draft.revision || store.data?.revision || "",
      },
    }));
    setValidation("");
  }
  function clearTask() {
    setDrafts((previous) => {
      const next = { ...previous };
      delete next[id];
      return next;
    });
    setValidation("");
  }
  async function saveAssignment() {
    const input = {
      humanEmployeeId: assignment.human ? Number(assignment.human) : null,
      aiAgentId: assignment.ai || null,
    };
    if (
      await store.save(
        `/conversations/${id}/assignment`,
        input,
        assignment.revision,
      )
    ) {
      setAssignments((previous) => {
        if (
          previous[id] &&
          JSON.stringify(previous[id]) !== JSON.stringify(assignment)
        )
          return previous;
        const next = { ...previous };
        delete next[id];
        return next;
      });
    }
  }
  async function saveTask(event: React.FormEvent) {
    event.preventDefault();
    if (!draft.title.trim() || !draft.priority) {
      setValidation("Indique título y prioridad.");
      return;
    }
    const parsed = draft.due ? new Date(draft.due + ":00-05:00") : null;
    if (parsed && !Number.isFinite(parsed.getTime())) {
      setValidation("Revise la fecha y hora en America/Bogota.");
      return;
    }
    const submitted = { ...draft, id: draft.id || crypto.randomUUID() };
    setDrafts((previous) => ({ ...previous, [id]: submitted }));
    if (
      await store.save(
        `/conversations/${id}/tasks/${submitted.id}?create=${!submitted.editing}`,
        {
          title: submitted.title,
          priority: submitted.priority,
          humanEmployeeId: submitted.human ? Number(submitted.human) : null,
          dueAt: parsed?.toISOString() ?? null,
          status: submitted.status,
        },
        submitted.revision,
      )
    ) {
      setDrafts((previous) => {
        if (JSON.stringify(previous[id]) !== JSON.stringify(submitted))
          return previous;
        const next = { ...previous };
        delete next[id];
        return next;
      });
    }
  }
  if (!saved)
    return (
      <section aria-label="Operación de conversación">
        <Notice error={!!store.error}>
          {store.error || "Cargando operación…"}
        </Notice>
        <Button variant="quiet" onClick={store.reload}>
          Reintentar operación
        </Button>
      </section>
    );
  return (
    <section
      className="inbox-operation-panel"
      aria-label="Operación de conversación"
    >
      <h3>Responsables</h3>
      <p className="scope-text">
        Humano y agente IA permanecen asignados al cambiar quién tiene el
        control. Registrar o asignar un agente no activa respuestas.
      </p>
      {store.error && <Notice error>{store.error}</Notice>}
      {store.feedback && <Notice>{store.feedback}</Notice>}
      <fieldset
        disabled={store.busy || store.loading}
        className="client-editor-fields"
      >
        <InboxDirectory
          scope="members"
          label="Responsable humano"
          value={assignment.human}
          name={assignment.humanName}
          refresh={refresh}
          onChange={(human, item) =>
            setAssignments((previous) => ({
              ...previous,
              [id]: { ...assignment, human, humanName: item?.name ?? "" },
            }))
          }
        />
        {saved.humanEmployeeId && !saved.humanSelectable && (
          <Notice>
            El responsable guardado ya no está disponible para nuevas
            asignaciones.
          </Notice>
        )}
        <InboxDirectory
          scope="agents"
          label="Agente IA asignado"
          value={assignment.ai}
          name={assignment.aiName}
          refresh={refresh}
          onChange={(ai, item) =>
            setAssignments((previous) => ({
              ...previous,
              [id]: { ...assignment, ai, aiName: item?.name ?? "" },
            }))
          }
        />
        {saved.aiAgentId && !saved.aiSelectable && (
          <Notice>
            El agente guardado ya no está disponible para nuevas asignaciones.
          </Notice>
        )}
        <div className="actions">
          <Button onClick={() => void saveAssignment()}>
            Guardar responsables
          </Button>
          <Button
            variant="quiet"
            onClick={() =>
              setAssignments((previous) => {
                const next = { ...previous };
                delete next[id];
                return next;
              })
            }
          >
            Descartar asignación
          </Button>
        </div>
      </fieldset>
      <AgentConversationPanel
        conversationId={id}
        refresh={refresh}
        onConfirmed={onConfirmed}
      />
      <h3>SLA de próxima respuesta</h3>
      <Badge>{slaLabels[saved.slaStatus] ?? "Sin medición"}</Badge>
      {saved.slaStatus !== "not_configured" &&
        saved.slaStatus !== "closed" &&
        saved.startedAt && (
          <dl className="detail-list">
            <dt>Desde</dt>
            <dd>{operationDate(saved.startedAt)}</dd>
            <dt>Vence</dt>
            <dd>{operationDate(saved.dueAt)}</dd>
            <dt>Primera respuesta pendiente</dt>
            <dd>{operationDate(saved.firstResponseDueAt)}</dd>
          </dl>
        )}
      <p className="scope-text">
        Política configurada 24/7, sin pausas. En canales externos solo cuenta
        una respuesta aceptada, entregada o leída por el proveedor; en
        conversaciones sin canal cuenta el registro saliente. Fechas en
        America/Bogota.
      </p>
      <h3>Tareas de seguimiento</h3>
      <ul className="inbox-task-list">
        {store.data!.tasks.map((task) => (
          <li key={task.id}>
            <strong>{task.title}</strong>
            <p>
              {task.status === "pending"
                ? "Pendiente"
                : task.status === "completed"
                  ? "Completada"
                  : "Cancelada"}{" "}
              ·{" "}
              {
                priorityOptions.find((option) => option.value === task.priority)
                  ?.label
              }
            </p>
            <p>
              {task.humanEmployeeId
                ? (task.humanName || "Empleado no disponible") +
                  (task.humanSelectable
                    ? ""
                    : " · no disponible para nuevas asignaciones")
                : "Sin responsable"}
            </p>
            <p>
              {operationDate(task.dueAt)}{" "}
              {task.overdue && <Badge>Tarea vencida · no es SLA</Badge>}
            </p>
            <Button
              variant="quiet"
              disabled={store.busy}
              onClick={() => {
                setDrafts((previous) => ({
                  ...previous,
                  [id]: {
                    id: task.id,
                    revision: store.data?.revision ?? "",
                    title: task.title,
                    priority: task.priority,
                    human:
                      task.humanEmployeeId == null
                        ? ""
                        : String(task.humanEmployeeId),
                    humanName: task.humanName,
                    due: taskInputDate(task.dueAt),
                    status: task.status,
                    editing: true,
                  },
                }));
                setValidation("");
              }}
            >
              Editar tarea
            </Button>
          </li>
        ))}
      </ul>
      {!store.data!.tasks.length && (
        <p>No hay tareas registradas en esta página.</p>
      )}
      <div className="actions">
        <Button
          variant="quiet"
          disabled={!offset || store.busy}
          onClick={() => setOffset(Math.max(0, offset - 25))}
        >
          Tareas anteriores
        </Button>
        <Button
          variant="quiet"
          disabled={!store.data!.hasMore || store.busy}
          onClick={() => setOffset(offset + 25)}
        >
          Más tareas
        </Button>
      </div>
      <form onSubmit={saveTask}>
        <h4>{draft.editing ? "Editar seguimiento" : "Nueva tarea"}</h4>
        {validation && <Notice error>{validation}</Notice>}
        <fieldset
          className="client-editor-fields"
          disabled={store.busy || store.loading}
        >
          <Field
            id="inbox-task-title"
            label="Título de tarea"
            maxLength={120}
            value={draft.title}
            onChange={(event) => changeTask({ title: event.target.value })}
          />
          <SelectField
            id="inbox-task-priority"
            label="Prioridad de tarea"
            value={draft.priority}
            options={[
              { value: "", label: "Seleccione prioridad" },
              ...priorityOptions,
            ]}
            onChange={(event) => changeTask({ priority: event.target.value })}
          />
          <InboxDirectory
            scope="members"
            label="Responsable de tarea"
            value={draft.human}
            name={draft.humanName}
            refresh={refresh}
            onChange={(human, item) =>
              changeTask({ human, humanName: item?.name ?? "" })
            }
          />
          <Field
            id="inbox-task-due"
            label="Vencimiento de tarea (America/Bogota)"
            type="datetime-local"
            value={draft.due}
            onChange={(event) => changeTask({ due: event.target.value })}
          />
          {draft.editing && (
            <SelectField
              id="inbox-task-status"
              label="Estado de tarea"
              value={draft.status}
              options={[
                { value: "pending", label: "Pendiente" },
                { value: "completed", label: "Completada" },
                { value: "cancelled", label: "Cancelada" },
              ]}
              onChange={(event) => changeTask({ status: event.target.value })}
            />
          )}
          <p className="scope-text">
            Una tarea completada o cancelada no se reabre. Puede corregir sus
            datos sin cambiar ese estado.
          </p>
          <div className="actions">
            <Button type="submit">Guardar tarea</Button>
            <Button variant="quiet" onClick={clearTask}>
              Descartar borrador de tarea
            </Button>
          </div>
        </fieldset>
      </form>
    </section>
  );
}
