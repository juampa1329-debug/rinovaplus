import type { CrmConfig } from "./crm";
import type { Client, Thread } from "./demo";
import { operationalStates, workflowOf } from "./workflow";

export function overviewData(
  clients: Client[],
  threads: Thread[],
  config: CrmConfig,
) {
  const stages = config.stages.map((stage) => ({
    key: stage.key,
    label: stage.label,
    count: clients.filter((client) => client.stage === stage.label).length,
  }));
  const unknown = clients.filter(
    (client) => !config.stages.some((stage) => stage.label === client.stage),
  ).length;
  if (unknown)
    stages.push({
      key: "__unknown",
      label: "Sin correspondencia",
      count: unknown,
    });
  const states = operationalStates.map((state) => ({
    key: state,
    label: state,
    count: threads.filter((thread) => workflowOf(thread).state === state)
      .length,
  }));
  return {
    stages,
    states,
    contacts: clients.length,
    conversations: threads.length,
    unread: threads.filter((thread) => thread.unread).length,
    tasks: threads.reduce(
      (sum, thread) =>
        sum +
        workflowOf(thread).tasks.filter((task) => task.status === "Pendiente")
          .length,
      0,
    ),
    open: states[0].count,
  };
}
export type OverviewData = ReturnType<typeof overviewData>;
