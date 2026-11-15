import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { operationFailure, send, useInstitution } from "./api";
import { ErrorFeedbackContext } from "./ErrorFeedback";

// A save refresh may finish after navigation. Keep results bound to their request view.
export function useAdsResource<T>(path: string) {
  const { session } = useInstitution();
  const report = useContext(ErrorFeedbackContext);
  const token = session.csrf_token,
    key = `${token}:${path}`;
  const current = useRef({ key, sequence: 0, active: true });
  const [result, setResult] = useState<{ key: string; value: T } | null>(null);
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const load = useCallback(
    async (initial = false) => {
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
        if (valid()) {
          const details = operationFailure(error, "No se pudo cargar.");
          setFailure({
            key: request.key,
            message: details.message,
          });
          if (initial) report?.(details);
        }
        throw error;
      }
    },
    [path, token, key, report],
  );
  const reload = useCallback(() => load(), [load]);
  useEffect(() => {
    const request = { key, sequence: 0, active: true };
    current.current = request;
    void load(true).catch(() => {});
    return () => {
      request.active = false;
    };
  }, [load, key]);
  return {
    value: result?.key === key ? result.value : null,
    error: failure?.key === key ? failure.message : "",
    reload,
  };
}
