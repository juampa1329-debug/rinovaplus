import { useEffect, useRef, useState } from "react";
import { api, labels, type Agent, type Catalog } from "../../agents/api";
import { Button, Notice, SelectField, TextArea } from "../../../shared/ui";
import { AssistantChat as GenericAssistantChat } from "./AssistantChat";

type Message = { role: "user" | "assistant"; content: string };
type Reply = {
  agent_id: string;
  config_version: number;
  text: string;
  model: string;
  handoff: boolean;
  sources: { id: string; title: string }[];
};

function profileBinding(catalog: Catalog | null, id: string): string {
  const chain: Agent[] = [];
  let agent = catalog?.agents.find((item) => item.id === id);
  while (agent && !chain.some((item) => item.id === agent?.id)) {
    chain.push(agent);
    agent = catalog?.agents.find((item) => item.id === agent?.parent_id);
  }
  return JSON.stringify(
    chain.map((item) => [item.id, item.version, item.revision, item.state]),
  );
}

export function AssistantChat({
  active,
  selectedOnly = false,
}: {
  active: boolean;
  selectedOnly?: boolean;
}) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!active) return;
    let live = true;
    void Promise.resolve().then(async () => {
      if (!live) return;
      setLoading(true);
      setError("");
      try {
        const next = await api<Catalog>("");
        if (live) setCatalog(next);
      } catch (reason) {
        if (live) setError((reason as Error).message);
      } finally {
        if (live) setLoading(false);
      }
    });
    return () => {
      live = false;
    };
  }, [active, refresh]);

  const agent = catalog?.agents.find((item) => item.id === selectedId);
  const selectedBinding = profileBinding(catalog, selectedId);
  return (
    <>
      {active && (
        <section className="panel" aria-label="Selección del asistente">
          <SelectField
            id="assistant-agent"
            label="Asistente para conversar"
            value={selectedId}
            disabled={loading}
            options={[
              {
                value: "",
                label: selectedOnly
                  ? "Seleccione un agente guardado"
                  : "Asistente general · ajustes globales",
              },
              ...(catalog?.agents ?? []).map((item) => ({
                value: item.id,
                label: `${item.name} · ${labels[item.state] ?? item.state} · versión ${item.version}`,
              })),
              ...(selectedId && !agent
                ? [
                    {
                      value: selectedId,
                      label: "Agente seleccionado no disponible",
                    },
                  ]
                : []),
            ]}
            onChange={(event) => setSelectedId(event.target.value)}
          />
          <Button
            variant="quiet"
            disabled={loading}
            onClick={() => setRefresh((value) => value + 1)}
          >
            Actualizar agentes guardados
          </Button>
          {loading && <p role="status">Cargando agentes guardados…</p>}
          {error && (
            <Notice error>
              {error} Actualice los agentes guardados para continuar.
            </Notice>
          )}
          {!loading && catalog && !catalog.agents.length && (
            <p>
              No hay agentes guardados.{" "}
              <a href="#/agents">Crear o administrar Mis agentes</a>.
            </p>
          )}
        </section>
      )}
      {!selectedOnly && <GenericAssistantChat active={active && !selectedId} />}
      {selectedId && (
        <ProfileConversation
          key={selectedId + selectedBinding}
          active={active}
          agent={agent}
          selectedBinding={selectedBinding}
          onCatalog={setCatalog}
          catalogLoading={loading}
          catalogError={error}
        />
      )}
    </>
  );
}

