import {
  type AiModel,
  type MediaConfig,
  type VoiceCatalog,
} from "../../../shared/aiSettings";
import { Button, Field, SelectField, TextArea } from "../../../shared/ui";

export function MediaSettingsFields({
  media,
  onChange,
  catalogs,
  geminiModels,
  groqAudioModels = [],
  loadAudioModels,
  outboundEnabled = false,
  loadCatalog,
  section,
}: {
  media: MediaConfig;
  onChange: (media: MediaConfig) => void;
  catalogs: Record<string, VoiceCatalog>;
  geminiModels: AiModel[];
  groqAudioModels?: AiModel[];
  loadAudioModels?: () => Promise<void>;
  outboundEnabled?: boolean;
  loadCatalog: (provider: string) => Promise<void>;
  section: string;
}) {
  const catalog = catalogs[media.voice_provider];
  function update<K extends keyof MediaConfig>(key: K, value: MediaConfig[K]) {
    onChange({ ...media, [key]: value });
  }
  function options(
    items: { id: string; name: string }[],
    selected: string,
    empty: string,
  ) {
    const values = items.map((item) => ({
      value: item.id,
      label: item.name === item.id ? item.name : `${item.name} · ${item.id}`,
    }));
    if (selected && !values.some((item) => item.value === selected))
      values.unshift({
        value: selected,
        label: `${selected} · Catálogo pendiente`,
      });
    return [{ value: "", label: empty }, ...values];
  }
  return (
    <section className="ai-test" aria-label="Voz, audio, visión y búsqueda">
      <h3>
        {section === "APIs" ? "Catálogos de voz" : "Voz para conversaciones"}
      </h3>
      <p className="scope-text">
        Se utiliza en Asistente. WhatsApp aún no está conectado; aquí no se
        envían notas a contactos.
      </p>
      {section === "IA" && (
        <div className="actions">
          {(
            [
              ["voice_enabled", "Voz habilitada"],
              ["prefer_voice", "Preferir nota de voz"],
              [
                "reply_audio_with_voice",
                "Si recibe nota de voz, responder con nota de voz",
              ],
              ["voice_limit_enabled", "Limitar notas de voz por conversación"],
            ] as const
          ).map(([key, label]) => (
            <label className="checkbox-label" key={key}>
              <input
                type="checkbox"
                checked={media[key]}
                onChange={(event) => update(key, event.target.checked)}
              />
              {label}
            </label>
          ))}
        </div>
      )}
      <div className="form-grid">
        <SelectField
          id={`voice-provider-${section}`}
          label="Proveedor de voz"
          value={media.voice_provider}
          options={[
            { value: "elevenlabs", label: "ElevenLabs" },
            { value: "google_tts", label: "Google Cloud TTS" },
            { value: "piper", label: "Piper" },
          ]}
          onChange={(event) =>
            onChange({
              ...media,
              voice_provider: event.target
                .value as MediaConfig["voice_provider"],
              voice_id: "",
              voice_model: "",
            })
          }
        />
        <SelectField
          id={`voice-name-${section}`}
          label="Nombre visible de voz"
          value={media.voice_id}
          options={options(
            catalog?.voices ?? [],
            media.voice_id,
            "Sin voz seleccionada",
          )}
          onChange={(event) => update("voice_id", event.target.value)}
        />
        {media.voice_provider === "elevenlabs" && (
          <SelectField
            id={`voice-model-${section}`}
            label="Modelo de voz"
            value={media.voice_model}
            options={options(
              catalog?.models ?? [],
              media.voice_model,
              "Sin modelo de voz",
            )}
            onChange={(event) => update("voice_model", event.target.value)}
          />
        )}
        <Field
          id={`voice-manual-${section}`}
          label="Voice ID manual opcional"
          value={media.voice_id}
          maxLength={200}
          onChange={(event) => update("voice_id", event.target.value)}
          hint="El ID debe existir en el catálogo de voces cargado. El nombre visible usa el nombre de su cuenta."
        />
        {section === "IA" && (
          <Field
            id="voice-conversation-limit"
            label="Máximo de notas de voz por conversación"
            type="number"
            min={0}
            max={100}
            disabled={!media.voice_limit_enabled}
            value={media.voice_limit}
            onChange={(event) =>
              update("voice_limit", Number(event.target.value))
            }
            hint="Cero impide generar voz. Cada intento consume un cupo, incluso si el proveedor falla; recargar conserva el contador durante 24 horas."
          />
        )}
      </div>
      <Button
        variant="secondary"
        disabled={media.voice_provider !== "piper" && !outboundEnabled}
        onClick={() => void loadCatalog(media.voice_provider)}
      >
        Cargar voces y modelos de{" "}
        {media.voice_provider === "elevenlabs"
          ? "ElevenLabs"
          : media.voice_provider === "google_tts"
            ? "Google Cloud TTS"
            : "Piper"}
      </Button>
      {catalog && (
        <p role="status">
          {catalog.voices.length} voces disponibles · {catalog.models.length}{" "}
          modelos de voz
          {!catalog.ready && " · Motor Piper pendiente de instalación"}
        </p>
      )}
      {(section === "IA" || section === "APIs") && (
        <>
          <TextArea
            id="voice-prompt"
            label="Prompt de voz"
            value={media.voice_prompt}
            maxLength={1000}
            onChange={(event) => update("voice_prompt", event.target.value)}
          />
          <p className="scope-text">
            Orienta el texto oral del asistente. El timbre y acento provienen de
            la voz elegida; ElevenLabs y Google TTS conservan su configuración
            de plataforma. Con voz habilitada, sin preferencia ni regla de
          audio, la IA decide si aporta valor.
          </p>
          <div className="form-grid">
            <SelectField
              id="audio-analysis-provider"
              label="Proveedor para transcribir audios"
              value={media.audio_provider || "gemini"}
              options={[
                { value: "gemini", label: "Google / Gemini" },
                { value: "groq", label: "Groq · transcripción Whisper" },
              ]}
              onChange={(event) =>
                onChange({
                  ...media,
                  audio_provider: event.target
                    .value as MediaConfig["audio_provider"],
                  audio_model: "",
                })
              }
            />
            <SelectField
              id="audio-analysis-model"
              label={
                media.audio_provider === "groq"
                  ? "Transcripción de audios · Groq"
                  : "Análisis de audios · Google / Gemini"
              }
              value={media.audio_model}
              options={options(
                media.audio_provider === "groq"
                  ? groqAudioModels
                  : geminiModels,
                media.audio_model,
                "Sin modelo de análisis",
              )}
              onChange={(event) => update("audio_model", event.target.value)}
            />
            <SelectField
              id="vision-analysis-model"
              label="Visión · Google / Gemini"
              value={media.vision_model}
              options={options(
                geminiModels,
                media.vision_model,
                "Sin modelo de visión",
              )}
              onChange={(event) => update("vision_model", event.target.value)}
            />
            <SelectField
              id="image-search-provider"
              label="Búsqueda web / imagen"
              value={media.search_provider}
              options={[
                { value: "tavily", label: "Tavily Search" },
                { value: "brave", label: "Brave Search API" },
                { value: "serpapi", label: "SerpAPI" },
              ]}
              onChange={(event) =>
                update(
                  "search_provider",
                  event.target.value as MediaConfig["search_provider"],
                )
              }
            />
          </div>
          {media.audio_provider === "groq" && loadAudioModels && (
            <Button
              variant="secondary"
              disabled={!outboundEnabled}
              onClick={() => void loadAudioModels()}
            >
              Cargar modelos de transcripción Groq
            </Button>
          )}
          <p className="scope-text">
            Cargue el catálogo Gemini en APIs para seleccionar análisis y
            visión. La búsqueda se solicita explícitamente en Asistente y
            devuelve fuentes externas.
          </p>
        </>
      )}
    </section>
  );
}
