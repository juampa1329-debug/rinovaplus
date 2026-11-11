import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import {
  useWorkspaceField,
  useWorkspaceState,
} from "../../../shared/workspaceSession";
import {
  aiRequest,
  credentialNames,
  defaultMedia,
  providerNames,
  type AiConfig,
  type AiModel,
  type AiProvider,
  type AiSnapshot,
  type CredentialProvider,
  type MediaConfig,
  type VoiceCatalog,
} from "../../../shared/aiSettings";
import {
  channelRequest,
  channelReferences,
  channelStates,
  type ChannelAccount,
  type ChannelKey,
} from "../../../shared/channels";
import { ChannelSettings } from "../../../features/ChannelSettings";
import { Badge, Button, Field, Notice, SelectField } from "../../../shared/ui";
import "./apiIntegrations.css";

const textProviders = Object.keys(providerNames) as AiProvider[];
const voiceProviders = ["elevenlabs", "google_tts", "piper"] as const;
const searchProviders = ["tavily", "brave", "serpapi"] as const;
const admissionChannels: ChannelKey[] = [
  "whatsapp",
  "instagram",
  "tiktok",
  "messenger",
  "facebook",
];
const descriptions: Record<string, string> = {
  gemini: "Modelos de Google para texto y análisis multimedia.",
  nvidia: "Modelos NVIDIA NIM mediante su API compatible con OpenAI.",
  openai: "Modelos de OpenAI con credencial propia.",
  anthropic: "Modelos Claude para conversación y análisis.",
  hermes:
    "Agente interno compatible con OpenAI, configurado por el administrador.",
  groq: "Inferencia de texto y transcripción, independientes de xAI / Grok.",
  mistral: "Modelos de Mistral para conversación y clasificación.",
  openrouter: "Acceso a modelos mediante OpenRouter, con respaldo explícito.",
  kimi: "Modelos de Moonshot AI para conversación y razonamiento.",
  xai: "Modelos Grok mediante la API de xAI.",
  elevenlabs: "Voces y modelos de síntesis disponibles en su cuenta.",
  google_tts: "Catálogo de voces de Google Cloud Text-to-Speech.",
  piper: "Síntesis de voz con Piper.",
  tavily: "Búsqueda web e imágenes para consultas explícitas del Asistente.",
  brave: "Búsqueda web e imágenes con Brave Search API.",
  serpapi: "Resultados estructurados de búsqueda web e imágenes.",
};
type Status = {
  provider: string;
  model: string;
  state: string;
  latency_ms: number | null;
  tokens: { input: number; output: number } | null;
  origin: string;
  checked_at: string;
  detail: string | null;
};
const statusNames: Record<string, string> = {
  not_checked: "Sin revisar",
  missing_key: "Sin API key",
  missing_endpoint: "Sin endpoint",
  outbound_disabled: "Salida externa deshabilitada",
  missing_model: "Sin modelo",
  available: "Respuesta confirmada",
  catalog_available: "Disponible en catálogo",
  error: "No disponible",
};
const statusDetails: Record<string, string> = {
  provider_endpoint_missing:
    "El administrador debe configurar HERMES_BASE_URL con el endpoint HTTPS del agente interno.",
  provider_key_missing:
    "Agregue la credencial de este proveedor. No se realizó una llamada externa.",
  outbound_disabled:
    "Autorice las consultas externas para realizar un diagnóstico. No se realizó una llamada externa.",
  model_selection_required: "Seleccione y guarde un modelo antes de revisarlo.",
  provider_rejected_request:
    "El proveedor rechazó la solicitud. Revise la clave, el modelo, los permisos y el saldo.",
  provider_temporary_failure: "El proveedor no está disponible temporalmente.",
  provider_rate_limited:
    "El proveedor indicó un límite de solicitudes o cuota (HTTP 429). Revise su panel antes de reintentar.",
  provider_timeout_or_network:
    "No se obtuvo respuesta dentro del tiempo permitido.",
  provider_connection_failed:
    "No se pudo establecer la conexión con el proveedor. Revise la red y la configuración.",
  provider_response_timeout:
    "El proveedor no respondió dentro del tiempo de lectura permitido. Revise su disponibilidad antes de reintentar.",
  provider_empty_or_blocked_response:
    "El proveedor no devolvió una respuesta de texto utilizable.",
  provider_invalid_response:
    "El proveedor devolvió una respuesta incompatible.",
  voice_catalog_required:
    "La voz guardada no está disponible en el catálogo consultado.",
  voice_model_required:
    "El modelo de voz guardado no está disponible en el catálogo consultado.",
  piper_unavailable: "El motor Piper no está disponible.",
  voice_catalog_verified_without_synthesis:
    "Catálogo y selección confirmados. No se generó audio ni se acreditó la síntesis.",
  provider_history_unsupported:
    "El modelo requiere conservar el contexto para continuar esta conversación.",
  settings_revision_conflict:
    "Los ajustes cambiaron. Recargue antes de revisar otra vez.",
};

