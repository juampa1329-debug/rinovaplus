import type { Client } from "../../../shared/demo";
import { ClientsError } from "../../clients/api/clientsApi";

export type ContactLink = {
  mergeId: string;
  sourceContactId: string;
  targetContactId: string;
};
export type ContactGroup = {
  primaryContactId: string;
  primaryConversationId: string;
  primaryContact: Client;
  memberContactIds: string[];
  links: ContactLink[];
  members: {
    contactId: string;
    conversationId: string;
    name: string;
    phone: string;
    channel: string;
  }[];
};
export type MergePreview = {
  sourceContactId: string;
  targetContactId: string;
  fingerprint: string;
  blockedReason: string | null;
  validationError: string | null;
  laterConfirmations: boolean;
  fields: {
    key: string;
    current: unknown;
    alternative: unknown;
    selected: string;
  }[];
  members: ContactGroup["members"];
  source: ContactGroup["members"][number];
};
async function request<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch("/api/local/crm/contact-merges" + path, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store",
    headers: {
      "X-CRM-Local": "1",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: signal
      ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
      : AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new ClientsError(response.status);
  return response.json() as Promise<T>;
}
export const contactMergeApi = {
  group: (id: string, signal?: AbortSignal) =>
    request<ContactGroup>(
      "/contacts/" + encodeURIComponent(id),
      undefined,
      signal,
    ),
  preview: (body: object, undo: boolean, signal?: AbortSignal) =>
    request<MergePreview>(
      undo ? "/undo/preflight" : "/preflight",
      body,
      signal,
    ),
  commit: (body: object, undo: boolean) =>
    request<{ mergeId: string; revision: string; replayed: boolean }>(
      undo ? "/undo" : "",
      body,
    ),
};
