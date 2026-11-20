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
  guide?: { path: string; version: string; sha256: string; content: string };
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
  return (
    <section
      className="agents-editor-section"
      aria-label="Skills comerciales y memoria"
    >
      <h4>Skills comerciales y memoria</h4>
      <p>
        Política central del backend para la IA general y todos los agentes. En
        cada turno se aplican los procedimientos pertinentes a la consulta,
        junto al system prompt de cada agente y la ficha del programa. El
        backend consulta los archivos SKILL.md de su biblioteca; no dependen de
        Codex. Las guías no conceden permisos.
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
          {skills.length} skills disponibles · aplicación automática por turno
        </strong>
        <Button
          type="button"
          variant="quiet"
          onClick={() => setReload((value) => value + 1)}
        >
          Actualizar skills
        </Button>
      </div>
      <div className="sales-skills-grid">
        {skills.map((skill) => (
          <div key={skill.id} className="sales-skill-card">
            <label title={skill.procedure}>
              <input type="checkbox" checked disabled />
              <span>
                <strong>{skill.name}</strong>
                <small>{skill.category}</small>
              </span>
            </label>
            {skill.guide && (
              <details className="sales-skill-guide">
                <summary>Consultar guía de {skill.name}</summary>
                <small>
                  {skill.guide.path} · {skill.guide.version}
                </small>
                <pre>{skill.guide.content}</pre>
                <small>SHA256 {skill.guide.sha256}</small>
              </details>
            )}
          </div>
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
