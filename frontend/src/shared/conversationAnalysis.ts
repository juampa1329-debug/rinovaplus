import type { Thread } from "./demo";
export type ConversationAnalysis = {
  temperature: "Frío" | "Tibio" | "Caliente" | "Sin evidencia";
  risk: "Bajo" | "Medio" | "Alto" | "No evaluable";
  humanRequested: boolean;
  waiting: string;
  summary: string;
  evidence: string[];
  nextAction: string;
};
function unquoted(value: string): string {
  return value
    .replace(/"[^"]*"|“[^”]*”|‘[^’]*’|'[^']*'/g, "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}
export function analyzeConversation(thread?: Thread): ConversationAnalysis {
  const incoming =
    thread?.messages.filter((message) => message.direction === "incoming") ??
    [];
  const latest = incoming.at(-1);
  const text = unquoted(latest?.body ?? "");
  const lastMessage = thread?.messages.at(-1);
  const wait = thread?.wait;
  const waiting =
    wait &&
    lastMessage?.id === wait.lastMessageId &&
    lastMessage.direction === "incoming" &&
    Number.isFinite(wait.minutes) &&
    wait.minutes >= 0
      ? `Espera sintética: ${wait.minutes} min · No es un SLA`
      : "Espera no evaluable";
  const humanRequested =
    /(?:prefiero|quiero|necesito|hablar|conversar|solicito|podria).*(?:asesor|humano|persona real)|asesor por favor/.test(
      text,
    ) && !/\b(?:no|nunca)\b.*(?:asesor|humano|persona real)/.test(text);
  let temperature: ConversationAnalysis["temperature"] = "Sin evidencia";
  let risk: ConversationAnalysis["risk"] = "No evaluable";
  let summary = latest
    ? "Sin señal explícita de intención comercial en el último mensaje recibido."
    : "No hay mensajes recibidos para analizar.";
  let nextAction =
    "Revise el contexto y pregunte qué orientación necesita; no asuma intención.";
  if (
    /no me interesa|no (?:quiero|deseo) (?:inscrib|matricul|continuar)|no continuare|ya no (?:me interesa|quiero (?:inscrib|matricul|continuar))|dejo la conversacion|no me contacten|nunca.*(?:inscrib|matricul)/.test(
      text,
    )
  ) {
    temperature = "Frío";
    risk = "Alto";
    summary =
      "Rechazo o intención de no continuar expresados en el último mensaje; señal posible de abandono, no predicción.";
    nextAction =
      "Revise la negativa y respete la decisión; no programe recontacto automático.";
  } else if (
    /lo pensare|no estoy seguro|mas adelante|tengo dudas|comparando/.test(text)
  ) {
    risk = "Medio";
    summary = "Duda o aplazamiento explícitos; intención no confirmada.";
    nextAction = "Aclare la duda y acuerde con la persona si desea continuar.";
  } else if (!/\b(?:no|nunca|ni|sin)\b/.test(text)) {
    if (
      /quiero (?:inscribirme|matricularme)|listo para (?:inscribirme|matricularme)|como me inscribo/.test(
        text,
      )
    ) {
      temperature = "Caliente";
      risk = "Bajo";
      summary =
        "Intención explícita de inscripción en el último mensaje, sin garantía de conversión.";
      nextAction =
        "Confirme los requisitos con un humano; la demo no registra matrículas ni pagos.";
    } else if (
      /me interesa|quiero conocer|quisiera (?:conocer|revisar)|informacion|jornada/.test(
        text,
      )
    ) {
      temperature = "Tibio";
      risk = "Bajo";
      summary =
        "Interés informativo explícito; todavía no confirma inscripción.";
      nextAction =
        "Responda la consulta y confirme el siguiente paso con la persona.";
    }
  }
  if (humanRequested)
    nextAction = "Priorice la revisión humana solicitada. " + nextAction;
  return {
    temperature,
    risk,
    humanRequested,
    waiting,
    summary,
    evidence: latest ? [latest.body] : [],
    nextAction,
  };
}
