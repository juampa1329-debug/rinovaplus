import type { CrmConfig } from "../../../shared/crm";
import {
  institutionHeaders,
  institutionUnauthorized,
} from "../../../shared/institutionSession";
import { ClientsError } from "../../clients/api/clientsApi";
export type ConfigurationSnapshot = { config: CrmConfig; revision: string };
const root = "/api/local/crm/configuration";
async function request(
  method: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<ConfigurationSnapshot> {
  const response = await fetch(root, {
    method,
    headers: {
      "X-CRM-Local": "1",
      ...institutionHeaders(),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
    signal: signal
      ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
      : AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    institutionUnauthorized(response.status);
    const error = new ClientsError(response.status);
    if (response.status === 422)
      error.message =
        "Revise claves, nombres, tipos y opciones. Las definiciones usadas se desactivan y conservan; el borrador no se perdió.";
    throw error;
  }
  const value = await response.json();
  if (
    !value?.config ||
    !Array.isArray(value.config.stages) ||
    !Array.isArray(value.config.tags) ||
    !Array.isArray(value.config.fields) ||
    typeof value.revision !== "string"
  )
    throw new ClientsError(502);
  return value;
}
export const crmConfigurationApi = {
  read: (signal?: AbortSignal) => request("GET", undefined, signal),
  save: (config: CrmConfig, expectedRevision: string, operationId: string) =>
    request("PUT", { config, expectedRevision, operationId }),
};
