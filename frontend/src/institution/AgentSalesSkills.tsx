import { useEffect, useState } from "react";
import { api, type Configuration } from "../modules/agents/api";
import { Button, Notice } from "../shared/ui";
import "./sales.css";
import { OperationDialog } from "./ErrorFeedback";

export type SalesSkill = {
  id: string;
  name: string;
  category: string;
  procedure: string;
};

export function AgentSalesSkills({
  configuration,
  guide,
  onChange,
}: {
  configuration: Configuration;
  guide: boolean;
  onChange: (value: Partial<Configuration>) => void;
}) {
  const [skills, setSkills] = useState<SalesSkill[]>([]);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let live = true;
    void api<{ items: SalesSkill[] }>("/sales/skills")
      .then((value) => {
        if (!Array.isArray(value.items))
          throw new Error(
            "No se pudo validar el catálogo de skills. Actualiza esta vista antes de guardar.",
          );
        if (live) {
          setSkills(value.items);
          setError("");
        }
      })
      .catch((failure: Error) => {
        if (live) setError(failure.message);
      });
    return () => {
      live = false;
    };
  }, [reload]);
  const selected = configuration.sales_skill_ids ?? [];
  return (
    <section
      className="agents-editor-section"
      aria-label="Skills comerciales y memoria"
    >
      <h4>Skills comerciales y memoria</h4>
      <p>
        Procedimientos que el agente aplica con su system prompt y los datos de
        su programa. Las skills no conceden permisos adicionales.
      </p>
      {error && <Notice error>{error}</Notice>}
      {error && (
        <OperationDialog
          guidance={{
            title: "No se pudieron cargar las skills",
            detail: error,
            nextStep:
              "Conservamos la configuración del agente. Cierra este aviso y pulsa Actualizar skills cuando termine el despliegue o se restablezca la conexión.",
          }}
          dismiss={() => setError("")}
        />
      )}
      <div className="sales-toolbar">
        <strong>
          {selected.length} de {skills.length} activas
        </strong>
        <Button
          type="button"
          variant="quiet"
          onClick={() => setReload((value) => value + 1)}
        >
          Actualizar skills
        </Button>
        <Button
          type="button"
          variant="quiet"
          disabled={!skills.length}
          onClick={() => onChange({ sales_skill_ids: skills.map((v) => v.id) })}
        >
          Seleccionar las 20 skills
        </Button>
        <Button
          type="button"
          variant="quiet"
          onClick={() => onChange({ sales_skill_ids: [] })}
        >
          Limpiar selección
        </Button>
      </div>
      <div className="sales-skills-grid">
        {skills.map((skill) => (
          <label key={skill.id} title={skill.procedure}>
            <input
              type="checkbox"
              checked={selected.includes(skill.id)}
              onChange={(event) =>
                onChange({
                  sales_skill_ids: event.target.checked
                    ? [...selected, skill.id]
                    : selected.filter((id) => id !== skill.id),
                })
              }
            />
            <span>
              <strong>{skill.name}</strong>
              <small>{skill.category}</small>
            </span>
          </label>
        ))}
      </div>
      <label className="sales-switch">
        <input
          type="checkbox"
          checked={configuration.sales_memory_enabled ?? false}
          onChange={(event) =>
            onChange({
              sales_memory_enabled: event.target.checked,
              ...(!event.target.checked ? { auto_sales_crm: false } : {}),
            })
          }
        />
        Conservar memoria comercial y contexto de este hilo
      </label>
      <label className="sales-switch">
        <input
          type="checkbox"
          disabled={!configuration.sales_memory_enabled}
          checked={configuration.auto_sales_crm ?? false}
          onChange={(event) =>
            onChange({ auto_sales_crm: event.target.checked })
          }
        />
        Completar datos comerciales y calificación CRM con evidencia
      </label>
      {guide && (
        <label className="sales-switch">
          <input
            type="checkbox"
            checked={configuration.sales_routing_enabled ?? false}
            onChange={(event) =>
              onChange({ sales_routing_enabled: event.target.checked })
            }
          />
          Derivar automáticamente al especialista según el interés o anuncio
          identificado
        </label>
      )}
      <p>
        La memoria pertenece a la conversación. Conserva citas y procedencia;
        las correcciones manuales de calificación se respetan. El SLA usa
        tiempos reales y el abandono muestra señales explicables. Matrículas y
        pagos siguen sus validaciones.
      </p>
    </section>
  );
}
