import { useEffect, useState } from "react";
import { send } from "./api";
import { Button, Notice, SelectField } from "../shared/ui";

export type VoiceAssignmentOptions = {
  profiles: { id: string; name: string; active: boolean; schools: string[] }[];
  schools: string[];
};

export function AgentVoiceSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const [options, setOptions] = useState<VoiceAssignmentOptions | null>(null);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    void send<VoiceAssignmentOptions>("voice/options")
      .then((result) => {
        if (active) {
          setOptions(result);
          setError("");
        }
      })
      .catch((failure) => {
        if (active)
          setError(
            failure instanceof Error
              ? failure.message
              : "No se pudieron consultar las voces.",
          );
      });
    return () => {
      active = false;
    };
  }, [refresh]);
  const available = options?.profiles.filter((p) => p.active) ?? [];
  const unavailable = value && !available.some((p) => p.id === value);
  return (
    <section
      className="agents-editor-section"
      aria-labelledby="agent-voice-heading"
    >
      <h4 id="agent-voice-heading">Voz del agente</h4>
      <p>
        Elige un perfil creado con una voz propia o predeterminada de
        ElevenLabs. Podrás cambiarlo después. Esta selección se guarda junto con
        la configuración del agente.
      </p>
      {error && <Notice error>{error} La selección actual se conserva.</Notice>}
      <SelectField
        id="agent-voice-profile"
        label="Perfil de voz para WhatsApp"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        options={[
          { value: "", label: "Automática · escuela o voz predeterminada" },
          ...(unavailable
            ? [
                {
                  value,
                  label:
                    "Perfil guardado no disponible · revisar en Voces y audios",
                },
              ]
            : []),
          ...available.map((p) => ({ value: p.id, label: p.name })),
        ]}
      />
      <p>
        La voz elegida aquí tiene prioridad sobre la escuela. Los chats que ya
        tienen una voz fijada la conservan; los límites y el control Humano
        siempre se respetan.
      </p>
      {!available.length && options && (
        <Notice>
          Crea al menos un perfil en Voces y audios para asignarlo. Las voces
          nuevas aparecerán al actualizar esta lista.
        </Notice>
      )}
      <Button
        type="button"
        variant="quiet"
        onClick={() => setRefresh((v) => v + 1)}
      >
        Actualizar voces disponibles
      </Button>
      <a href="#/settings/voice" target="_blank" rel="noopener noreferrer">
        Administrar voces y escuelas
      </a>
    </section>
  );
}
