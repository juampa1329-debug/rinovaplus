import { useEffect } from "react";
const pending = new Set<symbol>();
export function allowNavigation() {
  return (
    pending.size === 0 ||
    window.confirm(
      "Hay cambios sin guardar. ¿Quieres descartarlos y continuar?",
    )
  );
}
export function useDraftGuard(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return;
    const id = Symbol();
    pending.add(id);
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => {
      pending.delete(id);
      window.removeEventListener("beforeunload", warn);
    };
  }, [dirty]);
}
