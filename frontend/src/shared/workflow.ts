import type { Thread } from "./demo";

export const operationalStates = ["Abierta", "En espera", "Cerrada"] as const;
export const priorities = ["Baja", "Normal", "Alta", "Urgente"] as const;
export const assignees = ["Sin asignar"] as const;
export type LocalTask = {
  id: string;
  title: string;
  due: string;
  status: "Pendiente" | "Completada" | "Cancelada";
};
export type Workflow = {
  state: (typeof operationalStates)[number];
  priority: (typeof priorities)[number];
  assignee: string;
  revision: number;
  tasks: LocalTask[];
  events: { id: string; at: string; description: string }[];
};
export function workflowOf(thread: Thread): Workflow {
  return (
    thread.workflow ?? {
      state: "Abierta",
      priority: "Normal",
      assignee: "Sin asignar",
      revision: 0,
      tasks: [],
      events: [],
    }
  );
}
export function recordOperation(
  thread: Thread,
  description: string,
  patch: Partial<Workflow> = {},
): Thread {
  const workflow = workflowOf(thread);
  return {
    ...thread,
    workflow: {
      ...workflow,
      ...patch,
      revision: workflow.revision + 1,
      events: [
        ...workflow.events,
        { id: crypto.randomUUID(), at: new Date().toISOString(), description },
      ],
    },
  };
}
export function updateOperation(
  thread: Thread,
  field: "state" | "priority" | "assignee",
  value: string,
): Thread {
  const choices = {
    state: operationalStates,
    priority: priorities,
    assignee: assignees,
  };
  const current = workflowOf(thread);
  if (
    (field === "assignee"
      ? !value.trim() || value.length > 100
      : !(choices[field] as readonly string[]).includes(value)) ||
    current[field] === value
  )
    return thread;
  const labels = {
    state: "Estado",
    priority: "Prioridad",
    assignee: "Responsable local",
  };
  return recordOperation(thread, `${labels[field]}: ${value}`, {
    [field]: value,
  });
}
export function changeControl(thread: Thread): Thread {
  const mode = thread.mode === "human" ? "ai" : "human";
  return recordOperation(
    { ...thread, mode },
    mode === "human"
      ? "Control humano tomado"
      : "Control reservado a IA · Sin envíos automáticos",
  );
}
export function validateTask(title: string, due: string): string | null {
  if (!title.trim() || title.trim().length > 120)
    return "Escriba un título de 1 a 120 caracteres.";
  if (due) {
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(due))
      return "Use una fecha y hora local válidas.";
    const date = new Date(due);
    const parts = [
      date.getFullYear(),
      date.getMonth() + 1,
      date.getDate(),
      date.getHours(),
      date.getMinutes(),
    ];
    const expected = due.split(/[-T:]/).map(Number);
    if (parts.some((part, index) => part !== expected[index]))
      return "Use una fecha y hora local válidas.";
  }
  return null;
}
export function addTask(thread: Thread, title: string, due: string): Thread {
  if (validateTask(title, due)) return thread;
  const tasks = [
    ...workflowOf(thread).tasks,
    {
      id: crypto.randomUUID(),
      title: title.trim(),
      due,
      status: "Pendiente" as const,
    },
  ];
  return recordOperation(thread, `Tarea creada: ${title.trim()}`, { tasks });
}
export function finishTask(
  thread: Thread,
  id: string,
  status: "Completada" | "Cancelada",
): Thread {
  const workflow = workflowOf(thread);
  const task = workflow.tasks.find(
    (item) => item.id === id && item.status === "Pendiente",
  );
  if (!task) return thread;
  return recordOperation(
    thread,
    `Tarea ${status.toLocaleLowerCase("es")}: ${task.title}`,
    {
      tasks: workflow.tasks.map((item) =>
        item.id === id ? { ...item, status } : item,
      ),
    },
  );
}
export function matchesQuickView(thread: Thread, view: string): boolean {
  return (
    view === "Todos" ||
    (view === "Sin leer" && thread.unread) ||
    (view === "Humano" && thread.mode === "human") ||
    (view === "IA" && thread.mode === "ai") ||
    (view === "Sin asignar" && workflowOf(thread).assignee === "Sin asignar")
  );
}
