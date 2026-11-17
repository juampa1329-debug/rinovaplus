import { useState } from "react";
import { Button, Field, SelectField } from "../shared/ui";

export type CrmVariable = {
  token: string;
  label: string;
  source: string;
  field_key?: string;
  example: string;
};
export type VariableBinding = {
  source: string;
  value?: string;
  field_key?: string;
};
export const standardVariables: CrmVariable[] = [
  ["customer_name", "Nombre completo", "Laura Gómez"],
  ["customer_first_name", "Primer nombre", "Laura"],
  ["customer_phone", "Teléfono", "+573000000000"],
  ["customer_email", "Correo", "ejemplo@example.com"],
  ["customer_city", "Ciudad", "Cartagena"],
  ["program", "Programa de interés", "Programa de ejemplo"],
  ["stage", "Etapa CRM", "Nuevo"],
  ["schedule", "Jornada informada", "Jornada de ejemplo"],
  ["campaign_name", "Nombre de campaña", "Información de programas"],
].map(([token, label, example]) => ({ token, label, example, source: token }));

export const templateNames = (text: string) => [
  ...new Set(
    Array.from(text.matchAll(/\{\{\s*([^{}]+?)\s*\}\}/g), (m) => m[1].trim()),
  ),
];

type Composition = {
  body_text: string;
  header_type: string;
  header_text: string;
  footer_text: string;
  buttons: { type: string; text: string }[];
  examples: Record<string, string>;
};
export function sampleValue(
  name: string,
  group: string,
  samples: Record<string, string>,
  variables: CrmVariable[],
) {
  return (
    samples[`${group}:${name}`] ??
    variables.find((v) => v.token === name)?.example ??
    ""
  );
}
export function metaExamples(doc: Composition, variables: CrmVariable[]) {
  return Object.fromEntries([
    ...templateNames(doc.body_text).map((name, i) => [
      `body.${i + 1}`,
      sampleValue(name, "body", doc.examples, variables),
    ]),
    ...(doc.header_type === "TEXT"
      ? templateNames(doc.header_text).map((name, i) => [
          `header.${i + 1}`,
          sampleValue(name, "header", doc.examples, variables),
        ])
      : []),
  ]);
}

export function TemplateVariableFields({
  group,
  text,
  samples,
  variables,
  insert,
  change,
}: {
  group: "body" | "header";
  text: string;
  samples: Record<string, string>;
  variables: CrmVariable[];
  insert: (token: string) => void;
  change: (key: string, value: string) => void;
}) {
  const [selected, setSelected] = useState(variables[0]?.token || "");
  const part = group === "body" ? "cuerpo" : "cabecera";
  return (
    <div className="broadcast-variable-tools">
      <div className="broadcast-insert-row">
        <SelectField
          id={`insert-${group}`}
          label={`Campo del CRM para ${part}`}
          value={selected}
          options={variables.map((v) => ({ value: v.token, label: v.label }))}
          onChange={(e) => setSelected(e.target.value)}
        />
        <Button
          variant="secondary"
          disabled={
            !selected ||
            (group === "header" && templateNames(text).length > 0) ||
            text.length + selected.length + 4 > (group === "body" ? 1024 : 60)
          }
          onClick={() => insert(selected)}
        >
          Insertar en {part}
        </Button>
      </div>
      {templateNames(text).length > 0 && (
        <p className="broadcast-help">
          Ejemplos para la revisión de Meta. Usa datos ficticios; el envío
          tomará el valor de cada contacto del CRM.
        </p>
      )}
      {templateNames(text).map((name, index) => (
        <Field
          key={name}
          id={`sample-${group}-${index}`}
          label={`Ejemplo: ${variables.find((v) => v.token === name)?.label || name} (${part} ${index + 1})`}
          required
          maxLength={1000}
          value={sampleValue(name, group, samples, variables)}
          onChange={(e) => change(`${group}:${name}`, e.target.value)}
        />
      ))}
    </div>
  );
}

export function TemplateChatPreview({
  doc,
  variables,
}: {
  doc: Composition;
  variables: CrmVariable[];
}) {
  const render = (text: string, group: string) =>
    text.replace(
      /\{\{\s*([^{}]+?)\s*\}\}/g,
      (_, name: string) =>
        sampleValue(name.trim(), group, doc.examples, variables) ||
        `[${variables.find((v) => v.token === name.trim())?.label || name.trim()}]`,
    );
  return (
    <aside className="broadcast-preview" aria-label="Vista previa de WhatsApp">
      <div className="broadcast-preview-title">
        <h3>Vista previa</h3>
        <span>Datos de ejemplo</span>
      </div>
      <div className="broadcast-phone">
        <div className="broadcast-phone-header">
          <span className="broadcast-business-avatar" aria-hidden="true">
            CBN
          </span>
          <div>
            <strong>Corporación Bolivariana del Norte</strong>
            <small>WhatsApp · plantilla</small>
          </div>
        </div>
        <div className="broadcast-phone-screen">
          <div className="broadcast-phone-message">
            {doc.header_type === "TEXT" && doc.header_text && (
              <strong>{render(doc.header_text, "header")}</strong>
            )}
            {["IMAGE", "VIDEO", "DOCUMENT"].includes(doc.header_type) && (
              <div className="broadcast-media-example">
                Cabecera:{" "}
                {
                  { IMAGE: "Imagen", VIDEO: "Video", DOCUMENT: "Documento" }[
                    doc.header_type
                  ]
                }
              </div>
            )}
            <p>
              {render(doc.body_text, "body") ||
                "Tu mensaje aparecerá aquí mientras escribes."}
            </p>
            {doc.footer_text && <small>{doc.footer_text}</small>}
            {doc.buttons.length > 0 && (
              <div className="broadcast-preview-buttons">
                {doc.buttons.map((b, i) => (
                  <span key={i}>{b.text || `Botón ${i + 1}`}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      <p className="broadcast-help">
        La vista previa no envía mensajes. Meta revisa y decide la aprobación de
        la plantilla.
      </p>
    </aside>
  );
}

export function templateStatus(value: string) {
  return (
    (
      {
        LOCAL_DRAFT: "Borrador",
        PENDING: "En revisión de Meta",
        APPROVED: "Aprobada por Meta",
        REJECTED: "Rechazada por Meta",
        PAUSED: "Pausada por Meta",
        DISABLED: "Deshabilitada por Meta",
        IN_APPEAL: "En apelación",
      } as Record<string, string>
    )[value] || value
  );
}
export function rejectionReason(value?: string) {
  return value && !["NONE", "NULL", "N/A"].includes(value.trim().toUpperCase())
    ? value
    : "";
}
export function qualityLabel(value?: string) {
  const score = (
    value?.match(/score['"]?\s*:\s*['"]?([A-Z]+)/i)?.[1] ||
    value ||
    "UNKNOWN"
  ).toUpperCase();
  return (
    (
      {
        GREEN: "Alta",
        YELLOW: "Media",
        RED: "Baja",
        UNKNOWN: "Todavía sin calificar",
      } as Record<string, string>
    )[score] || "Todavía sin calificar"
  );
}
