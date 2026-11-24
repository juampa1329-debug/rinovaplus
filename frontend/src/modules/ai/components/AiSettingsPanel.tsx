import { ApiIntegrationsPanel } from "./ApiIntegrationsPanel";
import {
  useWorkspaceField,
  useWorkspaceState,
} from "../../../shared/workspaceSession";
import { MediaSettingsFields } from "./MediaSettingsFields";
import { useEffect, useState } from "react";
import {
  aiRequest,
  providerNames,
  defaultMedia,
  type VoiceCatalog,
  type AiConfig,
  type AiModel,
  type AiProvider,
  type AiSnapshot,
  type AiTestResult,
} from "../../../shared/aiSettings";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../../../shared/ui";

const providers = Object.entries(providerNames).map(([value, label]) => ({
  value,
  label,
}));
const numericFields = [
  ["max_tokens", "Máximo de tokens por solicitud", 64, 8192, 1],
  ["temperature", "Temperatura", 0, 2, 0.1],
  [
    "wait_seconds",
    "Espera desde el último mensaje (seg; recomendado 60)",
    0,
    3600,
    1,
  ],
  [
    "typing_ms",
    "Tiempo de escritura antes del primer envío (ms)",
    0,
    15000,
    100,
  ],
  ["chars_per_message", "Caracteres por mensaje", 40, 4000, 1],
  ["fragment_delay_ms", "Espera entre fragmentos (ms)", 0, 30000, 100],
  ["output_tokens", "Máximo de tokens de salida", 64, 8192, 1],
  ["recent_messages", "Mensajes recientes", 0, 30, 1],
  ["history_chars", "Caracteres por mensaje histórico", 40, 4000, 1],
] as const;

