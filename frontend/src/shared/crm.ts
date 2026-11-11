import type { Client } from "./demo";
import { validateClient } from "./demo";
import { validateInstitutionalProfile } from "../modules/contacts/api/institutionalIdentity";
export type PipelineStage = {
  key: string;
  label: string;
  probability: number | null;
  active?: boolean;
};
export const fieldTypes = [
  "Text",
  "Number",
  "List",
  "Date",
  "Boolean",
  "Email",
  "Phone",
  "URL",
] as const;
export type CustomField = {
  key: string;
  label: string;
  type: (typeof fieldTypes)[number];
  options: string[];
  active: boolean;
  required?: boolean;
};
export const fieldTypeLabels: Record<CustomField["type"], string> = {
  Text: "Texto",
  Number: "Número",
  List: "Lista",
  Date: "Fecha",
  Boolean: "Sí/No",
  Email: "Correo",
  Phone: "Teléfono",
  URL: "URL",
};
export type CrmConfig = {
  stages: PipelineStage[];
  tags: string[];
  inactiveTags?: string[];
  fields: CustomField[];
};
type ConfigResult = { config: CrmConfig; error?: string };
export function seedCrmConfig(): CrmConfig {
  return {
    stages: ["Nuevo", "Contactado", "Interés", "Solicitud preparada"].map(
      (label, index) => ({ key: `stage_${index}`, label, probability: null }),
    ),
    tags: [],
    fields: [],
  };
}
const normalize = (value: string) => value.trim().toLocaleLowerCase("es");
const validKey = (key: string) =>
  /^[a-z][a-z0-9_]{0,39}$/.test(key) &&
  !["constructor", "prototype"].includes(key);
