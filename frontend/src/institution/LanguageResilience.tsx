import { Button, Field, SelectField } from "../shared/ui";
import { LiveModelSelect } from "./LiveModelSelect";
import { useCrmConfiguration } from "../modules/crm-configuration/hooks/useCrmConfiguration";
import { providerNames, type AiProvider } from "../shared/aiSettings";

const engineOptions = Object.entries(providerNames).map(([value, label]) => ({
  value,
  label,
}));

type Route = {
  provider: AiProvider;
  model: string;
  input_usd_per_million: number;
  output_usd_per_million: number;
};
export type LanguagePolicy = {
  enabled: boolean;
  fallback_on_timeout?: boolean;
  primary?: Route | null;
  opening?: Route | null;
  opening_stage_keys?: string[];
  reply_max_tokens?: number;
  routes: Route[];
};

function OpeningStages({
  policy,
  onChange,
}: {
  policy: LanguagePolicy;
  onChange: (value: LanguagePolicy) => void;
}) {
  const { config, ready, error } = useCrmConfiguration();
  return (
    <fieldset>
      <legend>Etapas CRM de apertura y orientación</legend>
      {error && <p role="alert">{error}</p>}
      {!ready && !error && <p>Cargando etapas del CRM…</p>}
      {config.stages
        .filter((stage) => stage.active !== false)
        .map((stage) => (
          <label className="checkbox-label" key={stage.key}>
            <input
              type="checkbox"
              checked={(policy.opening_stage_keys ?? []).includes(stage.key)}
              onChange={(e) =>
                onChange({
                  ...policy,
                  opening_stage_keys: e.target.checked
                    ? [...(policy.opening_stage_keys ?? []), stage.key]
                    : (policy.opening_stage_keys ?? []).filter(
                        (key) => key !== stage.key,
                      ),
                })
              }
            />
            {stage.label}
          </label>
        ))}
    </fieldset>
  );
}

