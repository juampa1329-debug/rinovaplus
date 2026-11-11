import { ConversationProcessing } from "../../conversation-events/pages/ConversationProcessing";
import { AnalysisSettings } from "../../conversation-analysis/pages/ConversationAnalysis";
import { useState } from "react";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import {
  useOperations,
  type Configuration,
  type DirectoryItem,
} from "../api/inboxOperations";
import { InboxDirectory } from "./InboxDirectory";
import { Button, Field, Notice, TextArea } from "../../../shared/ui";
export function InboxOperationSettings({
  refresh,
  onConfirmed,
}: {
  refresh: number;
  onConfirmed: () => void;
}) {
  const store = useOperations<Configuration>(
    "/configuration",
    refresh,
    onConfirmed,
  );
  const [employee, setEmployee] = useState<DirectoryItem | null>(null);
  const [member, setMember] = useState<DirectoryItem | null>(null);
  const [agent, setAgent] = useWorkspaceField("inboxOperations", "agent");
  const [policy, setPolicy] = useWorkspaceField("inboxOperations", "policy");
  const [validation, setValidation] = useState("");
  const draft = agent ?? {
    revision: store.data?.revision ?? "",
    id: "",
    name: "",
    description: "",
    enabled: false,
  };
  const currentPolicy = policy ?? {
    revision: store.data?.revision ?? "",
    enabled: store.data?.policy?.enabled ?? false,
    threshold: store.data?.policy
      ? String(store.data.policy.thresholdMinutes)
      : "",
  };
  async function saveAgent(event: React.FormEvent) {
    event.preventDefault();
    if (!draft.name.trim()) {
      setValidation("Indique el nombre del agente.");
      return;
    }
    const submitted = { ...draft, id: draft.id || crypto.randomUUID() };
    setAgent(submitted);
    if (
      await store.save(
        "/agents/" + submitted.id,
        {
          name: submitted.name,
          description: submitted.description,
          enabled: submitted.enabled,
        },
        submitted.revision,
      )
    )
      setAgent(null);
  }
  async function savePolicy(event: React.FormEvent) {
    event.preventDefault();
    if (
      !/^\d+$/.test(currentPolicy.threshold) ||
      Number(currentPolicy.threshold) < 1 ||
      Number(currentPolicy.threshold) > 525600
    ) {
      setValidation(
        "Indique un umbral entero entre 1 y 525600 minutos; no hay valor predeterminado.",
      );
      return;
    }
    if (
      await store.save(
        "/policy",
        {
          enabled: currentPolicy.enabled,
          thresholdMinutes: Number(currentPolicy.threshold),
        },
        currentPolicy.revision,
      )
    )
      setPolicy(null);
  }
  return (
    <section
      className="panel inbox-operation-settings"
      aria-labelledby="inbox-settings-title"
    >
      <h2 id="inbox-settings-title">Configuración de operación Inbox</h2>
      <ConversationProcessing />
      <AnalysisSettings />
      <p>
        La membresía define quién puede recibir conversaciones y tareas.
      </p>
      {store.error && (
        <Notice error>
          {store.error}{" "}
          <Button variant="quiet" onClick={store.reload}>
            Reintentar configuración
          </Button>
        </Notice>
      )}
      {store.feedback && <Notice>{store.feedback}</Notice>}
      {validation && <Notice error>{validation}</Notice>}
      <fieldset
        disabled={!store.data || store.busy || store.loading}
        className="client-editor-fields"
      >
        <details open>
          <summary>Equipo de Admisiones</summary>
          <p>
            El equipo empieza vacío. Seleccione empleados activos existentes; no
            se infiere membresía por nombre o área.
          </p>
          <InboxDirectory
            scope="employees"
            label="Empleado para Admisiones"
            value={employee ? String(employee.id) : ""}
            name={employee?.name}
            eligible={false}
            refresh={refresh}
            onChange={(_id, item) => setEmployee(item ?? null)}
          />
          <Button
            disabled={!employee}
            onClick={async () => {
              if (
                employee &&
                (await store.save(
                  "/members/" + employee.id,
                  { enabled: true },
                  employee.revision,
                ))
              )
                setEmployee(null);
            }}
          >
            Añadir al equipo de Admisiones
          </Button>
          <InboxDirectory
            scope="members"
            label="Miembro de Admisiones"
            value={member ? String(member.id) : ""}
            name={member?.name}
            eligible={false}
            refresh={refresh}
            onChange={(_id, item) => setMember(item ?? null)}
          />
          {member && (
            <p>
              {member.enabled
                ? "Membresía habilitada"
                : "Membresía deshabilitada"}
              {member.sourceActive
                ? ""
                : " · empleado inactivo o no disponible"}
            </p>
          )}
          <Button
            disabled={!member || (!member.enabled && !member.sourceActive)}
            onClick={async () => {
              if (
                member &&
                (await store.save(
                  "/members/" + member.id,
                  {
                    enabled: !member.enabled,
                  },
                  member.revision,
                ))
              )
                setMember(null);
            }}
          >
            {member?.enabled ? "Deshabilitar miembro" : "Habilitar miembro"}
          </Button>
          <p className="scope-text">
            Deshabilitar conserva sus asignaciones y tareas históricas.
          </p>
        </details>
        <details>
          <summary>Registro de agentes IA</summary>
          <p>
            Son definiciones persistidas para asignación. No ejecutan IA, no
            conectan proveedores y no generan respuestas.
          </p>
          <InboxDirectory
            scope="agents"
            label="Agente registrado"
            value={draft.id}
            name={draft.name}
            eligible={false}
            refresh={refresh}
            onChange={(id, item) => {
              setValidation("");
              setAgent(
                id && item
                  ? {
                      id,
                      revision: item.revision ?? store.data?.revision ?? "",
                      name: item.name,
                      description: item.description ?? "",
                      enabled: item.enabled,
                    }
                  : null,
              );
            }}
          />
          <Button
            variant="quiet"
            onClick={() => {
              setAgent({
                id: crypto.randomUUID(),
                revision: store.data?.revision ?? "",
                name: "",
                description: "",
                enabled: false,
              });
              setValidation("");
            }}
          >
            Nuevo agente
          </Button>
          <form onSubmit={saveAgent}>
            <Field
              id="registered-agent-name"
              label="Nombre del agente"
              maxLength={100}
              value={draft.name}
              onChange={(event) =>
                setAgent({
                  ...draft,
                  id: draft.id || crypto.randomUUID(),
                  name: event.target.value,
                })
              }
            />
            <TextArea
              id="registered-agent-description"
              label="Descripción y responsabilidad del agente"
              maxLength={1000}
              value={draft.description}
              onChange={(event) =>
                setAgent({
                  ...draft,
                  id: draft.id || crypto.randomUUID(),
                  description: event.target.value,
                })
              }
            />
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={draft.enabled}
                onChange={(event) =>
                  setAgent({
                    ...draft,
                    id: draft.id || crypto.randomUUID(),
                    enabled: event.target.checked,
                  })
                }
              />
              Disponible para asignación · no activa ejecución
            </label>
            <div className="actions">
              <Button type="submit">Guardar registro de agente</Button>
              <Button variant="quiet" onClick={() => setAgent(null)}>
                Descartar agente
              </Button>
            </div>
          </form>
        </details>
        <details>
          <summary>Política SLA de próxima respuesta</summary>
          <Notice>
            Tiempo transcurrido 24/7, sin horarios laborales ni pausas. Inicia
            con el entrante más antiguo posterior al último mensaje saliente.
            Registrar un saliente resuelve la espera. Espera y control IA no pausan; conversación cerrada
            queda excluida. El vencimiento exacto ya cuenta como vencido.
          </Notice>
          <p>
            {store.data?.policy?.enabled
              ? "Política habilitada"
              : "SLA no configurado o deshabilitado"}
            . Activar o cambiar el umbral evalúa mensajes pendientes reales
            existentes. Sin entrante pendiente no hay medición.
          </p>
          <form onSubmit={savePolicy}>
            <Field
              id="sla-threshold"
              label="Umbral SLA en minutos transcurridos"
              type="number"
              min={1}
              max={525600}
              step={1}
              value={currentPolicy.threshold}
              onChange={(event) => {
                setPolicy({ ...currentPolicy, threshold: event.target.value });
                setValidation("");
              }}
            />
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={currentPolicy.enabled}
                onChange={(event) =>
                  setPolicy({ ...currentPolicy, enabled: event.target.checked })
                }
              />
              Habilitar esta política de respuesta 24/7
            </label>
            <div className="actions">
              <Button type="submit">Guardar política SLA</Button>
              <Button variant="quiet" onClick={() => setPolicy(null)}>
                Descartar política
              </Button>
            </div>
          </form>
        </details>
      </fieldset>
    </section>
  );
}
