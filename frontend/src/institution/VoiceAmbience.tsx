export type Ambience = {
  enabled: boolean;
  voice_volume: number;
  office_volume: number;
  typing_volume: number;
  ducking: boolean;
};

export const ambienceDefaults: Ambience = {
  enabled: false,
  voice_volume: 1,
  office_volume: 0.12,
  typing_volume: 0.16,
  ducking: true,
};

export function VoiceAmbience({
  id,
  value,
  onChange,
  disabled = false,
}: {
  id: string;
  value?: Ambience;
  onChange: (value: Ambience) => void;
  disabled?: boolean;
}) {
  const current = { ...ambienceDefaults, ...value };
  return (
    <fieldset className="voice-ambience" disabled={disabled}>
      <legend>Ambiente de oficina y tecleo</legend>
      <p>
        Sonidos sintéticos de ventilación y teclado, sin conversaciones de otras
        personas.
      </p>
      <label className="voice-check">
        <input
          type="checkbox"
          checked={current.enabled}
          onChange={(e) => onChange({ ...current, enabled: e.target.checked })}
        />
        Activar ambiente en este perfil
      </label>
      <div className="voice-mixer-tracks">
        {(
          [
            ["voice_volume", "Voz principal", 1.5],
            ["office_volume", "Ambiente de oficina", 1],
            ["typing_volume", "Tecleo", 1],
          ] as const
        ).map(([key, label, max]) => (
          <div className="voice-mixer-track" key={key}>
            <div className="voice-slider-label">
              <label htmlFor={`${id}-${key}`}>{label}</label>
              <output htmlFor={`${id}-${key}`}>
                {Math.round(current[key] * 100)}%
              </output>
            </div>
            <input
              id={`${id}-${key}`}
              type="range"
              min={key === "voice_volume" ? 0.2 : 0}
              max={max}
              step={0.01}
              value={current[key]}
              disabled={!current.enabled}
              aria-valuetext={`${Math.round(current[key] * 100)} por ciento`}
              onChange={(e) =>
                onChange({ ...current, [key]: Number(e.target.value) })
              }
            />
            <small>
              {key === "voice_volume"
                ? "La voz conserva el protagonismo."
                : "0% silencia esta pista."}
            </small>
          </div>
        ))}
      </div>
      <label className="voice-check">
        <input
          type="checkbox"
          checked={current.ducking}
          disabled={!current.enabled}
          onChange={(e) => onChange({ ...current, ducking: e.target.checked })}
        />
        Bajar el fondo automáticamente mientras habla la voz
      </label>
      <small>
        La mezcla se hace en RinovaPlus. Ajustarla sobre una muestra existente
        no vuelve a generar voz ni consume caracteres de ElevenLabs.
      </small>
    </fieldset>
  );
}
