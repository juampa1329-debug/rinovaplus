import { useWorkspaceState } from "../shared/workspaceSession";
import type { Client, Thread } from "../shared/demo";
import type { SettingsDraft } from "./Settings";
import { assistantBlockReason, responseExample } from "../shared/assistant";
import { Button, Notice, TextArea } from "../shared/ui";

export function AssistantPreview({
  client,
  thread,
  settings,
  reviewed,
  onUse,
  binding,
}: {
  binding: string;
  client: Client;
  thread: Thread;
  settings: SettingsDraft;
  reviewed: boolean;
  onUse?: (body: string) => void;
}) {
  const [responses, setResponses] = useWorkspaceState("responses");
  const key = `${onUse ? "inbox" : "assistant"}:${client.id}`;
  const current =
    responses[key]?.binding === binding
      ? responses[key]
      : { binding, body: "", reviewed: false, used: false };
  const { body, reviewed: responseReviewed, used } = current;
  function update(patch: Partial<typeof current>) {
    setResponses((items) => ({ ...items, [key]: { ...current, ...patch } }));
  }
  const reason = assistantBlockReason(thread, reviewed);
  return (
    <section
      className="assistant-preview"
      aria-label="Plantilla de respuesta local"
    >
      <h3>Preparar respuesta con plantilla</h3>
      <p className="analysis-disclaimer">
        Plantilla local de demostración · No es un modelo de IA
      </p>
      <p>
        Contexto ficticio: {client.name || client.phone}. Las instrucciones
        guardadas se muestran para revisión; no se ejecutan ni interpretan como
        órdenes.
      </p>
      <details className="scope-note">
        <summary>Configuración utilizada · Solo demo</summary>
        <p>Nombre: {settings.assistantName}</p>
        <p>Estilo: {settings.style}</p>
        <p>
          Instrucciones de referencia (no ejecutadas):{" "}
          {settings.instructions || "Sin notas"}
        </p>
        <p>
          El ejemplo utiliza una plantilla fija según estilo y programa
          ficticio, no genera respuestas a partir de estas instrucciones.
        </p>
      </details>
      {reason && <Notice>{reason}</Notice>}
      <Button
        variant="secondary"
        disabled={!!reason}
        onClick={() => {
          update({
            body: responseExample(client, settings),
            reviewed: false,
            used: false,
          });
        }}
      >
        Generar ejemplo local
      </Button>
      {body && (
        <>
          <TextArea
            id="assistant-response"
            label="Respuesta de ejemplo editable"
            value={body}
            maxLength={1500}
            onChange={(event) => {
              update({
                body: event.target.value,
                reviewed: false,
                used: false,
              });
            }}
            aria-describedby="assistant-response-limit"
          />
          <small id="assistant-response-limit">
            {body.trim().length} / 1500 caracteres · Edición humana; no se
            envía.
          </small>
          <div className="actions">
            <Button
              variant="secondary"
              disabled={
                !!reason ||
                !body.trim() ||
                body.trim().length > 1500 ||
                responseReviewed
              }
              onClick={() => update({ reviewed: true })}
            >
              Marcar respuesta revisada
            </Button>
            {onUse && (
              <Button
                disabled={
                  !!reason ||
                  !responseReviewed ||
                  !body.trim() ||
                  body.trim().length > 1500
                }
                onClick={() => {
                  onUse(body.trim());
                  update({ used: true });
                }}
              >
                Usar en borrador local
              </Button>
            )}
            <Button
              variant="quiet"
              onClick={() => {
                update({ body: "", reviewed: false, used: false });
              }}
            >
              Descartar ejemplo
            </Button>
          </div>
          {responseReviewed && (
            <Notice>
              Respuesta revisada por la persona que opera esta demo. No acredita
              evaluación de un modelo.
            </Notice>
          )}
          {used && (
            <Notice>
              Copiada solo al compositor de este hilo. Revise y añada
              explícitamente; no se envió.
            </Notice>
          )}
        </>
      )}
    </section>
  );
}
