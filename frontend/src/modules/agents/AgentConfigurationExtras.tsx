import { Field, SelectField } from "../../shared/ui";
import {
  memoryChoices,
  toolGroups,
  type Agent,
  type Configuration,
} from "./api";

export function AgentConfigurationExtras({
  draft,
  configure,
  versions,
}: {
  draft: Agent;
  configure: (value: Partial<Configuration>) => void;
  versions: number[];
}) {
  const config = draft.configuration;
  const toggle = (
    field: "memories" | "capabilities" | "industry_policies",
    value: string,
  ) => {
    const current = config[field] ?? [];
    configure({
      [field]: current.includes(value)
        ? current.filter((v) => v !== value)
        : [...current, value],
    });
  };
  const price = (
    id: string,
    label: string,
    field:
      | "input_usd_per_million"
      | "output_usd_per_million"
      | "fallback_input_usd_per_million"
      | "fallback_output_usd_per_million",
  ) => (
    <Field
      id={id}
      label={label}
      type="number"
      min={0}
      step="any"
      value={config[field] ?? ""}
      onChange={(e) =>
        configure({
          [field]: e.target.value === "" ? null : Number(e.target.value),
        })
      }
      hint="Tarifa informada por el operador; USD por un millón de tokens."
    />
  );
  return (
    <>
      <section
        className="agents-editor-section"
        aria-labelledby="agent-persona-heading"
      >
        <h4 id="agent-persona-heading">Nombre y estilo de atención</h4>
        <Field
          id="agent-advisor-name"
          label="Nombre de atención"
          maxLength={50}
          value={config.advisor_name ?? ""}
          onChange={(event) => configure({ advisor_name: event.target.value })}
          hint="Por ejemplo, Juan para el perfil de voz actual. Es un nombre de presentación del agente; no la identidad de un empleado. Puedes ajustarlo al cambiar su voz."
        />
      </section>
      <section
        className="agents-editor-section"
        aria-labelledby="agent-budget-heading"
      >
        <h4 id="agent-budget-heading">Presupuesto y experimentos A/B</h4>
        <div className="agents-form-grid">
          <Field
            id="agent-usd-budget"
            label="Presupuesto USD/mes"
            type="number"
            min={0}
            step="any"
            value={config.monthly_usd_limit ?? 0}
            onChange={(e) =>
              configure({ monthly_usd_limit: Number(e.target.value) })
            }
            hint="Cero no aplica un límite monetario; el límite de tokens sigue visible arriba."
          />
          <Field
            id="agent-usage-alert"
            label="Alerta de uso %"
            type="number"
            min={1}
            max={100}
            value={config.usage_alert_percent ?? 80}
            onChange={(e) =>
              configure({ usage_alert_percent: Number(e.target.value) })
            }
          />
        </div>
        <label>
          <input
            type="checkbox"
            checked={config.hard_stop ?? true}
            onChange={(e) => configure({ hard_stop: e.target.checked })}
          />
          Detener al superar el presupuesto
        </label>
        <p>
          El costo se estima con las tarifas que informe. La reserva cubre
          intentos y respaldo; los valores no equivalen a facturación del
          proveedor. Sin tarifa, el costo aparece como desconocido. Un corte USD
          configurado requiere tarifas completas.
        </p>
        <div className="agents-form-grid">
          {price(
            "agent-input-price",
            "Entrada · USD / 1 M tokens",
            "input_usd_per_million",
          )}
          {price(
            "agent-output-price",
            "Salida · USD / 1 M tokens",
            "output_usd_per_million",
          )}
          {config.fallback_model &&
            price(
              "agent-fallback-input-price",
              "Respaldo entrada · USD / 1 M tokens",
              "fallback_input_usd_per_million",
            )}
          {config.fallback_model &&
            price(
              "agent-fallback-output-price",
              "Respaldo salida · USD / 1 M tokens",
              "fallback_output_usd_per_million",
            )}
        </div>
        <label>
          <input
            type="checkbox"
            checked={config.ab_enabled ?? false}
            onChange={(e) => configure({ ab_enabled: e.target.checked })}
          />
          Activar experimento A/B
        </label>
        <div className="agents-form-grid">
          <Field
            id="agent-ab-variant"
            label="Variante actual"
            maxLength={40}
            value={config.ab_variant ?? "A"}
            onChange={(e) => configure({ ab_variant: e.target.value })}
          />
          <SelectField
            id="agent-ab-compare"
            label="Comparar contra versión de este agente"
            value={
              config.ab_compare_version ? String(config.ab_compare_version) : ""
            }
            options={[
              { value: "", label: "Seleccione una versión anterior" },
              ...versions
                .filter((v) => v <= draft.version)
                .map((v) => ({ value: String(v), label: "Versión " + v })),
            ]}
            onChange={(e) =>
              configure({ ab_compare_version: Number(e.target.value) || null })
            }
          />
          <Field
            id="agent-ab-traffic"
            label="Tráfico para la variante actual %"
            type="number"
            min={1}
            max={99}
            value={config.ab_traffic_percent ?? 50}
            onChange={(e) =>
              configure({ ab_traffic_percent: Number(e.target.value) })
            }
          />
        </div>
        <p>
          La comparación usa una versión guardada de este mismo agente y
          programa. Cada conversación automática conserva su grupo; las
          asignaciones manuales y el simulador no cambian de variante por
          sorpresa. Se aplican permisos actuales y presupuesto actual. En el
          simulador puede elegir qué variante probar.
        </p>
      </section>
      <section
        className="agents-editor-section"
        aria-labelledby="agent-industry-heading"
      >
        <h4 id="agent-industry-heading">Políticas de admisiones</h4>
        <div className="agents-checks">
          {[
            ["academy", "Academia"],
            ["privacy", "Privacidad"],
            ["payments", "Orientación sobre pagos"],
            ["minors", "Atención a menores de edad"],
          ].map(([value, label]) => (
            <label key={value}>
              <input
                type="checkbox"
                checked={config.industry_policies?.includes(value) ?? false}
                onChange={() => toggle("industry_policies", value)}
              />
              {label}
            </label>
          ))}
        </div>
        <p>
          Estas políticas agregan orientación contextual. Los límites
          institucionales y la atención humana se mantienen siempre.
        </p>
      </section>
      <section
        className="agents-editor-section"
        aria-labelledby="agent-tools-heading"
      >
        <h4 id="agent-tools-heading">Herramientas</h4>
        {toolGroups.map((group) => (
          <div key={group.name}>
            <h5>{group.name}</h5>
            <div className="agents-checks">
              {group.items.map(([value, label]) => (
                <label key={value}>
                  <input
                    type="checkbox"
                    checked={config.capabilities.includes(value)}
                    onChange={() => toggle("capabilities", value)}
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>
        ))}
        <p>
          Las herramientas proporcionan contexto o preparan documentos internos.
          Tareas y notas requieren conversación del mismo ámbito y los permisos
          correspondientes. No se ejecutan pagos, matrículas ni envíos masivos.
        </p>
      </section>
      <section
        className="agents-editor-section"
        aria-labelledby="agent-memory-heading"
      >
        <h4 id="agent-memory-heading">Memoria y permisos</h4>
        <div className="agents-memory-permissions">
          <div>
            <h5>Contexto que puede recuperar</h5>
            <div className="agents-memory-options">
              {memoryChoices.map(([value, label, detail]) => (
                <label key={value}>
                  <input
                    type="checkbox"
                    checked={config.memories?.includes(value) ?? false}
                    onChange={() => toggle("memories", value)}
                  />
                  <span>
                    <strong>{label}</strong>
                    <small>{detail}</small>
                  </span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <h5>Permisos de operación</h5>
            <div className="agents-memory-options">
              <label>
                <input
                  type="checkbox"
                  checked={config.require_human_approval ?? true}
                  onChange={(e) =>
                    configure({ require_human_approval: e.target.checked })
                  }
                />
                <span>
                  <strong>Confirmar acciones con cambios</strong>
                  <small>
                    Se aplica a notas y tareas de una conversación; no
                    condiciona crear o guardar el agente.
                  </small>
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={config.allow_safe_actions ?? false}
                  onChange={(e) =>
                    configure({ allow_safe_actions: e.target.checked })
                  }
                />
                <span>
                  <strong>Puede ejecutar acciones seguras</strong>
                  <small>
                    Permite registrar tareas y notas internas; no concede acceso
                    a servicios externos.
                  </small>
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={config.allow_reply}
                  onChange={(e) => configure({ allow_reply: e.target.checked })}
                />
                <span>
                  <strong>Puede responder mensajes</strong>
                  <small>
                    Sujeto a canales, fuentes, conexión y control humano
                    existentes.
                  </small>
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={config.allow_crm_update ?? false}
                  onChange={(e) =>
                    configure({ allow_crm_update: e.target.checked })
                  }
                />
                <span>
                  <strong>Puede actualizar CRM</strong>
                  <small>
                    Permite notas y tareas de seguimiento mediante las
                    operaciones del Inbox.
                  </small>
                </span>
              </label>
            </div>
            <div className="agents-context-links">
              <a href="#/memory">Consultar memoria</a>
              <a href="#/knowledge">Administrar conocimiento</a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
