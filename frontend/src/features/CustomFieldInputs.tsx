import type { CustomField } from "../shared/crm";
import { Field, SelectField } from "../shared/ui";
export function CustomFieldInputs({
  fields,
  values,
  errors,
  onChange,
}: {
  fields: CustomField[];
  values: Record<string, string>;
  errors: Record<string, string>;
  onChange: (key: string, value: string) => void;
}) {
  return (
    <div className="form-grid">
      {fields
        .filter((field) => field.active)
        .map((field) => {
          const id = `client-custom-${field.key}`;
          const value = values[field.key] ?? "";
          if (field.type === "Boolean")
            return (
              <SelectField
                key={field.key}
                id={id}
                label={field.label + (field.required ? " (obligatorio)" : "")}
                options={["Sin definir", "Sí", "No"]}
                value={
                  value === "true"
                    ? "Sí"
                    : value === "false"
                      ? "No"
                      : "Sin definir"
                }
                error={errors[field.key]}
                onChange={(event) =>
                  onChange(
                    field.key,
                    event.target.value === "Sí"
                      ? "true"
                      : event.target.value === "No"
                        ? "false"
                        : "",
                  )
                }
              />
            );
          if (field.type === "List")
            return (
              <div className="field" key={field.key}>
                <label htmlFor={id}>
                  {field.label}
                  {field.required ? " (obligatorio)" : ""}
                </label>
                <select
                  id={id}
                  value={value}
                  aria-invalid={!!errors[field.key]}
                  aria-describedby={
                    errors[field.key] ? `${id}-error` : undefined
                  }
                  onChange={(event) => onChange(field.key, event.target.value)}
                >
                  <option value="">Sin definir</option>
                  {field.options.map((option) => (
                    <option key={option}>{option}</option>
                  ))}
                </select>
                {errors[field.key] && (
                  <small className="field-error" id={`${id}-error`}>
                    {errors[field.key]}
                  </small>
                )}
              </div>
            );
          const type =
            field.type === "Date"
              ? "date"
              : field.type === "Number"
                ? "number"
                : field.type === "Email"
                  ? "email"
                  : field.type === "URL"
                    ? "url"
                    : "text";
          return (
            <Field
              key={field.key}
              id={id}
              label={field.label + (field.required ? " (obligatorio)" : "")}
              type={type}
              step={type === "number" ? "any" : undefined}
              maxLength={500}
              hint={
                field.type === "Phone"
                  ? "Ingrese un teléfono con formato válido."
                  : undefined
              }
              value={value}
              error={errors[field.key]}
              onChange={(event) => onChange(field.key, event.target.value)}
            />
          );
        })}
    </div>
  );
}
