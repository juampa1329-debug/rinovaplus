import { Button, Field, SelectField } from "../shared/ui";
import { LiveModelSelect } from "./LiveModelSelect";

type Route = {
  provider: "gemini" | "openrouter";
  model: string;
  input_usd_per_million: number;
  output_usd_per_million: number;
};
type Policy = {
  enabled: boolean;
  fallback_on_timeout?: boolean;
  primary?: Route | null;
  routes: Route[];
};

export function LanguageResilience({
  value,
  onChange,
  onSave,
}: {
  value: unknown;
  onChange: (value: Policy) => void;
  onSave?: () => Promise<void>;
}) {
  const policy = (value ?? { enabled: false, routes: [] }) as Policy;
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
            options={[
              { value: "openrouter", label: "OpenRouter" },
              { value: "gemini", label: "Gemini" },
            ]}
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
        interpretación de audio conserva Gemini. Los agentes del simulador
        mantienen su respaldo propio.
      </p>
      {policy.routes.map((route, index) => (
        <fieldset key={index}>
          <legend>Alternativa {index + 1}</legend>
          <SelectField
            id={`language-backup-provider-${index}`}
            label={`Proveedor del respaldo ${index + 1}`}
            value={route.provider}
            options={[
              { value: "openrouter", label: "OpenRouter" },
              { value: "gemini", label: "Gemini" },
            ]}
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
