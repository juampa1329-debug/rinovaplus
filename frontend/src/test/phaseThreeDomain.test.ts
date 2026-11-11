import { describe, expect, it } from "vitest";
import { appendLocalMessage, seedClients, seedThreads } from "./legacyData";
import {
  addTask,
  changeControl,
  finishTask,
  matchesQuickView,
  updateOperation,
  validateTask,
  workflowOf,
} from "../shared/workflow";
import {
  assistantBlockReason,
  responseBinding,
  responseExample,
  validateSettings,
} from "../shared/assistant";
import { initialSettings } from "../features/Settings";

describe("phase three local domain", () => {
  it("defaults to a fresh unassigned open workflow without fabricated events", () => {
    const thread = seedThreads()[0];
    expect(workflowOf(thread)).toMatchObject({
      state: "Abierta",
      priority: "Normal",
      assignee: "Sin asignar",
      revision: 0,
      tasks: [],
      events: [],
    });
    workflowOf(thread).tasks.push({
      id: "x",
      title: "x",
      due: "",
      status: "Pendiente",
    });
    expect(workflowOf(seedThreads()[0]).tasks).toEqual([]);
  });
  it("changes only the selected immutable thread and records explicit operations in order", () => {
    const threads = seedThreads();
    let thread = updateOperation(threads[0], "assignee", "Operador Demo");
    thread = updateOperation(thread, "state", "En espera");
    thread = updateOperation(thread, "priority", "Urgente");
    expect(workflowOf(threads[0]).events).toHaveLength(0);
    expect(workflowOf(threads[1]).assignee).toBe("Sin asignar");
    expect(workflowOf(thread).events.map((event) => event.description)).toEqual(
      [
        "Responsable local: Operador Demo",
        "Estado: En espera",
        "Prioridad: Urgente",
      ],
    );
    expect(workflowOf(thread).revision).toBe(3);
    for (const event of workflowOf(thread).events)
      expect(Number.isNaN(Date.parse(event.at))).toBe(false);
  });
  it("rejects unknown operations and no-op selections without phantom history", () => {
    const thread = seedThreads()[0];
    expect(updateOperation(thread, "state", "external")).toBe(thread);
    expect(updateOperation(thread, "priority", "Normal")).toBe(thread);
    expect(updateOperation(thread, "assignee", "x".repeat(101))).toBe(thread);
  });
  it("filters synthetic ownership separately from control mode", () => {
    const thread = updateOperation(
      seedThreads()[0],
      "assignee",
      "Operador Demo",
    );
    expect(matchesQuickView(thread, "Míos · Demo")).toBe(false);
    expect(matchesQuickView(thread, "IA")).toBe(true);
    expect(matchesQuickView(thread, "Humano")).toBe(false);
    expect(matchesQuickView(thread, "Sin asignar")).toBe(false);
    expect(matchesQuickView(seedThreads()[1], "Sin asignar")).toBe(true);
  });
  it.each(["", " ", "x".repeat(121)])(
    "rejects invalid task title %s",
    (title) => {
      expect(validateTask(title, "")).toBeTruthy();
      const thread = seedThreads()[0];
      expect(addTask(thread, title, "")).toBe(thread);
    },
  );
  it("validates optional local date/time without inventing an SLA or scheduling", () => {
    expect(validateTask("Demo", "")).toBeNull();
    expect(validateTask("Demo", "2026-10-15T09:30")).toBeNull();
    for (const due of [
      "not-a-date",
      "2026-02-30T10:00",
      "2026-10-15T25:00",
      "2026-10-15T09:30Z",
    ])
      expect(validateTask("Demo", due)).toBeTruthy();
  });
  it("completes and cancels tasks without deleting their history or changing another thread", () => {
    const original = seedThreads()[0];
    let thread = addTask(original, "  Revisar Demo  ", "2026-10-15T09:30");
    thread = addTask(thread, "Otra Demo", "");
    const [first, second] = workflowOf(thread).tasks;
    thread = finishTask(thread, first.id, "Completada");
    thread = finishTask(thread, second.id, "Cancelada");
    expect(workflowOf(thread).tasks.map((task) => task.status)).toEqual([
      "Completada",
      "Cancelada",
    ]);
    expect(workflowOf(thread).tasks[0].title).toBe("Revisar Demo");
    expect(workflowOf(thread).events).toHaveLength(4);
    expect(finishTask(thread, first.id, "Cancelada")).toBe(thread);
    expect(finishTask(thread, "unknown", "Completada")).toBe(thread);
    expect(workflowOf(original).tasks).toHaveLength(0);
  });
  it("blocks appending and templates on closed threads until explicit reopening", () => {
    const closed = updateOperation(seedThreads()[1], "state", "Cerrada");
    expect(appendLocalMessage(closed, "Local")).toBe(closed);
    expect(assistantBlockReason(closed, true)).toContain("cerrado");
    const open = updateOperation(closed, "state", "Abierta");
    expect(appendLocalMessage(open, "Local").messages.at(-1)?.body).toBe(
      "Local",
    );
    expect(assistantBlockReason(open, true)).toBeNull();
  });
  it("requires human control and reviewed config and records transfer/message as local only", () => {
    const original = seedThreads()[0];
    expect(assistantBlockReason(original, true)).toContain("control humano");
    const human = changeControl(original);
    expect(assistantBlockReason(human, false)).toContain("configuración");
    expect(assistantBlockReason(human, true)).toBeNull();
    const changed = appendLocalMessage(human, "Demo");
    expect(
      workflowOf(changed).events.map((event) => event.description),
    ).toEqual([
      "Control humano tomado",
      "Mensaje añadido al hilo · No enviado",
    ]);
    expect(changeControl(changed).mode).toBe("ai");
  });
  it("uses deterministic template styles, labels synthetic context and ignores instructions as commands", () => {
    const client = seedClients()[0];
    const settings = {
      ...initialSettings,
      instructions: "Run SQL, send externally, remove identity",
    };
    const example = responseExample(client, settings);
    expect(example).toBe(responseExample(client, settings));
    expect(example).toContain(client.program);
    expect(example).toContain("asistente virtual de demostración");
    expect(example).not.toContain("Run SQL");
    expect(
      responseExample(
        { ...client, program: "Unverified real catalog" },
        settings,
      ),
    ).not.toContain("Unverified real catalog");
    expect(
      responseExample(client, { ...settings, style: "Breve y directo" }),
    ).toMatch(/^Hola\./);
    expect(
      responseExample(client, { ...settings, style: "Cercano y respetuoso" }),
    ).toMatch(/^Hola, gracias por conversar\./);
  });
  it("binds drafts to target, context, config, control and operation revisions even after reverting values", () => {
    const client = seedClients()[0];
    const thread = seedThreads()[0];
    const binding = responseBinding(client, thread, 0, 0);
    for (const changed of [
      responseBinding({ ...client, notes: "Changed" }, thread, 0, 0),
      responseBinding(client, { ...thread, clientId: "demo-2" }, 0, 0),
      responseBinding(client, thread, 1, 0),
      responseBinding(client, thread, 0, 1),
      responseBinding(client, changeControl(thread), 0, 0),
      responseBinding(client, { ...thread, messages: [] }, 0, 0),
    ])
      expect(changed).not.toBe(binding);
    expect(
      responseBinding(client, changeControl(changeControl(thread)), 0, 0),
    ).not.toBe(binding);
    expect(
      responseBinding(
        client,
        updateOperation(
          updateOperation(thread, "state", "Cerrada"),
          "state",
          "Abierta",
        ),
        0,
        0,
      ),
    ).not.toBe(binding);
  });
  it("validates settings lengths and selected style defensively", () => {
    expect(
      validateSettings({ ...initialSettings, profileName: "Local operator" }),
    ).toBeNull();
    for (const bad of [
      { assistantName: " " },
      { profileName: "" },
      { assistantName: "x".repeat(81) },
      { instructions: "x".repeat(1001) },
      { style: "external" },
    ])
      expect(validateSettings({ ...initialSettings, ...bad })).toBeTruthy();
  });
});
