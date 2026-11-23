import { useEffect, useState } from "react";
import type { ComponentProps } from "react";
import { Button, Field, Notice, SelectField } from "../shared/ui";
import { ResourceState, useResource } from "./Settings";

export type CrmField = {
  key: string;
  label: string;
  type: string;
  options: string[];
};
export type DemographicFields = Partial<
  Record<"gender" | "birth_date" | "region" | "country", string>
>;
export type AudienceFilters = {
  contact_ids: string[];
  program_ids: number[];
  stages: string[];
  cities: string[];
  tags: string[];
  audience_mode?: "segment" | "contacts";
  last_incoming_bucket?: "any" | "unknown" | "0_29" | "30_59" | "60_89" | "90_plus";
  tag_match?: "all" | "any";
  schedules?: string[];
  contact_types?: string[];
  genders?: string[];
  regions?: string[];
  countries?: string[];
  age_min?: number | null;
  age_max?: number | null;
  custom_fields?: { field_key: string; values: string[]; match?: "exact" | "contains" }[];
};

function TokenField(props: ComponentProps<typeof Field>) {
  const incoming = String(props.value ?? ""),
    [text, setText] = useState(incoming);
  const canonical = (v: string) =>
    v
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .join(",");
  return (
    <Field
      {...props}
      maxLength={2000}
      value={canonical(text) === canonical(incoming) ? text : incoming}
      onChange={(e) => {
        setText(e.target.value);
        props.onChange?.(e);
      }}
    />
  );
}

function Choices({
  label,
  values,
  options,
  onChange,
}: {
  label: string;
  values: string[];
  options: { value: string; label: string }[];
  onChange: (v: string[]) => void;
}) {
  const [search, setSearch] = useState("");
  const visible = options.filter((o) =>
    o.label.toLocaleLowerCase("es").includes(search.toLocaleLowerCase("es")),
  );
  return (
    <fieldset className="broadcast-choices">
      <legend>
        {label}{" "}
        <small>
          {values.length ? `${values.length} seleccionados` : "Todos"}
        </small>
      </legend>
      {options.length > 8 && (
        <Field
          id={`find-${label}`}
          label={`Buscar en ${label.toLocaleLowerCase("es")}`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      )}
      <div className="broadcast-choice-list">
        {visible.map((o) => (
          <label key={o.value}>
            <input
              type="checkbox"
              checked={values.includes(o.value)}
              onChange={(e) =>
                onChange(
                  e.target.checked
                    ? [...values, o.value]
                    : values.filter((v) => v !== o.value),
                )
              }
            />
            <span>{o.label}</span>
          </label>
        ))}
        {!visible.length && (
          <p className="broadcast-help">No hay opciones registradas.</p>
        )}
      </div>
    </fieldset>
  );
}

function People({
  account,
  selected,
  change,
}: {
  account: string;
  selected: string[];
  change: (ids: string[]) => void;
}) {
  const [search, setSearch] = useState(""),
    [query, setQuery] = useState(""),
    [offset, setOffset] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search);
      setOffset(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);
  const data = useResource<{
    items: { contact_id: string; name: string; phone: string }[];
    has_more: boolean;
  }>(
    `broadcasts/accounts/${account}/identities?audience=true&search=${encodeURIComponent(query)}&offset=${offset}`,
  );
  const items = [
    ...new Map(
      (data.value?.items || []).map((v) => [v.contact_id, v]),
    ).values(),
  ];
  return (
    <div className="broadcast-people">
      <Field
        id="audience-people-search"
        label="Buscar personas por nombre o teléfono"
        maxLength={100}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <p>
        {selected.length} personas seleccionadas. Sólo se muestran contactos de
        la cuenta elegida.
      </p>
      {!data.value ? (
        <ResourceState error={data.error} />
      ) : (
        <>
          <div className="broadcast-choice-list">
            {items.map((p) => (
              <label key={p.contact_id}>
                <input
                  type="checkbox"
                  checked={selected.includes(p.contact_id)}
                  aria-label={`Seleccionar a ${p.name}, ${p.phone}`}
                  onChange={(e) =>
                    change(
                      e.target.checked
                        ? [...selected, p.contact_id]
                        : selected.filter((v) => v !== p.contact_id),
                    )
                  }
                />
                <span>
                  {p.name}
                  <small>{p.phone}</small>
                </span>
              </label>
            ))}
            {!items.length && <p>No se encontraron personas.</p>}
          </div>
          <div className="institution-actions">
            <Button
              variant="quiet"
              disabled={!offset}
              onClick={() => setOffset(Math.max(0, offset - 100))}
            >
              Personas anteriores
            </Button>
            <Button
              variant="quiet"
              disabled={!data.value.has_more}
              onClick={() => setOffset(offset + 100)}
            >
              Más personas
            </Button>
          </div>
        </>
      )}
      {data.error && data.value && <Notice error>{data.error}</Notice>}
    </div>
  );
}

