import { useEffect, useState } from "react";
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
import { ApiError, useInstitution, useIntent, useTask, type Setting } from "./api";
import { ResourceState, useResource } from "./Settings";
import { useDraftGuard } from "./drafts";
import "./voice.css";

export type VoiceProfile = {
  id: string;
  name: string;
  voice_id: string;
  model_id: string;
  active: boolean;
  agent_ids: string[];
  schools: string[];
};
export type VoicePolicy = {
  enabled: boolean;
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
  max_audios_per_conversation: 3,
  mode: "voice_notes_or_long",
  long_reply_min_chars: 400,
  max_text_chars: 2000,
  max_audio_seconds: 60,
  daily_character_limit: 20000,
  default_profile_id: "",
  profiles: [],
};
type CatalogItem = { id: string; name: string; language?: string };
type VoiceCatalog = { voices: CatalogItem[]; models: CatalogItem[] };
type Usage = {
  daily_characters: number;
  daily_attempts: number;
  history: {
    id: string;
    state: string;
    code: string | null;
    at: string;
    profile: string;
    characters: number;
  }[];
};
type Preview = {
  state: string;
  code?: string;
  audio_url: string | null;
  duration: number;
  characters: number;
};

export function VoiceWorkspace() {
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
  const [assignments, setAssignments] = useState<Catalog | null>(null);
  const [previewProfile, setPreviewProfile] = useState(
    saved.default_profile_id,
  );
  const [sample, setSample] = useState(
    "Hola, soy el asistente virtual de CBN. Puedo orientarte sobre nuestros programas y ayudarte a resolver tus preguntas. ¿Qué te gustaría conocer?",
  );
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const usage = useResource<Usage>("voice/usage");
  const changed = JSON.stringify(saved) !== JSON.stringify(draft);
  useDraftGuard(changed);
  const writable = session.actions.includes("settings.ai.write");
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
                hint="0 = sólo texto. El cupo pertenece al hilo y no se reinicia al pasar a Humano o reiniciar el servidor."
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
              </div>
              <Button
                variant="secondary"
                disabled={!session.actions.includes("settings.providers.read")}
                onClick={() =>
                  void task.run(
                    async () =>
                      setCatalog(await call<VoiceCatalog>("voice/catalog")),
                    "Catálogo de ElevenLabs actualizado.",
                  )
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
                      profile(p.id, { model_id: event.target.value })
                    }
                    options={[
                      { value: "", label: "Selecciona un modelo" },
                      ...(!catalog && p.model_id
                        ? [{ value: p.model_id, label: p.model_id }]
                        : []),
                      ...modelOptions,
                    ]}
                  />
                  <details>
                    <summary>Asignar agentes y escuelas</summary>
                    <p>
                      Un agente tiene prioridad sobre la escuela del programa
                      asignado en CRM. Preguntar por un programa no cambia la
                      asignación.
                    </p>
                    {assignments?.agents.map((agent) => (
                      <label className="voice-check" key={agent.id}>
                        <input
                          type="checkbox"
                          checked={p.agent_ids.includes(agent.id)}
                          onChange={(event) =>
                            profile(p.id, {
                              agent_ids: event.target.checked
                                ? [...p.agent_ids, agent.id]
                                : p.agent_ids.filter((id) => id !== agent.id),
                            })
                          }
                        />
                        {agent.name}
                      </label>
                    ))}
                    <Field
                      id={`voice-schools-${p.id}`}
                      label="Escuelas (separadas por coma)"
                      defaultValue={p.schools.join(", ")}
                      onBlur={(event) =>
                        profile(p.id, {
                          schools: event.target.value
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean),
                        })
                      }
                      hint="Usa el nombre de escuela guardado en Académico. Una escuela o agente sólo puede tener un perfil activo."
                    />
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
            <Button type="submit" disabled={!changed}>
              Guardar configuración de voz
            </Button>
          </div>
        </fieldset>
      </form>
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
        {preview && !preview.audio_url && (
          <Notice error>
            Esta generación quedó {preview.state}. No se reintenta
            automáticamente para evitar otro consumo. Revisa el historial.
          </Notice>
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
                </div>
                <span>{v.characters} caracteres</span>
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
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function PreviewPlayer({ url }: { url: string }) {
  const [source, setSource] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    let objectUrl = "";
    void fetch(url, { credentials: "same-origin", cache: "no-store", headers: { "X-CRM-Local": "1" }, signal: abort.signal })
      .then(async response => {
        if (!response.ok) throw new ApiError(response.status, "voice_preview_unavailable");
        const blob = await response.blob();
        if (!abort.signal.aborted) { objectUrl = URL.createObjectURL(blob); setSource(objectUrl); }
      }).catch(failure => { if (!abort.signal.aborted) setError((failure as Error).message); });
    return () => { abort.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [url]);
  return error ? <Notice error>{error}</Notice> : source ? <audio controls preload="metadata" src={source} aria-label="Muestra de voz generada" /> : <span role="status">Cargando muestra privada…</span>;
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
