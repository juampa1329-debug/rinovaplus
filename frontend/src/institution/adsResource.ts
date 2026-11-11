import { useCallback, useEffect, useRef, useState } from "react";
import { send, useInstitution } from "./api";

// A save refresh may finish after navigation. Keep results bound to their request view.
export function useAdsResource<T>(path: string) {
  const { session } = useInstitution();
  const token = session.csrf_token,
    key = `${token}:${path}`;
  const current = useRef({ key, sequence: 0, active: true });
  const [result, setResult] = useState<{ key: string; value: T } | null>(null);
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const reload = useCallback(async () => {
    const request = current.current,
      sequence = request.key === key ? ++request.sequence : -1;
    const valid = () =>
      request.key === key &&
      request === current.current &&
      request.active &&
      request.sequence === sequence;
    try {
      const value = await send<T>(path, "GET", undefined, token);
      if (valid()) {
        setResult({ key: request.key, value });
        setFailure(null);
      }
      return value;
    } catch (error) {
      if (valid())
        setFailure({
          key: request.key,
          message:
            error instanceof Error ? error.message : "No se pudo cargar.",
        });
      throw error;
    }
  }, [path, token, key]);
  useEffect(() => {
    const request = { key, sequence: 0, active: true };
    current.current = request;
    void reload().catch(() => {});
    return () => {
      request.active = false;
    };
  }, [reload, key]);
  return {
    value: result?.key === key ? result.value : null,
    error: failure?.key === key ? failure.message : "",
    reload,
  };
}
