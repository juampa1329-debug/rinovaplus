import type { Client } from "../../../shared/demo";
import type { CrmConfig } from "../../../shared/crm";
import { splitTags } from "../../../shared/crm";
import type { Program } from "../../catalog/model";
import { CustomFieldInputs } from "../../../features/CustomFieldInputs";
import { InstitutionalContact } from "../../contacts/components/InstitutionalContact";
import { Field, SelectField, TextArea, Notice } from "../../../shared/ui";
import { useRuntime } from "../../../shared/runtimeCapabilities";

export function ClientFields({
  client,
  setDraft,
  config,
  programs,
  catalogError,
  tags,
  stages,
  fieldErrors,
  setFeedback,
  onOpenContact,
}: {
  client: Client;
  setDraft: (client: Client) => void;
  config: CrmConfig;
  programs: Program[];
  catalogError: string;
  tags: string[];
  stages: string[];
  fieldErrors: Record<string, string>;
  setFeedback: (value: string) => void;
  onOpenContact?: (id: string) => void;
}) {
  const { features } = useRuntime().capabilities;
  function change(
    key: Exclude<
      keyof Client,
      "customValues" | "programId" | "institutionalProfile"
    >,
    value: string,
  ) {
    setDraft({ ...client, [key]: value });
    setFeedback("");
  }
  return (
    <>
      {" "}
      <div className="form-grid">
        <Field
          id="client-name"
          label="Nombre visible"
          maxLength={100}
          value={client.name}
          error={fieldErrors.name}
          onChange={(event) => change("name", event.target.value)}
        />
        <Field
          id="client-phone"
          label="Teléfono"
          maxLength={40}
          value={client.phone}
          hint="Dato de contacto; no vincula automáticamente una identidad académica."
          onChange={(event) => change("phone", event.target.value)}
        />
        <Field
          id="client-city"
          label="Ciudad"
          maxLength={100}
          value={client.city}
          onChange={(event) => change("city", event.target.value)}
        />
        <SelectField
          id="client-stage"
          label="Etapa"
          error={fieldErrors.stage}
          options={stages.map((stage) => ({
            value: stage,
            label: stage
              ? stage +
                (config.stages.some(
                  (item) => item.label === stage && item.active === false,
                )
                  ? " · inactiva, conservada"
                  : !config.stages.some((item) => item.label === stage)
                    ? " · heredada, conservada"
                    : "")
              : "Seleccione una etapa",
          }))}
          value={client.stage}
          onChange={(event) => change("stage", event.target.value)}
        />
        {features.academic && (
          <SelectField
            id="client-program"
            label="Programa de interés"
            value={client.programId == null ? "" : String(client.programId)}
            options={[
              { value: "", label: "Sin programa seleccionado" },
              ...programs.map((program) => ({
                value: String(program.id),
                label: program.label || `Programa ${program.id}`,
              })),
            ]}
            onChange={(event) => {
              const program = programs.find(
                (item) => String(item.id) === event.target.value,
              );
              setDraft({
                ...client,
                programId: program?.id ?? null,
                program: program?.label ?? "",
              });
            }}
          />
        )}
        <Field
          id="client-schedule"
          label="Jornada informada"
          maxLength={100}
          value={client.schedule}
          onChange={(event) => change("schedule", event.target.value)}
          hint="Texto informado; no confirma una oferta o jornada académica."
        />
        {catalogError && <Notice>{catalogError}</Notice>}
        <Field
          id="client-type"
          label="Tipo de contacto (texto libre)"
          maxLength={100}
          value={client.type}
          onChange={(event) => change("type", event.target.value)}
        />
        <Field
          id="client-interests"
          label="Intereses del contacto"
          maxLength={300}
          value={client.interests}
          onChange={(event) => change("interests", event.target.value)}
        />
      </div>
      {features.academic && (
        <InstitutionalContact
          client={client}
          onChange={setDraft}
          errors={fieldErrors}
          programs={programs}
          onOpenContact={onOpenContact}
        />
      )}
      <fieldset className="tag-picker">
        <legend>Aplicar etiquetas compartidas</legend>
        {tags
          .filter(
            (item) =>
              !config.inactiveTags?.includes(item) ||
              splitTags(client.tags).includes(item),
          )
          .map((item) => (
            <label className="checkbox-label" key={item}>
              <input
                type="checkbox"
                checked={splitTags(client.tags).includes(item)}
                onChange={(event) => {
                  const current = splitTags(client.tags);
                  change(
                    "tags",
                    (event.target.checked
                      ? [...current, item]
                      : current.filter((value) => value !== item)
                    ).join(", "),
                  );
                }}
              />
              {item}
              {config.inactiveTags?.includes(item) &&
                " · inactiva, valor conservado"}
            </label>
          ))}
      </fieldset>
      {!tags.length && (
        <p className="scope-text">
          No hay etiquetas configuradas. Se crean desde Clientes → Configurar
          CRM.
        </p>
      )}
      {fieldErrors.tags && <Notice error>{fieldErrors.tags}</Notice>}
      <p className="scope-text">
        Etiquetas aplicadas: {client.tags || "Sin etiquetas"}
      </p>
      <TextArea
        id="client-notes"
        label="Notas internas"
        maxLength={1000}
        value={client.notes}
        onChange={(event) => change("notes", event.target.value)}
      />
      <h3>Campos personalizados</h3>
      <CustomFieldInputs
        fields={config.fields}
        values={client.customValues}
        errors={fieldErrors}
        onChange={(key, value) => {
          setDraft({
            ...client,
            customValues: { ...client.customValues, [key]: value },
          });
          setFeedback("");
        }}
      />
      {Object.keys(client.customValues).some(
        (key) => !config.fields.some((field) => field.key === key),
      ) && (
        <details className="scope-note">
          <summary>Valores sin definición conservados</summary>
          <p>
            Estos valores no tienen una definición disponible. Se conservan sin
            reinterpretarlos ni permitir cambios.
          </p>
          <dl className="detail-list">
            {Object.entries(client.customValues)
              .filter(
                ([key]) => !config.fields.some((field) => field.key === key),
              )
              .map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{value || "Sin valor"}</dd>
                </div>
              ))}
          </dl>
        </details>
      )}
      {config.fields.some(
        (field) => !field.active && client.customValues[field.key],
      ) && (
        <details className="scope-note">
          <summary>Valores de campos inactivos conservados</summary>
          <dl className="detail-list">
            {config.fields
              .filter(
                (field) => !field.active && client.customValues[field.key],
              )
              .map((field) => (
                <div key={field.key}>
                  <dt>{field.label}</dt>
                  <dd>{client.customValues[field.key]}</dd>
                </div>
              ))}
          </dl>
        </details>
      )}
    </>
  );
}