export function LanguageResilience({
  value,
  onChange,
  onSave,
}: {
  value: unknown;
  onChange: (value: LanguagePolicy) => void;
  onSave?: () => Promise<void>;
}) {
  const policy = (value ?? { enabled: false, routes: [] }) as LanguagePolicy;
  const update = (index: number, patch: Partial<Route>) =>
    onChange({
      ...policy,
      routes: policy.routes.map((route, i) =>
        i === index ? { ...route, ...patch } : route,
      ),
    });
  return (
    <section className="panel" aria-label="Respaldo de lenguaje">
      <h3>Motor de conversaciones y respaldos · P21</h3>
      <p>
        Si el principal rechaza una solicitud por modelo retirado, saturación o
        servicio no disponible, se consulta la siguiente alternativa compatible.
        Se conservan las instrucciones, skills y contexto. También puedes
        permitir el respaldo cuando agota el tiempo de generación de texto.
      </p>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={policy.enabled}
          onChange={(event) =>
            onChange({ ...policy, enabled: event.target.checked })
          }
        />
        Habilitar respaldo en mensajes y comentarios automáticos
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={!!policy.primary}
          disabled={!policy.enabled}
          onChange={(event) =>
            onChange({
              ...policy,
              primary: event.target.checked
                ? {
                    provider: "openrouter",
                    model: "",
                    input_usd_per_million: 0,
                    output_usd_per_million: 0,
                  }
                : null,
            })
          }
        />
        Elegir principal para mensajes y comentarios
      </label>
      {policy.primary && (
        <fieldset>
          <legend>Principal de conversaciones</legend>
          <SelectField
            id="language-primary-provider"
            label="Proveedor principal de conversaciones"
            value={policy.primary.provider}
            options={engineOptions}
            onChange={(event) =>
              onChange({
                ...policy,
                primary: {
                  ...policy.primary!,
                  provider: event.target.value as Route["provider"],
                  model: "",
                },
              })
            }
          />
          <LiveModelSelect
            id="language-primary-model"
            label="Modelo principal de conversaciones"
            category="text"
            provider={policy.primary.provider}
            value={policy.primary.model}
            onChange={(model) =>
              onChange({ ...policy, primary: { ...policy.primary!, model } })
            }
            onSelect={(model) =>
              onChange({
                ...policy,
                primary: {
                  ...policy.primary!,
                  model: model.id,
                  input_usd_per_million: model.input_usd_per_million ?? 0,
                  output_usd_per_million: model.output_usd_per_million ?? 0,
                },
              })
            }
          />
          <div className="form-grid">
            <Field
              id="language-primary-input"
              label="Tope principal USD por millón de entrada"
              type="number"
              min={0}
              max={100000}
              step="0.001"
              value={String(policy.primary.input_usd_per_million)}
              onChange={(e) =>
                onChange({
                  ...policy,
                  primary: {
                    ...policy.primary!,
                    input_usd_per_million: Number(e.target.value),
                  },
                })
              }
            />
            <Field
              id="language-primary-output"
              label="Tope principal USD por millón de salida"
              type="number"
              min={0}
              max={100000}
              step="0.001"
              value={String(policy.primary.output_usd_per_million)}
              onChange={(e) =>
                onChange({
                  ...policy,
                  primary: {
                    ...policy.primary!,
                    output_usd_per_million: Number(e.target.value),
                  },
                })
              }
            />
          </div>
          <p>
            Las tarifas se cargan desde el catálogo al elegir el modelo. Puedes
            reducir los topes; si el precio los supera, esa ruta no se utiliza.
          </p>
        </fieldset>
      )}
      {policy.primary && (
        <>
          <Field
            id="language-reply-tokens"
            label="Máximo de tokens por respuesta de los agentes"
            type="number"
            min={512}
            max={8000}
            step={1}
            value={String(policy.reply_max_tokens ?? 2000)}
            onChange={(e) =>
              onChange({ ...policy, reply_max_tokens: Number(e.target.value) })
            }
          />
          <p>
            Este máximo da espacio a la respuesta completa y al registro CRM. No
            obliga a escribir más ni es un cupo de mensajes. Las instrucciones
            siguen pidiendo respuestas breves en partes completas.
          </p>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={!!policy.opening}
              disabled={!policy.enabled}
              onChange={(e) =>
                onChange({
                  ...policy,
                  opening: e.target.checked
                    ? {
                        provider: "openrouter",
                        model: "",
                        input_usd_per_million: 0,
                        output_usd_per_million: 0,
                      }
                    : null,
                })
              }
            />
            Usar otro modelo para apertura y orientación
          </label>
          {policy.opening && (
            <fieldset>
              <legend>Modelo de apertura</legend>
              <SelectField
                id="language-opening-provider"
                label="Proveedor de apertura"
                value={policy.opening.provider}
                options={engineOptions}
                onChange={(e) =>
                  onChange({
                    ...policy,
                    opening: {
                      ...policy.opening!,
                      provider: e.target.value as Route["provider"],
                      model: "",
                    },
                  })
                }
              />
              <LiveModelSelect
                id="language-opening-model"
                label="Modelo de apertura y orientación"
                category="text"
                provider={policy.opening.provider}
                value={policy.opening.model}
                onChange={(model) =>
                  onChange({
                    ...policy,
                    opening: { ...policy.opening!, model },
                  })
                }
                onSelect={(model) =>
                  onChange({
                    ...policy,
                    opening: {
                      ...policy.opening!,
                      model: model.id,
                      input_usd_per_million: model.input_usd_per_million ?? 0,
                      output_usd_per_million: model.output_usd_per_million ?? 0,
                    },
                  })
                }
              />
              <p>
                Tarifa máxima de entrada: {policy.opening.input_usd_per_million}{" "}
                USD/millón. Salida: {policy.opening.output_usd_per_million}{" "}
                USD/millón. Se cargan al elegir el modelo.
              </p>
              <OpeningStages policy={policy} onChange={onChange} />
              <p>
                Financiación, objeciones, cierre y seguimiento usan el principal
                comercial, incluso si la ficha aún está en una etapa inicial. Si
                falla la apertura, se intenta el principal comercial y después
                sus respaldos. Todas las rutas conservan las mismas skills y
                memoria.
              </p>
            </fieldset>
          )}
        </>
      )}
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={policy.fallback_on_timeout === true}
          disabled={!policy.enabled}
          onChange={(event) =>
            onChange({ ...policy, fallback_on_timeout: event.target.checked })
          }
        />
        Usar respaldo si el principal agota el tiempo de respuesta
      </label>
      <p>
        Sólo genera una alternativa de texto antes de enviar al canal. La
        solicitud original podría consumir tokens y conserva su reserva; el
        respaldo reserva su propio cupo. No repite envíos a Meta ni notas de voz
        y respeta Humano. Si el respaldo tampoco confirma resultado, queda para
        revisión.
      </p>
      <p>
        Orden de preferencia:{" "}
        {policy.primary
          ? "primero el principal elegido aquí"
          : "primero el modelo del agente"}
        , después esta lista. Aplica a texto y audio ya transcrito. La
        interpretación de audio usa el modelo de audio elegido en APIs y
        modelos. Los agentes heredan este motor. Una prueba con modelo explícito
        en el simulador conserva su selección de prueba.
      </p>
      {policy.routes.map((route, index) => (
        <fieldset key={index}>
          <legend>Alternativa {index + 1}</legend>
          <SelectField
            id={`language-backup-provider-${index}`}
            label={`Proveedor del respaldo ${index + 1}`}
            value={route.provider}
            options={engineOptions}
            onChange={(event) =>
              update(index, {
                provider: event.target.value as Route["provider"],
                model: "",
              })
            }
          />
          <LiveModelSelect
            id={`language-backup-model-${index}`}
            provider={route.provider}
            category="text"
            value={route.model}
            label={`Modelo del respaldo ${index + 1}`}
            onChange={(model) => update(index, { model })}
            onSelect={(model) =>
              update(index, {
                model: model.id,
                input_usd_per_million: model.input_usd_per_million ?? 0,
                output_usd_per_million: model.output_usd_per_million ?? 0,
              })
            }
          />
          <div className="form-grid">
            <Field
              id={`language-backup-input-${index}`}
              label="Tope USD por millón de tokens de entrada"
              type="number"
              min={0}
              max={100000}
              step="0.001"
              value={String(route.input_usd_per_million)}
              onChange={(event) =>
                update(index, {
                  input_usd_per_million: Number(event.target.value),
                })
              }
            />
            <Field
              id={`language-backup-output-${index}`}
              label="Tope USD por millón de tokens de salida"
              type="number"
              min={0}
              max={100000}
              step="0.001"
              value={String(route.output_usd_per_million)}
              onChange={(event) =>
                update(index, {
                  output_usd_per_million: Number(event.target.value),
                })
              }
            />
          </div>
          <p>
            Cero admite sólo tarifas gratuitas en OpenRouter. Se comprueban
            catálogo, formato JSON, contexto, salida y precio antes de usarlo.
            Para Gemini estos valores son máximos revisados por el operador.
            Cada intento reserva cupo por separado.
          </p>
          <Button
            variant="quiet"
            onClick={() =>
              onChange({
                ...policy,
                routes: policy.routes.filter((_, i) => i !== index),
              })
            }
          >
            Quitar alternativa {index + 1}
          </Button>
        </fieldset>
      ))}
      <Button
        variant="secondary"
        disabled={policy.routes.length >= 3}
        onClick={() =>
          onChange({
            ...policy,
            routes: [
              ...policy.routes,
              {
                provider: "openrouter",
                model: "",
                input_usd_per_million: 0,
                output_usd_per_million: 0,
              },
            ],
          })
        }
      >
        Añadir modelo de respaldo
      </Button>
      <p>
        Revisa las alternativas y pulsa Guardar ajustes al final. Cambiar esta
        lista no habilita una conversación en Humano.
      </p>
      {onSave && (
        <Button variant="secondary" onClick={() => void onSave()}>
          Guardar motor y respaldos
        </Button>
      )}
    </section>
  );
}
