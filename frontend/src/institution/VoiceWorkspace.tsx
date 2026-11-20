import { useContext, useEffect, useRef, useState } from "react";
import {
  Badge,
  Button,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../shared/ui";
import { Icon } from "../shared/Icon";
import { api, type Catalog } from "../modules/agents/api";
import {
  ApiError,
  send,
  useInstitution,
  useIntent,
  useTask,
  type Setting,
} from "./api";
import { ResourceState, useResource } from "./Settings";
import { useDraftGuard } from "./drafts";
import { ErrorFeedback, ErrorFeedbackContext } from "./ErrorFeedback";
import { explainChannelError } from "./channelErrors";
import "./voice.css";
import {
  VoiceAmbience,
  ambienceDefaults,
  type Ambience,
} from "./VoiceAmbience";

export type VoiceProfile = {
  id: string;
  name: string;
  voice_id: string;
  model_id: string;
  active: boolean;
  delivery?: string;
  allow_reactions?: boolean;
  speech_instructions?: string;
  stability?: number | null;
  similarity_boost?: number;
  language_code?: string;
  greeting_tone?: string;
  ambience?: Ambience;
  agent_ids: string[];
  schools: string[];
};
export type VoicePolicy = {
  enabled: boolean;
  scope: "selected_conversations" | "all";
  conversation_ids: string[];
  max_audios_per_conversation: number;
  mode: string;
  long_reply_min_chars: number;
  max_text_chars: number;
  max_audio_seconds: number;
  daily_character_limit: number;
  default_profile_id: string;
  profiles: VoiceProfile[];
};
const defaults: VoicePolicy = {
  enabled: false,
  scope: "selected_conversations",
  conversation_ids: [],
  max_audios_per_conversation: 3,
  mode: "voice_notes_or_long",
  long_reply_min_chars: 400,
  max_text_chars: 2000,
  max_audio_seconds: 60,
  daily_character_limit: 20000,
  default_profile_id: "",
  profiles: [],
};
type CatalogItem = {
  id: string;
  name: string;
  language?: string;
  languages?: { id: string; name: string }[];
};
type VoiceCatalog = { voices: CatalogItem[]; models: CatalogItem[] };
type Usage = {
  used?: number;
  pinned?: { name: string } | null;
  daily_characters: number;
  daily_attempts: number;
  reported_attempts?: number;
  reported_characters?: number | null;
  uncertain_attempts?: number;
  running_attempts?: number;
  history: {
    id: string;
    state: string;
    code: string | null;
    at: string;
    profile: string;
    characters: number;
    reported_characters?: number | null;
    duration?: number | null;
    audio_url?: string | null;
    greeting_tone?: string;
  }[];
};
type Preview = {
  id?: string;
  remix_available?: boolean;
  state: string;
  code?: string;
  audio_url: string | null;
  duration: number;
  characters: number;
};
const greetingTones = [
  { value: "inherit", label: "Natural" },
  { value: "warm", label: "Cálida" },
  { value: "calm", label: "Tranquila" },
  { value: "upbeat", label: "Animada" },
] as const;

export function VoiceWorkspace() {
  return (
    <ErrorFeedback explain={explainChannelError}>
      <VoiceWorkspaceContent />
    </ErrorFeedback>
  );
}
function VoiceWorkspaceContent() {
  const settings = useResource<Setting>("settings/ai");
  if (!settings.value) return <ResourceState error={settings.error} />;
  return (
    <VoiceEditor
      key={settings.value.revision}
      initial={settings.value}
      reload={settings.reload}
    />
  );
}

function VoiceEditor({
  initial,
  reload,
}: {
  initial: Setting;
  reload: () => Promise<Setting>;
}) {
  const { call, session } = useInstitution();
  const task = useTask(),
    intent = useIntent(),
    previewIntent = useIntent();
  const saved = {
    ...defaults,
    ...(initial.document.voice as Partial<VoicePolicy> | undefined),
  };
  const [draft, setDraft] = useState<VoicePolicy>(saved);
  const [catalog, setCatalog] = useState<VoiceCatalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [assignments, setAssignments] = useState<Catalog | null>(null);
  const [pilotConversations, setPilotConversations] = useState<
    { id: string; label: string }[]
  >([]);
  const [pilotError, setPilotError] = useState("");
  const [previewProfile, setPreviewProfile] = useState(
    saved.default_profile_id,
  );
  const [sample, setSample] = useState(
    "Hola, qué gusto saludarte. En CBN puedes explorar nuestros programas y resolver tus dudas con calma. Cuéntame, ¿qué te gustaría aprender?",
  );
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [historyPreview, setHistoryPreview] = useState("");
  const [balance, setBalance] = useState<{
    used: number;
    limit: number;
    remaining: number;
    tier: string;
    checked_at: string;
    reset_at: number | null;
  } | null>(null);
  const [comparisons, setComparisons] = useState<
    { tone: string; result: Preview }[]
  >([]);
  const comparisonIntents = useRef(new Map<string, string>());
  const previewMounted = useRef(true);
  useEffect(() => {
    previewMounted.current = true;
    return () => {
      previewMounted.current = false;
    };
  }, []);
  const [usageConversation, setUsageConversation] = useState("");
  const usage = useResource<Usage>(
    "voice/usage" +
      (usageConversation
        ? `?conversation=${encodeURIComponent(usageConversation)}`
        : ""),
  );
  const changed = JSON.stringify(saved) !== JSON.stringify(draft);
  useDraftGuard(changed);
  const writable = session.actions.includes("settings.ai.write");
  const pilotAllowed = writable && session.actions.includes("inbox.read");
  useEffect(() => {
    let active = true;
    if (pilotAllowed)
      void send<{ items: { id: string; label: string }[] }>(
        "voice/conversations",
        "GET",
        undefined,
        session.csrf_token,
      )
        .then((value) => {
          if (active) {
            setPilotConversations(value.items);
            setPilotError("");
          }
        })
        .catch((error) => {
          if (active) setPilotError((error as Error).message);
        });
    return () => {
      active = false;
    };
  }, [pilotAllowed, session.csrf_token]);
  useEffect(() => {
    let active = true;
    void api<Catalog>("")
      .then((value) => {
        if (active) setAssignments(value);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  const catalogAllowed = session.actions.includes("settings.providers.read");
  useEffect(() => {
    let active = true;
    if (catalogAllowed)
      void send<VoiceCatalog>(
        "voice/catalog",
        "GET",
        undefined,
        session.csrf_token,
      )
        .then((value) => {
          if (active) {
            setCatalog(value);
            setCatalogError("");
          }
        })
        .catch((error) => {
          if (active) setCatalogError((error as Error).message);
        });
    return () => {
      active = false;
    };
  }, [session.csrf_token, catalogAllowed]);
  const update = <K extends keyof VoicePolicy>(key: K, value: VoicePolicy[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const profile = (id: string, patch: Partial<VoiceProfile>) =>
    setDraft((current) => ({
      ...current,
      profiles: current.profiles.map((p) =>
        p.id === id ? { ...p, ...patch } : p,
      ),
    }));
  const modelOptions =
    catalog?.models.map((v) => ({ value: v.id, label: v.name })) ?? [];
  const voiceOptions =
    catalog?.voices.map((v) => ({
      value: v.id,
      label: `${v.name}${v.language ? " · " + v.language : ""}`,
    })) ?? [];
  const schoolNames = [
    ...new Set(
      (assignments?.programs?.items ?? [])
        .map((p) => p.school?.trim())
        .filter((s): s is string => !!s),
    ),
  ].sort((a, b) => a.localeCompare(b, "es"));

  return (
    <div className="voice-workspace">
      <header className="voice-hero panel">
        <div>
          <span className="voice-eyebrow">ELEVENLABS · WHATSAPP</span>
          <h2>
            <Icon name="microphone" /> Una voz con criterio
          </h2>
          <p>
            El agente responde con su contexto y sus instrucciones. Tú decides
            cuándo usar audio y cuánto puede consumir cada conversación.
          </p>
        </div>
        <Badge>{draft.enabled ? "Voz activada" : "Respuestas por texto"}</Badge>
      </header>
      {task.notices}
      <div className="voice-summary">
        <article className="panel">
          <small>Por conversación</small>
          <strong>{draft.max_audios_per_conversation} audios</strong>
          <span>Al llegar al máximo, continúa por texto.</span>
        </article>
        <article className="panel">
          <small>Últimas 24 horas</small>
          <strong>
            {usage.value?.daily_characters.toLocaleString("es-CO") ?? "—"}{" "}
            caracteres
          </strong>
          <span>Reservados para generación y muestras.</span>
        </article>
        <article className="panel">
          <small>Identidad de voz</small>
          <strong>
            {draft.profiles.filter((p) => p.active).length} perfiles activos
          </strong>
          <span>Agente → escuela → voz predeterminada.</span>
        </article>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void task.run(async () => {
            const body = {
              revision: initial.revision,
              document: { ...initial.document, voice: draft },
            };
            await call("settings/ai", "PUT", {
              ...body,
              operation_id: intent.get(body),
            });
            intent.clear();
            await reload();
          }, "Política de voz guardada. Los contadores existentes se conservan.");
        }}
      >
        <fieldset disabled={!writable || task.busy || previewBusy}>
          <section className="panel voice-policy">
            <h3>Cuándo responder con voz</h3>
            <label className="voice-check">
              <input
                type="checkbox"
                checked={draft.enabled}
                onChange={(event) => update("enabled", event.target.checked)}
              />{" "}
              Activar audios automáticos de los agentes en WhatsApp
            </label>
            <SelectField
              id="voice-scope"
              label="Dónde aplicar la voz automática"
              value={draft.scope}
              onChange={(event) =>
                update("scope", event.target.value as VoicePolicy["scope"])
              }
              options={[
                {
                  value: "selected_conversations",
                  label: "Sólo conversaciones seleccionadas · piloto",
                },
                { value: "all", label: "Todas las conversaciones de WhatsApp" },
              ]}
            />
            {draft.scope === "selected_conversations" ? (
              <div className="voice-pilot">
                <p>
                  El piloto sólo genera voz para los hilos que marques. Las
                  demás conversaciones continúan por texto. El modo Humano sigue
                  teniendo prioridad.
                </p>
                {pilotError && <Notice error>{pilotError}</Notice>}
                {pilotConversations.map((target) => (
                  <label className="voice-check" key={target.id}>
                    <input
                      type="checkbox"
                      checked={draft.conversation_ids.includes(target.id)}
                      onChange={(event) =>
                        update(
                          "conversation_ids",
                          event.target.checked
                            ? [...draft.conversation_ids, target.id]
                            : draft.conversation_ids.filter(
                                (id) => id !== target.id,
                              ),
                        )
                      }
                    />
                    {target.label}
                  </label>
                ))}
                {!draft.conversation_ids.length && (
                  <p className="voice-note">
                    Selecciona un chat antes de activar el piloto.
                  </p>
                )}
              </div>
            ) : (
              <Notice>
                Al guardar con la voz activada, esta política se aplicará a
                todos los hilos de WhatsApp que estén en IA, incluidos los
                nuevos.
              </Notice>
            )}
            <div className="voice-fields">
              <SelectField
                id="voice-mode"
                label="Usar audio"
                value={draft.mode}
                onChange={(event) => update("mode", event.target.value)}
                options={[
                  {
                    value: "voice_notes",
                    label: "Cuando el cliente mande una nota de voz",
                  },
                  {
                    value: "long_explanations",
                    label: "Sólo para explicaciones largas",
                  },
                  {
                    value: "voice_notes_or_long",
                    label: "Nota de voz o explicación larga",
                  },
                  {
                    value: "voice_notes_and_long",
                    label: "Nota de voz y explicación larga a la vez",
                  },
                ]}
              />
              <Field
                id="voice-limit"
                label="Máximo de audios por conversación"
                type="number"
                min={0}
                max={100}
                required
                value={draft.max_audios_per_conversation}
                onChange={(event) =>
                  update(
                    "max_audios_per_conversation",
                    Number(event.target.value),
                  )
                }
                hint="0 = sólo texto de IA. El cupo de audios automáticos pertenece al hilo y no se reinicia al pasar a Humano o reiniciar el servidor. Las notas manuales no consumen ese cupo."
              />
              <Field
                id="voice-long"
                label="Explicación larga a partir de"
                type="number"
                min={120}
                max={2000}
                required
                value={draft.long_reply_min_chars}
                onChange={(event) =>
                  update("long_reply_min_chars", Number(event.target.value))
                }
                hint="Caracteres de la respuesta, incluidos espacios."
              />
              <Field
                id="voice-max-seconds"
                label="Duración máxima por audio (segundos)"
                type="number"
                min={0}
                max={300}
                required
                value={draft.max_audio_seconds}
                onChange={(event) =>
                  update("max_audio_seconds", Number(event.target.value))
                }
                hint="0 = sin límite de duración configurado. Estimamos antes de generar y verificamos el resultado: si se pasa, va completo por texto, sin cortes. El procesador admite archivos de hasta 5 minutos."
              />
              <Field
                id="voice-max-text"
                label="Máximo de caracteres por audio"
                type="number"
                min={draft.long_reply_min_chars}
                max={3000}
                required
                value={draft.max_text_chars}
                onChange={(event) =>
                  update("max_text_chars", Number(event.target.value))
                }
                hint="Una respuesta más extensa se envía completa por texto; no se recortan datos."
              />
              <Field
                id="voice-daily"
                label="Tope de caracteres en 24 horas"
                type="number"
                min={0}
                max={10000000}
                required
                value={draft.daily_character_limit}
                onChange={(event) =>
                  update("daily_character_limit", Number(event.target.value))
                }
                hint="Incluye muestras e intentos. 0 = sin tope interno diario; sigue aplicando el máximo por conversación."
              />
            </div>
            <p className="voice-note">
              En Humano la IA no genera ni envía audios. Si el proveedor falla,
              falta saldo o se agota el cupo, la respuesta continúa por texto.
              Un intento reservado ocupa un lugar aunque su resultado sea
              incierto, para evitar cobros duplicados.
            </p>
          </section>
          <section className="panel">
            <div className="voice-section-heading">
              <div>
                <h3>Voces de tu equipo</h3>
                <p>
                  Elige voces disponibles en tu cuenta. La primera voz utilizada
                  permanece asociada al hilo.
                </p>
                <p>
                  Para ofrecer otra voz en conversaciones nuevas, crea otro
                  perfil. Si pausas un perfil o cambias su voz/modelo, los hilos
                  que lo tenían fijado continúan por texto.
                </p>
              </div>
              <Button
                variant="secondary"
                disabled={!session.actions.includes("settings.providers.read")}
                onClick={() =>
                  void task.run(async () => {
                    setCatalog(await call<VoiceCatalog>("voice/catalog"));
                    setCatalogError("");
                  }, "Catálogo de ElevenLabs actualizado.")
                }
              >
                {catalog ? "Actualizar catálogo" : "Cargar voces y modelos"}
              </Button>
            </div>
            <p>
              <a href="#/settings/models">
                Guardar o reemplazar la clave de ElevenLabs en APIs y modelos
              </a>
            </p>
            {!catalog && (
              <p className="voice-note">
                Carga el catálogo para elegir voces y modelos con sus nombres,
                sin escribir identificadores manualmente.
              </p>
            )}
            <div className="voice-profiles">
              {draft.profiles.map((p, index) => (
                <article className="voice-profile" key={p.id}>
                  <div className="voice-section-heading">
                    <h4>Voz {index + 1}</h4>
                    <label className="voice-check">
                      <input
                        type="checkbox"
                        checked={p.active}
                        onChange={(event) =>
                          profile(p.id, { active: event.target.checked })
                        }
                      />{" "}
                      Disponible
                    </label>
                  </div>
                  <Field
                    id={`voice-name-${p.id}`}
                    label="Nombre del perfil"
                    maxLength={100}
                    required
                    value={p.name}
                    onChange={(event) =>
                      profile(p.id, { name: event.target.value })
                    }
                  />
                  <SelectField
                    id={`voice-choice-${p.id}`}
                    label="Voz de ElevenLabs"
                    value={p.voice_id}
                    disabled={!catalog}
                    onChange={(event) =>
                      profile(p.id, { voice_id: event.target.value })
                    }
                    options={[
                      { value: "", label: "Selecciona una voz" },
                      ...(!catalog && p.voice_id
                        ? [
                            {
                              value: p.voice_id,
                              label:
                                "Voz guardada · carga el catálogo para ver su nombre",
                            },
                          ]
                        : []),
                      ...voiceOptions,
                    ]}
                  />
                  <SelectField
                    id={`voice-model-${p.id}`}
                    label="Modelo de voz"
                    value={p.model_id}
                    disabled={!catalog}
                    onChange={(event) =>
                      profile(p.id, {
                        model_id: event.target.value,
                        language_code: "",
                      })
                    }
                    options={[
                      { value: "", label: "Selecciona un modelo" },
                      ...(!catalog && p.model_id
                        ? [{ value: p.model_id, label: p.model_id }]
                        : []),
                      ...modelOptions,
                    ]}
                  />
                  <div className="voice-tuning">
                    <div className="voice-slider-label">
                      <label htmlFor={`voice-stability-${p.id}`}>
                        Estabilidad
                      </label>
                      <output htmlFor={`voice-stability-${p.id}`}>
                        {Math.round(stabilityFor(p) * 100)}%
                      </output>
                    </div>
                    <input
                      id={`voice-stability-${p.id}`}
                      type="range"
                      min={0}
                      max={1}
                      step={p.model_id.startsWith("eleven_v3") ? 0.5 : 0.01}
                      value={stabilityFor(p)}
                      aria-valuetext={`${Math.round(stabilityFor(p) * 100)} por ciento`}
                      onChange={(event) =>
                        profile(p.id, { stability: Number(event.target.value) })
                      }
                    />
                    <div className="voice-range-legend">
                      <small>Creativo</small>
                      <small>Robusto</small>
                    </div>
                    <div className="voice-slider-label">
                      <label htmlFor={`voice-similarity-${p.id}`}>
                        Similitud
                      </label>
                      <output htmlFor={`voice-similarity-${p.id}`}>
                        {Math.round((p.similarity_boost ?? 0.75) * 100)}%
                      </output>
                    </div>
                    <input
                      id={`voice-similarity-${p.id}`}
                      type="range"
                      min={0}
                      max={1}
                      step={0.01}
                      value={p.similarity_boost ?? 0.75}
                      aria-valuetext={`${Math.round((p.similarity_boost ?? 0.75) * 100)} por ciento`}
                      onChange={(event) =>
                        profile(p.id, {
                          similarity_boost: Number(event.target.value),
                        })
                      }
                    />
                    <div className="voice-range-legend">
                      <small>Baja</small>
                      <small>Alta</small>
                    </div>
                    <SelectField
                      id={`voice-language-${p.id}`}
                      label="Idioma"
                      value={p.language_code ?? ""}
                      disabled={
                        !catalog || p.model_id === "eleven_multilingual_v2"
                      }
                      onChange={(event) =>
                        profile(p.id, { language_code: event.target.value })
                      }
                      options={[
                        { value: "", label: "Automático" },
                        ...(catalog?.models
                          .find((m) => m.id === p.model_id)
                          ?.languages?.map((l) => ({
                            value: l.id,
                            label:
                              (
                                {
                                  es: "Español",
                                  en: "Inglés",
                                  pt: "Portugués",
                                  fr: "Francés",
                                } as Record<string, string>
                              )[l.id] ?? l.name,
                          })) ?? []),
                      ]}
                    />
                    <small>
                      {p.model_id === "eleven_multilingual_v2"
                        ? "Este modelo detecta el idioma automáticamente; no admite fijarlo por API."
                        : "Los idiomas se cargan del modelo elegido. Menor estabilidad da más variación; mayor similitud conserva más rasgos de la voz original."}
                    </small>
                  </div>
                  <details>
                    <summary>Ambiente y mezcla de audio</summary>
                    <VoiceAmbience
                      id={`ambience-${p.id}`}
                      value={p.ambience}
                      onChange={(value) => profile(p.id, { ambience: value })}
                    />
                  </details>
                  <details>
                    <summary>Naturalidad e interpretación</summary>
                    <SelectField
                      id={`voice-greeting-${p.id}`}
                      label="Entonación del saludo"
                      value={p.greeting_tone ?? "inherit"}
                      onChange={(event) =>
                        profile(p.id, { greeting_tone: event.target.value })
                      }
                      disabled={!/^(eleven_v3|eleven_v4)/.test(p.model_id)}
                      options={greetingTones.map((v) => ({ ...v }))}
                    />
                    <small>
                      La entonación elegida se aplica al saludo inicial; después
                      continúa el estilo general. Requiere Eleven v4 o v3.
                      Puedes compararlas en Probar saludos, sin cambiar la voz
                      guardada.
                    </small>
                    <SelectField
                      id={`voice-delivery-${p.id}`}
                      label="Estilo de voz"
                      value={p.delivery ?? "conversational"}
                      onChange={(event) =>
                        profile(p.id, {
                          delivery: event.target.value,
                          stability: null,
                        })
                      }
                      options={[
                        {
                          value: "conversational",
                          label: "Cercano y conversado",
                        },
                        { value: "calm", label: "Calmado y empático" },
                        { value: "expressive", label: "Expresivo y animado" },
                        { value: "neutral", label: "Neutro" },
                      ]}
                    />
                    <label className="voice-check">
                      <input
                        type="checkbox"
                        checked={p.allow_reactions ?? false}
                        onChange={(event) =>
                          profile(p.id, {
                            allow_reactions: event.target.checked,
                          })
                        }
                      />{" "}
                      Permitir reacciones naturales cuando el contexto lo
                      justifique
                    </label>
                    <p>
                      Eleven v4 y v3 admiten indicaciones de entonación y
                      reacciones. No insertamos suspiros en cada frase ni
                      alteramos los hechos de la respuesta. Cada modelo recibe
                      sólo parámetros compatibles.
                    </p>
                    <TextArea
                      id={`voice-instructions-${p.id}`}
                      label="Cómo debe hablar este agente"
                      maxLength={1000}
                      value={p.speech_instructions ?? ""}
                      placeholder="Ejemplo: tono colombiano cercano, frases cortas, pausas suaves y una pregunta al final. Evita leer como un anuncio."
                      onChange={(event) =>
                        profile(p.id, {
                          speech_instructions: event.target.value,
                        })
                      }
                    />
                  </details>
                  <details>
                    <summary>Asignar agentes y escuelas</summary>
                    <p>
                      Un agente tiene prioridad sobre la escuela del programa
                      asignado en CRM. Preguntar por un programa no cambia la
                      asignación.
                    </p>
                    <Button
                      type="button"
                      variant="quiet"
                      onClick={() =>
                        void task.run(async () => {
                          setAssignments(await api<Catalog>(""));
                        }, "Agentes y escuelas actualizados.")
                      }
                    >
                      Actualizar agentes y escuelas
                    </Button>
                    <p>
                      La voz elegida al crear o editar el agente tiene
                      prioridad. Estas casillas son asignaciones automáticas
                      para agentes sin una elección directa.
                    </p>
                    {assignments?.agents.map((agent) => (
                      <label className="voice-check" key={agent.id}>
                        <input
                          type="checkbox"
                          checked={p.agent_ids.includes(agent.id)}
                          disabled={!!agent.configuration?.voice_profile_id}
                          onChange={(event) =>
                            profile(p.id, {
                              agent_ids: event.target.checked
                                ? [...p.agent_ids, agent.id]
                                : p.agent_ids.filter((id) => id !== agent.id),
                            })
                          }
                        />
                        {agent.name}
                        {agent.configuration?.voice_profile_id
                          ? " · voz elegida en el agente"
                          : ""}
                      </label>
                    ))}
                    <fieldset>
                      <legend>Escuelas de este perfil</legend>
                      {[...new Set([...schoolNames, ...p.schools])].map(
                        (school) => (
                          <label className="voice-check" key={school}>
                            <input
                              type="checkbox"
                              checked={p.schools.includes(school)}
                              onChange={(event) =>
                                profile(p.id, {
                                  schools: event.target.checked
                                    ? [...p.schools, school]
                                    : p.schools.filter((s) => s !== school),
                                })
                              }
                            />
                            {school}
                            {!schoolNames.includes(school)
                              ? " · ya no está en el catálogo"
                              : ""}
                          </label>
                        ),
                      )}
                      {!schoolNames.length && (
                        <p>
                          Las escuelas aparecen al registrar programas en
                          Académico. Actualiza la lista cuando hayas creado una
                          escuela.
                        </p>
                      )}
                    </fieldset>
                  </details>
                </article>
              ))}
            </div>
            <div className="voice-actions">
              <Button
                variant="secondary"
                disabled={!catalog || draft.profiles.length >= 20}
                onClick={() => {
                  const id = crypto.randomUUID();
                  update("profiles", [
                    ...draft.profiles,
                    {
                      id,
                      name: `Voz ${draft.profiles.length + 1}`,
                      voice_id: "",
                      model_id: "",
                      active: true,
                      agent_ids: [],
                      schools: [],
                    },
                  ]);
                  if (!draft.default_profile_id)
                    update("default_profile_id", id);
                }}
              >
                Añadir perfil de voz
              </Button>
            </div>
            <SelectField
              id="voice-default"
              label="Voz predeterminada"
              value={draft.default_profile_id}
              onChange={(event) =>
                update("default_profile_id", event.target.value)
              }
              options={[
                { value: "", label: "Selecciona un perfil" },
                ...draft.profiles
                  .filter((p) => p.active)
                  .map((p) => ({ value: p.id, label: p.name })),
              ]}
            />
          </section>
          <div className="voice-save">
            <span>
              {changed
                ? "Tienes cambios sin guardar"
                : `Configuración guardada · versión ${initial.revision}`}
            </span>
            <Button
              type="submit"
              disabled={
                !changed ||
                (draft.enabled &&
                  draft.scope === "selected_conversations" &&
                  !draft.conversation_ids.length)
              }
            >
              Guardar configuración de voz
            </Button>
          </div>
          {catalogError && <Notice error>{catalogError}</Notice>}
        </fieldset>
      </form>
      {session.actions.includes("agents.manage") && (
        <VoiceRuleCheck
          assignments={assignments}
          conversations={pilotConversations}
        />
      )}
      <section className="panel voice-preview">
        <div>
          <h3>Escucha antes de activar</h3>
          <p>
            La muestra usa ElevenLabs y consume caracteres. No se envía a ningún
            contacto. Guarda los perfiles antes de generar.
          </p>
        </div>
        <SelectField
          id="voice-preview-profile"
          label="Perfil para la muestra"
          disabled={task.busy || previewBusy}
          value={previewProfile}
          onChange={(event) => {
            setPreviewProfile(event.target.value);
            setPreview(null);
          }}
          options={[
            { value: "", label: "Selecciona un perfil guardado" },
            ...saved.profiles
              .filter((p) => p.active)
              .map((p) => ({ value: p.id, label: p.name })),
          ]}
        />
        <TextArea
          id="voice-sample"
          label="Texto de muestra"
          disabled={task.busy || previewBusy}
          maxLength={400}
          value={sample}
          onChange={(event) => {
            setSample(event.target.value);
            setPreview(null);
          }}
        />
        <div className="voice-actions">
          <small>{sample.length}/400 caracteres</small>
          <Button
            disabled={
              !writable ||
              task.busy ||
              previewBusy ||
              !previewProfile ||
              !sample.trim() ||
              changed
            }
            onClick={() => {
              setPreviewBusy(true);
              void task
                .run(async () => {
                  const body = { profile_id: previewProfile, text: sample };
                  const result = await call<Preview>("voice/previews", "POST", {
                    ...body,
                    operation_id: previewIntent.get(body),
                  });
                  setPreview(result);
                  await usage.reload();
                }, "Muestra consultada. Si ya existía, no se generó ni cobró otra vez.")
                .finally(() => setPreviewBusy(false));
            }}
          >
            {previewBusy ? "Generando muestra…" : "Generar muestra"}
          </Button>
        </div>
        {preview?.audio_url && (
          <div className="voice-player">
            <PreviewPlayer url={preview.audio_url} />
            <span>
              {Math.round(preview.duration)} segundos · {preview.characters}{" "}
              caracteres
            </span>
          </div>
        )}
        {preview?.remix_available && preview.id && (
          <AmbiencePreview
            key={`${preview.id}-${previewProfile}`}
            operation={preview.id}
            initial={
              saved.profiles.find((p) => p.id === previewProfile)?.ambience
            }
            disabled={!writable || task.busy || previewBusy}
            apply={(value) => profile(previewProfile, { ambience: value })}
          />
        )}
        {preview && !preview.audio_url && (
          <Notice error>
            Esta generación quedó {preview.state}. No se reintenta
            automáticamente para evitar otro consumo. Revisa el historial.
          </Notice>
        )}
        <div className="voice-section-heading">
          <div>
            <h4>Probar saludos</h4>
            <p>
              Compara el mismo texto en cuatro entonaciones con la voz guardada.
              Cada muestra consume caracteres; no se envían mensajes ni cambia
              tu configuración. Empieza el texto con un saludo para escuchar la
              diferencia.
            </p>
          </div>
          <Button
            variant="secondary"
            disabled={
              !writable ||
              task.busy ||
              previewBusy ||
              changed ||
              !previewProfile ||
              !sample.trim() ||
              !/^(eleven_v3|eleven_v4)/.test(
                saved.profiles.find((p) => p.id === previewProfile)?.model_id ??
                  "",
              )
            }
            onClick={() => {
              setPreviewBusy(true);
              setComparisons([]);
              void task
                .run(async () => {
                  for (const tone of greetingTones) {
                    if (!previewMounted.current) break;
                    const body = {
                      profile_id: previewProfile,
                      text: sample,
                      greeting_tone: tone.value,
                    };
                    const key = JSON.stringify(body);
                    let id = comparisonIntents.current.get(key);
                    if (!id) {
                      id = crypto.randomUUID();
                      comparisonIntents.current.set(key, id);
                    }
                    const result = await call<Preview>(
                      "voice/previews",
                      "POST",
                      { ...body, operation_id: id },
                    );
                    if (previewMounted.current)
                      setComparisons((current) => [
                        ...current,
                        { tone: tone.label, result },
                      ]);
                    if (!result.audio_url)
                      throw new ApiError(409, "voice_preview_result_review");
                  }
                  if (previewMounted.current) await usage.reload();
                }, "Comparación de saludos lista. Escucha cada opción y elige la entonación del perfil.")
                .finally(() => {
                  if (previewMounted.current) setPreviewBusy(false);
                });
            }}
          >
            {previewBusy ? "Generando muestras…" : "Generar cuatro saludos"}
          </Button>
        </div>
        {comparisons.length > 0 && (
          <div className="voice-profiles">
            {comparisons.map((c) => (
              <article className="voice-profile" key={c.tone}>
                <h4>{c.tone}</h4>
                {c.result.audio_url ? (
                  <>
                    <PreviewPlayer url={c.result.audio_url} />
                    <small>
                      {Math.round(c.result.duration)} segundos ·{" "}
                      {c.result.characters} caracteres
                    </small>
                  </>
                ) : (
                  <Notice error>
                    Resultado pendiente de revisión. No generamos otra muestra
                    automáticamente.
                  </Notice>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
      <section className="panel">
        <div className="voice-section-heading">
          <div>
            <h3>Actividad y consumo</h3>
            <p>
              Caracteres reservados antes de generar. ElevenLabs determina el
              coste según tu plan y modelo; aquí no se estiman dólares.
            </p>
            <p>
              Reportados por el proveedor en las últimas 24 horas:{" "}
              <strong>
                {usage.value?.reported_characters?.toLocaleString("es-CO") ??
                  "Sin recibos disponibles"}
              </strong>
              {!!usage.value?.reported_attempts &&
                ` · ${usage.value.reported_attempts} recibos`}
              . La ausencia de recibo no significa consumo cero.
            </p>
            <p>
              {usage.value?.uncertain_attempts ?? 0} resultados inciertos ·{" "}
              {usage.value?.running_attempts ?? 0} en curso o pendientes de
              revisión. Conservan su reserva y no se reintentan automáticamente.
            </p>
          </div>
          <Button
            variant="quiet"
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                await usage.reload();
              }, "Actividad actualizada.")
            }
          >
            Actualizar actividad
          </Button>
        </div>
        {pilotAllowed && (
          <SelectField
            id="voice-usage-conversation"
            label="Consultar cupo de conversación"
            value={usageConversation}
            onChange={(event) => setUsageConversation(event.target.value)}
            options={[
              { value: "", label: "Actividad de toda la institución" },
              ...pilotConversations.map((c) => ({
                value: c.id,
                label: c.label,
              })),
            ]}
          />
        )}
        {usageConversation && usage.value && (
          <Notice>
            Este hilo conserva {usage.value.used ?? 0} reservas de audio
            automático. Cupo vigente: {draft.max_audios_per_conversation};
            quedan{" "}
            {Math.max(
              0,
              draft.max_audios_per_conversation - (usage.value.used ?? 0),
            )}
            . Voz fijada:{" "}
            {usage.value.pinned?.name ?? "Se decidirá en el primer audio"}. El
            historial de abajo corresponde a toda la institución.
          </Notice>
        )}
        {catalogAllowed && (
          <Button
            type="button"
            variant="secondary"
            disabled={task.busy}
            onClick={() =>
              void task.run(async () => {
                setBalance(await call("voice/balance"));
              }, "Uso de la cuenta consultado.")
            }
          >
            Consultar uso de la cuenta ElevenLabs
          </Button>
        )}
        {balance && (
          <Notice>
            Cuenta ElevenLabs · {balance.tier}:{" "}
            {balance.used.toLocaleString("es-CO")} de{" "}
            {balance.limit.toLocaleString("es-CO")} unidades del plan
            utilizadas; {balance.remaining.toLocaleString("es-CO")} disponibles.
            <p>
              Consulta de toda la cuenta, incluidos otros proyectos; no sólo
              RinovaPlus. Consultado:{" "}
              {new Date(balance.checked_at).toLocaleString("es-CO")}.
              {balance.reset_at
                ? ` Renovación informada: ${new Date(balance.reset_at * 1000).toLocaleString("es-CO")}.`
                : ""}{" "}
              No modifica tu plan ni autoriza sobreconsumo.
            </p>
          </Notice>
        )}
        {usage.error && <Notice error>{usage.error}</Notice>}
        {!usage.value?.history.length ? (
          <p className="voice-note">
            Las muestras y respuestas de voz aparecerán aquí, con su resultado y
            consumo.
          </p>
        ) : (
          <div className="voice-history" role="list">
            {usage.value.history.map((v) => (
              <article role="listitem" key={v.id}>
                <div>
                  <strong>{v.profile}</strong>
                  <small>{new Date(v.at).toLocaleString("es-CO")}</small>
                  {v.audio_url && (
                    <small>
                      Saludo:{" "}
                      {greetingTones.find(
                        (tone) => tone.value === v.greeting_tone,
                      )?.label ?? "Natural"}
                    </small>
                  )}
                </div>
                <span>{v.characters} caracteres</span>
                <small>
                  {v.reported_characters == null
                    ? "Sin conteo confirmado por ElevenLabs"
                    : `${v.reported_characters} reportados por ElevenLabs`}
                  {v.duration != null
                    ? ` · ${Math.round(v.duration)} segundos`
                    : ""}
                </small>
                <Badge>
                  {(
                    {
                      confirmed: "Audio generado",
                      running: "En curso o pendiente de revisión",
                      abandoned: "Cancelado",
                      failed: "No generado",
                      uncertain: "Resultado por revisar",
                    } as Record<string, string>
                  )[v.state] ?? v.state}
                </Badge>
                {v.code && <small>{voiceReason(v.code)}</small>}
                {v.audio_url && (
                  <Button
                    variant="secondary"
                    type="button"
                    onClick={() =>
                      setHistoryPreview(historyPreview === v.id ? "" : v.id)
                    }
                  >
                    {historyPreview === v.id
                      ? "Ocultar muestra"
                      : "Escuchar muestra"}
                  </Button>
                )}
                {v.audio_url && historyPreview === v.id && (
                  <PreviewPlayer url={v.audio_url} />
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function PreviewPlayer({ url }: { url: string }) {
  const report = useContext(ErrorFeedbackContext);
  const [loaded, setLoaded] = useState({ url: "", source: "" });
  const [failed, setFailed] = useState({ url: "", message: "" });
  const source = loaded.url === url ? loaded.source : "";
  const error = failed.url === url ? failed.message : "";
  useEffect(() => {
    const abort = new AbortController();
    const trigger = document.activeElement;
    let objectUrl = "";
    void fetch(url, {
      credentials: "same-origin",
      cache: "no-store",
      headers: { "X-CRM-Local": "1" },
      signal: abort.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const result = (await response.json().catch(() => ({}))) as {
            detail?: string;
          };
          throw new ApiError(
            response.status,
            typeof result.detail === "string"
              ? result.detail
              : "voice_preview_unavailable",
          );
        }
        const blob = await response.blob();
        if (!abort.signal.aborted) {
          objectUrl = URL.createObjectURL(blob);
          setLoaded({ url, source: objectUrl });
        }
      })
      .catch((failure) => {
        if (!abort.signal.aborted) {
          setFailed({ url, message: (failure as Error).message });
          report?.(
            {
              message: (failure as Error).message,
              code: failure instanceof ApiError ? failure.detail : undefined,
              status: failure instanceof ApiError ? failure.status : undefined,
            },
            trigger,
          );
        }
      });
    return () => {
      abort.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [url, report]);
  return error ? (
    <Notice error>{error}</Notice>
  ) : source ? (
    <div className="voice-preview-player">
      <audio
        controls
        preload="metadata"
        src={source}
        aria-label="Muestra de voz generada"
      />
      <a href={source} download="nota-de-voz.ogg">
        Descargar audio
      </a>
    </div>
  ) : (
    <span role="status">Cargando muestra privada…</span>
  );
}

function AmbiencePreview({
  operation,
  initial,
  disabled,
  apply,
}: {
  operation: string;
  initial?: Ambience;
  disabled: boolean;
  apply: (value: Ambience) => void;
}) {
  const [mix, setMix] = useState<Ambience>({ ...ambienceDefaults, ...initial });
  const [rendered, setRendered] = useState("");
  const [sequence, setSequence] = useState(0);
  const signature = JSON.stringify(mix);
  const [heard, setHeard] = useState("");
  return (
    <div className="voice-mix-preview">
      <h4>Mezcla de la muestra · sin nueva generación</h4>
      <VoiceAmbience
        id="preview-ambience"
        value={mix}
        disabled={disabled}
        onChange={setMix}
      />
      <div className="voice-actions">
        <Button
          disabled={disabled}
          onClick={() => {
            const params = new URLSearchParams(
              Object.entries(mix).map(([key, value]) => [key, String(value)]),
            );
            setRendered(
              `/api/institution/voice/previews/${encodeURIComponent(operation)}/mix?${params}`,
            );
            setHeard(signature);
            setSequence((n) => n + 1);
          }}
        >
          Escuchar mezcla
        </Button>
        <Button
          variant="secondary"
          disabled={disabled}
          onClick={() => apply(mix)}
        >
          Usar esta mezcla en el perfil
        </Button>
      </div>
      {rendered && heard !== signature && (
        <p role="status">
          Ajustes modificados. Pulsa Escuchar mezcla para actualizar la muestra.
        </p>
      )}
      {rendered && <PreviewPlayer key={sequence} url={rendered} />}
      <p>
        Escuchar no cambia la configuración. Para aplicarla a los siguientes
        audios, usa la mezcla y guarda la configuración de voz.
      </p>
    </div>
  );
}

function stabilityFor(profile: VoiceProfile) {
  const preset = (
    {
      conversational: 0.4,
      calm: 0.65,
      expressive: 0.3,
      neutral: 0.7,
    } as Record<string, number>
  )[profile.delivery ?? "conversational"];
  const value = profile.stability ?? preset;
  return profile.model_id.startsWith("eleven_v3")
    ? Math.round(value * 2) / 2
    : value;
}

function VoiceRuleCheck({
  assignments,
  conversations,
}: {
  assignments: Catalog | null;
  conversations: { id: string; label: string }[];
}) {
  const { call } = useInstitution();
  const task = useTask();
  const [text, setText] = useState(
    "Hola, quisiera conocer los programas de CBN.",
  );
  const [incoming, setIncoming] = useState(true),
    [conversation, setConversation] = useState(""),
    [agent, setAgent] = useState(""),
    [program, setProgram] = useState("");
  type Result = {
    eligible: boolean;
    reason: string | null;
    profile: string | null;
    estimated_seconds: number;
    used: number;
    cap: number;
    conversation_checked: boolean;
    pinned: boolean;
    network_called: boolean;
    persisted: boolean;
  };
  const [result, setResult] = useState<{ key: string; value: Result } | null>(
    null,
  );
  const body = {
    text,
    incoming_voice: incoming,
    ...(conversation
      ? { conversation_id: conversation }
      : {
          ...(agent ? { agent_id: agent } : {}),
          ...(program ? { program_id: Number(program) } : {}),
        }),
  };
  const signature = JSON.stringify(body);
  const visible = result?.key === signature ? result.value : null;
  return (
    <section className="panel" aria-labelledby="voice-check-heading">
      <h3 id="voice-check-heading">Comprueba la voz y los límites</h3>
      <p>
        Prueba la selección y las reglas locales sin generar audio, enviar
        mensajes ni consumir ElevenLabs. Selecciona un chat para usar su
        control, contexto y reservas reales.
      </p>
      <SelectField
        id="voice-check-conversation"
        label="Conversación para comprobar"
        value={conversation}
        onChange={(e) => setConversation(e.target.value)}
        options={[
          { value: "", label: "Simulación de asignación · sin conversación" },
          ...conversations.map((v) => ({ value: v.id, label: v.label })),
        ]}
      />
      <div className="voice-fields">
        <SelectField
          id="voice-check-agent"
          label="Agente de la simulación"
          disabled={!!conversation}
          value={agent}
          onChange={(e) => setAgent(e.target.value)}
          options={[
            { value: "", label: "Sin elección directa de agente" },
            ...(assignments?.agents ?? [])
              .filter((a) => a.state !== "archived")
              .map((a) => ({ value: a.id, label: a.name })),
          ]}
        />
        <SelectField
          id="voice-check-program"
          label="Programa y escuela de la simulación"
          disabled={!!conversation}
          value={program}
          onChange={(e) => setProgram(e.target.value)}
          options={[
            { value: "", label: "Sin programa confirmado" },
            ...(assignments?.programs?.items ?? []).map((p) => ({
              value: String(p.program_id),
              label: `${p.name} · ${p.school ?? "Sin escuela"}`,
            })),
          ]}
        />
      </div>
      <label className="voice-check">
        <input
          type="checkbox"
          checked={incoming}
          onChange={(e) => setIncoming(e.target.checked)}
        />
        El mensaje del cliente es una nota de voz
      </label>
      <TextArea
        id="voice-check-text"
        label="Respuesta de ejemplo para comprobar"
        value={text}
        maxLength={3000}
        onChange={(e) => setText(e.target.value)}
      />
      <Button
        type="button"
        variant="secondary"
        disabled={task.busy || !text.trim()}
        onClick={() =>
          void task.run(async () => {
            setResult({
              key: signature,
              value: await call<Result>("voice/check", "POST", body),
            });
          }, "")
        }
      >
        Comprobar sin generar audio
      </Button>
      {task.notices}
      {visible && (
        <Notice>
          {visible.eligible
            ? "Las reglas locales permiten audio; el catálogo, la credencial y el proveedor se validan al generar."
            : voiceReason(visible.reason ?? "")}
          <p>
            Voz: {visible.profile ?? "No disponible"}
            {visible.pinned ? " · fijada en el hilo" : ""}. Duración estimada:{" "}
            {visible.estimated_seconds} segundos. Reservas del hilo:{" "}
            {visible.used} de {visible.cap}.
          </p>
          {!visible.conversation_checked && (
            <p>
              Simulación de asignación. No confirma el control ni el alcance de
              un chat real.
            </p>
          )}
        </Notice>
      )}
    </section>
  );
}

export function voiceReason(code: string) {
  return (
    (
      {
        voice_duration_estimated_exceeded:
          "La duración estimada excede el máximo; la respuesta se envía completa por texto, sin generar audio.",
        voice_duration_actual_exceeded:
          "El audio generado duró más de lo permitido y se descartó sin recortarlo. La respuesta continúa por texto.",
        voice_conversation_limit:
          "Se alcanzó el máximo del hilo; continúa por texto.",
        voice_daily_limit: "Se alcanzó el cupo diario; continúa por texto.",
        voice_paused: "Voz pausada; continúa por texto.",
        voice_human_control:
          "La conversación está en Humano o cerrada; la IA no genera ni envía audio.",
        voice_scope_text_only:
          "Este hilo no está incluido en el alcance de voz; continúa por texto.",
        voice_profile_unavailable:
          "La voz del hilo está pausada o ya no está disponible; continúa por texto. Revisa el perfil de voz.",
        voice_text_preferred:
          "El mensaje no cumple el modo de audio elegido; la respuesta continúa por texto.",
        voice_text_too_large:
          "El texto supera el máximo por audio; continúa completo por texto, sin recortes.",
        voice_insufficient_credits:
          "ElevenLabs no tiene saldo suficiente. Revisa el saldo; la conversación continúa por texto.",
        voice_payment_required:
          "ElevenLabs requiere revisar el plan o el pago. La conversación continúa por texto.",
        provider_timeout_or_network:
          "El proveedor no confirmó el resultado. No repetimos la generación para evitar otro cobro.",
        voice_configuration_changed:
          "Cambió la configuración o la autorización; se canceló el uso del audio.",
        gemini_whatsapp_control_or_history_changed:
          "Cambió el control o llegó otro mensaje; el audio no se envió.",
        voice_catalog_required:
          "La voz o el modelo ya no están disponibles. Actualiza el catálogo y el perfil.",
        voice_invalid_key:
          "ElevenLabs rechazó la clave. Reemplázala en APIs y modelos.",
        voice_insufficient_permissions:
          "La clave no permite generar audio o consultar voces. Revisa sus permisos en ElevenLabs.",
      } as Record<string, string>
    )[code] ??
    "La generación requiere revisión. La respuesta puede continuar por texto. Código: " +
      code
  );
}
