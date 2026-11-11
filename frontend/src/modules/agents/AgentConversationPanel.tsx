import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../../shared/ui";
import {
  api,
  labels,
  message,
  mutation,
  type Catalog,
  type Context,
  type Conversation,
} from "./api";
import "./agents.css";
import { ProgramSelector } from "./ProgramSelector";

type Props = {
  conversationId: string;
  refresh: number;
  onConfirmed: () => void;
  institutional?: boolean;
  canWrite?: boolean;
};

export function AgentConversationPanel(props: Props) {
  return <ConversationAgents key={props.conversationId} {...props} />;
}

function ConversationAgents({
  conversationId,
  refresh,
  onConfirmed,
  institutional = false,
  canWrite = true,
}: Props) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [detail, setDetail] = useState<Conversation | null>(null);
  const [mode, setMode] = useState("automatic");
  const [agentId, setAgentId] = useState("");
  const [contextId, setContextId] = useState("");
  const [editing, setEditing] = useState<Context | null>(null);
  const [newContextId, setNewContextId] = useState(() => crypto.randomUUID());
  const [program, setProgram] = useState("");
  const [stage, setStage] = useState("");
  const [applicant, setApplicant] = useState("");
  const [period, setPeriod] = useState("");
  const [evidence, setEvidence] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  async function load() {
    const config = await api<Catalog>(institutional ? "/selection" : "");
    setCatalog(config);
    if (config.installed) {
      const result = await api<Conversation>(
        `/conversations/${conversationId}`,
      );
      setDetail(result);
      setMode(result.mode);
      setContextId(result.context_id ?? "");
      setAgentId(result.selection?.agent_id ?? "");
    }
  }
  useEffect(() => {
    let live = true;
    void api<Catalog>(institutional ? "/selection" : "")
      .then(async (config) => {
        if (!live) return;
        setCatalog(config);
        if (!config.installed) return;
        const result = await api<Conversation>(
          `/conversations/${conversationId}`,
        );
        if (live) {
          setError("");
          setDetail(result);
          setMode(result.mode);
          setContextId(result.context_id ?? "");
          setAgentId(result.selection?.agent_id ?? "");
        }
      })
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [conversationId, refresh, institutional]);
  async function act(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setFeedback("");
    try {
      await work();
      await load();
      setConfirmed(false);
      setFeedback(
        "Contexto confirmado. La operación no modifica estados del SIIE.",
      );
      onConfirmed();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No se pudo completar la operación.",
      );
    } finally {
      setBusy(false);
    }
  }
  function edit(context: Context | null) {
    setEditing(context);
    setProgram(context ? String(context.program_id) : "");
    setStage(context?.stage_id ?? "");
    setApplicant(context?.applicant_id ? String(context.applicant_id) : "");
    setPeriod(context?.period_id ? String(context.period_id) : "");
    setEvidence("");
    setConfirmed(false);
  }
  if (catalog && !catalog.installed) return null;
  const activeContext = detail?.contexts.find((c) => c.id === contextId);
  const name = (id: string | null | undefined) =>
    catalog?.agents.find((a) => a.id === id)?.name ??
    "Sin responsable disponible";
  return (
    <section
      className="agents-conversation"
      aria-label="Agentes y contexto de admisiones"
    >
      <h3>Agentes de admisiones</h3>
      {error && <Notice error>{error}</Notice>}
      {feedback && <Notice>{feedback}</Notice>}
      {!detail && !error && <p>Cargando contexto de admisiones…</p>}
      {error && (
        <Button variant="quiet" onClick={() => void act(async () => {})}>
          Actualizar contexto
        </Button>
      )}
      {detail && catalog?.installed && (
        <>
          {detail.selection ? (
            <>
              <Badge>{name(detail.selection.agent_id)}</Badge>
              <p>
                Supervisor del programa:{" "}
                {detail.selection.supervisor_id
                  ? name(detail.selection.supervisor_id)
                  : "Orientador institucional"}{" "}
                · versión {detail.selection.version}.
              </p>
            </>
          ) : (
            <p>
              {detail.blocked
                ? message(detail.blocked)
                : "Sin agente seleccionado"}
            </p>
          )}
          <fieldset disabled={busy || !canWrite}>
            <SelectField
              id={`agents-context-${conversationId}`}
              label="Programa y postulación"
              value={contextId}
              options={[
                { value: "", label: "Sin programa confirmado · orientador" },
                ...detail.contexts.map((c) => ({
                  value: c.id,
                  label: `${catalog.programs.items.find((p) => p.program_id === c.program_id)?.name ?? "Programa guardado"}${c.applicant_id ? " · solicitud vinculada" : " · interés confirmado"}`,
                })),
              ]}
              onChange={(e) => {
                setContextId(e.target.value);
                setConfirmed(false);
              }}
            />
            {activeContext && (
              <p>
                Etapa:{" "}
                {catalog.stages.find((s) => s.id === activeContext.stage_id)
                  ?.name ?? "Sin etapa aprobada"}
                .
              </p>
            )}
            <SelectField
              id={`agents-mode-${conversationId}`}
              label="Modalidad de atención"
              value={mode}
              options={["automatic", "manual", "human"].map((value) => ({
                value,
                label: labels[value],
              }))}
              onChange={(e) => {
                setMode(e.target.value);
                setConfirmed(false);
              }}
            />
            {mode === "manual" && (
              <SelectField
                id={`agents-owner-${conversationId}`}
                label="Agente protegido"
                value={agentId}
                options={[
                  { value: "", label: "Seleccione responsable" },
                  ...catalog.agents
                    .filter((a) => a.state === "active")
                    .map((a) => ({ value: a.id, label: a.name })),
                ]}
                onChange={(e) => {
                  setAgentId(e.target.value);
                  setConfirmed(false);
                }}
              />
            )}
            <p>
              {mode === "human"
                ? "Tomar atención humana invalida respuestas automáticas pendientes. El asesor humano asignado se conserva."
                : mode === "manual"
                  ? "La asignación se conserva hasta que una persona la libere; los conflictos no se resuelven cambiando de agente."
                  : "La resolución utiliza únicamente el programa y etapa confirmados. Liberar a automático no activa proveedores ni transportes."}
            </p>
            <TextArea
              id={`agents-assignment-evidence-${conversationId}`}
              label="Motivo y evidencia de la decisión"
              value={evidence}
              maxLength={1000}
              rows={3}
              onChange={(e) => {
                setEvidence(e.target.value);
                setConfirmed(false);
              }}
            />
            <label>
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              Confirmo el programa, la postulación y la modalidad seleccionados.
            </label>
            <Button
              disabled={
                !confirmed ||
                !evidence.trim() ||
                (mode === "manual" && !agentId)
              }
              onClick={() =>
                void act(async () => {
                  await api(
                    `/conversations/${conversationId}/assignment`,
                    "PUT",
                    {
                      ...mutation(detail.revision),
                      mode,
                      agent_id: mode === "manual" ? agentId : null,
                      context_id: contextId || null,
                      note: evidence,
                      confirmed,
                    },
                  );
                })
              }
            >
              {mode === "human"
                ? "Tomar atención humana"
                : mode === "manual"
                  ? "Proteger asignación"
                  : "Confirmar atención automática"}
            </Button>
          </fieldset>
          <details>
            <summary>Confirmar programa, solicitud o cambio de etapa</summary>
            <fieldset disabled={busy || !canWrite}>
              <p>
                Una postulación nueva conserva las anteriores. Las condiciones y
                evidencias de la etapa deben comprobarse por una persona.
              </p>
              <SelectField
                id={`agents-edit-context-${conversationId}`}
                label="Contexto a revisar"
                value={editing?.id ?? ""}
                options={[
                  { value: "", label: "Crear otro contexto" },
                  ...detail.contexts.map((c) => ({
                    value: c.id,
                    label:
                      catalog.programs.items.find(
                        (p) => p.program_id === c.program_id,
                      )?.name ?? "Programa guardado",
                  })),
                ]}
                onChange={(e) =>
                  edit(
                    detail.contexts.find((c) => c.id === e.target.value) ??
                      null,
                  )
                }
              />
              <ProgramSelector
                id={`agents-context-program-${conversationId}`}
                label="Programa confirmado"
                disabled={!!editing}
                value={program}
                programs={catalog.programs.items}
                emptyLabel="Seleccione un programa vigente"
                onChange={(value) => {
                  setProgram(value);
                  setStage("");
                  setConfirmed(false);
                }}
              />
              <SelectField
                id={`agents-context-stage-${conversationId}`}
                label="Etapa confirmada"
                value={stage}
                options={[
                  { value: "", label: "Sin etapa confirmada" },
                  ...catalog.stages
                    .filter(
                      (s) => s.program_id === Number(program) && s.approved,
                    )
                    .map((s) => ({ value: s.id, label: s.name })),
                ]}
                onChange={(e) => {
                  setStage(e.target.value);
                  setConfirmed(false);
                }}
              />
              {stage &&
                (() => {
                  const selected = catalog.stages.find((s) => s.id === stage);
                  return selected ? (
                    <dl>
                      <dt>Entrada</dt>
                      <dd>{selected.entry_rule}</dd>
                      <dt>Salida</dt>
                      <dd>{selected.exit_rule}</dd>
                      <dt>Evidencia requerida</dt>
                      <dd>{selected.evidence_required}</dd>
                    </dl>
                  ) : null;
                })()}
              {!institutional && (
                <details>
                  <summary>
                    Vincular una solicitud institucional existente
                  </summary>
                  <p>
                    Opcional. Esta confirmación enlaza el registro exacto; no
                    busca coincidencias por nombre, documento o teléfono. El
                    servidor valida programa y período.
                  </p>
                  <Field
                    id={`agents-applicant-${conversationId}`}
                    label="Identificador de la solicitud SIIE"
                    type="number"
                    min={1}
                    disabled={!!editing}
                    value={applicant}
                    onChange={(e) => {
                      setApplicant(e.target.value);
                      setConfirmed(false);
                    }}
                  />
                  <Field
                    id={`agents-period-${conversationId}`}
                    label="Identificador del período de la solicitud"
                    type="number"
                    min={1}
                    disabled={!!editing}
                    value={period}
                    onChange={(e) => {
                      setPeriod(e.target.value);
                      setConfirmed(false);
                    }}
                  />
                </details>
              )}
              <p>
                Para confirmar este contexto complete el motivo y la casilla de
                revisión del bloque anterior. Guardarlo no lo selecciona
                automáticamente para responder.
              </p>
              <Button
                disabled={busy || !program || !confirmed || !evidence.trim()}
                onClick={() =>
                  void act(async () => {
                    const key = editing?.id ?? newContextId;
                    await api(
                      `/conversations/${conversationId}/contexts/${key}`,
                      "PUT",
                      {
                        ...mutation(editing?.revision ?? 0),
                        program_id: Number(program),
                        applicant_id: Number(applicant) || null,
                        period_id: Number(period) || null,
                        stage_id: stage || null,
                        evidence,
                        confirmed,
                      },
                    );
                    setEditing(null);
                    setNewContextId(crypto.randomUUID());
                  })
                }
              >
                Confirmar contexto y evidencia
              </Button>
            </fieldset>
          </details>
          {institutional && canWrite && detail.selection && (
            <ConversationDraft
              key={`${conversationId}:${detail.revision}:${detail.selection.version}`}
              conversationId={conversationId}
              revision={detail.revision}
            />
          )}
          <a href="#/agents">Administrar agentes y etapas</a>
        </>
      )}
    </section>
  );
}

