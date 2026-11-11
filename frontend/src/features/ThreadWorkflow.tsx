import { useState } from "react";
import { useInboxDrafts } from "../shared/inboxSession";
import type { Thread } from "../shared/demo";
import {
  addTask,
  finishTask,
  operationalStates,
  priorities,
  updateOperation,
  validateTask,
  workflowOf,
} from "../shared/workflow";
import { Badge, Button, Field, Notice, SelectField } from "../shared/ui";

export function ThreadOperation({
  thread,
  onChange,
  showAssignee = true,
}: {
  thread: Thread;
  showAssignee?: boolean;
  onChange: (thread: Thread) => void;
}) {
  const workflow = workflowOf(thread);
  const [assignees, setAssignees] = useInboxDrafts("assignees");
  const key = thread.id ?? thread.clientId;
  const assigneeDraft =
    assignees[key] ??
    (workflow.assignee === "Sin asignar" ? "" : workflow.assignee);
  const setAssigneeDraft = (value: string) =>
    setAssignees((previous) => ({ ...previous, [key]: value }));
  return (
    <div className="thread-operation">
      <SelectField
        id="thread-state"
        label="Estado del hilo local"
        options={[...operationalStates]}
        value={workflow.state}
        onChange={(e) =>
          onChange(updateOperation(thread, "state", e.target.value))
        }
      />
      {showAssignee && (
        <Field
          id="thread-assignee"
          label="Responsable local"
          maxLength={100}
          value={assigneeDraft}
          onChange={(e) => setAssigneeDraft(e.target.value)}
          onBlur={() => {
            const updated = updateOperation(
              thread,
              "assignee",
              assigneeDraft.trim() || "Sin asignar",
            );
            if (updated !== thread) onChange(updated);
          }}
          hint="Etiqueta local; no concede permisos."
        />
      )}
      <SelectField
        id="thread-priority"
        label="Prioridad del hilo local"
        options={[...priorities]}
        value={workflow.priority}
        onChange={(e) =>
          onChange(updateOperation(thread, "priority", e.target.value))
        }
      />
    </div>
  );
}
export function ThreadFollowUp({
  thread,
  onChange,
}: {
  thread: Thread;
  onChange: (thread: Thread) => void;
}) {
  const [drafts, setDrafts] = useInboxDrafts("tasks");
  const { title, due } = drafts[thread.clientId] ?? { title: "", due: "" };
  const setTitle = (value: string) =>
    setDrafts((items) => ({
      ...items,
      [thread.clientId]: { title: value, due },
    }));
  const setDue = (value: string) =>
    setDrafts((items) => ({
      ...items,
      [thread.clientId]: { title, due: value },
    }));
  const [error, setError] = useState("");
  const workflow = workflowOf(thread);
  return (
    <>
      <dl className="detail-list operational-context">
        <dt>Estado local</dt>
        <dd>{workflow.state}</dd>
        <dt>Responsable local</dt>
        <dd>{workflow.assignee}</dd>
        <dt>Prioridad humana</dt>
        <dd>{workflow.priority}</dd>
        <dt>Tareas pendientes</dt>
        <dd>
          {workflow.tasks.filter((task) => task.status === "Pendiente").length}
        </dd>
      </dl>
      <details className="workflow-details">
        <summary>Seguimiento humano · Tareas ({workflow.tasks.length})</summary>
        <p>
          No programa avisos, envíos ni recontacto. Fecha opcional: hora local
          de este navegador; no SLA.
        </p>
        <form
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            const problem = validateTask(title, due);
            setError(problem ?? "");
            if (!problem) {
              onChange(addTask(thread, title, due));
              setDrafts((items) => ({
                ...items,
                [thread.clientId]: { title: "", due: "" },
              }));
            }
          }}
        >
          <Field
            id="task-title"
            label="Título de tarea ficticia"
            maxLength={120}
            value={title}
            error={error || undefined}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Field
            id="task-due"
            label="Fecha y hora opcional de tarea"
            type="datetime-local"
            value={due}
            onChange={(e) => setDue(e.target.value)}
          />
          <Button type="submit">Añadir tarea local</Button>
        </form>
        {!workflow.tasks.length && <p>Sin tareas en este hilo.</p>}
        <ul className="workflow-list">
          {workflow.tasks.map((task) => (
            <li key={task.id}>
              <strong>{task.title}</strong>
              <Badge>{task.status}</Badge>
              <p>
                {task.due
                  ? task.due.replace("T", " ") + " · Hora local del navegador"
                  : "Sin vencimiento"}
              </p>
              {task.status === "Pendiente" && (
                <div className="actions">
                  <Button
                    variant="secondary"
                    aria-label={`Completar tarea ${task.title}`}
                    onClick={() =>
                      onChange(finishTask(thread, task.id, "Completada"))
                    }
                  >
                    Completar
                  </Button>
                  <Button
                    variant="quiet"
                    aria-label={`Cancelar tarea ${task.title}`}
                    onClick={() =>
                      onChange(finishTask(thread, task.id, "Cancelada"))
                    }
                  >
                    Cancelar tarea
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </details>
      <details className="workflow-details">
        <summary>Timeline local · Eventos ({workflow.events.length})</summary>
        <Notice>
          Registro temporal de acciones explícitas. No es auditoría persistida
          ni recibo del proveedor. Mensajes iniciales: fixtures.
        </Notice>
        {!workflow.events.length && (
          <p>Sin acciones registradas en esta pestaña.</p>
        )}
        <ol className="workflow-list">
          {workflow.events.map((event, index) => (
            <li key={event.id}>
              <strong>
                {index + 1}. {event.description}
              </strong>
              <small>
                <time dateTime={event.at}>
                  {new Date(event.at).toLocaleString("es-CO", {
                    timeZone: "America/Bogota",
                  })}
                </time>{" "}
                · America/Bogota · Local
              </small>
            </li>
          ))}
        </ol>
      </details>
    </>
  );
}
