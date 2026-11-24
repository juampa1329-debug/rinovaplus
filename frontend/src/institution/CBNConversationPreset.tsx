import { useState } from "react";
import { Button } from "../shared/ui";
import { useInstitution, useTask, type Document } from "./api";
import { OperationDialog } from "./ErrorFeedback";

type Profile = { document: Document; reviewed_at: string; sources: string[] };

export function CBNConversationPreset({
  disabled,
  apply,
}: {
  disabled: boolean;
  apply: (value: Document) => void;
}) {
  const { call } = useInstitution();
  const task = useTask();
  const [profile, setProfile] = useState<Profile | null>(null);
  return (
    <section className="panel">
      <h3>Atención CBN · tono y ritmo de conversación</h3>
      <p>
        Prepara el prompt institucional revisado, ideas breves completas, emojis
        discretos y una cadencia de lectura. Puedes ajustar cada valor antes de
        guardar.
      </p>
      <p>
        La propuesta usa 60 segundos de espera tras el último mensaje, 1,5
        segundos de preparación y tres segundos entre partes; unos 350
        caracteres por parte como referencia, conservando frases y condiciones
        completas. El indicador depende de Meta y en WhatsApp marca como
        procesado el mensaje entrante.
      </p>
      <Button
        variant="secondary"
        disabled={disabled || task.busy}
        onClick={() =>
          void task.run(
            async () =>
              setProfile(await call<Profile>("settings/ai/cbn-style")),
            "Propuesta lista para revisión; todavía no se ha guardado.",
          )
        }
      >
        Preparar prompt y cadencia CBN
      </Button>
      {task.notices}
      {profile && (
        <OperationDialog
          guidance={{
            title: "Preparar el estilo institucional",
            detail:
              "Se reemplazará el prompt general de tu borrador y se ajustarán las opciones de brevedad, partes, espera e indicador. Los modelos, voces, credenciales, límites de consumo y reglas de comentarios se conservan.",
            nextStep:
              "Revisa los campos y pulsa Guardar ajustes para publicarlos. El nombre de atención se edita por agente; no representa la identidad de un empleado.",
          }}
          dismiss={() => setProfile(null)}
          dismissLabel="Conservar borrador"
          confirm={{
            label: "Usar en el borrador",
            run: () => apply(profile.document),
          }}
        />
      )}
    </section>
  );
}
