import clientFixtures from "../../../backend/app/client_fixtures.json";
import type { Client, Thread } from "../shared/demo";
export {
  appendLocalMessage,
  emptyApplication,
  emptyClient,
  filterClients,
  validateApplication,
  validateClient,
} from "../shared/demo";
export const programs = [
  "Auxiliar administrativo · Demo",
  "Asistencia contable · Demo",
  "Atención a la primera infancia · Demo",
];
export const schedules = [
  "Diurna · Demo",
  "Nocturna · Demo",
  "Sabatina · Demo",
];

export function seedClients(): Client[] {
  return structuredClone(clientFixtures);
}

export function seedThreads(): Thread[] {
  return [
    {
      clientId: "demo-1",
      channel: "WhatsApp",
      wait: { lastMessageId: "a3", minutes: 18 },
      unread: true,
      mode: "ai",
      messages: [
        {
          id: "a1",
          body: "Hola. Quiero conocer el programa de auxiliar administrativo.",
          direction: "incoming",
        },
        {
          id: "a2",
          body: "Soy el asistente virtual de demostración. Un asesor puede orientarle sobre la jornada.",
          direction: "outgoing",
        },
        {
          id: "a3",
          body: "Me interesa la jornada. Prefiero conversar con un asesor.",
          direction: "incoming",
        },
      ],
    },
    {
      clientId: "demo-2",
      channel: "Facebook",
      unread: false,
      mode: "human",
      messages: [
        {
          id: "b1",
          body: "Quiero inscribirme. Quisiera revisar el formulario antes de continuar.",
          direction: "incoming",
        },
      ],
    },
    {
      clientId: "demo-3",
      channel: "Instagram",
      unread: true,
      mode: "ai",
      messages: [
        {
          id: "c1",
          body: "Ya no me interesa la jornada sabatina. No continuaré.",
          direction: "incoming",
        },
      ],
    },
    {
      clientId: "demo-4",
      channel: "TikTok",
      unread: false,
      mode: "human",
      messages: [
        {
          id: "d1",
          body: "Mensaje saliente ficticio. No hay respuesta recibida.",
          direction: "outgoing",
        },
      ],
    },
  ];
}
