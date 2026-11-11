import { crmConfigurationApi } from "../modules/crm-configuration/api/crmConfigurationApi";
import { strategyApi } from "../modules/conversation-strategy/api/strategy";
import { contactMergeApi } from "../modules/contacts/api/contactMergeApi";
import { institutionalIdentityApi } from "../modules/contacts/api/institutionalIdentity";
import { contactActivityApi } from "../modules/contacts/api/contactActivity";
import { seedCrmConfig } from "../shared/crm";
import { inboxOperationsApi } from "../modules/inbox/api/inboxOperations";
import {
  inboxApi,
  type InboxDetail,
  type InboxSummary,
} from "../modules/inbox/api/inboxApi";
import { workflowOf } from "../shared/workflow";
import { vi } from "vitest";
import { clientsApi, ClientsError } from "../modules/clients/api/clientsApi";
import { filterClients, type Thread } from "../shared/demo";
import { seedClients, seedThreads } from "./legacyData";
import { filterByTag } from "../shared/crm";
import * as channels from "../shared/channels";
export function mockChannelSettings() {
  return vi
    .spyOn(channels, "channelRequest")
    .mockImplementation(async <T>(path: string, method = "GET"): Promise<T> => {
      if (method !== "GET")
        throw new Error("Unexpected channel write in read-only fixture");
      const responses: Record<string, unknown> = {
        "/api/v1/channels": { channels: [] },
        "/api/local/crm/configuration": { config: seedCrmConfig() },
        "/api/v1/social-comments": { comments: [] },
        "/api/v1/channels/transport/status": {
          queued: 0,
          failed: 0,
          uncertain: 0,
          receiptsFailed: 0,
          lastError: null,
        },
      };
      if (!(path in responses))
        throw new Error(`Unexpected channel fixture path: ${path}`);
      return structuredClone(responses[path]) as T;
    });
}
export function inboxDetailState(
  thread: Thread,
  revision: string,
): Pick<InboxDetail, "destinations" | "miniCrm" | "operation"> {
  const assignment = {
    humanEmployeeId: null,
    aiAgentId: null,
    humanName:
      workflowOf(thread).assignee === "Sin asignar"
        ? ""
        : workflowOf(thread).assignee,
    aiName: null,
    humanSelectable: false,
    aiSelectable: false,
    controlMode: thread.mode,
    slaStatus: "not_configured",
    startedAt: null,
    dueAt: null,
    thresholdMinutes: null,
    firstResponseDueAt: null,
  };
  return {
    destinations: [],
    operation: { revision, offset: 0, hasMore: false, tasks: [], assignment },
    miniCrm: {
      leadScore: null,
      temperature: null,
      assessmentSource: "not_evaluated",
      takeover: thread.mode === "human",
      controlEpoch: "0",
      readSequence: "0",
      inFlightOrUncertain: 0,
      stateScope: "conversation",
      assignment,
    },
  };
}
export function mockLocalClients() {
  vi.spyOn(strategyApi, "read").mockImplementation(async (id) => ({
    revision: "0",
    conversationId: id,
    autonomy: {
      requested: false,
      effective: false,
      globalPaused: false,
      planCurrent: false,
      reasons: ["not_requested", "plan_missing_or_stale"],
    },
    metrics: { tasksCreated: 0, feedback: 0, useful: 0 },
    plan: null,
    provenance: null,
  }));
  vi.spyOn(contactActivityApi, "read").mockImplementation(
    async (id, filters) => ({
      items: [],
      limit: 25,
      hasMore: false,
      nextCursor: null,
      metrics: {
        scope: "selected_contact_all_messages_current_tasks",
        calculatedAt: "2026-10-16T12:00:00.0000000Z",
        messages: {
          messages: 0,
          incoming: 0,
          outgoing: 0,
          lastMessageAt: null,
        },
        tasks: {
          pendingTasks: 0,
          completedTasks: 0,
          cancelledTasks: 0,
          overdueTasks: 0,
        },
        sla: { status: "not_configured", startedAt: null, dueAt: null },
      },
      historyScope: {
        contactId: id,
        kind: filters.kind,
        fromDate: filters.fromDate || null,
        toDate: filters.toDate || null,
        dateZone: "America/Bogota",
        upperBound: "exclusive_next_day",
        timestamps: "UTC",
        fieldHistory: "not_recorded",
        actorIdentity: "local_label_not_authenticated",
        inboxAvailable: true,
      },
    }),
  );
  vi.spyOn(institutionalIdentityApi, "catalog").mockResolvedValue({
    documentTypes: [],
    periods: { items: [], activePeriodId: null, selectionRequired: true },
  });
  vi.spyOn(institutionalIdentityApi, "candidates").mockImplementation(
    async (body) => ({
      items: [],
      offset: body.offset,
      limit: 25,
      hasMore: false,
      mode: body.mode,
      criteriaRequired: false,
      identityScope:
        body.mode === "identity"
          ? "all_periods_and_programs"
          : "selected_period_and_program",
    }),
  );
  let configuration = seedCrmConfig();
  let configRevision = 1;
  vi.spyOn(crmConfigurationApi, "read").mockImplementation(async () =>
    structuredClone({
      config: configuration,
      revision: String(configRevision),
    }),
  );
  vi.spyOn(crmConfigurationApi, "save").mockImplementation(
    async (value, expected) => {
      if (expected !== String(configRevision)) throw new ClientsError(409);
      configuration = structuredClone(value);
      configRevision++;
      return {
        config: structuredClone(configuration),
        revision: String(configRevision),
      };
    },
  );
  let clients = seedClients();
  const threads: Thread[] = seedThreads().map((thread) => ({
    ...thread,
    id: crypto.randomUUID(),
  }));
  let revision = 1;
  vi.spyOn(contactMergeApi, "group").mockImplementation(async (id) => {
    const primaryContact = clients.find((c) => c.id === id) ?? clients[0];
    const conversationId =
      threads.find((thread) => thread.clientId === id)?.id ??
      "synthetic-thread";
    return {
      primaryContactId: id,
      primaryContact,
      primaryConversationId: conversationId,
      memberContactIds: [id],
      links: [],
      members: [
        {
          contactId: id,
          conversationId,
          name: primaryContact.name,
          phone: primaryContact.phone,
          channel: "Local",
        },
      ],
    };
  });
  const snapshot = () =>
    structuredClone({ clients, threads, revision: String(revision) });
  vi.spyOn(clientsApi, "workspace").mockImplementation(async () => snapshot());
  vi.spyOn(clientsApi, "list").mockImplementation(
    async (
      query = "",
      stage = "Todas",
      tag = "Todas",
      _signal,
      filters = {},
    ) => ({
      ...snapshot(),
      clients: structuredClone(
        filterByTag(filterClients(clients, query, stage), tag).filter(
          (item) =>
            (!filters.city ||
              item.city.trim().toLowerCase() ===
                filters.city.trim().toLowerCase()) &&
            (!filters.contactType ||
              item.type.trim().toLowerCase() ===
                filters.contactType.trim().toLowerCase()) &&
            ((filters.programId === undefined && !filters.program) ||
              (filters.programId !== undefined &&
                item.programId === filters.programId) ||
              (item.programId == null &&
                !!filters.program &&
                item.program.trim().toLowerCase() ===
                  filters.program.trim().toLowerCase())),
        ),
      ),
    }),
  );
  vi.spyOn(clientsApi, "read").mockImplementation(async (id) => {
    const client = clients.find((item) => item.id === id);
    if (!client) throw new ClientsError(404);
    return { client: structuredClone(client), revision: String(revision) };
  });
  vi.spyOn(clientsApi, "save").mockImplementation(
    async (client, expected, create, _operationId, conversationId) => {
      if (expected !== String(revision)) throw new ClientsError(409);
      clients = clients.some((item) => item.id === client.id)
        ? clients.map((item) =>
            item.id === client.id ? structuredClone(client) : item,
          )
        : [...clients, structuredClone(client)];
      if (create)
        threads.push({
          id: conversationId,
          clientId: client.id,
          channel: "Local",
          unread: false,
          mode: "human",
          messages: [],
        });
      revision++;
      return snapshot();
    },
  );
  vi.spyOn(clientsApi, "conversation").mockImplementation(async (id, input) => {
    const body = input as {
      expectedRevision: string;
      state: string;
      priority: string;
      assignee: string;
      mode: "human" | "ai";
      unread: boolean;
    };
    if (body.expectedRevision !== String(revision)) throw new ClientsError(409);
    const thread = threads.find((item) => item.id === id);
    if (!thread) throw new ClientsError(404);
    Object.assign(thread, {
      mode: body.mode,
      unread: body.unread,
      workflow: {
        state: (
          {
            open: "Abierta",
            waiting: "En espera",
            closed: "Cerrada",
          } as Record<string, string>
        )[body.state],
        priority: (
          {
            low: "Baja",
            normal: "Normal",
            high: "Alta",
            urgent: "Urgente",
          } as Record<string, string>
        )[body.priority],
        assignee: body.assignee || "Sin asignar",
        tasks: [],
        events: [],
        revision: 0,
      },
    });
    revision++;
    return snapshot();
  });
  vi.spyOn(clientsApi, "message").mockImplementation(async (id, input) => {
    const body = input as {
      expectedRevision: string;
      messageId: string;
      body: string;
    };
    if (body.expectedRevision !== String(revision)) throw new ClientsError(409);
    const thread = threads.find((item) => item.id === id);
    if (!thread) throw new ClientsError(404);
    thread.messages.push({
      id: body.messageId,
      body: body.body,
      direction: "outgoing",
    });
    revision++;
    return snapshot();
  });
  const summary = (thread: Thread): InboxSummary => ({
    ...structuredClone(thread),
    id: thread.id!,
    name: clients.find((item) => item.id === thread.clientId)?.name ?? "",
    phone: clients.find((item) => item.id === thread.clientId)?.phone ?? "",
    preview: thread.messages.at(-1)?.body ?? null,
    createdAt: "2026-10-15T12:00:00Z",
    updatedAt: "2026-10-15T12:00:00Z",
    lastMessageAt: thread.messages.length ? "2026-10-15T12:00:00Z" : null,
  });
  vi.spyOn(inboxOperationsApi, "read").mockImplementation(
    async <T>(path: string): Promise<T> => {
      if (path.startsWith("/directory"))
        return { items: [], offset: 0, hasMore: false, revision: "0" } as T;
      if (path === "/configuration")
        return { policy: null, revision: "0" } as T;
      return {
        revision: "0",
        offset: 0,
        hasMore: false,
        tasks: [],
        assignment: {
          humanEmployeeId: null,
          aiAgentId: null,
          humanName: "",
          aiName: null,
          humanSelectable: false,
          aiSelectable: false,
          controlMode: "human",
          slaStatus: "not_configured",
          startedAt: null,
          dueAt: null,
          thresholdMinutes: null,
          firstResponseDueAt: null,
        },
      } as T;
    },
  );
  vi.spyOn(inboxApi, "options").mockImplementation(async () => ({
    channels: [...new Set(threads.map((item) => item.channel))],
    assignees: [
      ...new Set(
        threads
          .map((item) => workflowOf(item).assignee)
          .filter((item) => item !== "Sin asignar"),
      ),
    ],
  }));
  vi.spyOn(inboxApi, "list").mockImplementation(async (filters) => {
    const found = threads.map(summary).filter((item) => {
      const workflow = workflowOf(item);
      return (
        (!filters.q ||
          [item.name, item.phone, item.preview]
            .join(" ")
            .toLowerCase()
            .includes(filters.q.toLowerCase())) &&
        (!filters.channel || item.channel === filters.channel) &&
        (!filters.mode || item.mode === filters.mode) &&
        (!filters.state ||
          { Abierta: "open", "En espera": "waiting", Cerrada: "closed" }[
            workflow.state
          ] === filters.state) &&
        (!filters.unread || item.unread) &&
        (!filters.assignee || workflow.assignee === filters.assignee) &&
        (!filters.assignment ||
          (filters.assignment === "unassigned") ===
            (workflow.assignee === "Sin asignar"))
      );
    });
    return {
      items: found.slice(filters.offset, filters.offset + 25),
      offset: filters.offset,
      limit: 25,
      hasMore: found.length > filters.offset + 25,
    };
  });
  vi.spyOn(inboxApi, "detail").mockImplementation(async (id) => {
    const client = clients.find((item) => item.id === id);
    const thread = threads.find((item) => item.clientId === id);
    if (!client || !thread) throw new ClientsError(404);
    return {
      client: structuredClone(client),
      thread: summary(thread),
      revision: String(revision),
      ...inboxDetailState(thread, String(revision)),
    };
  });
  vi.spyOn(inboxApi, "messages").mockImplementation(async (id, before) => {
    const thread = threads.find((item) => item.id === id);
    if (!thread) throw new ClientsError(404);
    const found = thread.messages
      .map((item, index) => ({
        ...item,
        createdAt: "2026-10-15T12:00:00Z",
        sequence: String(index + 1),
        channel: thread.channel,
        identityId: null,
        deliveryState: item.direction === "incoming" ? "received" : "local",
        deliveryError: null,
        attachment: null,
      }))
      .filter((item) => !before || Number(item.sequence) < Number(before));
    const items = found.slice(-50);
    return {
      items: structuredClone(items),
      hasMore: found.length > 50,
      before: items[0]?.sequence ?? null,
      limit: 50,
    };
  });
  vi.spyOn(inboxApi, "change").mockImplementation(async (id, body) => {
    await clientsApi.conversation(id, body);
    return { revision: String(revision) };
  });
  vi.spyOn(inboxApi, "send").mockImplementation(async (id, body) => {
    await clientsApi.message(id, body);
    return { revision: String(revision) };
  });
  vi.spyOn(inboxApi, "saveContact").mockImplementation(async (_id, input) => {
    const body = input as {
      client: (typeof clients)[number];
      expectedRevision: string;
      operationId: string;
      conversationId: string;
    };
    await clientsApi.save(
      body.client,
      body.expectedRevision,
      false,
      body.operationId,
      body.conversationId,
    );
    return { revision: String(revision) };
  });
}
