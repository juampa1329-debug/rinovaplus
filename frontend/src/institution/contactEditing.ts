import type { Client } from "../shared/demo";

const fields = {
  name: "Nombre visible",
  phone: "Teléfono",
  city: "Ciudad",
  schedule: "Jornada informada",
  stage: "Etapa",
  tags: "Etiquetas",
  notes: "Notas internas",
  type: "Tipo de contacto",
  interests: "Intereses del contacto",
} as const;

export function contactConflicts(base: Client, draft: Client, current: Client) {
  const result: {
    key: string;
    label: string;
    saved: string;
    edited: string;
  }[] = [];
  for (const key of Object.keys(fields) as (keyof typeof fields)[]) {
    if (
      draft[key] !== base[key] &&
      current[key] !== base[key] &&
      current[key] !== draft[key]
    )
      result.push({
        key,
        label: fields[key],
        saved: current[key],
        edited: draft[key],
      });
  }
  for (const key of new Set([
    ...Object.keys(base.customValues),
    ...Object.keys(draft.customValues),
  ])) {
    if (
      draft.customValues[key] !== base.customValues[key] &&
      current.customValues[key] !== base.customValues[key] &&
      current.customValues[key] !== draft.customValues[key]
    )
      result.push({
        key: `custom:${key}`,
        label: key,
        saved: current.customValues[key] ?? "",
        edited: draft.customValues[key] ?? "",
      });
  }
  return result;
}

// Called only after the operator reviews the current saved values. Never saves.
export function rebaseReviewedContact(
  base: Client,
  draft: Client,
  current: Client,
): Client {
  const result = { ...current, customValues: { ...current.customValues } };
  for (const key of Object.keys(fields) as (keyof typeof fields)[])
    if (draft[key] !== base[key]) result[key] = draft[key];
  for (const key of new Set([
    ...Object.keys(base.customValues),
    ...Object.keys(draft.customValues),
  ])) {
    if (draft.customValues[key] === base.customValues[key]) continue;
    if (draft.customValues[key] === undefined) delete result.customValues[key];
    else result.customValues[key] = draft.customValues[key];
  }
  return result;
}
