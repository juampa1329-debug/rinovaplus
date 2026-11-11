import type { Client, Message, Thread } from "../../../shared/demo";
import {
  institutionHeaders,
  institutionUnauthorized,
} from "../../../shared/institutionSession";
import { ClientsError } from "../../clients/api/clientsApi";
import type { ContactGroup } from "../../contacts/api/contactMergeApi";
import type { OperationDetail } from "./inboxOperations";
import type { InboxMedia } from "./mediaApi";

export type DeliveryIntent = {
  delivery: "local" | "external";
  identityId?: string;
  mediaId?: string;
};
export type Assessment = {
  leadScore: number | null;
  temperature: "cold" | "warm" | "hot" | null;
};
export type Destination = {
  id: string;
  channel: string;
  externalId: string;
  state: string;
  mediaKinds: string[];
};
export const channelNames: Record<string, string> = {
  local: "CRM",
  whatsapp: "WhatsApp",
  instagram: "Instagram",
  messenger: "Messenger",
  facebook: "Facebook",
  tiktok: "TikTok",
};
export const deliveryLabels: Record<string, string> = {
  local: "Guardado",
  received: "Recibido",
  queued: "En cola",
  sending: "Envío iniciado",
  sent: "Aceptado por el proveedor",
  delivered: "Entregado",
  read: "Leído por el destinatario",
  failed: "Envío fallido",
  uncertain: "Resultado incierto · no reenviar sin reconciliar",
};

export type InboxSummary = Thread & {
  id: string;
  name: string;
  phone: string;
  preview: string | null;
  createdAt: string;
  updatedAt: string;
  lastMessageAt: string | null;
};
export type InboxDetail = {
  client: Client;
  thread: InboxSummary;
  revision: string;
  contactGroup?: ContactGroup | null;
  destinations: Destination[];
  miniCrm: Assessment & {
    assessmentSource: string;
    takeover: boolean;
    controlEpoch?: string;
    readSequence?: string;
    inFlightOrUncertain?: number;
    stateScope: "conversation";
    assignment?: OperationDetail["assignment"];
  };
  operation: OperationDetail | null;
};
export type InboxPage = {
  items: InboxSummary[];
  offset: number;
  limit: number;
  hasMore: boolean;
};
export type MessagePage = {
  items: (Message & {
    createdAt: string;
    sequence: string;
    channel: string;
    identityId: string | null;
    deliveryState: string;
    deliveryError: string | null;
    attachment: InboxMedia | null;
  })[];
  before: string | null;
  hasMore: boolean;
  limit: number;
};
export type InboxFilters = {
  q: string;
  channel: string;
  state: string;
  mode: string;
  assignment: string;
  assignee: string;
  unread: boolean;
  offset: number;
  humanId?: string;
  aiId?: string;
  sla?: string;
  stage?: string;
};
async function request<T>(
  path: string,
  signal?: AbortSignal,
  method = "GET",
  body?: unknown,
): Promise<T> {
  try {
    const response = await fetch("/api/local/crm/inbox" + path, {
      method,
      cache: "no-store",
      headers: {
        "X-CRM-Local": "1",
        ...institutionHeaders(),
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
        : AbortSignal.timeout(15000),
    });
    if (!response.ok) {
      institutionUnauthorized(response.status);
      throw new ClientsError(response.status);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (signal?.aborted) throw error;
    throw error instanceof ClientsError ? error : new ClientsError(0);
  }
}
export const inboxApi = {
  list: (filters: InboxFilters, signal?: AbortSignal) =>
    request<InboxPage>(
      "?" +
        new URLSearchParams(
          Object.entries(filters)
            .filter(
              ([key, value]) =>
                !(["humanId", "aiId", "sla"].includes(key) && !value),
            )
            .map(([key, value]) => [key, String(value)]),
        ),
      signal,
    ),
  options: (signal?: AbortSignal) =>
    request<{ channels: string[]; assignees: string[] }>("/options", signal),
  detail: (contactId: string, signal?: AbortSignal) =>
    request<InboxDetail>("/contacts/" + encodeURIComponent(contactId), signal),
  messages: (id: string, before?: string | null, signal?: AbortSignal) =>
    request<MessagePage>(
      `/conversations/${encodeURIComponent(id)}/messages${before ? "?before=" + encodeURIComponent(before) : ""}`,
      signal,
    ),
  change: (id: string, body: unknown) =>
    request<{ revision: string }>(
      `/conversations/${encodeURIComponent(id)}`,
      undefined,
      "PUT",
      body,
    ),
  saveContact: (id: string, body: unknown) =>
    request<{ revision: string }>(
      `/contacts/${encodeURIComponent(id)}`,
      undefined,
      "PUT",
      body,
    ),
  send: (id: string, body: unknown) =>
    request<{ revision: string }>(
      `/conversations/${encodeURIComponent(id)}/messages`,
      undefined,
      "POST",
      body,
    ),
};
