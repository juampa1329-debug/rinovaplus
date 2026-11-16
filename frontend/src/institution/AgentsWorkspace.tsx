import { useEffect, useState } from "react";
import { AgentsPanel } from "../modules/agents/AgentsPanel";
import { api, mutation, type Agent, type Catalog } from "../modules/agents/api";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { allowNavigation } from "./drafts";

export function AgentsWorkspace({
  academicPrograms = false,
}: {
  academicPrograms?: boolean;
}) {
  const [refresh, setRefresh] = useState(0);
  return (
    <>
      {academicPrograms ? (
        <a href="#/academic">Administrar programas en Académico</a>
      ) : (
        <ProgramRegistry onSaved={() => setRefresh((v) => v + 1)} />
      )}
      <VersionRestore
        onSaved={() => setRefresh((v) => v + 1)}
        refresh={refresh}
      />
      <AgentsPanel key={refresh} />
    </>
  );
}

function ProgramRegistry({ onSaved }: { onSaved: () => void }) {
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [school, setSchool] = useState("");
  const [schedule, setSchedule] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  return (
    <details className="panel">
      <summary>Catálogo de programas para los agentes</summary>
      <p>
        Registre programas declarados por la institución para organizar sus
        agentes. Los datos académicos oficiales se consultarán mediante el mapeo
        SIIE revisado.
      </p>
      {error && <Notice error>{error}</Notice>}
      {saved && (
        <Notice>Programa guardado. Ya puede asignarlo a un agente.</Notice>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          setSaved(false);
          void (async () => {
            try {
              const entry = await api<{ revision: number }>(
                `/programs/${Number(id)}`,
              );
              await api(`/programs/${Number(id)}`, "PUT", {
                ...mutation(entry.revision),
                name,
                school,
                schedule,
                active: true,
              });
              setSaved(true);
              if (allowNavigation()) onSaved();
            } catch (reason) {
              setError(
                reason instanceof Error
                  ? reason.message
                  : "No se pudo guardar.",
              );
            } finally {
              setBusy(false);
            }
          })();
        }}
      >
        <fieldset disabled={busy}>
          <Field
            id="declared-program-id"
            label="Identificador del programa"
            type="number"
            min={1}
            required
            value={id}
            onChange={(e) => setId(e.target.value)}
          />
          <Field
            id="declared-program-name"
            label="Nombre del programa"
            maxLength={180}
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Field
            id="declared-program-school"
            label="Escuela"
            maxLength={100}
            value={school}
            onChange={(e) => setSchool(e.target.value)}
          />
          <Field
            id="declared-program-schedule"
            label="Jornada"
            maxLength={100}
            value={schedule}
            onChange={(e) => setSchedule(e.target.value)}
          />
          <Button type="submit">Guardar programa</Button>
        </fieldset>
      </form>
      <a href="#/settings/models">Configurar proveedores y modelos</a>
    </details>
  );
}

function VersionRestore({
  onSaved,
  refresh,
}: {
  onSaved: () => void;
  refresh: number;
}) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selected, setSelected] = useState("");
  const [versions, setVersions] = useState<number[]>([]);
  const [version, setVersion] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    void api<Catalog>("")
      .then((v) => {
        if (live) setAgents(v.agents);
      })
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [refresh]);
  useEffect(() => {
    let live = true;
    void Promise.resolve().then(async () => {
      if (!live) return;
      setVersion("");
      setVersions([]);
      if (selected)
        await api<{ versions: number[] }>(`/profiles/${selected}/console`)
          .then((v) => {
            if (live) setVersions(v.versions ?? []);
          })
          .catch((e) => live && setError(e.message));
    });
    return () => {
      live = false;
    };
  }, [selected, refresh]);
  const agent = agents.find((v) => v.id === selected);
  return (
    <details className="panel">
      <summary>Restaurar una versión de configuración</summary>
      <p>
        La restauración crea una versión nueva en pausa y conserva el historial
        y las asignaciones. Revise su configuración antes de reanudarla.
      </p>
      {error && <Notice error>{error}</Notice>}
      <fieldset disabled={busy}>
        <SelectField
          id="restore-agent"
          label="Agente"
          value={selected}
          options={[
            { value: "", label: "Seleccione un agente" },
            ...agents.map((v) => ({ value: v.id, label: v.name })),
          ]}
          onChange={(e) => setSelected(e.target.value)}
        />
        <SelectField
          id="restore-version"
          label="Versión a recuperar"
          value={version}
          options={[
            { value: "", label: "Seleccione una versión" },
            ...versions
              .filter((v) => v !== agent?.version)
              .map((v) => ({ value: String(v), label: `Versión ${v}` })),
          ]}
          onChange={(e) => setVersion(e.target.value)}
        />
        <TextArea
          id="restore-note"
          label="Motivo de restauración"
          maxLength={1000}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <Button
          disabled={!agent || !version || !note.trim()}
          onClick={() => {
            if (!agent || !allowNavigation()) return;
            setBusy(true);
            setError("");
            void api(`/profiles/${agent.id}/restore-version`, "POST", {
              ...mutation(agent.revision),
              version: Number(version),
              note,
            })
              .then(() => {
                setNote("");
                onSaved();
              })
              .catch((e) => setError(e.message))
              .finally(() => setBusy(false));
          }}
        >
          Restaurar configuración en pausa
        </Button>
      </fieldset>
    </details>
  );
}
