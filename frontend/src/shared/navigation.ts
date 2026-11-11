import { useSyncExternalStore } from "react";

export const modules = [
  {
    path: "admissions",
    label: "Admisiones",
    group: "Operación",
    title: "Admisiones",
    phase: "Admisiones",
    description:
      "Aspirantes por período, estudiantes existentes y seguimiento con datos reales.",
  },
  {
    path: "overview",
    label: "Resumen",
    group: "Operación",
    title: "Resumen de admisiones",
    phase: "Gestión",
    description: "Una vista de trabajo para priorizar cada siguiente paso.",
  },
  {
    path: "clients",
    label: "Clientes y prospectos",
    group: "Operación",
    title: "Clientes y oportunidades",
    phase: "Gestión",
    description:
      "Una ficha, un contexto y un siguiente paso para cada contacto.",
  },
  {
    path: "inbox",
    label: "Inbox",
    group: "Operación",
    title: "Conversaciones",
    phase: "Gestión",
    description:
      "Atención humana visible y contexto compartido con la ficha CRM.",
  },
  {
    path: "assistant",
    label: "Asistente",
    group: "Gestión",
    title: "Asistente y automatizaciones",
    phase: "Fase 3",
    description: "Comportamiento transparente, siempre bajo control humano.",
  },
  {
    path: "campaigns",
    label: "Campañas",
    group: "Gestión",
    title: "Campañas de admisiones",
    phase: "Gestión",
    description:
      "Riesgo, seguimiento y audiencias con control de consentimiento.",
  },
  {
    path: "agents",
    label: "Agentes de admisiones",
    group: "Gestión",
    title: "Agentes de admisiones",
    phase: "Gestión",
    description: "Agentes personalizados para orientar cada programa.",
  },
  {
    path: "knowledge",
    label: "Conocimiento",
    group: "Gestión",
    title: "Conocimiento y catálogo",
    phase: "Fases 3 / 7C",
    description: "Fuentes verificables sin reemplazar el catálogo de SIIE.",
  },
  {
    path: "memory",
    label: "Memoria",
    group: "Gestión",
    title: "Memoria del aspirante",
    phase: "Gestión",
    description:
      "Declaraciones con evidencia, contexto y reinicio por conversación.",
  },
  {
    path: "settings",
    label: "Ajustes e integraciones",
    group: "Gestión",
    title: "Ajustes",
    phase: "Configuración",
    description:
      "Configuración visible. Activación y conexión, siempre por separado.",
  },
] as const;

function subscribe(callback: () => void) {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
}
export function useRoute() {
  return useSyncExternalStore(
    subscribe,
    () => window.location.hash.slice(1).replace(/^\//, "") || "overview",
  );
}

export function navigate(path: string) {
  window.location.hash = `/${path}`;
}
