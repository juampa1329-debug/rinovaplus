import type { ReviewRecord } from "../shared/review";
import type { OperationRecord } from "../shared/operations";
import type { SocialComment } from "../shared/comments";
import type { CrmConfig } from "../shared/crm";
import { programs, schedules } from "./legacyData";
export function seedReviews(): ReviewRecord[] {
  return (["pending", "observed", "rejected"] as const).map(
    (status, index) => ({
      id: `review-demo-${index + 1}`,
      name: `Aspirante Demo ${["A", "B", "C"][index]}`,
      email: index === 1 ? "" : `aspirante-${index + 1}@example.invalid`,
      program: programs[index],
      schedule: schedules[index],
      syntheticConfirmed: true,
      status,
      history: [
        {
          status: "pending",
          reason:
            "Fixture independiente del formulario; no solicitud recibida.",
          at: "",
          actor: "Escenario sintético",
        },
        ...(status === "pending"
          ? []
          : [
              {
                status: "in_review" as const,
                reason: "Revisión ilustrativa previa.",
                at: "",
                actor: "Revisor ficticio",
              },
              {
                status,
                reason:
                  status === "observed"
                    ? "Correo de ejemplo ausente; observación sintética."
                    : "Rechazo ilustrativo para probar reapertura; no decisión académica real.",
                at: "",
                actor: "Revisor ficticio",
              },
            ]),
      ],
    }),
  );
}

export function seedOperations(): OperationRecord[] {
  const scenarios = [
    [
      "stable",
      "Operación estable · Fixture",
      "Ejercicio de pausa preventiva, sin servicio conectado.",
      "Revisé el retorno manual del escenario sin activar servicios.",
    ],
    [
      "provider",
      "Proveedor no disponible · Fixture",
      "Incidencia ficticia de proveedor. No consulta una API ni cambia credenciales.",
      "Revisé el plan de caída, revocación upstream y rotación; su ejecución sigue pendiente.",
    ],
    [
      "queue",
      "Cola detenida · Fixture",
      "Incidencia ficticia de cola. No existen trabajos o mensajes a procesar aquí.",
      "Revisé el plan de restauración y reconciliación durable; no procesé ni reintenté trabajos.",
    ],
    [
      "uncertain",
      "Envío incierto · Fixture",
      "Resultado ficticio sin confirmación. Nunca reenvía ni declara entrega real.",
      "Revisé la incertidumbre antes de cualquier reenvío; no marqué entrega confirmada.",
    ],
  ];
  return scenarios.map(([id, name, description, check]) => ({
    id: `ops-demo-${id}`,
    name,
    description,
    status: id === "stable" ? "stable" : "degraded",
    incident: id === "stable" ? "none" : "open",
    revision: 0,
    checks: [
      {
        id: "isolation",
        label:
          "Verifiqué el alcance sintético y que no hay datos, proveedores o colas reales.",
        checked: false,
      },
      {
        id: "human",
        label:
          "Revisé preservar el control humano; no cambiar responsables, consentimientos ni reglas core.",
        checked: false,
      },
      { id: "reconciliation", label: check, checked: false },
    ],
    history: [],
  }));
}

export function seedComments(): SocialComment[] {
  return [
    {
      id: "comment-facebook",
      platform: "Facebook",
      author: "Perfil Demo A",
      post: "Publicación ficticia: orientación sobre programas",
      body: "¿Dónde puedo conocer las jornadas?",
      status: "Pendiente",
      replies: [],
    },
    {
      id: "comment-instagram",
      platform: "Instagram",
      author: "Perfil Demo B",
      post: "Publicación ficticia: recorrido de admisiones",
      body: "Me gustaría recibir información del formulario.",
      status: "Pendiente",
      replies: [],
    },
    {
      id: "comment-tiktok",
      platform: "TikTok",
      author: "Perfil Demo C",
      post: "Video ficticio: conoce la experiencia académica",
      body: "¿Hay atención de un asesor?",
      status: "Respondido",
      replies: [
        {
          id: "reply-demo",
          body: "Respuesta ficticia de ejemplo. No publicada.",
        },
      ],
    },
  ];
}
export function fixtureCrmConfig(): CrmConfig {
  return {
    stages: [
      { key: "nuevo", label: "Nuevo", probability: 0 },
      { key: "contactado", label: "Contactado", probability: 20 },
      { key: "interes", label: "Interés", probability: 50 },
      { key: "solicitud", label: "Solicitud preparada", probability: 80 },
    ],
    tags: ["Solicita asesoría", "Formulario", "Contacto nuevo", "Seguimiento"],
    fields: [
      {
        key: "correo",
        label: "Correo de ejemplo",
        type: "Email",
        options: [],
        active: true,
      },
    ],
  };
}