const derivedKeys = [
  "summary",
  "intention",
  "behavior",
  "objections",
  "commitments",
  "next_action",
  "lead_score",
  "lead_temperature",
  "churn_risk",
  "ai_context",
];
export function addStage(
  config: CrmConfig,
  stage: PipelineStage,
): ConfigResult {
  const key = normalize(stage.key);
  const label = stage.label.trim();
  if (!validKey(key) || !label || label.length > 60)
    return {
      config,
      error:
        "Use una clave única (letras, números, guion bajo) y un nombre de hasta 60 caracteres.",
    };
  if (
    config.stages.some(
      (item) => item.key === key || normalize(item.label) === normalize(label),
    )
  )
    return { config, error: "La clave o el nombre de etapa ya existe." };
  if (
    stage.probability !== null &&
    (!Number.isFinite(stage.probability) ||
      stage.probability < 0 ||
      stage.probability > 100)
  )
    return {
      config,
      error: "La probabilidad configurada debe estar entre 0 y 100.",
    };
  return {
    config: {
      ...config,
      stages: [
        ...config.stages,
        { key, label, probability: stage.probability },
      ],
    },
  };
}
export function updateStageProbability(
  config: CrmConfig,
  key: string,
  probability: number | null,
): ConfigResult {
  if (
    !config.stages.some((item) => item.key === key) ||
    (probability !== null &&
      (!Number.isFinite(probability) || probability < 0 || probability > 100))
  )
    return { config, error: "Seleccione una etapa y un valor entre 0 y 100." };
  return {
    config: {
      ...config,
      stages: config.stages.map((item) =>
        item.key === key ? { ...item, probability } : item,
      ),
    },
  };
}
export function addTag(config: CrmConfig, value: string): ConfigResult {
  const tag = value.trim();
  if (!tag || tag.length > 60 || tag.includes(","))
    return {
      config,
      error: "Escriba una etiqueta de hasta 60 caracteres, sin comas.",
    };
  if (config.tags.some((item) => normalize(item) === normalize(tag)))
    return { config, error: "Esta etiqueta ya existe." };
  return { config: { ...config, tags: [...config.tags, tag] } };
}
export function splitTags(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}
export function allTags(config: CrmConfig, clients: Client[]): string[] {
  return [
    ...new Set([
      ...config.tags.filter((tag) => !config.inactiveTags?.includes(tag)),
      ...clients.flatMap((client) => splitTags(client.tags)),
    ]),
  ];
}
export function filterByTag(clients: Client[], tag: string): Client[] {
  return tag === "Todas"
    ? clients
    : clients.filter((client) =>
        splitTags(client.tags).some(
          (item) => normalize(item) === normalize(tag),
        ),
      );
}
export function tagCounts(
  clients: Client[],
  tags: string[],
): Record<string, number> {
  return Object.fromEntries(
    tags.map((tag) => [tag, filterByTag(clients, tag).length]),
  );
}
export function addCustomField(
  config: CrmConfig,
  field: CustomField,
): ConfigResult {
  const key = normalize(field.key);
  const label = field.label.trim();
  const options = field.options.map((item) => item.trim()).filter(Boolean);
  if (
    !validKey(key) ||
    derivedKeys.includes(key) ||
    !label ||
    label.length > 60 ||
    !fieldTypes.includes(field.type)
  )
    return {
      config,
      error: "Use una clave única válida y un nombre de hasta 60 caracteres.",
    };
  if (config.fields.some((item) => item.key === key))
    return {
      config,
      error: "La clave del campo ya existe, incluso si está inactivo.",
    };
  if (
    field.type === "List" &&
    (!options.length ||
      options.length > 30 ||
      options.some((item) => item.length > 80) ||
      new Set(options.map(normalize)).size !== options.length)
  )
    return {
      config,
      error:
        "La lista requiere entre 1 y 30 opciones únicas de hasta 80 caracteres.",
    };
  return {
    config: {
      ...config,
      fields: [
        ...config.fields,
        {
          ...field,
          key,
          label,
          options: field.type === "List" ? options : [],
          active: true,
        },
      ],
    },
  };
}
export function deactivateField(config: CrmConfig, key: string): CrmConfig {
  return {
    ...config,
    fields: config.fields.map((field) =>
      field.key === key ? { ...field, active: false } : field,
    ),
  };
}
function validValue(field: CustomField, value: string): boolean {
  if (!value.trim())
    return (!value || field.type === "Text") && !field.required;
  if (value.length > 500) return false;
  switch (field.type) {
    case "Text":
      return true;
    case "Number":
      return /^-?\d+(\.\d+)?$/.test(value) && Number.isFinite(Number(value));
    case "List":
      return field.options.includes(value);
    case "Boolean":
      return value === "true" || value === "false";
    case "Date":
      return (
        /^\d{4}-\d{2}-\d{2}$/.test(value) &&
        !Number.isNaN(Date.parse(value)) &&
        new Date(value).toISOString().slice(0, 10) === value
      );
    case "Email":
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
    case "Phone":
      return (
        /^\+?[\d ()-]{5,30}$/.test(value) &&
        value.replace(/\D/g, "").length >= 5
      );
    case "URL": {
      try {
        const url = new URL(value);
        return (
          ["https:", "http:"].includes(url.protocol) &&
          !!url.hostname &&
          !/\s/.test(value) &&
          (!url.port || (Number(url.port) > 0 && Number(url.port) < 65536))
        );
      } catch {
        return false;
      }
    }
  }
}
export function validateCrmClient(
  client: Client,
  config: CrmConfig,
  previous?: Client,
): Record<string, string> {
  const errors: Record<string, string> = {};
  Object.assign(
    errors,
    validateInstitutionalProfile(client.institutionalProfile),
  );
  const base = validateClient(client);
  if (base) errors.name = base;
  if (
    client.name.length > 100 ||
    client.phone.length > 40 ||
    client.city.length > 100 ||
    client.type.length > 100 ||
    client.interests.length > 300 ||
    client.tags.length > 1000 ||
    client.notes.length > 1000
  )
    errors.details =
      "Uno de los campos supera el límite permitido para la ficha local.";
  if (
    previous?.stage !== client.stage &&
    !config.stages.some(
      (stage) =>
        stage.label === client.stage &&
        (stage.active !== false || previous?.stage === client.stage),
    )
  )
    errors.stage = "Seleccione una etapa configurada.";
  if (
    splitTags(client.tags).some(
      (tag) =>
        (!config.tags.includes(tag) || config.inactiveTags?.includes(tag)) &&
        !splitTags(previous?.tags ?? "").includes(tag),
    )
  )
    errors.tags = "Seleccione etiquetas activas configuradas.";
  for (const field of config.fields.filter((item) => item.active))
    if (!validValue(field, client.customValues[field.key] ?? ""))
      errors[field.key] =
        `Revise ${field.label}: valor no válido para ${fieldTypeLabels[field.type]}.`;
  return errors;
}
