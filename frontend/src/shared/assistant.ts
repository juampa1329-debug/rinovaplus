import type { Client, Thread } from "./demo";
import type { SettingsDraft } from "../features/Settings";
import { workflowOf } from "./workflow";

export function validateSettings(draft: SettingsDraft): string | null {
  if (
    !draft.assistantName.trim() ||
    draft.assistantName.trim().length > 80 ||
    !draft.profileName.trim() ||
    draft.profileName.trim().length > 80
  )
    return "Nombre de asistente y perfil ficticio requieren de 1 a 80 caracteres.";
  if (draft.instructions.length > 1000)
    return "Las instrucciones admiten hasta 1000 caracteres.";
  if (
    ![
      "Claro y profesional",
      "Cercano y respetuoso",
      "Breve y directo",
    ].includes(draft.style)
  )
    return "Seleccione un estilo de demostración válido.";
  return null;
}
export function assistantBlockReason(
  thread: Thread,
  reviewed: boolean,
): string | null {
  if (workflowOf(thread).state === "Cerrada")
    return "Hilo cerrado. Reabra la conversación para preparar una respuesta.";
  if (thread.mode !== "human")
    return "Tome control humano para preparar y revisar una plantilla local.";
  if (!reviewed)
    return "Guarde y revise la configuración en Asistente o Ajustes → IA antes de usar plantillas.";
  return null;
}
export function responseExample(
  client: Client,
  settings: SettingsDraft,
): string {
  const program = client.program.includes("· Demo")
    ? client.program
    : "programa ficticio · Demo";
  const opening =
    settings.style === "Cercano y respetuoso"
      ? "Hola, gracias por conversar."
      : settings.style === "Breve y directo"
        ? "Hola."
        : "Hola, gracias por su consulta.";
  return `${opening} Soy ${settings.assistantName.trim()} (asistente virtual de demostración). Podemos revisar con un asesor su interés en ${program}. ¿Qué información desea aclarar? No contamos aquí con catálogo, precios o disponibilidad reales.`;
}
export function responseBinding(
  client: Client,
  thread: Thread,
  configRevision: number,
  contextRevision: number,
): string {
  return JSON.stringify([
    client,
    thread.clientId,
    thread.messages,
    thread.mode,
    workflowOf(thread).revision,
    configRevision,
    contextRevision,
  ]);
}