function ConversationDraft({
  conversationId,
  revision,
}: {
  conversationId: string;
  revision: number;
}) {
  const [question, setQuestion] = useState("");
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{
    text?: string;
    network_called: boolean;
    handoff?: boolean;
    sources: { id: string; title: string }[];
  } | null>(null);
  const [uncertain, setUncertain] = useState(false);
  async function generate(paid: boolean) {
    setBusy(true);
    setError("");
    if (paid) setUncertain(true);
    try {
      const next = await api<NonNullable<typeof result>>(
        `/conversations/${conversationId}/draft`,
        "POST",
        {
          request_id: crypto.randomUUID(),
          revision,
          question,
          call_provider: paid,
          acknowledge_consumption: paid && ack,
          channel: "local",
        },
      );
      setResult(next);
      setUncertain(false);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "No se pudo obtener el borrador.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <details>
      <summary>Borrador del agente asignado</summary>
      <p>
        Utiliza el programa y la versión actuales. Revise la respuesta antes de
        usarla; generarla no envía mensajes.
      </p>
      {error && <Notice error>{error}</Notice>}
      <fieldset disabled={busy}>
        <TextArea
          id={`agent-draft-${conversationId}`}
          label="Consulta para el agente"
          maxLength={2000}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <Button
          variant="secondary"
          disabled={!question.trim()}
          onClick={() => void generate(false)}
        >
          Revisar contexto sin consumir IA
        </Button>
        <label>
          <input
            type="checkbox"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
          />
          Confirmo el consumo de IA para este borrador.
        </label>
        <Button
          disabled={!question.trim() || !ack || uncertain}
          onClick={() => void generate(true)}
        >
          Generar borrador
        </Button>
      </fieldset>
      {uncertain && (
        <Notice>
          El intento puede haber consumido presupuesto. Revise la supervisión
          antes de iniciar otro.
        </Notice>
      )}
      {result && (
        <div role="status">
          {result.text ? (
            <p className="agents-response-text">{result.text}</p>
          ) : (
            <p>
              Contexto disponible: {result.sources.length} fuentes. Sin consumo
              de IA.
            </p>
          )}
          {result.handoff && <p>Requiere atención de un asesor.</p>}
          {result.sources.map((s) => (
            <p key={s.id}>{s.title}</p>
          ))}
        </div>
      )}
    </details>
  );
}
