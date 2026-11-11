import { useEffect, useState } from "react";
import { useWorkspaceState } from "../shared/workspaceSession";
import { usePanelEntrance } from "../shared/usePanelEntrance";
import { Badge, EmptyState } from "../shared/ui";
import { AiSettingsPanel } from "../modules/ai";
import { ChannelSettings } from "./ChannelSettings";
import { AdmissionsSettingsPanel } from "../modules/ai/components/AdmissionsPanel";
import { DatabaseSettings } from "./DatabaseSettings";
export const settingsSections = [
  "IA",
  "Canales",
  "Base de datos",
  "APIs",
  "Diagnóstico",
  "Usuarios",
  "Perfil",
  "Seguridad",
] as const;
export type SettingsDraft = {
  assistantName: string;
  style: string;
  instructions: string;
  profileName: string;
  position: string;
  timezone: string;
};
export const initialSettings: SettingsDraft = {
  assistantName: "Asistente virtual",
  style: "Claro y profesional",
  instructions:
    "Identificarse como asistente virtual. Derivar dudas a un asesor.",
  profileName: "",
  position: "",
  timezone: "America/Bogota",
};

export function Settings() {
  const [section] = useWorkspaceState("settingsSection");
  const entranceRef = usePanelEntrance(section);
  const [health, setHealth] = useState("");
  useEffect(() => {
    if (section !== "Diagnóstico") return;
    const controller = new AbortController();
    void fetch("/health/live", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const value = await response.json();
        if (!controller.signal.aborted)
          setHealth(
            value.mode === "local_sql_copy"
              ? "Servicio disponible"
              : "Servicio no disponible",
          );
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setHealth("No se pudo comprobar el estado.");
      });
    return () => controller.abort();
  }, [section]);
  return (
    <div ref={entranceRef}>
      <section
        className="panel settings-panel"
        aria-labelledby="settings-title"
      >
        <div className="panel-heading">
          <h2 id="settings-title">{section}</h2>
          <Badge>Configuración</Badge>
        </div>
        <AiSettingsPanel section={section} active />
        {section === "IA" && <AdmissionsSettingsPanel />}
        {section === "Canales" && <ChannelSettings />}
        {section === "Base de datos" && <DatabaseSettings />}
        {section === "Diagnóstico" && (
          <>
            <p role="status">{health || "Consultando proceso…"}</p>
            <p>
              Clientes e Inbox informan los errores de conexión en sus
              operaciones. La preparación completa del sistema permanece
              pendiente; este estado no verifica proveedores ni permisos
              empresariales.
            </p>
          </>
        )}
        {["Usuarios", "Perfil", "Seguridad"].includes(section) && (
          <EmptyState title="Identidad pendiente">
            No hay una sesión autenticada ni perfiles de usuarios conectados. La
            administración de cuentas y permisos aún no está disponible.
          </EmptyState>
        )}
      </section>
    </div>
  );
}
