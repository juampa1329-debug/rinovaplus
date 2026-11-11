export interface AdmissionPeriod {
  id: number;
  label: string;
  active: boolean;
}
export interface AdmissionState {
  id: number;
  label: string;
}
export interface AdmissionPage<T> {
  items: T[];
  offset: number;
  limit: number;
  hasMore: boolean;
}
export interface Applicant {
  id: number;
  name: string;
  periodId: number;
  period: string;
  offerId: number | null;
  offerPeriodId: number | null;
  offerPeriod: string | null;
  programId: number | null;
  program: string | null;
  programSchedule: string | null;
  registeredAt: string;
  sourceConfirmed: boolean;
}
export interface StudentMatch {
  id: number;
  name: string;
  offerId: number;
  periodId: number | null;
  period: string | null;
  program: string | null;
}
export interface HistoricalFollowup {
  id: number;
  body: string;
  truncated: boolean;
  date: string | null;
  dueDate: string | null;
  stateId: number;
  state: string | null;
}
export interface Followup {
  id: string;
  body: string;
  stateId: number;
  state: string | null;
  dueDate: string | null;
  revision: number;
  createdAt: string;
  updatedAt: string;
}
export interface ApplicantDetail {
  applicant: Applicant & {
    documentTypeId: number;
    document: string;
    mobile: string;
    phone: string | null;
    email: string | null;
  };
  schedules: { id: number; scheduleId: number; label: string }[];
  matchingAvailable: boolean;
  matches: AdmissionPage<StudentMatch>;
  history: AdmissionPage<HistoricalFollowup>;
}
export interface FollowupInput {
  operationId: string;
  expectedRevision: number;
  body: string;
  stateId: number;
  dueDate: string | null;
}
export class AdmissionsError extends Error {
  constructor(public status: number) {
    super(
      status === 409
        ? "El seguimiento cambió. Recargue los datos; su borrador se conserva."
        : "No fue posible completar la operación. Intente nuevamente.",
    );
  }
}
async function request<T>(
  path: string,
  signal?: AbortSignal,
  method = "GET",
  body?: FollowupInput,
): Promise<T> {
  const response = await fetch(`/api/local/admissions${path}`, {
    method,
    signal,
    cache: "no-store",
    headers: {
      "X-CRM-Local": "1",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) throw new AdmissionsError(response.status);
  return response.json() as Promise<T>;
}
export type AdmissionFilterOption = {
  programId: number;
  program: string | null;
  scheduleId: number | null;
  schedule: string | null;
};
export const admissionsApi = {
  filters: (periodId: number, signal?: AbortSignal) =>
    request<{ periodId: number; items: AdmissionFilterOption[] }>(
      `/filters?periodId=${periodId}`,
      signal,
    ),
  periods: (signal?: AbortSignal) =>
    request<{
      items: AdmissionPeriod[];
      activePeriodId: number | null;
      selectionRequired: boolean;
    }>("/periods", signal),
  states: (signal?: AbortSignal) =>
    request<{ items: AdmissionState[] }>("/followup-states", signal),
  applicants: (
    periodId: number,
    query: string,
    offset: number,
    signal?: AbortSignal,
    filters: { programId?: number; scheduleId?: number } = {},
  ) =>
    request<AdmissionPage<Applicant> & { periodId: number }>(
      `/applicants?${new URLSearchParams({
        periodId: String(periodId),
        q: query,
        offset: String(offset),
        ...(filters.programId === undefined
          ? {}
          : { programId: String(filters.programId) }),
        ...(filters.scheduleId === undefined
          ? {}
          : { scheduleId: String(filters.scheduleId) }),
      })}`,
      signal,
    ),
  detail: (
    id: number,
    periodId: number,
    matchOffset: number,
    historyOffset: number,
    signal?: AbortSignal,
  ) =>
    request<ApplicantDetail>(
      `/applicants/${id}?${new URLSearchParams({ periodId: String(periodId), matchOffset: String(matchOffset), historyOffset: String(historyOffset) })}`,
      signal,
    ),
  followups: (id: number, periodId: number, offset = 0, signal?: AbortSignal) =>
    request<AdmissionPage<Followup>>(
      `/applicants/${id}/followups?periodId=${periodId}&offset=${offset}`,
      signal,
    ),
  save: (
    id: number,
    periodId: number,
    followupId: string,
    body: FollowupInput,
    create: boolean,
  ) =>
    request<AdmissionPage<Followup>>(
      `/applicants/${id}/followups/${followupId}?periodId=${periodId}`,
      undefined,
      create ? "POST" : "PUT",
      body,
    ),
};
