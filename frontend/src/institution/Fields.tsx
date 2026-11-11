import { Field, SelectField, TextArea } from "../shared/ui";
import type { Document, FieldSpec } from "./api";

export function at(value: Document, path: string): unknown {
  return path
    .split(".")
    .reduce<unknown>(
      (node, key) =>
        node && typeof node === "object" ? (node as Document)[key] : undefined,
      value,
    );
}
export function update(value: Document, path: string, next: unknown): Document {
  const result = structuredClone(value);
  const keys = path.split(".");
  let node = result;
  keys.slice(0, -1).forEach((key) => {
    if (!node[key] || typeof node[key] !== "object") node[key] = {};
    node = node[key] as Document;
  });
  node[keys.at(-1)!] = next;
  return result;
}
export function TypedFields({
  specs,
  value,
  onChange,
  prefix,
  disabled = false,
}: {
  specs: FieldSpec[];
  value: Document;
  onChange: (next: Document) => void;
  prefix: string;
  disabled?: boolean;
}) {
  return (
    <div className="institution-fields">
      {specs.map((spec) => {
        const current = at(value, spec.path),
          id = `${prefix}-${spec.path}`,
          change = (v: unknown) => onChange(update(value, spec.path, v));
        if (spec.type === "boolean")
          return (
            <label key={id} className="institution-check">
              <input
                id={id}
                type="checkbox"
                checked={current === true}
                disabled={disabled || spec.read_only}
                onChange={(event) => change(event.target.checked)}
              />
              {spec.label}
            </label>
          );
        if (spec.options?.length)
          return (
            <SelectField
              key={id}
              id={id}
              label={spec.label}
              value={current == null ? "" : String(current)}
              disabled={disabled || spec.read_only}
              options={[
                ...(spec.nullable
                  ? [{ value: "", label: "Sin proveedor de respaldo" }]
                  : []),
                ...spec.options.map((option) => ({
                  value: String(option),
                  label: String(option),
                })),
              ]}
              onChange={(event) =>
                change(
                  event.target.value === "" && spec.nullable
                    ? null
                    : event.target.value,
                )
              }
            />
          );
        if (spec.multiline)
          return (
            <TextArea
              key={id}
              id={id}
              label={spec.label}
              value={String(current ?? "")}
              maxLength={spec.max_length}
              disabled={disabled || spec.read_only}
              onChange={(event) => change(event.target.value)}
            />
          );
        return (
          <Field
            key={id}
            id={id}
            label={spec.label}
            type={
              spec.type === "integer" || spec.type === "number"
                ? "number"
                : "text"
            }
            value={current == null ? "" : String(current)}
            min={spec.minimum}
            max={spec.maximum}
            step={spec.type === "number" ? "any" : undefined}
            maxLength={spec.max_length}
            readOnly={spec.read_only}
            disabled={disabled}
            hint={
              spec.read_only ? "Se configura en APIs y modelos." : undefined
            }
            onChange={(event) =>
              change(
                spec.type === "integer" || spec.type === "number"
                  ? Number(event.target.value)
                  : event.target.value,
              )
            }
          />
        );
      })}
    </div>
  );
}
