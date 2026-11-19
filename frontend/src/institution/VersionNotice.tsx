import { useEffect, useState } from "react";
import { allowNavigation } from "./drafts";
import { foregroundPolling } from "./readCoordinator";

export function VersionNotice() {
  const [available, setAvailable] = useState(false);
  useEffect(() => {
    const build = document.querySelector<HTMLMetaElement>(
      'meta[name="rinova-build"]',
    )?.content;
    let active = true,
      running = false,
      lastCheck = 0;
    const failed = () => setAvailable(true);
    const check = async () => {
      if (
        !build ||
        !foregroundPolling() ||
        running ||
        Date.now() - lastCheck < 30_000
      )
        return;
      lastCheck = Date.now();
      running = true;
      try {
        const response = await fetch("/frontend-version.json", {
          cache: "no-store",
          signal: AbortSignal.timeout(5000),
        });
        if (response.ok) {
          const next = (await response.json()) as { build?: unknown };
          if (active && typeof next.build === "string" && next.build !== build)
            setAvailable(true);
        }
      } catch {
        /* Offline is not evidence of a new release. */
      } finally {
        running = false;
      }
    };
    const timer = window.setInterval(() => void check(), 60_000);
    window.addEventListener("focus", check);
    window.addEventListener("vite:preloadError", failed);
    document.addEventListener("visibilitychange", check);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener("focus", check);
      window.removeEventListener("vite:preloadError", failed);
      document.removeEventListener("visibilitychange", check);
    };
  }, []);
  if (!available) return null;
  return (
    <aside className="version-notice" role="status">
      <strong>Hay una actualización de RinovaPlus.</strong>
      <span>
        Guarda tus cambios antes de recargar para cargar los archivos nuevos.
      </span>
      <button
        type="button"
        onClick={() => {
          if (allowNavigation()) window.location.reload();
        }}
      >
        Recargar RinovaPlus
      </button>
    </aside>
  );
}
