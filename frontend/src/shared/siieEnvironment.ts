// Pin the first backend context for this page lifetime. Never silently retarget
// selected IDs/cursors after a server environment change; reload clears selectors.
export type SiieEnvironment = { base_url: string; fingerprint: string };
let pinned: SiieEnvironment | null = null;
const relevant = (path: string) =>
  /(?:^|\/)siie(?:-registration|\/|$)|import-siie/.test(path);
export function siieHeaders(path: string): Record<string, string> {
  return relevant(path) && pinned
    ? { "X-SIIE-Environment": pinned.fingerprint }
    : {};
}
export function observeSiie(path: string, value: unknown) {
  if (
    !relevant(path) ||
    !value ||
    typeof value !== "object" ||
    !("environment" in value)
  )
    return;
  if ("environment_current" in value && value.environment_current === false)
    return;
  const next = value.environment as SiieEnvironment | null;
  if (
    !next ||
    typeof next.base_url !== "string" ||
    !/^[0-9a-f]{64}$/.test(next.fingerprint)
  )
    return;
  if (pinned && pinned.fingerprint !== next.fingerprint)
    throw new Error(
      "SIIE cambió de entorno. Recarga RinovaPlus y consulta los catálogos nuevos; tus trabajos anteriores se conservan en su entorno original.",
    );
  pinned ??= next;
}
export const siieEnvironment = () => pinned;
