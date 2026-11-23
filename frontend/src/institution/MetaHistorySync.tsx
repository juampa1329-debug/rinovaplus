import { useState } from "react";
import { Button, Notice, SelectField } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import { useResource, ResourceState } from "./Settings";

export function MetaHistorySync({ done }: { done: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        variant="quiet"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        Traer historial de Meta
      </Button>
      {open && <HistoryForm done={done} />}
    </>
  );
}

function HistoryForm({ done }: { done: () => void }) {
  const data = useResource<{
    items: { id: string; name: string; channel: string }[];
  }>("workspace/inbox/meta-history-accounts");
  const [account, setAccount] = useState("");
  const [after, setAfter] = useState("");
  const [summary, setSummary] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  return (
    <section
      aria-label="Sincronizar historial de Meta"
      className="comments-original"
    >
      <h3>Conversaciones iniciadas desde Meta</h3>
      <p className="scope-text">
        Trae mensajes salientes y nombres de los últimos siete días, hasta 25
        hilos por consulta. No vuelve a enviarlos, no activa la IA sobre
        mensajes antiguos y no abre la ventana de 24 horas.
      </p>
      {!data.value && <ResourceState error={data.error} />}
      <SelectField
        id="meta-history-account"
        label="Cuenta de Meta"
        value={account}
        options={[
          { value: "", label: "Selecciona una cuenta" },
          ...(data.value?.items ?? []).map((item) => ({
            value: item.id,
            label: item.name,
          })),
        ]}
        onChange={(event) => {
          setAccount(event.target.value);
          setAfter("");
          setHasMore(false);
          setSummary("");
        }}
      />
      {task.notices}
      {summary && <Notice>{summary}</Notice>}
      <Button
        variant="secondary"
        disabled={
          !account || task.busy || !session.actions.includes("inbox.write")
        }
        onClick={() =>
          void task.run(async () => {
            const body = { after };
            const result = await call<{
              imported: number;
              skipped: number;
              has_more: boolean;
              after: string;
            }>(`workspace/inbox/meta-history/${account}`, "POST", {
              ...body,
              operation_id: intent.get({ account, ...body }),
            });
            intent.clear();
            setAfter(result.after);
            setHasMore(result.has_more);
            setSummary(
              `${result.imported} mensajes incorporados. ${result.skipped} elementos sin información suficiente. No se envió ningún mensaje.${result.has_more ? " Hay más hilos para consultar." : " Consulta terminada."}`,
            );
            done();
          })
        }
      >
        {task.busy
          ? "Consultando Meta…"
          : hasMore
            ? "Traer otros hilos"
            : "Sincronizar mensajes salientes"}
      </Button>
    </section>
  );
}