export function BroadcastAudience({
  account,
  filters,
  mapping,
  fields,
  programs,
  stages,
  tags,
  facets,
  change,
}: {
  account: string;
  filters: AudienceFilters;
  mapping: DemographicFields;
  fields: CrmField[];
  programs: { program_id: number; name: string }[];
  stages: string[];
  tags: string[];
  facets?: { schedules: string[]; contact_types: string[]; cities: string[] };
  change: (filters: AudienceFilters, mapping: DemographicFields) => void;
}) {
  const update = (part: Partial<AudienceFilters>) =>
    change({ ...filters, ...part }, mapping);
  const split = (value: string) => [
    ...new Set(
      value
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean),
    ),
  ];
  const custom = filters.custom_fields || [];
  return (
    <details className="broadcast-audience" open>
      <summary>Destinatarios y segmentación</summary>
      <p className="broadcast-help">
        Los filtros se combinan: una persona debe cumplir cada grupo elegido.
        Dentro de programas, jornadas o estados basta con coincidir con una
        opción. Vacío incluye todos.
      </p>
      <label className="broadcast-check">
        <input
          type="checkbox"
          checked={
            filters.audience_mode === "contacts" || !!filters.contact_ids.length
          }
          onChange={(e) =>
            update({
              audience_mode: e.target.checked ? "contacts" : "segment",
              contact_ids: [],
            })
          }
        />
        Elegir personas específicas
      </label>
      <SelectField
        id="audience-last-incoming"
        label="Tiempo desde el último mensaje recibido"
        value={filters.last_incoming_bucket || "any"}
        options={[
          { value: "any", label: "Cualquier antigüedad" },
          { value: "unknown", label: "Sin mensaje recibido verificable" },
          { value: "0_29", label: "0–29 días" },
          { value: "30_59", label: "30–59 días" },
          { value: "60_89", label: "60–89 días" },
          { value: "90_plus", label: "90 días o más" },
        ]}
        onChange={(e) => update({ last_incoming_bucket: e.target.value as AudienceFilters["last_incoming_bucket"] })}
      />
      <p className="broadcast-help">Usa la fecha real recibida del canal, en la zona horaria de la campaña. Una preinscripción o gestión administrativa no demuestra una conversación; sin evidencia queda en su grupo propio.</p>
      {(filters.audience_mode === "contacts" || !!filters.contact_ids.length) &&
        (account ? (
          <People
            key={account}
            account={account}
            selected={filters.contact_ids}
            change={(contact_ids) => update({ contact_ids })}
          />
        ) : (
          <Notice>Selecciona primero la cuenta de envío.</Notice>
        ))}
      {filters.audience_mode === "contacts" && !filters.contact_ids.length && (
        <Notice>
          Elige al menos una persona antes de guardar. Una selección vacía nunca
          enviará a toda la cuenta.
        </Notice>
      )}
      <div className="broadcast-filter-grid">
        <Choices
          label="Programas de interés"
          values={filters.program_ids.map(String)}
          options={programs.map((p) => ({
            value: String(p.program_id),
            label: p.name,
          }))}
          onChange={(v) => update({ program_ids: v.map(Number) })}
        />
        <Choices
          label="Estados del CRM"
          values={filters.stages}
          options={stages.map((v) => ({ value: v, label: v }))}
          onChange={(stages) => update({ stages })}
        />
        <Choices
          label="Grupos y etiquetas"
          values={filters.tags}
          options={[...new Set([...tags, ...filters.tags])].map((v) => ({
            value: v,
            label: v,
          }))}
          onChange={(tags) => update({ tags })}
        />
        <SelectField
          id="audience-tag-match"
          label="Coincidencia de grupos"
          value={filters.tag_match || "all"}
          options={[
            { value: "all", label: "Debe tener todos los grupos elegidos" },
            { value: "any", label: "Cualquiera de los grupos elegidos" },
          ]}
          onChange={(e) =>
            update({ tag_match: e.target.value as "all" | "any" })
          }
        />
        <TokenField
          id="audience-schedules"
          label="Jornadas, separadas por coma"
          list="broadcast-schedules"
          value={(filters.schedules || []).join(", ")}
          onChange={(e) => update({ schedules: split(e.target.value) })}
          hint="Ejemplo: Nocturna. Usa el valor declarado en la ficha CRM."
        />
        <TokenField
          id="audience-types"
          label="Tipos de contacto, separados por coma"
          list="broadcast-contact-types"
          value={(filters.contact_types || []).join(", ")}
          onChange={(e) => update({ contact_types: split(e.target.value) })}
          hint="Ejemplo: Aspirante, Estudiante activo. Es información declarada del CRM, no una matrícula verificada."
        />
        <TokenField
          id="audience-cities"
          label="Ciudades, separadas por coma"
          list="broadcast-cities"
          value={filters.cities.join(", ")}
          onChange={(e) => update({ cities: split(e.target.value) })}
        />
      </div>
      {(["schedules", "contact_types", "cities"] as const).map((key) => (
        <datalist key={key} id={`broadcast-${key.replace("_", "-")}`}>
          {(facets?.[key] || []).map((v) => (
            <option key={v} value={v} />
          ))}
        </datalist>
      ))}
      <details className="broadcast-demographics">
        <summary>Género, edad y ubicación</summary>
        <p className="broadcast-help">
          Selecciona qué campos personalizados del CRM contienen estos datos.
          RinovaPlus no los deduce del nombre, la foto o el teléfono. La edad se
          calcula desde una fecha de nacimiento válida.
        </p>
        <div className="broadcast-filter-grid">
          {(
            [
              ["gender", "Campo CRM para género"],
              ["birth_date", "Campo CRM para fecha de nacimiento"],
              ["region", "Campo CRM para departamento o región"],
              ["country", "Campo CRM para país"],
            ] as const
          ).map(([key, label]) => (
            <SelectField
              key={key}
              id={`demographic-${key}`}
              label={label}
              value={mapping[key] || ""}
              options={[
                { value: "", label: "Sin campo configurado" },
                ...fields
                  .filter((f) => key !== "birth_date" || f.type === "Date")
                  .map((f) => ({ value: f.key, label: f.label })),
              ]}
              onChange={(e) => {
                const next = { ...mapping };
                if (e.target.value) next[key] = e.target.value;
                else delete next[key];
                const clear =
                  key === "birth_date"
                    ? { age_min: null, age_max: null }
                    : key === "gender"
                      ? { genders: [] }
                      : key === "region"
                        ? { regions: [] }
                        : { countries: [] };
                change({ ...filters, ...(!e.target.value ? clear : {}) }, next);
              }}
            />
          ))}
          <TokenField
            id="audience-genders"
            label="Géneros, separados por coma"
            disabled={!mapping.gender}
            value={(filters.genders || []).join(", ")}
            onChange={(e) => update({ genders: split(e.target.value) })}
            hint="Ejemplo: Hombre, Mujer. Vacío incluye todos los valores, incluido Sin dato."
          />
          <div className="broadcast-binding">
            {(["age_min", "age_max"] as const).map((key, i) => (
              <Field
                key={key}
                id={`audience-${key}`}
                type="number"
                min={0}
                max={120}
                label={i ? "Edad máxima" : "Edad mínima"}
                disabled={!mapping.birth_date}
                value={filters[key] ?? ""}
                onChange={(e) =>
                  update({
                    [key]:
                      e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            ))}
          </div>
          <TokenField
            id="audience-regions"
            label="Departamentos o regiones, separados por coma"
            disabled={!mapping.region}
            value={(filters.regions || []).join(", ")}
            onChange={(e) => update({ regions: split(e.target.value) })}
          />
          <TokenField
            id="audience-countries"
            label="Países, separados por coma"
            disabled={!mapping.country}
            value={(filters.countries || []).join(", ")}
            onChange={(e) => update({ countries: split(e.target.value) })}
          />
        </div>
      </details>
      <details>
        <summary>Otros campos personalizados</summary>
        {custom.map((f, i) => (
          <div key={i} className="broadcast-custom-filter">
            <SelectField
              id={`custom-filter-${i}`}
              label={`Campo adicional ${i + 1}`}
              value={f.field_key}
              options={[
                { value: "", label: "Selecciona un campo" },
                ...fields.map((f) => ({ value: f.key, label: f.label })),
              ]}
              onChange={(e) =>
                update({
                  custom_fields: custom.map((v, n) =>
                    n === i ? { ...v, field_key: e.target.value } : v,
                  ),
                })
              }
            />
            <TokenField
              id={`custom-values-${i}`}
              label={`Valores permitidos ${i + 1}`}
              value={f.values.join(", ")}
              onChange={(e) =>
                update({
                  custom_fields: custom.map((v, n) =>
                    n === i ? { ...v, values: split(e.target.value) } : v,
                  ),
                })
              }
            />
            <SelectField
              id={`custom-match-${i}`}
              label={`Coincidencia del campo ${i + 1}`}
              value={f.match || "exact"}
              options={[{ value: "exact", label: "Valor completo" }, { value: "contains", label: "Contiene alguno de los valores" }]}
              onChange={(e) => update({ custom_fields: custom.map((v, n) => n === i ? { ...v, match: e.target.value as "exact" | "contains" } : v) })}
            />
            <Button
              variant="quiet"
              onClick={() =>
                update({ custom_fields: custom.filter((_, n) => n !== i) })
              }
            >
              Quitar filtro {i + 1}
            </Button>
          </div>
        ))}
        <Button
          variant="secondary"
          disabled={!fields.length || custom.length >= 20}
          onClick={() =>
            update({
              custom_fields: [
                ...custom,
                { field_key: fields[0]?.key || "", values: [] },
              ],
            })
          }
        >
          Agregar filtro de campo CRM
        </Button>
      </details>
      <p className="broadcast-help">
        Los estados, grupos y campos se administran en{" "}
        <a href="#/clients">CRM → Configurar CRM</a>. La ficha de cada persona
        guarda sus valores. Siempre se excluyen falta de consentimiento, control
        Humano, No contactar y duplicados.
      </p>
    </details>
  );
}