function FocusModal({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    const previous = document.activeElement;
    dialog?.showModal();
    return () => {
      dialog?.close();
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, []);
  return createPortal(
    <dialog
      ref={ref}
      className="api-modal"
      aria-label={title}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="configuration-row">
        <div>
          <h3>{title}</h3>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <Button variant="quiet" onClick={onClose}>
          Cerrar
        </Button>
      </div>
      {children}
    </dialog>,
    document.body,
  );
}

function ApiGroup({
  title,
  note,
  items,
  opened,
  toggle,
  render,
}: {
  title: string;
  note: string;
  items: { id: string; name: string; description: string }[];
  opened: string[];
  toggle: (id: string) => void;
  render: (id: string) => ReactNode;
}) {
  return (
    <section className="api-group" aria-label={title}>
      <div className="configuration-row">
        <h3>{title}</h3>
        <small>{note}</small>
      </div>
      <div className="api-tiles">
        {items
          .filter((item) => !opened.includes(item.id))
          .map((item) => (
            <article className="api-tile" key={item.id}>
              <h4>{item.name}</h4>
              <p>{item.description}</p>
              <Button
                variant="quiet"
                aria-expanded={false}
                aria-label={`Añadir ${item.name}`}
                onClick={() => toggle(item.id)}
              >
                Añadir
              </Button>
            </article>
          ))}
      </div>
      <div
        className={`api-editors${title === "Canales de admisiones" ? " api-editors-channels" : ""}`}
      >
        {items
          .filter((item) => opened.includes(item.id))
          .map((item) => (
            <article className="api-editor" key={item.id}>
              <div className="configuration-row">
                <div>
                  <h4>{item.name}</h4>
                  <p>{item.description}</p>
                </div>
                <Button
                  variant="quiet"
                  aria-expanded={true}
                  aria-label={`Ocultar ${item.name}`}
                  onClick={() => toggle(item.id)}
                >
                  Ocultar
                </Button>
              </div>
              {render(item.id)}
            </article>
          ))}
      </div>
    </section>
  );
}

export function ApiIntegrationsPanel() {
  const [, setSettingsSection] = useWorkspaceState("settingsSection");
  const [snapshot, setSnapshot] = useWorkspaceField("ai", "snapshot");
  const [draft, setDraft] = useWorkspaceField("ai", "draft");
  const [catalogs, setCatalogs] = useWorkspaceField("ai", "catalogs");
  const [voiceCatalogs, setVoiceCatalogs] = useWorkspaceField(
    "ai",
    "voiceCatalogs",
  );
  const [busy, setBusy] = useWorkspaceField("ai", "busy");
  const [error, setError] = useWorkspaceField("ai", "error");
  const [feedback, setFeedback] = useWorkspaceField("ai", "feedback");
  const [opened, setOpened] = useState<string[]>([]);
  const [credential, setCredential] = useState<CredentialProvider | null>(null);
  const [secret, setSecret] = useState("");
  const [credentialFeedback, setCredentialFeedback] = useState<
    Partial<Record<CredentialProvider, string>>
  >({});
  const [status, setStatus] = useState<Status | null>(null);
  const [statusTarget, setStatusTarget] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<ChannelAccount[]>([]);
  const [refreshedAt, setRefreshedAt] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    channelRequest<{ channels: ChannelAccount[] }>(
      "/api/v1/channels",
      "GET",
      undefined,
      controller.signal,
    )
      .then((data) => setAccounts(data.channels))
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, [setError]);
  if (!snapshot || !draft) return null;
  const current = snapshot;
  const settings = draft;
  const media = settings.media ?? defaultMedia;
  const dirty = JSON.stringify(current.settings) !== JSON.stringify(settings);
  const providerOptions = textProviders.map((value) => ({
    value,
    label: providerNames[value],
  }));
  function toggle(id: string) {
    setOpened((previous) =>
      previous.includes(id)
        ? previous.filter((value) => value !== id)
        : [...previous, id],
    );
  }
  async function run(label: string, action: () => Promise<void>) {
    setBusy(label);
    setError("");
    setFeedback("");
    try {
      await action();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "No se pudo completar la operación.",
      );
    } finally {
      setBusy("");
    }
  }
  function applyConnection(data: AiSnapshot) {
    setSnapshot((previous) => (previous ? { ...previous, ...data } : previous));
    setCatalogs({});
    setVoiceCatalogs({});
    setStatus(null);
  }
  async function saveSettings(value: AiConfig) {
    const saved = await aiRequest<{ revision: number; settings: AiConfig }>(
      "settings",
      "PUT",
      { revision: current.revision, settings: value },
    );
    setSnapshot((previous) =>
      previous ? { ...previous, ...saved } : previous,
    );
    setDraft(saved.settings);
    setFeedback(
      `Ajustes guardados · Revisión ${saved.revision}. No se activaron solicitudes externas.`,
    );
  }
  function source(id: string) {
    return current.providers.find((item) => item.id === id);
  }
  function credentialRow(id: CredentialProvider) {
    const state = source(id);
    return (
      <>
        <div className="api-credential-row">
          <div>
            <strong>{state?.environment_variable || "API key"}</strong>
            <small>
              {state?.credential_source === "local"
                ? "Guardada cifrada · Sin validación automática"
                : state?.credential_source === "environment"
                  ? "Disponible"
                  : "Sin guardar"}
            </small>
          </div>
          <Button
            variant="secondary"
            disabled={!!busy || !current.credential_storage_available}
            onClick={() => {
              setSecret("");
              setError("");
              setCredential(id);
            }}
          >
            Agregar
          </Button>
        </div>
        {credentialFeedback[id] && <Notice>{credentialFeedback[id]}</Notice>}
      </>
    );
  }
  function modelsFor(provider: AiProvider) {
    const value =
      settings.provider_models?.[provider] ??
      (settings.provider === provider
        ? settings.model
        : settings.backup_provider === provider
          ? settings.backup_model
          : "");
    const items = catalogs[provider] ?? [];
    return {
      value,
      items,
      origin: items.some((item) => item.id === value)
        ? "Catálogo consultado"
        : value
          ? "Manual · Sin verificar"
          : "Sin modelo",
    };
  }
  async function loadModels(provider: AiProvider) {
    await run("Cargando modelos", async () => {
      const data = await aiRequest<{ models: AiModel[] }>(
        `models/${provider}`,
        "POST",
        {},
      );
      setCatalogs((previous) => ({ ...previous, [provider]: data.models }));
      setFeedback(
        `${data.models.length} modelos recibidos de ${providerNames[provider]}. El catálogo no confirma permisos de inferencia.`,
      );
    });
  }
  function saveModel(provider: AiProvider) {
    const selected = modelsFor(provider).value;
    const activeChanged =
      settings.provider === provider && selected !== current.settings.model;
    const value = {
      ...settings,
      provider_models: { ...settings.provider_models, [provider]: selected },
      ...(settings.provider === provider
        ? {
            model: selected,
            fallback_model:
              settings.fallback_model === selected
                ? ""
                : settings.fallback_model,
          }
        : {}),
      ...(settings.backup_provider === provider
        ? {
            backup_model: selected,
            backup_fallback_model:
              settings.backup_fallback_model === selected
                ? ""
                : settings.backup_fallback_model,
          }
        : {}),
      ...(activeChanged ? { enabled: false } : {}),
    };
    void run("Guardando modelo", () => saveSettings(value));
  }
  async function inspect(provider: string) {
    setStatusTarget(provider);
    setStatus(null);
    await run("Revisando estado", async () => {
      const voice = voiceProviders.includes(
        provider as (typeof voiceProviders)[number],
      );
      const savedVoice =
        current.settings.voice_models?.[
          provider as (typeof voiceProviders)[number]
        ];
      const model = voice
        ? (savedVoice?.model ?? "")
        : (current.settings.provider_models?.[provider as AiProvider] ??
          (current.settings.provider === provider
            ? current.settings.model
            : current.settings.backup_provider === provider
              ? current.settings.backup_model
              : ""));
      const data = await aiRequest<Status>(`model-status/${provider}`, "POST", {
        revision: current.revision,
        credential_revision: current.credential_revision,
        model,
        voice_id: voice ? (savedVoice?.voice_id ?? "") : "",
      });
      setStatus(data);
    });
  }
  function textEditor(id: string) {
    const provider = id as AiProvider;
    const { value, items, origin } = modelsFor(provider);
    return (
      <>
        <Badge>
          {source(id)?.credential_source === "local"
            ? "Guardada"
            : source(id)?.configured
              ? "Disponible en entorno"
              : "Sin guardar"}
        </Badge>
        {credentialRow(provider)}
        <SelectField
          id={`api-model-${id}`}
          label="Modelo"
          value={items.some((item) => item.id === value) ? value : ""}
          options={[
            { value: "", label: "Seleccione del catálogo consultado" },
            ...items.map((item) => ({
              value: item.id,
              label:
                item.name === item.id ? item.id : `${item.name} · ${item.id}`,
            })),
          ]}
          onChange={(event) =>
            setDraft({
              ...settings,
              provider_models: {
                ...settings.provider_models,
                [provider]: event.target.value,
              },
            })
          }
        />
        <Field
          id={`api-model-manual-${id}`}
          label="ID del modelo"
          maxLength={200}
          pattern={String.raw`[A-Za-z0-9._:\/\-]*`}
          value={value}
          hint={origin}
          onChange={(event) =>
            setDraft({
              ...settings,
              provider_models: {
                ...settings.provider_models,
                [provider]: event.target.value,
              },
            })
          }
        />
        <div className="actions">
          <Button
            variant="secondary"
            disabled={!!busy}
            onClick={() => void loadModels(provider)}
          >
            Cargar modelos
          </Button>
          <Button
            disabled={!!busy || !value}
            onClick={() => saveModel(provider)}
          >
            Guardar modelo
          </Button>
          <Button
            variant="secondary"
            disabled={!!busy}
            onClick={() => void inspect(provider)}
          >
            Revisar estatus
          </Button>
        </div>
        {id === "hermes" && (
          <small>
            El endpoint HTTPS se administra mediante HERMES_BASE_URL. Esta
            pantalla no configura herramientas ni acciones del agente.
          </small>
        )}
      </>
    );
  }
  function voiceEditor(id: string) {
    const provider = id as MediaConfig["voice_provider"];
    const selection =
      settings.voice_models?.[provider] ??
      (media.voice_provider === provider
        ? { model: media.voice_model, voice_id: media.voice_id }
        : { model: "", voice_id: "" });
    const catalog = voiceCatalogs[provider];
    function updateVoice(patch: Partial<typeof selection>) {
      setDraft({
        ...settings,
        voice_models: {
          ...settings.voice_models,
          [provider]: { ...selection, ...patch },
        },
      });
    }
    return (
      <>
        {provider !== "piper" ? (
          credentialRow(provider)
        ) : (
          <p>
            No requiere API key.
          </p>
        )}
        <SelectField
          id={`api-voice-${id}`}
          label="Voz del catálogo"
          value={
            catalog?.voices.some((item) => item.id === selection.voice_id)
              ? selection.voice_id
              : ""
          }
          options={[
            { value: "", label: "Seleccione una voz disponible" },
            ...(catalog?.voices ?? []).map((item) => ({
              value: item.id,
              label: item.name,
            })),
          ]}
          onChange={(event) => updateVoice({ voice_id: event.target.value })}
        />
        <Field
          id={`api-voice-manual-${id}`}
          label="ID de voz"
          maxLength={200}
          value={selection.voice_id}
          hint={
            catalog?.voices.some((item) => item.id === selection.voice_id)
              ? "Voz presente en el catálogo consultado"
              : "Manual · Sin verificar"
          }
          onChange={(event) => updateVoice({ voice_id: event.target.value })}
        />
        {provider === "elevenlabs" && (
          <>
            <SelectField
              id={`api-voice-model-${id}`}
              label="Modelo de síntesis"
              value={
                catalog?.models.some((item) => item.id === selection.model)
                  ? selection.model
                  : ""
              }
              options={[
                { value: "", label: "Seleccione del catálogo" },
                ...(catalog?.models ?? []).map((item) => ({
                  value: item.id,
                  label: item.name,
                })),
              ]}
              onChange={(event) => updateVoice({ model: event.target.value })}
            />
            <Field
              id={`api-voice-model-manual-${id}`}
              label="ID del modelo de síntesis"
              value={selection.model}
              maxLength={200}
              onChange={(event) => updateVoice({ model: event.target.value })}
            />
          </>
        )}
        <div className="actions">
          <Button
            variant="secondary"
            disabled={!!busy}
            onClick={() =>
              void run("Cargando voces", async () => {
                const data = await aiRequest<VoiceCatalog>(
                  `voice-catalog/${provider}`,
                  "POST",
                  {},
                );
                setVoiceCatalogs((previous) => ({
                  ...previous,
                  [provider]: data,
                }));
                setFeedback(
                  data.ready
                    ? "Catálogo consultado. La síntesis aún no se ha probado."
                    : "Piper no tiene el motor instalado.",
                );
              })
            }
          >
            Cargar modelos
          </Button>
          <Button
            disabled={!!busy || !selection.voice_id}
            onClick={() =>
              void run("Guardando voz", () =>
                saveSettings({
                  ...settings,
                  voice_models: {
                    ...settings.voice_models,
                    [provider]: selection,
                  },
                  ...(media.voice_provider === provider
                    ? {
                        media: {
                          ...media,
                          voice_model: selection.model,
                          voice_id: selection.voice_id,
                        },
                      }
                    : {}),
                }),
              )
            }
          >
            Guardar modelo
          </Button>
          <Button
            variant="secondary"
            disabled={!!busy}
            onClick={() => void inspect(provider)}
          >
            Revisar estatus
          </Button>
        </div>
        <small>
          Revisar estatus comprueba el catálogo y la selección; no genera una
          nota de voz.
        </small>
      </>
    );
  }
  return (
    <div className="api-integrations" aria-label="Configuración de APIs">
      <div className="configuration-row">
        <div>
          <h3>Conexiones de la aplicación</h3>
          <p>
            Agregue los proveedores que utilizará. Las claves se guardan
            cifradas y no vuelven a mostrarse.
          </p>
        </div>
        <Badge>
          {current.outbound_enabled
            ? "Consultas externas autorizadas"
            : "Salida externa deshabilitada"}
        </Badge>
      </div>
      {error && <Notice error>{error}</Notice>}
      {feedback && <Notice>{feedback}</Notice>}
      {busy && <p role="status">{busy}…</p>}
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={current.outbound_enabled}
          disabled={!!busy || !current.credential_storage_available}
          onChange={(event) => {
            const enabled = event.target.checked;
            void run("Guardando permiso", async () => {
              applyConnection(
                await aiRequest<AiSnapshot>("outbound", "PUT", {
                  revision: current.credential_revision,
                  enabled,
                }),
              );
              setFeedback(
                enabled
                  ? "Consultas externas autorizadas por el operador. Las revisiones pueden generar costes."
                  : "Consultas externas deshabilitadas.",
              );
            });
          }}
        />
        Permitir consultas y diagnósticos externos
      </label>
      <ApiGroup
        title="Proveedores IA"
        note="LLM / modelos"
        items={textProviders.map((id) => ({
          id,
          name: providerNames[id],
          description: descriptions[id],
        }))}
        opened={opened}
        toggle={toggle}
        render={textEditor}
      />
      <div className="api-selection">
        <h4>Selección de uso</h4>
        {!current.settings.enabled && (
          <Notice>
            IA está deshabilitada. Después de guardar el modelo, habilite y
            valide IA para conversar.
            <div className="actions">
              <Button
                variant="secondary"
                onClick={() => setSettingsSection("IA")}
              >
                Configurar y habilitar IA
              </Button>
            </div>
          </Notice>
        )}
        <p>
          Guardar un proveedor o modelo no habilita IA. La activación se
          administra en Ajustes → IA.
        </p>
        <div className="form-grid">
          <SelectField
            id="api-use-primary"
            label="Proveedor principal"
            value={settings.provider}
            options={providerOptions}
            onChange={(event) => {
              const provider = event.target.value as AiProvider;
              const same = settings.backup_provider === provider;
              setDraft({
                ...settings,
                provider,
                model: settings.provider_models?.[provider] ?? "",
                fallback_model: "",
                ...(same
                  ? {
                      backup_provider: null,
                      backup_model: "",
                      backup_fallback_model: "",
                    }
                  : {}),
              });
            }}
          />
          <SelectField
            id="api-use-backup"
            label="Proveedor de respaldo"
            value={settings.backup_provider ?? ""}
            options={[
              { value: "", label: "Sin respaldo" },
              ...providerOptions.filter(
                (item) => item.value !== settings.provider,
              ),
            ]}
            onChange={(event) => {
              const provider = event.target.value as AiProvider;
              setDraft({
                ...settings,
                backup_provider: provider || null,
                backup_model: settings.provider_models?.[provider] ?? "",
                backup_fallback_model: "",
              });
            }}
          />
        </div>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={settings.fallback_enabled}
            onChange={(event) =>
              setDraft({ ...settings, fallback_enabled: event.target.checked })
            }
          />
          Permitir el respaldo elegido al ejecutar IA
        </label>
        <Button
          disabled={!!busy}
          onClick={() =>
            void run("Guardando selección", () =>
              saveSettings({
                ...settings,
                enabled:
                  current.settings.enabled &&
                  settings.provider === current.settings.provider &&
                  settings.model === current.settings.model,
              }),
            )
          }
        >
          Guardar selección
        </Button>
      </div>
      <ApiGroup
        title="Voz"
        note="ElevenLabs / Google / Piper"
        items={voiceProviders.map((id) => ({
          id,
          name: id === "piper" ? "Piper" : credentialNames[id],
          description: descriptions[id],
        }))}
        opened={opened}
        toggle={toggle}
        render={voiceEditor}
      />
      <div className="api-selection">
        <SelectField
          id="api-use-voice"
          label="Proveedor de voz utilizado por el Asistente"
          value={media.voice_provider}
          options={voiceProviders.map((value) => ({
            value,
            label: value === "piper" ? "Piper" : credentialNames[value],
          }))}
          onChange={(event) => {
            const provider = event.target
              .value as MediaConfig["voice_provider"];
            const selection = settings.voice_models?.[provider];
            setDraft({
              ...settings,
              media: {
                ...media,
                voice_provider: provider,
                voice_model: selection?.model ?? "",
                voice_id: selection?.voice_id ?? "",
              },
            });
          }}
        />
        <Button
          disabled={!!busy}
          onClick={() =>
            void run("Guardando proveedor de voz", () => saveSettings(settings))
          }
        >
          Guardar selección de voz
        </Button>
      </div>
      <ApiGroup
        title="Búsqueda web e imágenes"
        note="Tavily / Brave / SerpAPI"
        items={searchProviders.map((id) => ({
          id,
          name: credentialNames[id],
          description: descriptions[id],
        }))}
        opened={opened}
        toggle={toggle}
        render={(id) => (
          <>
            {credentialRow(id as CredentialProvider)}
            <Badge>
              {media.search_provider === id
                ? "Seleccionado"
                : "No seleccionado"}
            </Badge>
            <Button
              variant="secondary"
              disabled={!!busy}
              onClick={() =>
                void run("Guardando búsqueda", () =>
                  saveSettings({
                    ...settings,
                    media: {
                      ...media,
                      search_provider: id as MediaConfig["search_provider"],
                    },
                  }),
                )
              }
            >
              Usar para búsquedas
            </Button>
          </>
        )}
      />
      <ApiGroup
        title="Canales de admisiones"
        note="Mensajes y cuentas oficiales"
        items={admissionChannels.map((id) => ({
          id,
          name: channelReferences[id].name,
          description: channelReferences[id].purpose,
        }))}
        opened={opened}
        toggle={toggle}
        render={(id) => (
          <>
            <Badge>
              {
                channelStates[
                  accounts.find((item) => item.channel === id)?.state ??
                    "unconfigured"
                ]
              }
            </Badge>
            <ChannelSettings focusedChannel={id as ChannelKey} />
          </>
        )}
      />
      <section className="api-group" aria-label="API interna">
        <div className="configuration-row">
          <h3>API interna</h3>
          <small>Base URL</small>
        </div>
        <code className="api-base-url">{window.location.origin}/api</code>
        <p>
          Administración de credenciales del CRM.
        </p>
        <Button
          variant="secondary"
          disabled={!!busy}
          onClick={() =>
            void run("Refrescando credenciales", async () => {
              const [latest, channels] = await Promise.all([
                aiRequest<AiSnapshot>("settings"),
                channelRequest<{ channels: ChannelAccount[] }>(
                  "/api/v1/channels",
                ),
              ]);
              setSnapshot(latest);
              if (!dirty) setDraft(latest.settings);
              setAccounts(channels.channels);
              setCatalogs({});
              setVoiceCatalogs({});
              setRefreshedAt(new Date().toLocaleString("es-CO"));
              setFeedback(
                "Metadatos de credenciales actualizados. No se rotaron claves ni se realizaron llamadas a proveedores.",
              );
            })
          }
        >
          Refrescar credenciales
        </Button>
        {refreshedAt && <p>Última actualización: {refreshedAt}</p>}
        <small>
          Revisión {current.revision} ·{" "}
          {dirty ? "Cambios sin guardar" : "Cambios guardados"} · Solo se
          consultan metadatos, nunca valores secretos.
        </small>
      </section>
      {credential && (
        <FocusModal
          title={credentialNames[credential]}
          subtitle={source(credential)?.environment_variable}
          onClose={() => {
            setSecret("");
            setCredential(null);
          }}
        >
          {error && <Notice error>{error}</Notice>}
          {busy && <Notice>{busy}… Espere la confirmación.</Notice>}
          {error && !secret && (
            <p>
              El valor se limpió del formulario. Vuelva a ingresarlo para
              reintentar; no se confirmó un nuevo guardado.
            </p>
          )}
          <p>
            Ingrese el valor completo. Se cifra y desaparece del
            navegador al guardar o cerrar. Guardar no valida la clave ni
            consulta al proveedor.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (busy) return;
              const provider = credential;
              const value = secret;
              setSecret("");
              void run("Guardando credencial", async () => {
                const data = await aiRequest<AiSnapshot>(
                  `credentials/${provider}`,
                  "PUT",
                  { revision: current.credential_revision, api_key: value },
                );
                applyConnection(data);
                if (
                  data.providers.find((item) => item.id === provider)
                    ?.credential_source !== "local"
                ) {
                  throw new Error(
                    "No se confirmó una credencial guardada para este proveedor. Actualice la información antes de continuar.",
                  );
                }
                setCredentialFeedback((previous) => ({
                  ...previous,
                  [provider]:
                    "Credencial cifrada guardada en este proyecto. Pendiente de validación con el proveedor.",
                }));
                setCredential(null);
                setFeedback(
                  `Credencial de ${credentialNames[provider]} guardada cifrada. Sin validación automática.`,
                );
              });
            }}
          >
            <Field
              id="api-modal-new-secret"
              label="Nuevo valor"
              type="password"
              autoFocus
              autoComplete="new-password"
              spellCheck={false}
              maxLength={4096}
              required
              value={secret}
              onChange={(event) => setSecret(event.target.value)}
            />
            <div className="actions">
              <Button type="submit" disabled={!!busy || !secret.trim()}>
                Guardar cifrado
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setSecret("");
                  setCredential(null);
                }}
              >
                Cancelar
              </Button>
              {source(credential)?.credential_source === "local" && (
                <Button
                  variant="quiet"
                  disabled={!!busy}
                  onClick={() => {
                    const provider = credential;
                    setSecret("");
                    void run("Eliminando credencial", async () => {
                      applyConnection(
                        await aiRequest<AiSnapshot>(
                          `credentials/${provider}`,
                          "DELETE",
                          { revision: current.credential_revision },
                        ),
                      );
                      setCredential(null);
                      setCredentialFeedback((previous) => ({
                        ...previous,
                        [provider]:
                          "Credencial guardada eliminada. Si existe una clave en el entorno, permanece disponible.",
                      }));
                      setFeedback(
                        "Credencial guardada eliminada.",
                      );
                    });
                  }}
                >
                  Eliminar credencial guardada
                </Button>
              )}
            </div>
          </form>
          {source(credential)?.credential_source === "environment" && (
            <small>
              Existe una clave en el entorno. Guardar crea una credencial del
              proyecto con prioridad.
            </small>
          )}
        </FocusModal>
      )}
      {statusTarget && (
        <FocusModal
          title="Estado del modelo"
          subtitle={
            statusTarget === "piper"
              ? "Piper"
              : credentialNames[statusTarget as CredentialProvider]
          }
          onClose={() => {
            setStatusTarget(null);
            setStatus(null);
          }}
        >
          {error && <Notice error>{error}</Notice>}
          {status ? (
            <>
              <dl className="api-status-facts">
                <div>
                  <dt>Modelo</dt>
                  <dd>{status.model || "Sin seleccionar"}</dd>
                </div>
                <div>
                  <dt>Estado</dt>
                  <dd>
                    <Badge>
                      {statusNames[status.state] ?? "No disponible"}
                    </Badge>
                  </dd>
                </div>
                <div>
                  <dt>Latencia</dt>
                  <dd>
                    {status.latency_ms === null
                      ? "Sin datos"
                      : `${status.latency_ms} ms`}
                  </dd>
                </div>
                <div>
                  <dt>Tokens (entrada / salida)</dt>
                  <dd>
                    {status.tokens
                      ? `${status.tokens.input} / ${status.tokens.output}`
                      : "Sin datos"}
                  </dd>
                </div>
                <div>
                  <dt>Origen</dt>
                  <dd>
                    {status.origin === "catalog"
                      ? "Catálogo consultado"
                      : "Manual / sin catálogo"}
                  </dd>
                </div>
                <div>
                  <dt>Última revisión</dt>
                  <dd>{new Date(status.checked_at).toLocaleString("es-CO")}</dd>
                </div>
              </dl>
              {status.detail && (
                <Notice error={status.state === "error"}>
                  {statusDetails[status.detail] ??
                    "La operación no pudo confirmarse. Revise la configuración del proveedor."}
                </Notice>
              )}
            </>
          ) : (
            <p role="status">
              {busy
                ? "Revisando estado…"
                : "No se pudo obtener el estado. Revise el aviso de la pantalla."}
            </p>
          )}
          <div className="actions">
            <Button
              disabled={!!busy}
              onClick={() => void inspect(statusTarget)}
            >
              Revisar otra vez
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setStatusTarget(null);
                setStatus(null);
              }}
            >
              Cerrar
            </Button>
          </div>
        </FocusModal>
      )}
    </div>
  );
}
