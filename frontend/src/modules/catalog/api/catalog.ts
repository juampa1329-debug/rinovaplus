export interface Period {
  id: number;
  label: string;
  startDate: string;
  endDate: string;
  sourceState: boolean;
}
export interface PeriodPage {
  items: Period[];
  page: { limit: number; offset: number; hasMore: boolean };
}
export interface School {
  id: number;
  label: string;
}
export interface Modality {
  id: number;
  label: string;
}
export interface SchoolPage {
  items: School[];
  page: PeriodPage["page"];
}
export interface ModalityPage {
  items: Modality[];
  page: PeriodPage["page"];
}
export interface Program {
  id: number;
  label: string | null;
  schoolId: number;
  modalityId: number;
}
export interface ProgramPage {
  items: Program[];
  page: PeriodPage["page"];
}
export interface ProgramFilters {
  schoolId?: number;
  modalityId?: number;
}
export type CatalogResource = "periods" | "schools" | "modalities" | "programs";
export type CatalogPage = PeriodPage | SchoolPage | ModalityPage | ProgramPage;
const sqlInt = (value: unknown): value is number =>
  typeof value === "number" &&
  Number.isInteger(value) &&
  value >= -2147483648 &&
  value <= 2147483647;
function isDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
    return false;
  const parsed = new Date(value + "T00:00:00Z");
  return (
    !Number.isNaN(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value
  );
}
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return (
    Object.keys(value).length === keys.length &&
    keys.every((key) => Object.hasOwn(value, key))
  );
}
function validatePage(
  value: unknown,
  offset: number,
  resource: CatalogResource,
): CatalogPage {
  if (
    !record(value) ||
    !Array.isArray(value.items) ||
    !record(value.page) ||
    !exactKeys(value, ["items", "page"]) ||
    !exactKeys(value.page, ["limit", "offset", "hasMore"]) ||
    value.page.limit !== 25 ||
    value.page.offset !== offset ||
    typeof value.page.hasMore !== "boolean" ||
    value.items.length > 25 ||
    (value.page.hasMore && value.items.length !== 25)
  )
    throw new Error("Invalid catalog response");
  const ids = new Set<number>();
  let previous: number | undefined;
  for (const item of value.items) {
    if (
      !record(item) ||
      !sqlInt(item.id) ||
      (typeof item.label !== "string" &&
        !(resource === "programs" && item.label === null)) ||
      (resource === "periods"
        ? !exactKeys(item, [
            "id",
            "label",
            "startDate",
            "endDate",
            "sourceState",
          ]) ||
          !isDate(item.startDate) ||
          !isDate(item.endDate) ||
          typeof item.sourceState !== "boolean"
        : resource === "programs"
          ? !exactKeys(item, ["id", "label", "schoolId", "modalityId"]) ||
            !sqlInt(item.schoolId) ||
            !sqlInt(item.modalityId)
          : !exactKeys(item, ["id", "label"])) ||
      ids.has(item.id) ||
      (previous !== undefined && item.id <= previous)
    )
      throw new Error("Invalid catalog response");
    ids.add(item.id);
    previous = item.id;
  }
  return value as unknown as CatalogPage;
}
export function validatePeriodPage(value: unknown, offset: number): PeriodPage {
  return validatePage(value, offset, "periods") as PeriodPage;
}
export function validateSchoolPage(value: unknown, offset: number): SchoolPage {
  return validatePage(value, offset, "schools") as SchoolPage;
}
export function validateModalityPage(
  value: unknown,
  offset: number,
): ModalityPage {
  return validatePage(value, offset, "modalities") as ModalityPage;
}
export function validateProgramPage(
  value: unknown,
  offset: number,
): ProgramPage {
  return validatePage(value, offset, "programs") as ProgramPage;
}
export function catalogOrigin(
  raw = import.meta.env.VITE_CATALOG_API_BASE_URL ?? "",
): string {
  if (raw === "") return "";
  const url = new URL(raw);
  if (
    url.protocol !== "http:" ||
    !["localhost", "127.0.0.1"].includes(url.hostname) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  )
    throw new Error("Invalid catalog origin");
  return url.origin;
}
export async function fetchPeriods(
  token: string,
  offset: number,
  signal: AbortSignal,
): Promise<PeriodPage> {
  return fetchCatalog("periods", token, offset, signal) as Promise<PeriodPage>;
}
export async function fetchCatalog(
  resource: CatalogResource,
  token: string,
  offset: number,
  signal: AbortSignal,
  filters: ProgramFilters = {},
): Promise<CatalogPage> {
  const paths = {
    periods: "/api/v1/catalog/periods",
    schools: "/api/v1/catalog/schools",
    modalities: "/api/v1/catalog/modalities",
    programs: "/api/v1/catalog/programs",
  };
  const query = new URLSearchParams({ limit: "25", offset: String(offset) });
  if (resource === "programs") {
    if (filters.schoolId !== undefined)
      query.set("schoolId", String(filters.schoolId));
    if (filters.modalityId !== undefined)
      query.set("modalityId", String(filters.modalityId));
  }
  const response = await fetch(
    `${catalogOrigin()}${paths[resource]}?${query}`,
    {
      method: "GET",
      headers: {
        "X-CRM-Local": "1",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      signal,
      cache: "no-store",
      credentials: "omit",
      redirect: "error",
    },
  );
  if (!response.ok)
    throw new Error(
      response.status === 401
        ? "Revise la clave de acceso temporal."
        : "El catálogo no está disponible. Intente nuevamente.",
    );
  const value: unknown = await response.json();
  if (resource === "periods") return validatePeriodPage(value, offset);
  if (resource === "schools") return validateSchoolPage(value, offset);
  if (resource === "modalities") return validateModalityPage(value, offset);
  return validateProgramPage(value, offset);
}

async function collectFilterOptions(
  resource: "schools" | "modalities",
  token: string,
  signal: AbortSignal,
): Promise<School[]> {
  const items: School[] = [];
  for (let offset = 0; offset < 1000; offset += 25) {
    signal.throwIfAborted();
    const result = (await fetchCatalog(
      resource,
      token,
      offset,
      signal,
    )) as SchoolPage;
    signal.throwIfAborted();
    if (
      items.length &&
      result.items.length &&
      result.items[0].id <= items[items.length - 1].id
    )
      throw new Error("Invalid filter pages");
    items.push(...result.items);
    if (!result.page.hasMore) return items;
  }
  throw new Error("Filter catalog exceeds local bound");
}
export async function fetchProgramFilterOptions(
  token: string,
  signal: AbortSignal,
): Promise<{ schools: School[]; modalities: Modality[] }> {
  const schools = await collectFilterOptions("schools", token, signal);
  const modalities = await collectFilterOptions("modalities", token, signal);
  return { schools, modalities };
}
