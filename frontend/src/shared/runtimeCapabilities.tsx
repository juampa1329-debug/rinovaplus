import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { Button, Notice } from "./ui";

export const featureNames = [
  "academic",
  "advancedCrm",
  "inboxOperations",
  "assessment",
  "media",
  "externalDelivery",
  "automation",
  "comments",
  "readSequence",
  "providers",
] as const;
type CoreCapabilities = {
  version: "cbn-ui-capabilities-v1";
  profile: "foundation" | "legacy";
  mode: string;
  modules: string[] | null;
  features: Record<(typeof featureNames)[number], boolean>;
  scope: string;
};
export const channelCapabilityNames = [
  "configuration",
  "stageOptions",
  "status",
  "comments",
  "credentials",
  "providerActions",
  "externalDelivery",
  "publicWebhooks",
  "workers",
] as const;
export type ChannelsCapabilities = {
  version: "cbn-ui-capabilities-v2";
  profile: "channels";
  mode: "local_channels_ui";
  modules: ["settings"];
  features: CoreCapabilities["features"];
  scope: "restored_rehearsal_only";
  channels: Record<(typeof channelCapabilityNames)[number], boolean>;
};
export type UiCapabilities = CoreCapabilities | ChannelsCapabilities;
type Runtime = {
  status: "loading" | "ready" | "error";
  capabilities: UiCapabilities;
  reload: () => void;
  actions?: readonly string[];
};
// Reusable components retain their existing legacy contract outside the app root.
// The real entrypoint always uses RuntimeProvider and waits for a verified manifest.
export const legacyCapabilities: CoreCapabilities = {
  version: "cbn-ui-capabilities-v1",
  profile: "legacy",
  mode: "local_demo",
  modules: null,
  features: Object.fromEntries(
    featureNames.map((key) => [key, true]),
  ) as UiCapabilities["features"],
  scope: "existing_local_composition",
};
export const RuntimeContext = createContext<Runtime>({
  status: "ready",
  capabilities: legacyCapabilities,
  reload: () => {},
});
export const useRuntime = () => useContext(RuntimeContext);
export const usePermission = (action: string) => {
  const actions = useContext(RuntimeContext).actions;
  return actions === undefined || actions.includes(action);
};

export function validateCapabilities(value: unknown): UiCapabilities {
  if (!value || typeof value !== "object")
    throw new Error("Invalid capabilities");
  const v = value as UiCapabilities;
  if (v.profile === "channels") {
    if (
      Object.keys(v).length !== 7 ||
      v.version !== "cbn-ui-capabilities-v2" ||
      v.mode !== "local_channels_ui" ||
      v.scope !== "restored_rehearsal_only" ||
      !Array.isArray(v.modules) ||
      v.modules.length !== 1 ||
      v.modules[0] !== "settings" ||
      !v.features ||
      Object.keys(v.features).length !== featureNames.length ||
      featureNames.some((key) => v.features[key] !== false) ||
      !v.channels ||
      Object.keys(v.channels).length !== channelCapabilityNames.length ||
      channelCapabilityNames.some(
        (key) => typeof v.channels[key] !== "boolean",
      ) ||
      [
        "credentials",
        "providerActions",
        "externalDelivery",
        "publicWebhooks",
        "workers",
      ].some(
        (key) =>
          v.channels[key as keyof ChannelsCapabilities["channels"]] !== false,
      )
    )
      throw new Error("Invalid channels capabilities");
    return v;
  }
  if (
    Object.keys(v).length !== 6 ||
    v.version !== "cbn-ui-capabilities-v1" ||
    !["foundation", "legacy"].includes(v.profile) ||
    !v.features ||
    Object.keys(v.features).length !== featureNames.length ||
    featureNames.some((key) => typeof v.features[key] !== "boolean")
  )
    throw new Error("Invalid capabilities");
  if (
    v.profile === "foundation" &&
    (v.mode !== "local_foundation" ||
      v.scope !== "restored_rehearsal_only" ||
      !Array.isArray(v.modules) ||
      v.modules.length !== 4 ||
      !["overview", "clients", "inbox", "settings"].every((key) =>
        v.modules?.includes(key),
      ) ||
      featureNames.some((key) => v.features[key]))
  )
    throw new Error("Invalid foundation capabilities");
  if (
    v.profile === "legacy" &&
    (!["local_demo", "local_sql_copy", "local_readonly_catalog"].includes(
      v.mode,
    ) ||
      v.modules !== null ||
      v.scope !== "existing_local_composition")
  )
    throw new Error("Invalid legacy capabilities");
  return v;
}

export function RuntimeProvider({ children }: { children: ReactNode }) {
  const [value, setValue] = useState<UiCapabilities | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/local/runtime", {
      cache: "no-store",
      headers: { "X-CRM-Local": "1" },
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Capabilities unavailable");
        const next = validateCapabilities(await response.json());
        if (!controller.signal.aborted) {
          setValue(next);
          setFailed(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setValue(null);
          setFailed(true);
        }
      });
    return () => controller.abort();
  }, [attempt]);
  const reload = () => {
    setValue(null);
    setFailed(false);
    setAttempt((n) => n + 1);
  };
  if (!value)
    return (
      <main className="public-main">
        <section className="panel">
          <Notice error={failed}>
            {failed
              ? "No se pudo comprobar la disponibilidad de las funciones."
              : "Comprobando funciones disponibles…"}
          </Notice>
          {failed && (
            <Button variant="secondary" onClick={reload}>
              Reintentar disponibilidad
            </Button>
          )}
        </section>
      </main>
    );
  return (
    <RuntimeContext.Provider
      value={{
        status: value ? "ready" : failed ? "error" : "loading",
        capabilities: value ?? legacyCapabilities,
        reload,
      }}
    >
      {children}
    </RuntimeContext.Provider>
  );
}