export function AiSettingsPanel({
  section,
  active,
}: {
  section: string;
  active: boolean;
}) {
  const [, setSettingsSection] = useWorkspaceState("settingsSection");
  const [snapshot, setSnapshot] = useWorkspaceField("ai", "snapshot");
  const [draft, setDraft] = useWorkspaceField("ai", "draft");
  const [catalogs, setCatalogs] = useWorkspaceField("ai", "catalogs");
  const [busy, setBusy] = useWorkspaceField("ai", "busy");
  const [error, setError] = useWorkspaceField("ai", "error");
  const [feedback, setFeedback] = useWorkspaceField("ai", "feedback");
  const [reloadPending, setReloadPending] = useWorkspaceField(
    "ai",
    "reloadPending",
  );
  const [prompt, setPrompt] = useWorkspaceField("ai", "prompt");
  const [history, setHistory] = useWorkspaceField("ai", "history");
  const [result, setResult] = useWorkspaceField("ai", "result");
  const [voiceCatalogs, setVoiceCatalogs] = useWorkspaceField(
    "ai",
    "voiceCatalogs",
  );
  const [groqAudioModels, setGroqAudioModels] = useState<AiModel[]>([]);
  const [testConversation, setTestConversation] = useState<{
    id: string;
    binding: string;
  } | null>(null);
  const visible = active && (section === "IA" || section === "APIs");
  const dirty =
    !!snapshot && JSON.stringify(snapshot.settings) !== JSON.stringify(draft);

  useEffect(() => {
    if (!visible) return;
    let live = true;
    aiRequest<AiSnapshot>("settings")
      .then((data) => {
        if (live) {
          setSnapshot(data);
          if (!dirty) setDraft(data.settings);
          setError("");
        }
      })
      .catch((reason: Error) => {
        if (live) setError(reason.message);
      });
    return () => {
      live = false;
    };
  }, [visible, section, setSnapshot, setDraft, setError]);

  function update<K extends keyof AiConfig>(key: K, value: AiConfig[K]) {
    if (!draft) return;
    setDraft({ ...draft, [key]: value });
    setResult(null);
    setFeedback("");
    setError("");
  }
  function choosePrimary(provider: AiProvider) {
    if (!draft) return;
    const sameBackup = draft.backup_provider === provider;
    setDraft({
      ...draft,
      provider,
      model: draft.provider_models?.[provider] ?? "",
      fallback_model: "",
      backup_provider: sameBackup ? null : draft.backup_provider,
      backup_model: sameBackup ? "" : draft.backup_model,
      backup_fallback_model: sameBackup ? "" : draft.backup_fallback_model,
    });
    setResult(null);
  }
  function chooseBackup(provider: AiProvider | null) {
    if (!draft) return;
    setDraft({
      ...draft,
      backup_provider: provider,
      backup_model: provider ? (draft.provider_models?.[provider] ?? "") : "",
      backup_fallback_model: "",
    });
    setResult(null);
  }
  async function loadGroqAudio() {
    await operation("Cargando modelos de audio", async () => {
      const data = await aiRequest<{ models: AiModel[] }>(
        "audio-models/groq",
        "POST",
        {},
      );
      setGroqAudioModels(data.models);
      setFeedback(
        "Catálogo de transcripción Groq consultado. Selecciona un modelo y guarda los ajustes.",
      );
    });
  }
  async function operation(label: string, action: () => Promise<void>) {
    setBusy(label);
    setError("");
    setFeedback("");
    try {
      await action();
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function reload() {
    await operation("Recargando", async () => {
      const data = await aiRequest<AiSnapshot>("settings");
      setSnapshot(data);
      setDraft(data.settings);
      setResult(null);
      setCatalogs({});
      setVoiceCatalogs({});
      setGroqAudioModels([]);
      setHistory([]);
      setReloadPending(false);
      setFeedback("Ajustes cargados.");
    });
  }
  const modelOptions = (
    provider: AiProvider | null,
    value: string,
    excluded = "",
  ) => {
    const models = provider ? (catalogs[provider] ?? []) : [];
    const options = models
      .filter((model) => model.id !== excluded)
      .map((model) => ({
        value: model.id,
        label:
          model.name === model.id ? model.id : `${model.name} · ${model.id}`,
      }));
    if (value && !options.some((option) => option.value === value))
      options.unshift({ value, label: `${value} · Catálogo pendiente` });
    return [{ value: "", label: "Sin modelo seleccionado" }, ...options];
  };
  if (!visible) return null;
  if (section === "APIs" && snapshot && draft) return <ApiIntegrationsPanel />;
  return (
    <section className="ai-settings" aria-label="Configuración IA">
      <div className="panel-heading">
        <div>
          <h3>
            {section === "APIs" ? "Proveedores y modelos" : "Ajustes de IA"}
          </h3>
          <p>Configure los asistentes y proveedores disponibles.</p>
        </div>
        <Badge>
          {snapshot?.outbound_enabled
            ? "Canales habilitados"
            : "Canales pendientes"}
        </Badge>
      </div>
      {error && <Notice error>{error}</Notice>}
      {feedback && <Notice>{feedback}</Notice>}
      {!draft || !snapshot ? (
        <>
          <p>Actualice la información para cargar y guardar los ajustes.</p>
          <Button disabled={!!busy} onClick={() => void reload()}>
            Cargar ajustes
          </Button>
        </>
      ) : (
        <>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void operation("Guardando", async () => {
                if (draft.enabled) {
                  if (!snapshot.outbound_enabled)
                    throw new Error(
                      "Autorice las consultas externas en Ajustes > APIs antes de habilitar IA.",
                    );
                  if (!draft.model)
                    throw new Error(
                      "Seleccione y guarde el modelo principal en Ajustes > APIs antes de habilitar IA.",
                    );
                  const requiredProviders = new Set<AiProvider>([
                    draft.provider,
                  ]);
                  if (
                    draft.fallback_enabled &&
                    draft.backup_provider &&
                    draft.backup_model
                  )
                    requiredProviders.add(draft.backup_provider);
                  for (const provider of requiredProviders) {
                    if (
                      !snapshot.providers.find((item) => item.id === provider)
                        ?.configured
                    )
                      throw new Error(
                        `Falta la credencial de ${providerNames[provider]}. Guárdela en Ajustes > APIs.`,
                      );
                    const data = await aiRequest<{ models: AiModel[] }>(
                      `models/${provider}`,
                      "POST",
                      {},
                    );
                    setCatalogs((previous) => ({
                      ...previous,
                      [provider]: data.models,
                    }));
                  }
                  const media = draft.media ?? defaultMedia;
                  if (media.voice_enabled) {
                    if (!media.voice_id)
                      throw new Error(
                        "Seleccione una voz antes de habilitar las respuestas de audio.",
                      );
                    if (
                      media.voice_provider === "elevenlabs" &&
                      !media.voice_model
                    )
                      throw new Error(
                        "Seleccione un modelo de ElevenLabs antes de habilitar las respuestas de audio.",
                      );
                    const catalog = await aiRequest<VoiceCatalog>(
                      `voice-catalog/${media.voice_provider}`,
                      "POST",
                      {},
                    );
                    setVoiceCatalogs((previous) => ({
                      ...previous,
                      [media.voice_provider]: catalog,
                    }));
                    if (
                      !catalog.ready ||
                      !catalog.voices.some((item) => item.id === media.voice_id)
                    )
                      throw new Error(
                        "La voz seleccionada no está disponible en el catálogo del proveedor. Seleccione otra voz y guarde de nuevo.",
                      );
                    if (
                      media.voice_provider === "elevenlabs" &&
                      !catalog.models.some(
                        (item) => item.id === media.voice_model,
                      )
                    )
                      throw new Error(
                        "El modelo de voz seleccionado no está disponible en su cuenta de ElevenLabs.",
                      );
                  }
                }
                const saved = await aiRequest<{
                  revision: number;
                  settings: AiConfig;
                }>("settings", "PUT", {
                  revision: snapshot.revision,
                  settings: draft,
                });
                setSnapshot({ ...snapshot, ...saved });
                setDraft(saved.settings);
                setResult(null);
                setFeedback(
                  saved.settings.enabled
                    ? "IA validada y habilitada. Abra Asistente para enviar su mensaje; no se envió ningún mensaje al guardar."
                    : "Ajustes guardados. IA permanece deshabilitada hasta que la habilite y guarde explícitamente.",
                );
              });
            }}
          >
            <fieldset disabled={!!busy} className="ai-fieldset">
              {
                <>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={draft.enabled}
                      onChange={(event) =>
                        update("enabled", event.target.checked)
                      }
                    />
                    IA habilitada para el Asistente
                  </label>
                  <p className="scope-text">
                    Para conversar, marque IA habilitada y pulse Validar y
                    guardar IA. Al guardar con IA habilitada se consultan los
                    catálogos de los proveedores elegidos y, si activó voz, su
                    catálogo de voces. No se genera una respuesta ni audio al
                    guardar.
                  </p>
                  <div className="actions">
                    <Button
                      variant="secondary"
                      onClick={() => setSettingsSection("APIs")}
                    >
                      Configurar APIs y modelos
                    </Button>
                    <Button
                      variant="quiet"
                      disabled={!snapshot.settings.enabled || dirty}
                      onClick={() => {
                        window.location.hash = "/assistant";
                      }}
                    >
                      Abrir Asistente
                    </Button>
                  </div>
                  <div className="form-grid">
                    <SelectField
                      id="ai-provider"
                      label="Proveedor principal"
                      options={providers}
                      value={draft.provider}
                      onChange={(event) =>
                        choosePrimary(event.target.value as AiProvider)
                      }
                    />
                    <div className="ai-model-summary">
                      <span>Modelo principal</span>
                      <strong>
                        {draft.model || "Sin modelo seleccionado"}
                      </strong>
                      <small>Seleccione el modelo en Ajustes → APIs.</small>
                    </div>
                  </div>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={draft.fallback_enabled}
                      onChange={(event) =>
                        update("fallback_enabled", event.target.checked)
                      }
                    />
                    Permitir fallback por modelo y proveedor de respaldo
                  </label>
                  <p className="scope-text">
                    Al habilitarlo, el Asistente puede usar los modelos de
                    respaldo elegidos. Solo se continúa ante límite de
                    solicitudes, timeout o fallo temporal; máximo cuatro
                    intentos, uno por modelo.
                  </p>
                  <div className="form-grid">
                    <SelectField
                      id="ai-fallback"
                      label="Fallback del modelo principal"
                      options={modelOptions(
                        draft.provider,
                        draft.fallback_model,
                        draft.model,
                      )}
                      value={draft.fallback_model}
                      disabled={!draft.fallback_enabled}
                      onChange={(event) =>
                        update("fallback_model", event.target.value)
                      }
                    />
                    <SelectField
                      id="ai-backup-provider"
                      label="Proveedor de respaldo"
                      options={[
                        { value: "", label: "Sin proveedor de respaldo" },
                        ...providers.filter(
                          (item) => item.value !== draft.provider,
                        ),
                      ]}
                      value={draft.backup_provider ?? ""}
                      disabled={!draft.fallback_enabled}
                      onChange={(event) =>
                        chooseBackup((event.target.value as AiProvider) || null)
                      }
                    />
                    <div className="ai-model-summary">
                      <span>Modelo de respaldo</span>
                      <strong>
                        {draft.backup_model || "Sin modelo de respaldo"}
                      </strong>
                      <small>Seleccione el modelo en Ajustes → APIs.</small>
                    </div>
                    <SelectField
                      id="ai-backup-fallback"
                      label="Fallback del modelo de respaldo"
                      options={modelOptions(
                        draft.backup_provider,
                        draft.backup_fallback_model,
                        draft.backup_model,
                      )}
                      value={draft.backup_fallback_model}
                      disabled={!draft.fallback_enabled || !draft.backup_model}
                      onChange={(event) =>
                        update("backup_fallback_model", event.target.value)
                      }
                    />
                  </div>
                  <TextArea
                    id="ai-system-prompt"
                    label="System prompt · Instrucciones de estilo"
                    rows={7}
                    maxLength={8000}
                    value={draft.system_prompt}
                    aria-describedby="ai-prompt-count"
                    onChange={(event) =>
                      update("system_prompt", event.target.value)
                    }
                  />
                  <small id="ai-prompt-count">
                    {Array.from(draft.system_prompt).length} / 8000 caracteres.
                    Identidad IA, control humano y protección de SIIE se se
                    mantienen en la configuración.
                  </small>
                  <div className="form-grid ai-numbers">
                    {numericFields
                      .slice(0, 2)
                      .map(([key, label, min, max, step]) => (
                        <Field
                          key={key}
                          id={`ai-${key}`}
                          label={label}
                          type="number"
                          min={min}
                          max={max}
                          step={step}
                          required
                          value={Number.isNaN(draft[key]) ? "" : draft[key]}
                          onChange={(event) =>
                            update(
                              key,
                              event.target.value === ""
                                ? NaN
                                : Number(event.target.value),
                            )
                          }
                        />
                      ))}
                  </div>
                  <h3>Ritmo de respuesta</h3>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={draft.brief_responses}
                      onChange={(event) =>
                        update("brief_responses", event.target.checked)
                      }
                    />
                    Respuestas breves sin perder contexto
                  </label>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={draft.split_responses}
                      onChange={(event) =>
                        update("split_responses", event.target.checked)
                      }
                    />
                    Fragmentar respuestas largas en mensajes naturales
                  </label>
                  <div className="form-grid ai-numbers">
                    {numericFields
                      .slice(2)
                      .map(([key, label, min, max, step]) => (
                        <Field
                          key={key}
                          id={`ai-${key}`}
                          label={label}
                          type="number"
                          min={min}
                          max={max}
                          step={step}
                          required
                          value={Number.isNaN(draft[key]) ? "" : draft[key]}
                          onChange={(event) =>
                            update(
                              key,
                              event.target.value === ""
                                ? NaN
                                : Number(event.target.value),
                            )
                          }
                        />
                      ))}
                  </div>
                  <MediaSettingsFields
                    media={draft.media ?? defaultMedia}
                    onChange={(media) => update("media", media)}
                    catalogs={voiceCatalogs}
                    geminiModels={catalogs.gemini ?? []}
                    groqAudioModels={groqAudioModels}
                    loadAudioModels={loadGroqAudio}
                    outboundEnabled={snapshot.outbound_enabled}
                    section="IA"
                    loadCatalog={async (provider) => {
                      await operation("Cargando voces", async () => {
                        const data = await aiRequest<VoiceCatalog>(
                          `voice-catalog/${provider}`,
                          "POST",
                          {},
                        );
                        setVoiceCatalogs((previous) => ({
                          ...previous,
                          [provider]: data,
                        }));
                      });
                    }}
                  />
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={draft.show_typing}
                      onChange={(event) =>
                        update("show_typing", event.target.checked)
                      }
                    />
                    Solicitar “escribiendo…” cuando el canal lo permita
                  </label>
                  <p className="scope-text">
                    La vista muestra un plan temporal. WhatsApp y su indicador
                    de escritura no están conectados. Se usa el menor de los dos
                    límites de tokens; tokens y caracteres son medidas
                    distintas.
                  </p>
                </>
              }
              <div className="actions">
                <Button type="submit">
                  {busy === "Guardando"
                    ? "Guardando…"
                    : draft.enabled
                      ? "Validar y guardar IA"
                      : "Guardar ajustes IA"}
                </Button>
                <Button
                  variant="secondary"
                  disabled={!dirty}
                  onClick={() => {
                    setDraft(snapshot.settings);
                    setResult(null);
                    setError("");
                    setFeedback("Cambios de IA pendientes descartados.");
                  }}
                >
                  Descartar cambios IA
                </Button>
                <Button
                  variant="quiet"
                  onClick={() => {
                    if (dirty) setReloadPending(true);
                    else void reload();
                  }}
                >
                  Recargar ajustes IA
                </Button>
              </div>
            </fieldset>
          </form>
          {reloadPending && (
            <div role="alert">
              <p>Recargar descartará los cambios IA sin guardar.</p>
              <div className="actions">
                <Button onClick={() => void reload()} disabled={!!busy}>
                  Confirmar recarga
                </Button>
                <Button variant="quiet" onClick={() => setReloadPending(false)}>
                  Conservar cambios
                </Button>
              </div>
            </div>
          )}
          <p className="scope-text">
            Versión {snapshot.revision} ·{" "}
            {dirty ? "Cambios sin guardar" : "Cambios guardados"}. conserva esta
            configuración.
          </p>
          {busy && <p role="status">{busy}…</p>}
          {section === "IA" && (
            <div className="ai-test">
              <h3>Probar IA</h3>
              <p>Revise la respuesta generada antes de continuar.</p>
              <TextArea
                id="ai-test-prompt"
                label="Mensaje"
                value={prompt}
                maxLength={2000}
                disabled={!!busy}
                onChange={(event) => {
                  setPrompt(event.target.value);
                  setResult(null);
                }}
              />
              <div className="actions">
                <Button
                  disabled={
                    !!busy ||
                    dirty ||
                    !draft.enabled ||
                    !snapshot.outbound_enabled ||
                    !prompt.trim()
                  }
                  onClick={() =>
                    void operation("Probando IA", async () => {
                      setResult(null);
                      const binding = `${snapshot.revision}:${snapshot.credential_revision}`;
                      let conversation = testConversation;
                      if (
                        !conversation ||
                        conversation.binding !== binding ||
                        !history.length
                      ) {
                        const created = await aiRequest<{
                          conversation_id: string;
                        }>("conversation", "POST", {});
                        conversation = { id: created.conversation_id, binding };
                        setTestConversation(conversation);
                      }
                      const data = await aiRequest<AiTestResult>(
                        "test",
                        "POST",
                        {
                          revision: snapshot.revision,
                          prompt,
                          history,
                          conversation_id: conversation.id,
                        },
                      );
                      setResult(data);
                      setHistory(
                        [
                          ...history,
                          { role: "user", content: prompt },
                          {
                            role: "assistant",
                            content: data.text.slice(-4000),
                          },
                        ].slice(-30) as typeof history,
                      );
                    })
                  }
                >
                  Probar IA con ajustes guardados
                </Button>
                <Button
                  variant="quiet"
                  disabled={!!busy || !history.length}
                  onClick={() => {
                    setHistory([]);
                    setResult(null);
                  }}
                >
                  Limpiar historial
                </Button>
              </div>
              <p className="scope-text">
                {history.length} mensajes en el historial.
              </p>
              {result && (
                <div className="ai-test-result" role="status">
                  <h4>Respuesta recibida · {providerNames[result.provider]}</h4>
                  <p>
                    {result.model} · Versión {result.revision} ·{" "}
                    {result.attempts.length} intento(s) ·{" "}
                    {result.history_messages_used} mensaje(s) históricos ·
                    Límite {result.effective_output_tokens} tokens
                  </p>
                  <p className="ai-response">{result.text}</p>
                  <h4>Plan de fragmentos</h4>
                  <ol>
                    {result.plan.map((fragment, index) => (
                      <li key={index}>
                        <strong>{fragment.after_ms / 1000} s</strong>
                        <p>{fragment.text}</p>
                      </li>
                    ))}
                  </ol>
                  <p>
                    {result.typing_requested
                      ? "Indicador de escritura solicitado; no disponible sin canal conectado."
                      : "Indicador de escritura no solicitado."}
                  </p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
