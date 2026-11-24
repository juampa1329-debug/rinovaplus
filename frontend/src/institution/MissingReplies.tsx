import { useRef, useState } from "react";
import { Button, Notice } from "../shared/ui";
import { useInstitution, useTask } from "./api";
import { OperationDialog } from "./ErrorFeedback";
import { useResource, ResourceState } from "./Settings";

type Candidate = {
  id: string;
  conversation_id: string;
  name: string;
  account: string;
  channel: string;
  at: string;
  proof: string;
};

export function MissingReplies({ conversation }: { conversation?: string }) {
  const [opened, setOpened] = useState(false);
  return opened ? (
    <Recovery conversation={conversation} />
  ) : (
    <Button variant="secondary" onClick={() => setOpened(true)}>
      Revisar entradas sin solicitud de IA
    </Button>
  );
}

function Recovery({ conversation }: { conversation?: string }) {
  const data = useResource<{ items: Candidate[] }>(
    `reply-recovery${conversation ? `?conversation_id=${encodeURIComponent(conversation)}` : ""}`,
  );
  const { call, session } = useInstitution();
  const task = useTask();
  const operation = useRef(crypto.randomUUID());
  const [selected, setSelected] = useState<string[]>([]);
  const [review, setReview] = useState(false);
  const chosen = data.value?.items.filter((v) => selected.includes(v.id)) ?? [];
  if (!data.value) return <ResourceState error={data.error} />;
  return (
    <section className="panel" aria-label="Entradas sin solicitud de IA">
      <h3>Consultas que no llegaron a iniciar la IA</h3>
      <p>
        Sólo aparecen las últimas entradas vigentes de chats en IA, recibidas en
        las últimas 24 horas, sin respuesta posterior ni operación de IA. No se
        repiten generaciones fallidas o envíos inciertos.
      </p>
      {data.error && <Notice error>{data.error}</Notice>}
      {task.notices}
      <Button
        variant="quiet"
        disabled={task.busy}
        onClick={() => void data.reload()}
      >
        Actualizar pendientes
      </Button>
      {!data.value.items.length && (
        <p>No hay entradas sin solicitud de IA para este filtro.</p>
      )}
      {!!data.value.items.length && (
        <>
          <Button
            variant="quiet"
            disabled={task.busy}
            onClick={() =>
              setSelected(data.value!.items.slice(0, 25).map((v) => v.id))
            }
          >
            Seleccionar hasta 25
          </Button>
          <ul>
            {data.value.items.map((v) => (
              <li key={v.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={selected.includes(v.id)}
                    disabled={
                      task.busy ||
                      (!selected.includes(v.id) && selected.length >= 25)
                    }
                    onChange={(e) =>
                      setSelected((old) =>
                        e.target.checked
                          ? [...old, v.id]
                          : old.filter((id) => id !== v.id),
                      )
                    }
                  />{" "}
                  {v.name} · {v.account} ·{" "}
                  {new Date(v.at).toLocaleString("es-CO")}
                </label>
              </li>
            ))}
          </ul>
          {session.actions.includes("settings.channels.write") &&
            session.actions.includes("inbox.write") && (
              <Button
                disabled={task.busy || !chosen.length}
                onClick={() => setReview(true)}
              >
                Revisar {chosen.length} respuestas pendientes
              </Button>
            )}
        </>
      )}
      {review && (
        <OperationDialog
          guidance={{
            title: "Preparar las respuestas pendientes",
            detail: `Se preparará una respuesta para ${chosen.length} conversaciones seleccionadas usando el contexto actual, las fuentes y las skills. Se conservan la espera configurada, los presupuestos y el modo Humano. No se reenvían mensajes anteriores.`,
            nextStep: chosen.map((v) => v.name).join(" · "),
          }}
          dismiss={() => setReview(false)}
          confirm={{
            label: "Poner respuestas en preparación",
            run: () =>
              void task.run(async () => {
                const result = await call<{ queued: number }>(
                  "reply-recovery",
                  "POST",
                  {
                    operation_id: operation.current,
                    confirmed: true,
                    inputs: chosen.map((v) => ({ id: v.id, proof: v.proof })),
                  },
                );
                if (result.queued !== chosen.length)
                  throw new Error("No se confirmó el lote completo.");
                operation.current = crypto.randomUUID();
                setReview(false);
                setSelected([]);
                await data.reload();
              }, "Entradas puestas en preparación. Comprueba sus respuestas y recibos en el Inbox."),
          }}
        />
      )}
    </section>
  );
}