function ProfileConversation({
  active,
  agent,
  selectedBinding,
  onCatalog,
  catalogLoading,
  catalogError,
}: {
  active: boolean;
  agent: Agent | undefined;
  selectedBinding: string;
  onCatalog: (catalog: Catalog) => void;
  catalogLoading: boolean;
  catalogError: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reply, setReply] = useState<Reply | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const epoch = useRef(0);
  const pending = useRef(false);
  useEffect(() => {
    pending.current = false;
    const current = epoch.current;
    void Promise.resolve().then(() => {
      if (current === epoch.current) setBusy(false);
    });
    return () => {
      epoch.current++;
    };
  }, [active]);

  function reset() {
    epoch.current++;
    pending.current = false;
    setBusy(false);
    setMessages([]);
    setReply(null);
    setError("");
    setUncertain(false);
  }

  const blocked = !agent
    ? "El agente ya no está disponible. Actualice Mis agentes."
    : agent.state !== "active" || agent.enabled === false
      ? "Este agente está pausado, archivado o sin activar. Revise su estado en Mis agentes antes de consumir IA."
      : !agent.configuration.channels.includes("local")
        ? "El perfil no permite Web · aplicación. Habilite ese canal y guarde en Mis agentes."
        : !(agent.configuration.primary_model ?? "").trim()
          ? "El agente no tiene modelo principal. Seleccione su proveedor y modelo, y guarde en Mis agentes."
          : !agent.configuration.monthly_token_limit
            ? "El agente no tiene cuota mensual configurada. Complete el presupuesto y guarde en Mis agentes."
            : uncertain
              ? "El intento pudo consumir presupuesto. Inicie una conversación nueva antes de volver a enviar."
              : catalogError
                ? "No se pudo actualizar el catálogo. Actualice los agentes guardados antes de enviar."
                : "";

  async function send() {
    if (
      !active ||
      !agent ||
      blocked ||
      catalogLoading ||
      pending.current ||
      !draft.trim()
    )
      return;
    const version = epoch.current;
    pending.current = true;
    setBusy(true);
    setError("");
    let generated = false;
    try {
      const latest = await api<Catalog>("");
      if (version !== epoch.current) return;
      onCatalog(latest);
      const current = latest.agents.find((item) => item.id === agent.id);
      if (
        !current ||
        current.state === "archived" ||
        profileBinding(latest, agent.id) !== selectedBinding
      ) {
        setError(
          "El perfil cambió. Revise la versión actual e inicie una conversación nueva.",
        );
        return;
      }
      const prompt = draft.trim();
      generated = true;
      const result = await api<Reply>("/simulate", "POST", {
        agent_id: current.id,
        config_version: current.version,
        program_id: current.program_id,
        stage_id: current.stage_id,
        question: prompt,
        history: messages
          .slice(-12)
          .map((item) => ({ ...item, content: item.content.slice(-1600) })),
        channel: "local",
        call_provider: true,
        acknowledge_consumption: true,
        request_id: crypto.randomUUID(),
      });
      if (version !== epoch.current) return;
      const after = await api<Catalog>("");
      if (version !== epoch.current) return;
      onCatalog(after);
      if (
        profileBinding(after, agent.id) !== selectedBinding ||
        result.agent_id !== agent.id ||
        result.config_version !== agent.version
      ) {
        setError(
          "El perfil cambió durante la respuesta. Inicie una conversación nueva; no se reenvía automáticamente.",
        );
        setUncertain(true);
        return;
      }
      setMessages((previous) =>
        [
          ...previous,
          { role: "user", content: prompt } as Message,
          { role: "assistant", content: result.text } as Message,
        ].slice(-60),
      );
      setReply(result);
      setDraft("");
    } catch (reason) {
      if (version === epoch.current) {
        setError((reason as Error).message);
        if (generated) setUncertain(true);
      }
    } finally {
      if (version === epoch.current) {
        pending.current = false;
        setBusy(false);
      }
    }
  }

  if (!active) return null;
  return (
    <section
      className="panel assistant-chat"
      aria-label="Conversación con agente guardado"
    >
      <div className="panel-heading">
        <div>
          <h2>Conversar con {agent?.name ?? "el agente"}</h2>
          {agent && (
            <p>
              {labels[agent.state] ?? agent.state} · versión {agent.version} ·{" "}
              {agent.configuration.provider ?? "openrouter"} ·{" "}
              {agent.configuration.primary_model || "Sin modelo"}
            </p>
          )}
        </div>
        <Button variant="secondary" onClick={reset}>
          Nueva conversación
        </Button>
      </div>
      <p>
        Conversación con la configuración guardada; también puede probar un
        borrador. Un agente archivado debe restaurarse primero.{" "}
        <a href="#/agents">Configurar o restaurar en Mis agentes</a>.
      </p>
      <p>
        Este modo admite texto. Voz, adjuntos y búsqueda externa están
        disponibles en el asistente general. El historial de esta conversación
        se limita a 12 mensajes de 1600 caracteres y se reinicia al cambiar de
        agente o versión.
      </p>
      {blocked && <Notice>{blocked}</Notice>}
      {error && <Notice error>{error}</Notice>}
      <div
        role="log"
        aria-label="Conversación con el agente"
        aria-live="polite"
        className="assistant-chat-log"
      >
        {!messages.length && (
          <p>
            Escriba un mensaje para conversar con la configuración del agente.
          </p>
        )}
        {messages.map((item, index) => (
          <article
            className={`assistant-chat-message ${item.role}`}
            key={index}
          >
            <strong>
              {item.role === "user"
                ? "Usted"
                : `${agent?.name} · asistente virtual`}
            </strong>
            <p>{item.content}</p>
          </article>
        ))}
      </div>
      {reply && (
        <div className="scope-note">
          <p>
            Modelo: {reply.model} · versión {reply.config_version}.
            {reply.handoff
              ? " Se recomienda continuar con una persona; no se ha enviado ninguna notificación."
              : ""}
          </p>
          {reply.sources.map((source) => (
            <p key={source.id}>{source.title}</p>
          ))}
        </div>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <TextArea
          id="profile-assistant-message"
          label="Mensaje para el agente"
          rows={3}
          maxLength={2000}
          value={draft}
          disabled={busy}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              void send();
            }
          }}
        />
        <p>
          Al pulsar Enviar mensaje autoriza consultar al proveedor configurado y
          consumir el presupuesto del perfil. Se envían sus instrucciones,
          fuentes institucionales e historial acotado. No se envían mensajes a
          canales externos ni se guardan expedientes.
        </p>
        <div className="actions">
          <Button
            type="submit"
            disabled={busy || catalogLoading || !!blocked || !draft.trim()}
          >
            {busy ? "Esperando respuesta…" : "Enviar mensaje"}
          </Button>
        </div>
        {busy && <p role="status">Consultando al proveedor del agente…</p>}
      </form>
    </section>
  );
}
