import type { Client, Thread } from "../../../shared/demo";
import {
  institutionHeaders,
  institutionUnauthorized,
} from "../../../shared/institutionSession";
import type { ContactLink } from "../../contacts/api/contactMergeApi";
export type ClientSnapshot = {
  clients: Client[];
  threads: Thread[];
  revision: string;
  contactGroups?: ContactLink[];
};
export type ClientResult = { client: Client; revision: string };
export type ClientFilters = {
  city?: string;
  contactType?: string;
  programId?: number;
  program?: string;
};
const root = "/api/local/crm";
export class ClientsError extends Error {
  constructor(public readonly status: number) {
    super(
      status === 409
        ? "Los datos cambiaron. Se actualizó la vista; revise el borrador antes de volver a guardar."
        : status === 422
          ? "Revise los campos y el programa seleccionado. El borrador se conserva."
          : status === 404
            ? "El registro no está disponible. El borrador se conserva."
            : "No se pudo confirmar la operación. El borrador se conserva; vuelva a intentarlo.",
    );
  }
}
async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  try {
    const response = await fetch(root + path, {
      method,
      headers: {
        "X-CRM-Local": "1",
        ...institutionHeaders(),
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
        : AbortSignal.timeout(15000),
    });
    if (!response.ok) {
      institutionUnauthorized(response.status);
      throw new ClientsError(response.status);
    }
    const value = await response.json();
    if (
      !value ||
      typeof value.revision !== "string" ||
      !(Array.isArray(value.clients) || value.client)
    )
      throw new ClientsError(502);
    return value;
  } catch (error) {
    if (signal?.aborted) throw error;
    throw error instanceof ClientsError ? error : new ClientsError(0);
  }
}
export const clientsApi = {
  workspace: (signal?: AbortSignal) =>
    request<ClientSnapshot>("", "GET", undefined, signal),
  list: (
    query = "",
    stage = "Todas",
    tag = "Todas",
    signal?: AbortSignal,
    filters: ClientFilters = {},
  ) =>
    request<ClientSnapshot>(
      "/clients?" +
        new URLSearchParams({
          q: query,
          stage: stage === "Todas" ? "" : stage,
          tag: tag === "Todas" ? "" : tag,
          city: filters.city ?? "",
          contactType: filters.contactType ?? "",
          ...(filters.programId === undefined
            ? {}
            : { programId: String(filters.programId) }),
          program: filters.program ?? "",
        }),
      "GET",
      undefined,
      signal,
    ),
  read: (id: string, signal?: AbortSignal) =>
    request<ClientResult>(
      "/clients/" + encodeURIComponent(id),
      "GET",
      undefined,
      signal,
    ),
  save: (
    client: Client,
    expectedRevision: string,
    create: boolean,
    operationId: string,
    conversationId: string,
  ) =>
    request<ClientSnapshot>(
      "/clients" + (create ? "" : "/" + encodeURIComponent(client.id)),
      create ? "POST" : "PUT",
      { client, expectedRevision, operationId, conversationId },
    ),
  conversation: (id: string, body: unknown) =>
    request<ClientSnapshot>(
      "/conversations/" + encodeURIComponent(id),
      "PUT",
      body,
    ),
  message: (id: string, body: unknown) =>
    request<ClientSnapshot>(
      "/conversations/" + encodeURIComponent(id) + "/messages",
      "POST",
      body,
    ),
};
