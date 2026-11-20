import { Button, Field, SelectField } from "../shared/ui";
import { LiveModelSelect } from "./LiveModelSelect";

type Route = {
  provider: "gemini" | "openrouter";
  model: string;
  input_usd_per_million: number;
  output_usd_per_million: number;
};
type Policy = { enabled: boolean; routes: Route[] };

export function LanguageResilience({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (value: Policy) => void;
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
      <h3>Modelos de respaldo · P21</h3>
      <p>
        Si Gemini rechaza una solicitud por modelo retirado, saturación o
        servicio no disponible, se consulta la siguiente alternativa compatible.
        Se conservan las instrucciones, skills y contexto. Los resultados
        inciertos se dejan para revisión.
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
      <p>
        Orden de preferencia: primero el modelo del agente, después esta lista.
        Aplica a texto y audio ya transcrito. La interpretación de audio
        conserva Gemini. Los agentes del simulador mantienen su respaldo propio.
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
            provider={route.provider}
            category="text"
            value={route.model}
            label={`Modelo del respaldo ${index + 1}`}
            onChange={(model) => update(index, { model })}
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
        lista no cambia el modelo principal ni habilita una conversación en
        Humano.
      </p>
    </section>
  );
}
