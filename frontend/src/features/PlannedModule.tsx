import { useState } from "react";
import { Badge, Button, Notice } from "../shared/ui";
import { navigate } from "../shared/navigation";

const plans: Record<
  string,
  { phase: string; purpose: string; sections: [string, string][]; gate: string }
> = {
  review: {
    phase: "Fase 5",
    purpose: "Separar recepción, revisión humana y aceptación académica.",
    sections: [
      [
        "Solicitud y comprobación",
        "Documento, programa y jornada; datos definitivos tras contrato y privacidad.",
      ],
      [
        "Observaciones del revisor",
        "Pendiente, observado o rechazado con historial y conflicto de edición.",
      ],
      [
        "Registro académico",
        "Bloqueado hasta contrato core, autorización, pruebas de reversión y transacción.",
      ],
    ],
    gate: "Sin solicitudes persistidas, decisiones reales o escritura core. Fase 1, P-011 y aceptación conectada de fases 4–5 pendientes; el formulario y la revisión LOCAL no prueban integración.",
  },
  knowledge: {
    phase: "Fases 3 / 7C",
    purpose:
      "El catálogo académico debe provenir de SIIE; fuentes derivadas nunca fijan precios o matrículas.",
    sections: [
      [
        "Catálogo académico",
        "Lectura autorizada y fuente verificable de programas y jornadas.",
      ],
      [
        "Fuentes y aliases",
        "Metadata, finalidad, formatos y retención por aprobar.",
      ],
      [
        "Evaluación y publicación",
        "Indexar, evaluar y publicar serán acciones separadas; no entrenamiento libre.",
      ],
    ],
    gate: "No se importan documentos, consultan URLs o indexan datos. P-001/P-023 abiertos.",
  },
  memory: {
    phase: "Fase 7C",
    purpose: "Revisar casos autorizados, no crear perfiles por inferencia.",
    sections: [
      [
        "Casos y finalidad",
        "Consentimiento, mínima información y alcance de uso.",
      ],
      [
        "Argumentos y fuentes",
        "Asistencia basada en evidencia, no promesas comerciales inventadas.",
      ],
      [
        "Retención y revisión",
        "Vencimiento, eliminación controlada y responsable de revisión.",
      ],
    ],
    gate: "Sin casos autorizados, almacenamiento, embeddings o modelo elegido. P-008/P-005 pendientes.",
  },
  access: {
    phase: "Fase 1",
    purpose:
      "Entrar con identidad verificada y permisos por acción, recurso y ambiente.",
    sections: [
      [
        "Identidad",
        "Proveedor y método por decidir; no se adopta JWT/OTP por la fuente.",
      ],
      [
        "Sesiones y recuperación",
        "Revocación, recuperación y 2FA probados antes de datos reales.",
      ],
      [
        "Permisos",
        "Invitación de un uso y protección del último administrador; cargo no concede acceso.",
      ],
    ],
    gate: "El prototipo es público local; no ingrese claves. P-026 y decisiones de seguridad pendientes.",
  },
  retention: {
    phase: "Fase 7D",
    purpose:
      "Definir seguimiento estudiantil con el propietario antes de usar datos reales.",
    sections: [
      [
        "Seguimiento",
        "Necesidad institucional y usuarios responsables pendientes.",
      ],
      ["Privacidad", "Finalidad, acceso y retención deben acordarse."],
      [
        "Acciones",
        "Sin scoring, campañas, cobros o contacto automatizado por este mockup.",
      ],
    ],
    gate: "Expansión condicionada posterior al piloto. No consulta estudiantes ni crea seguimiento.",
  },
  corporate: {
    phase: "Fase 7E",
    purpose:
      "Organizar relaciones institucionales con un alcance aún no aprobado.",
    sections: [
      [
        "Directorio",
        "Organizaciones y contactos; contratos/datos por definir.",
      ],
      [
        "Interacciones",
        "Historial y próximos pasos solo tras aceptación de alcance.",
      ],
      [
        "Integración",
        "Convenios, vacantes y facturación no se infieren de la referencia.",
      ],
    ],
    gate: "Expansión condicionada posterior al piloto, sin contratos o datos corporativos reales.",
  },
};

export function PlannedModule({ path }: { path: string }) {
  const plan = plans[path];
  if (!plan) return null;
  return (
    <section className="panel planned-panel">
      <div className="panel-heading">
        <h2>
          {path === "review"
            ? "Alcance conectado pendiente"
            : "Alcance previsto"}
        </h2>
        <Badge>
          {plan.phase} ·{" "}
          {path === "review" ? "Integración pendiente" : "Pendiente"}
        </Badge>
      </div>
      <p className="lead-copy">{plan.purpose}</p>
      <dl className="planned-sections">
        {plan.sections.map(([title, description]) => (
          <div key={title}>
            <dt>{title}</dt>
            <dd>{description}</dd>
          </div>
        ))}
      </dl>
      <Notice>{plan.gate}</Notice>
      {path === "access" && (
        <Button variant="secondary" onClick={() => navigate("settings")}>
          Revisar diseño de Ajustes
        </Button>
      )}
    </section>
  );
}

export function CreatorReference() {
  const tabs = [
    "Creadores",
    "Campañas",
    "Recursos",
    "Derechos",
    "Rendimiento",
    "Spark",
    "Auditoría",
  ];
  const [tab, setTab] = useState(tabs[0]);
  const descriptions: Record<string, string> = {
    Creadores:
      "Perfil, plataforma y pipeline. Contacto crea un alcance planned; no equivale a enviar correo.",
    Campañas:
      "Objetivo, presupuesto y entregables. Un brief requiere revisión; no publica campaña.",
    Recursos: "URL y metadatos de contenido autorizado, no carga de archivos.",
    Derechos:
      "Entregables y vencimientos. Aprobar seis meses no valida automáticamente un contrato.",
    Rendimiento:
      "Puntuación, reuso y permisos requieren reglas verificables, no métricas inventadas.",
    Spark:
      "Revisión previa separada de derechos y publicación. No se publican anuncios.",
    Auditoría:
      "Eventos inmutables y referencias, con permisos y retención por definir.",
  };
  return (
    <section className="panel planned-panel">
      <Notice>
        CRM de creadores es distinto de Clientes. Fase 7F condicionada;
        necesidad institucional y permisos aún no aceptados.
      </Notice>
      <nav
        className="horizontal-tabs"
        aria-label="Referencia de CRM de creadores"
      >
        {tabs.map((item) => (
          <button
            key={item}
            aria-current={tab === item ? "page" : undefined}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </nav>
      <h2>{tab}</h2>
      <p className="lead-copy">{descriptions[tab]}</p>
      <p>
        Esta vista permite revisar la estructura de las referencias. No hay
        formularios de ejecución, scoring, recursos o registros reales.
      </p>
    </section>
  );
}
