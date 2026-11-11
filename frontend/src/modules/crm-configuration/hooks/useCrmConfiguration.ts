import { useCallback, useEffect, useRef, useState } from "react";
import type { CrmConfig } from "../../../shared/crm";
import { ClientsError } from "../../clients/api/clientsApi";
import {
  crmConfigurationApi,
  type ConfigurationSnapshot,
} from "../api/crmConfigurationApi";
export function useCrmConfiguration() {
  const [config, setConfig] = useState<CrmConfig>({
    stages: [],
    tags: [],
    fields: [],
  });
  const [revision, setRevision] = useState("");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const attempt = useRef<{
    key: string;
    operation: string;
    revision: string;
  } | null>(null);
  const busy = useRef(false);
  const sequence = useRef(0);
  const accept = useCallback((value: ConfigurationSnapshot) => {
    setConfig(value.config);
    setRevision(value.revision);
    setReady(true);
    setError("");
  }, []);
  async function reload(signal?: AbortSignal) {
    if (busy.current) return;
    const token = ++sequence.current;
    try {
      const value = await crmConfigurationApi.read(signal);
      if (signal?.aborted || token !== sequence.current) return;
      accept(value);
    } catch {
      if (!signal?.aborted && token === sequence.current)
        setError(
          "No se pudo cargar la configuración CRM. Las fichas y sus borradores se conservan.",
        );
    }
  }
  useEffect(() => {
    const controller = new AbortController();
    const token = ++sequence.current;
    void crmConfigurationApi
      .read(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted && token === sequence.current)
          accept(value);
      })
      .catch(() => {
        if (!controller.signal.aborted && token === sequence.current)
          setError(
            "No se pudo cargar la configuración CRM. Las fichas y sus borradores se conservan.",
          );
      });
    return () => controller.abort();
  }, [accept]);
  async function save(value: CrmConfig) {
    if (!ready || busy.current)
      throw new Error("La configuración CRM todavía no está disponible.");
    busy.current = true;
    sequence.current++;
    const key = JSON.stringify(value);
    if (attempt.current?.key !== key || attempt.current.revision !== revision)
      attempt.current = { key, operation: crypto.randomUUID(), revision };
    try {
      const result = await crmConfigurationApi.save(
        value,
        attempt.current.revision,
        attempt.current.operation,
      );
      accept(result);
      attempt.current = null;
      setError("");
    } catch (failure) {
      if (failure instanceof ClientsError && failure.status === 409) {
        busy.current = false;
        await reload();
        attempt.current = null;
      }
      throw failure;
    } finally {
      busy.current = false;
    }
  }
  return { config, ready, revision, error, save, reload };
}
