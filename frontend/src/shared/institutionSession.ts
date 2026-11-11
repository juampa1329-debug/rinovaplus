// The institutional entrypoint keeps CSRF in memory; older apps remain unchanged.
let csrf = "";
let expired: (() => void) | undefined;

export function bindInstitutionSession(value: string, onExpired?: () => void) {
  csrf = value;
  expired = onExpired;
}

export function institutionHeaders(): Record<string, string> {
  return csrf ? { "X-CSRF-Token": csrf } : {};
}

export function institutionUnauthorized(status: number) {
  if (status === 401 && csrf) {
    const notify = expired;
    csrf = "";
    expired = undefined;
    notify?.();
  }
}
