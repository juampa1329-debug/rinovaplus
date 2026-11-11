import { useEffect, useRef, useState } from "react";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import type { CrmConfig, CustomField } from "../../../shared/crm";
import {
  addStage,
  addTag,
  addCustomField,
  deactivateField,
  fieldTypes,
  fieldTypeLabels,
  updateStageProbability,
  tagCounts,
} from "../../../shared/crm";
import type { Client } from "../../../shared/demo";
import { Button, Field, Notice, SelectField, Badge } from "../../../shared/ui";
import { usePermission } from "../../../shared/runtimeCapabilities";

export function CrmConfiguration({
  config,
  clients,
  onChange,
  onReload,
  revision = "",
  loadError = "",
  ready = true,
  openRequest = 0,
  onOpened,
}: {
  config: CrmConfig;
  clients: Client[];
  onChange: (config: CrmConfig) => void | Promise<void>;
  onReload?: () => void;
  revision?: string;
  loadError?: string;
  ready?: boolean;
  openRequest?: number;
  onOpened?: () => void;
}) {
  const canWrite = usePermission("settings.crm.write");
  const panel = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    if (!openRequest) return;
    // Route heading focus runs first; consume this explicit navigation once.
    const timer = window.setTimeout(() => {
      if (!panel.current) return;
      panel.current.open = true;
      const summary = panel.current.querySelector<HTMLElement>("summary");
      summary?.focus({ preventScroll: true });
      summary?.scrollIntoView?.({ block: "start", behavior: "instant" });
      onOpened?.();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [openRequest, onOpened]);
  const [stageKey, setStageKey] = useWorkspaceField("crm", "stageKey");
  const [stageLabel, setStageLabel] = useWorkspaceField("crm", "stageLabel");
  const [probability, setProbability] = useWorkspaceField("crm", "probability");
  const [probabilityDrafts, setProbabilityDrafts] = useWorkspaceField(
    "crm",
    "probabilityDrafts",
  );
  const [tag, setTag] = useWorkspaceField("crm", "tag");
  const [fieldKey, setFieldKey] = useWorkspaceField("crm", "fieldKey");
  const [fieldLabel, setFieldLabel] = useWorkspaceField("crm", "fieldLabel");
  const [fieldType, setFieldType] = useWorkspaceField("crm", "fieldType");
  const [options, setOptions] = useWorkspaceField("crm", "options");
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [required, setRequired] = useWorkspaceField("crm", "required");
  const tags = config.tags;
  const counts = tagCounts(clients, tags);
  async function accept(
    result: { config: CrmConfig; error?: string },
    success: string,
  ) {
    setError(result.error ?? "");
    setFeedback("");
    if (result.error || saving || !ready) return false;
    setSaving(true);
    try {
      await onChange(result.config);
      setFeedback(success);
      return true;
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "No se pudo guardar. El borrador se conserva.",
      );
      return false;
    } finally {
      setSaving(false);
    }
  }
  return (
    <details ref={panel} className="panel crm-configuration">
      <summary>Configurar CRM local — etapas, etiquetas y campos</summary>
      <p className="scope-text">
        Catálogo compartido en SQL para Clientes y mini CRM. Las etapas,
        etiquetas y campos adoptados provienen de fichas guardadas; no se
        infiere su significado ni una evaluación IA.
      </p>
      <p className="scope-text">
        {ready
          ? `Revisión SQL: ${revision || "disponible"}`
          : "Cargando configuración CRM…"}
      </p>
      {onReload && (
        <Button variant="secondary" disabled={saving} onClick={onReload}>
          Recargar configuración CRM
        </Button>
      )}
      {loadError && <Notice error>{loadError}</Notice>}
      {error && <Notice error>{error}</Notice>}
      {feedback && <Notice>{feedback}</Notice>}
      <fieldset
        disabled={saving || !ready || !canWrite}
        className="configuration-grid"
      >
        <section aria-label="Configurar etapas">
          <h3>Pipeline</h3>
          <p className="scope-text">
            Probabilidad configurada de la etapa; NO es una predicción del
            cliente. Puede quedar sin definir. Las claves y nombres guardados se
            conservan para mantener la historia.
          </p>
          <ul className="configuration-list">
            {config.stages.map((stage) => (
              <li key={stage.key}>
                <span>
                  {stage.label}
                  <small>Clave: {stage.key}</small>
                  <small>
                    {stage.active === false
                      ? "Inactiva; fichas conservadas"
                      : "Activa"}
                  </small>
                </span>
                <Field
                  id={`probability-${stage.key}`}
                  label={`Probabilidad configurada: ${stage.label} (%)`}
                  type="number"
                  min={0}
                  max={100}
                  value={
                    probabilityDrafts[stage.key] ??
                    (stage.probability === null
                      ? ""
                      : String(stage.probability))
                  }
                  hint="Vacío: sin probabilidad definida."
                  onChange={(event) =>
                    setProbabilityDrafts((items) => ({
                      ...items,
                      [stage.key]: event.target.value,
                    }))
                  }
                />
                <Button
                  variant="secondary"
                  onClick={() =>
                    void accept(
                      updateStageProbability(
                        config,
                        stage.key,
                        (probabilityDrafts[stage.key] ??
                          (stage.probability === null
                            ? ""
                            : String(stage.probability))) === ""
                          ? null
                          : Number(
                              probabilityDrafts[stage.key] ?? stage.probability,
                            ),
                      ),
                      "Probabilidad de etapa actualizada.",
                    )
                  }
                >
                  Guardar probabilidad de {stage.label}
                </Button>
                <Button
                  variant="quiet"
                  onClick={() =>
                    void accept(
                      {
                        config: {
                          ...config,
                          stages: config.stages.map((item) =>
                            item.key === stage.key
                              ? { ...item, active: item.active === false }
                              : item,
                          ),
                        },
                      },
                      "Disponibilidad de etapa actualizada.",
                    )
                  }
                >
                  {stage.active === false ? "Activar" : "Desactivar"} etapa{" "}
                  {stage.label}
                </Button>
              </li>
            ))}
          </ul>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (
                await accept(
                  addStage(config, {
                    key: stageKey,
                    label: stageLabel,
                    probability:
                      probability === "" ? null : Number(probability),
                    active: true,
                  }),
                  "Etapa añadida.",
                )
              ) {
                setStageKey("");
                setStageLabel("");
              }
            }}
            noValidate
          >
            <Field
              id="stage-key"
              label="Clave de nueva etapa"
              maxLength={40}
              value={stageKey}
              onChange={(event) => setStageKey(event.target.value)}
            />
            <Field
              id="stage-label"
              label="Nombre de nueva etapa"
              maxLength={60}
              value={stageLabel}
              onChange={(event) => setStageLabel(event.target.value)}
            />
            <Field
              id="stage-probability"
              label="Probabilidad de nueva etapa (%)"
              type="number"
              min={0}
              max={100}
              value={probability}
              onChange={(event) => setProbability(event.target.value)}
            />
            <Button type="submit">Añadir etapa local</Button>
          </form>
        </section>
        <section aria-label="Configurar etiquetas">
          <h3>Etiquetas compartidas</h3>
          <ul className="configuration-list">
            {tags.map((item) => (
              <li key={item}>
                <span>{item}</span>
                <Badge>{counts[item]} fichas</Badge>
                <Button
                  variant="quiet"
                  onClick={() =>
                    void accept(
                      {
                        config: {
                          ...config,
                          inactiveTags: config.inactiveTags?.includes(item)
                            ? config.inactiveTags.filter((tag) => tag !== item)
                            : [...(config.inactiveTags ?? []), item],
                        },
                      },
                      "Disponibilidad de etiqueta actualizada.",
                    )
                  }
                >
                  {config.inactiveTags?.includes(item)
                    ? "Activar"
                    : "Desactivar"}{" "}
                  etiqueta {item}
                </Button>
              </li>
            ))}
          </ul>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (
                await accept(
                  addTag({ ...config, tags }, tag),
                  "Etiqueta añadida.",
                )
              )
                setTag("");
            }}
            noValidate
          >
            <Field
              id="new-tag"
              label="Nueva etiqueta"
              maxLength={60}
              value={tag}
              onChange={(event) => setTag(event.target.value)}
            />
            <Button type="submit">Añadir etiqueta local</Button>
          </form>
        </section>
        <section aria-label="Configurar campos">
          <h3>Campos personalizados</h3>
          <ul className="configuration-list">
            {config.fields.map((field) => (
              <li key={field.key}>
                <span>
                  {field.label}
                  <small>
                    {field.key} · {fieldTypeLabels[field.type]} ·{" "}
                    {field.active ? "Activo" : "Inactivo; valores conservados"}
                    {field.required && " · Obligatorio"}
                  </small>
                </span>
                <Button
                  variant="quiet"
                  onClick={() => {
                    void accept(
                      {
                        config: field.active
                          ? deactivateField(config, field.key)
                          : {
                              ...config,
                              fields: config.fields.map((item) =>
                                item.key === field.key
                                  ? { ...item, active: true }
                                  : item,
                              ),
                            },
                      },
                      "Campo actualizado; los valores guardados se conservan.",
                    );
                  }}
                >
                  {field.active ? "Desactivar" : "Activar"} {field.label}
                </Button>
              </li>
            ))}
          </ul>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (
                await accept(
                  addCustomField(config, {
                    key: fieldKey,
                    label: fieldLabel,
                    type: fieldType,
                    options: options.split(","),
                    active: true,
                    required,
                  }),
                  "Campo añadido.",
                )
              ) {
                setFieldKey("");
                setFieldLabel("");
                setOptions("");
                setRequired(false);
              }
            }}
            noValidate
          >
            <Field
              id="custom-field-key"
              label="Clave de nuevo campo"
              maxLength={40}
              value={fieldKey}
              onChange={(event) => setFieldKey(event.target.value)}
            />
            <Field
              id="custom-field-label"
              label="Nombre de nuevo campo"
              maxLength={60}
              value={fieldLabel}
              onChange={(event) => setFieldLabel(event.target.value)}
            />
            <SelectField
              id="custom-field-type"
              label="Tipo de nuevo campo"
              options={fieldTypes.map((type) => ({
                value: type,
                label: fieldTypeLabels[type],
              }))}
              value={fieldType}
              onChange={(event) =>
                setFieldType(event.target.value as CustomField["type"])
              }
            />
            {fieldType === "List" && (
              <Field
                id="custom-field-options"
                label="Opciones separadas por comas"
                maxLength={2400}
                value={options}
                onChange={(event) => setOptions(event.target.value)}
              />
            )}
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={required}
                onChange={(event) => setRequired(event.target.checked)}
              />
              Campo obligatorio al guardar una ficha
            </label>
            <Button type="submit">Añadir campo local</Button>
          </form>
        </section>
      </fieldset>
    </details>
  );
}
