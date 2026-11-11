import { ClientsError } from "../../clients/api/clientsApi";
import type { AdmissionPeriod } from "../../admissions/api/admissionsApi";

export type InstitutionalProfile = {
  givenNames: string;
  firstSurname: string;
  secondSurname: string;
  documentTypeId: number | null;
  document: string;
  email: string;
  aspirationPeriodId: number | null;
};
export const trimIdentitySpaces = (value: string) =>
  value.replace(/^ +| +$/g, "");
export const emptyInstitutionalProfile = (): InstitutionalProfile => ({
  givenNames: "",
  firstSurname: "",
  secondSurname: "",
  documentTypeId: null,
  document: "",
  email: "",
  aspirationPeriodId: null,
});
export type IdentityCatalog = {
  documentTypes: { id: number; label: string; code: string }[];
  periods: {
    items: AdmissionPeriod[];
    activePeriodId: number | null;
    selectionRequired: boolean;
  };
};
export type IdentitySearch = {
  mode: "identity" | "name";
  source: "all" | "crm" | "applicant" | "student";
  name: string;
  period: string;
  program: string;
  offset: number;
};
export type IdentityLookup = {
  mode: "identity" | "name";
  source: IdentitySearch["source"];
  ownContactId: string | null;
  documentTypeId: number | null;
  document: string;
  email: string;
  phone: string;
  name: string;
  periodId: number | null;
  programId: number | null;
  offset: number;
};
export type IdentityCandidate = {
  source: "crm" | "student" | "applicant";
  sourceId: string;
  contactId: string | null;
  name: string;
  givenNames: string | null;
  firstSurname: string | null;
  secondSurname: string | null;
  documentTypeId: number | null;
  document: string | null;
  phone: string | null;
  alternatePhone: string | null;
  email: string | null;
  periodId: number | null;
  period: string | null;
  offerPeriodId: number | null;
  offerPeriod: string | null;
  programId: number | null;
  program: string | null;
  city: string | null;
  reasons: string[];
};
export type IdentityPage = {
  items: IdentityCandidate[];
  offset: number;
  limit: number;
  hasMore: boolean;
  mode: IdentityLookup["mode"];
  criteriaRequired: boolean;
  identityScope: string;
};

async function request<T>(
  path: string,
  signal?: AbortSignal,
  body?: unknown,
): Promise<T> {
  try {
    const response = await fetch("/api/local/crm/identity" + path, {
      method: body ? "POST" : "GET",
      headers: {
        "X-CRM-Local": "1",
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
      signal: signal
        ? AbortSignal.any([signal, AbortSignal.timeout(15000)])
        : AbortSignal.timeout(15000),
    });
    if (!response.ok) throw new ClientsError(response.status);
    return await response.json();
  } catch (failure) {
    if (signal?.aborted) throw failure;
    throw new Error(
      "No se pudo consultar la información institucional. El borrador se conserva; reintente.",
      { cause: failure },
    );
  }
}
export const institutionalIdentityApi = {
  catalog: (signal?: AbortSignal) =>
    request<IdentityCatalog>("/catalog", signal),
  candidates: (body: IdentityLookup, signal?: AbortSignal) =>
    request<IdentityPage>("/candidates", signal, body),
};
export function validateInstitutionalProfile(
  profile?: InstitutionalProfile | null,
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!profile) return errors;
  if (
    profile.givenNames.length > 100 ||
    profile.firstSurname.length > 30 ||
    profile.secondSurname.length > 30
  )
    errors.institutionalName =
      "Revise la longitud de nombres y apellidos informados.";
  if (
    profile.document.length > 16 ||
    !!trimIdentitySpaces(profile.document) !== (profile.documentTypeId !== null)
  )
    errors.institutionalDocument =
      "Seleccione un tipo real y escriba su documento como texto, de hasta 16 caracteres.";
  if (
    profile.email.length > 160 ||
    (trimIdentitySpaces(profile.email) &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimIdentitySpaces(profile.email)))
  )
    errors.institutionalEmail =
      "Escriba un correo válido de hasta 160 caracteres.";
  return errors;
}
