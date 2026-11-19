// Never persist API results or credentials. Coalesce only concurrent reads.
const pending = new Map<string, Promise<unknown>>();
let retryAt = 0;
const channel =
  typeof BroadcastChannel === "function"
    ? new BroadcastChannel("rinovaplus-read-backoff-v1")
    : undefined;
channel?.addEventListener("message", (event: MessageEvent<unknown>) => {
  if (
    typeof event.data === "number" &&
    Number.isFinite(event.data) &&
    event.data > Date.now() &&
    event.data <= Date.now() + 300_000
  )
    retryAt = Math.max(retryAt, event.data);
});

export function readRetrySeconds() {
  return Math.max(0, Math.ceil((retryAt - Date.now()) / 1000));
}
export function observeReadLimit(header: string | null) {
  const seconds =
    header && /^\d+(\.\d+)?$/.test(header)
      ? Number(header)
      : header
        ? (Date.parse(header) - Date.now()) / 1000
        : 60;
  retryAt = Math.max(
    retryAt,
    Date.now() +
      Math.min(300, Math.max(1, Number.isFinite(seconds) ? seconds : 60)) *
        1000,
  );
  channel?.postMessage(retryAt);
}
export function coordinatedRead<T>(
  key: string,
  load: () => Promise<T>,
): Promise<T> {
  const existing = pending.get(key);
  if (existing) return existing as Promise<T>;
  const promise = load().finally(() => {
    if (pending.get(key) === promise) pending.delete(key);
  });
  pending.set(key, promise);
  return promise;
}
export function foregroundPolling() {
  return !document.hidden && document.hasFocus();
}
