import { useState } from "react";
import { Badge, Button, Field, Notice } from "../shared/ui";
import { useResource } from "./Settings";
import { useInstitution, useIntent, useTask } from "./api";

export function ContactPreference({ id }: { id: string }) {
  const data = useResource<{ no_contact: boolean }>(
    `workspace/contact-preference/${encodeURIComponent(id)}`,
  );
  const { session, call } = useInstitution(),
    intent = useIntent(),
    task = useTask();
  const [reason, setReason] = useState(""),
    [confirmed, setConfirmed] = useState(false);
  if (data.error)
    return (
      <Notice error>No se pudo consultar la preferencia de contacto.</Notice>
    );
  if (!data.value) return <p>Consultando preferencia de contacto…</p>;
  return data.value.no_contact ? (
    <Notice>
      <Badge>No contactar</Badge> Esta persona pidió no recibir mensajes. Se
      excluye de campañas y seguimientos. Una nueva autorización debe quedar
      registrada antes de retomarlos.
    </Notice>
  ) : (
    <>
      <p className="scope-text">
        Sin solicitud de no contacto registrada. Cada campaña verifica por
        separado el consentimiento y el modo IA.
      </p>
      {session.actions.includes("crm.write") && (
        <details>
          <summary>Registrar solicitud de No contactar</summary>
          <p>
            Excluye esta persona de campañas y seguimientos, cancela salidas que
            aún no han comenzado y cierra sus conversaciones vinculadas. No
            envía una respuesta.
          </p>
          <Field
            id={`no-contact-reason-${id}`}
            label="Motivo de No contactar"
            maxLength={400}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.preventDefault();
            }}
          />
          <label>
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            Confirmo que esta persona pidió no recibir mensajes.
          </label>
          <Button
            disabled={task.busy || !confirmed || reason.trim().length < 3}
            onClick={() =>
              void task.run(async () => {
                const body = { reason: reason.trim(), confirmed: true };
                await call(
                  `workspace/contact-preference/${encodeURIComponent(id)}`,
                  "POST",
                  { ...body, operationId: intent.get({ id, ...body }) },
                );
                await data.reload();
                intent.clear();
              }, "Solicitud de No contactar registrada.")
            }
          >
            Registrar No contactar
          </Button>
          {task.notices}
        </details>
      )}
    </>
  );
}
