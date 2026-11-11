export const sidebarCollapsedKey = "crm-cbn-sidebar-collapsed-v1";
export const inboxContextOpenKey = "crm-cbn-inbox-context-open-v1";

export function readBooleanPreference(key: string, fallback: boolean): boolean {
  try {
    const stored = localStorage.getItem(key);
    if (stored === "true") return true;
    if (stored === "false") return false;
  } catch {
    // Visual controls still use their default when storage is unavailable.
  }
  return fallback;
}

export function writeBooleanPreference(key: string, value: boolean): void {
  try {
    localStorage.setItem(key, value ? "true" : "false");
  } catch {
    // The current session remains usable without persistent browser storage.
  }
}
