import { recordOperation, workflowOf, type Workflow } from "./workflow";
import type { InstitutionalProfile } from "../modules/contacts/api/institutionalIdentity";
export type Client = {
  id: string;
  programId?: number | null;
  name: string;
  phone: string;
  city: string;
  program: string;
  schedule: string;
  stage: string;
  tags: string;
  notes: string;
  type: string;
  interests: string;
  customValues: Record<string, string>;
  institutionalProfile?: InstitutionalProfile | null;
};

export const stages = ["Nuevo", "Contactado", "Interés", "Solicitud preparada"];
export const programs: string[] = [];
export const schedules: string[] = [];
export function seedClients(): Client[] {
  return [];
}

export function emptyClient(): Client {
  return {
    id: "",
    name: "",
    phone: "",
    city: "",
    program: "",
    schedule: "",
    stage: stages[0],
    tags: "",
    notes: "",
    type: "",
    interests: "",
    customValues: {},
  };
}

export function filterClients(
  clients: Client[],
  query: string,
  stage = "Todas",
): Client[] {
  const normalized = query.trim().toLocaleLowerCase("es");
  return clients.filter(
    (client) =>
      (stage === "Todas" || client.stage === stage) &&
      [client.name, client.phone, client.city, client.program, client.tags]
        .join(" ")
        .toLocaleLowerCase("es")
        .includes(normalized),
  );
}

export function validateClient(client: Client): string | null {
  return client.name.trim() || client.phone.trim()
    ? null
    : "Escriba un nombre visible o un teléfono.";
}

export type Message = {
  id: string;
  body: string;
  direction: "incoming" | "outgoing";
  createdAt?: string;
};
export const messageChannels = [
  "Local",
  "WhatsApp",
  "Facebook",
  "Messenger",
  "Instagram",
  "TikTok",
] as const;
export type Thread = {
  id?: string;
  clientId: string;
  workflow?: Workflow;
  unread: boolean;
  mode: "human" | "ai";
  messages: Message[];
  channel: string;
  wait?: { lastMessageId: string; minutes: number };
};
export function seedThreads(): Thread[] {
  return [];
}

export function appendLocalMessage(thread: Thread, body: string): Thread {
  if (
    !body.trim() ||
    body.trim().length > 4000 ||
    thread.mode !== "human" ||
    workflowOf(thread).state === "Cerrada"
  )
    return thread;
  return recordOperation(
    {
      ...thread,
      wait: undefined,
      messages: [
        ...thread.messages,
        { id: crypto.randomUUID(), body: body.trim(), direction: "outgoing" },
      ],
    },
    "Mensaje añadido al hilo · No enviado",
  );
}

export type ApplicationDraft = {
  name: string;
  email: string;
  program: string;
  schedule: string;
  consent: boolean;
};
export function emptyApplication(): ApplicationDraft {
  return {
    name: "",
    email: "",
    program: "",
    schedule: "",
    consent: false,
  };
}
export function validateApplication(
  draft: ApplicationDraft,
): Partial<Record<keyof ApplicationDraft, string>> {
  const errors: Partial<Record<keyof ApplicationDraft, string>> = {};
  if (!draft.name.trim()) errors.name = "Escriba un nombre ficticio.";
  else if (draft.name.trim().length > 100)
    errors.name = "Use un nombre ficticio de hasta 100 caracteres.";
  if (
    draft.email.trim().length > 160 ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.email.trim())
  )
    errors.email =
      "Escriba un correo de ejemplo válido, como demo@example.invalid.";
  if (!programs.includes(draft.program))
    errors.program = "Seleccione un programa de demostración.";
  if (!schedules.includes(draft.schedule))
    errors.schedule = "Seleccione una jornada de demostración.";
  if (draft.consent !== true)
    errors.consent =
      "Confirme que utilizará solo datos ficticios en esta demostración.";
  return errors;
}
