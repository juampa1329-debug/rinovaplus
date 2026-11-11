import { useState } from "react";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import { ResourceState, useResource } from "./Settings";
import { allowNavigation, useDraftGuard } from "./drafts";

type Comment = {
  id: string;
  integration_id: string;
  channel: string;
  account: string;
  external_id: string;
  author: string;
  body: string;
  received_at: string;
  row_version: string;
  state: string;
  contact_id?: string;
  conversation_id?: string;
  reply_state?: string;
  liked?: boolean;
  synthetic_demo?: boolean;
  preview?: { caption?: string; permalink?: string };
  capabilities: { public_comment_reply: boolean; comment_like: boolean };
};
const labels: Record<string, string> = {
  new: "Nuevo",
  read: "Leído",
  archived: "Archivado",
  deleted: "Eliminado",
  queued: "En cola",
  sending: "Enviando",
  accepted: "Aceptado por el proveedor",
  sent: "Enviado",
  delivered: "Entregado",
  uncertain: "Resultado incierto",
  failed: "Fallido",
  cancelled: "Cancelado",
};

export function Comments() {
  const [channel, setChannel] = useState(""),
    [state, setState] = useState("all"),
    [q, setQ] = useState(""),
    [query, setQuery] = useState(""),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState("");
  const data = useResource<{
    items: Comment[];
    total: number;
    has_more: boolean;
  }>(
    "comments?" +
      new URLSearchParams({ channel, state, q: query, offset: String(offset) }),
  );
  const comment = data.value?.items.find((v) => v.id === selected);
  const change = (fn: () => void) => {
    if (allowNavigation()) {
      fn();
      setOffset(0);
      setSelected("");
    }
  };
  return (
    <>
      <form
        className="institution-actions"
        onSubmit={(e) => {
          e.preventDefault();
          change(() => setQuery(q));
        }}
      >
        <Field
          id="comment-search"
          label="Buscar comentarios"
          value={q}
          maxLength={200}
          onChange={(e) => setQ(e.target.value)}
        />
        <SelectField
          id="comment-channel"
          label="Canal"
          value={channel}
          onChange={(e) => change(() => setChannel(e.target.value))}
          options={[
            { value: "", label: "Todos los canales" },
            { value: "facebook", label: "Facebook" },
            { value: "instagram", label: "Instagram" },
            { value: "tiktok", label: "TikTok" },
          ]}
        />
        <SelectField
          id="comment-state"
          label="Estado"
          value={state}
          onChange={(e) => change(() => setState(e.target.value))}
          options={[
            { value: "all", label: "Todos los estados" },
            ...["new", "read", "archived", "deleted"].map((value) => ({
              value,
              label: labels[value],
            })),
          ]}
        />
        <Button type="submit">Buscar</Button>
        <Button variant="secondary" onClick={() => void data.reload()}>
          Actualizar
        </Button>
      </form>
      {data.error && <Notice error>{data.error}</Notice>}
      {!data.value ? (
        <ResourceState error={data.error} />
      ) : (
        <div className="institution-channel-layout">
          <aside className="panel" aria-label="Lista de comentarios">
            <p>{data.value.total} comentarios</p>
            {data.value.items.map((row) => (
              <Button
                variant={row.id === selected ? "primary" : "quiet"}
                key={row.id}
                onClick={() => {
                  if (allowNavigation()) setSelected(row.id);
                }}
              >
                <span>
                  {row.account} · {labels[row.state] || row.state}
                </span>
                <span>{row.body.slice(0, 110)}</span>
              </Button>
            ))}
            {!data.value.items.length && (
              <p>No hay comentarios para estos filtros.</p>
            )}
            <div className="institution-actions">
              <Button
                variant="secondary"
                disabled={!offset}
                onClick={() => {
                  if (allowNavigation()) setOffset(Math.max(0, offset - 25));
                }}
              >
                Anteriores
              </Button>
              <Button
                variant="secondary"
                disabled={!data.value.has_more}
                onClick={() => {
                  if (allowNavigation()) setOffset(offset + 25);
                }}
              >
                Siguientes
              </Button>
            </div>
          </aside>
          {comment ? (
            <CommentDetail
              key={comment.id}
              comment={comment}
              done={data.reload}
            />
          ) : (
            <section className="panel">
              <h3>Selecciona un comentario</h3>
              <p>Consulta su origen, responde o vincúlalo con el CRM.</p>
            </section>
          )}
        </div>
      )}
    </>
  );
}
function CommentDetail({
  comment,
  done,
}: {
  comment: Comment;
  done: () => Promise<unknown>;
}) {
  const [reply, setReply] = useState(""),
    [name, setName] = useState(""),
    { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  useDraftGuard(!!reply || !!name);
  const writable = session.actions.includes("inbox.write"),
    active = comment.state !== "deleted";
  const act = (action: string) =>
    void task.run(async () => {
      const body = {
        row_version: comment.row_version,
        action,
        ...(action === "reply" ? { body: reply } : {}),
        ...(action === "convert" ? { display_name: name } : {}),
      };
      await call(`comments/${comment.id}`, "POST", {
        ...body,
        operation_id: intent.get(body),
      });
      if (action === "reply") setReply("");
      if (action === "convert") setName("");
      await done();
    });
  const effect = (action: string) =>
    void task.run(async () => {
      const result = await call<{ status: string }>(
        `comments/${comment.id}/effects/${action}`,
        "POST",
        {
          row_version: comment.row_version,
          operation_id: intent.get({
            comment: comment.id,
            action,
            row_version: comment.row_version,
          }),
        },
      );
      if (result.status !== "confirmed")
        throw new Error(
          result.status === "uncertain"
            ? "El resultado es incierto. Revisa el proveedor antes de repetir."
            : "El proveedor no confirmó la acción.",
        );
      await done();
    });
  return (
    <section className="panel">
      <h3>
        {comment.account} · {comment.channel}
      </h3>
      {comment.synthetic_demo && (
        <Notice>
          Datos ficticios para explorar el CRM. Este ejemplo no realiza llamadas
          a proveedores.
        </Notice>
      )}
      <p>
        {comment.author || "Autor sin identificar"} ·{" "}
        {new Date(comment.received_at).toLocaleString("es-CO")}
      </p>
      <p>{comment.body}</p>
      <p>
        {labels[comment.state] || comment.state}
        {comment.reply_state
          ? " · " + (labels[comment.reply_state] || comment.reply_state)
          : ""}
      </p>
      {task.notices}
      {comment.preview?.caption && (
        <blockquote>{comment.preview.caption}</blockquote>
      )}
      <div className="institution-actions">
        <Button
          variant="secondary"
          disabled={
            !writable ||
            !active ||
            task.busy ||
            comment.channel === "tiktok" ||
            comment.synthetic_demo
          }
          onClick={() => effect("preview")}
        >
          Actualizar publicación
        </Button>
        {comment.capabilities.comment_like && (
          <Button
            variant="secondary"
            disabled={!writable || !active || task.busy}
            onClick={() => effect(comment.liked ? "unlike" : "like")}
          >
            {comment.liked ? "Quitar Me gusta" : "Me gusta"}
          </Button>
        )}
        <Button
          variant="secondary"
          disabled={!writable || !active || task.busy || comment.synthetic_demo}
          onClick={() =>
            void task.run(async () => {
              const result = await call<{ status: string; draft: string }>(
                `comments/${comment.id}/suggest`,
                "POST",
                {
                  operation_id: intent.get({
                    comment: comment.id,
                    row_version: comment.row_version,
                    action: "suggest",
                  }),
                  row_version: comment.row_version,
                },
              );
              if (result.status !== "confirmed")
                throw new Error(
                  "No se obtuvo un borrador confirmado. Revisa el estado antes de volver a solicitarlo.",
                );
              setReply(result.draft);
            })
          }
        >
          Sugerir respuesta con IA
        </Button>
      </div>
      <div className="institution-actions">
        {["read", "archive", "reopen"].map((action, i) => (
          <Button
            variant="secondary"
            key={action}
            disabled={!writable || !active || task.busy}
            onClick={() => act(action)}
          >
            {["Marcar leído", "Archivar", "Reabrir"][i]}
          </Button>
        ))}
      </div>
      {comment.conversation_id ? (
        <p>
          <a href={`#/inbox/${comment.conversation_id}`}>
            Abrir conversación vinculada
          </a>
        </p>
      ) : (
        <div>
          <Field
            id="comment-lead-name"
            label="Nombre del contacto en CRM"
            maxLength={180}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Button
            disabled={
              !writable ||
              !active ||
              task.busy ||
              !session.actions.includes("crm.write")
            }
            onClick={() => act("convert")}
          >
            Crear contacto en CRM
          </Button>
          <p>Esta vinculación no habilita mensajes privados al autor.</p>
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          act("reply");
        }}
      >
        <TextArea
          id="comment-public-reply"
          label="Respuesta pública"
          value={reply}
          maxLength={4000}
          onChange={(e) => setReply(e.target.value)}
        />
        <Button
          type="submit"
          disabled={
            !writable ||
            !active ||
            task.busy ||
            !reply.trim() ||
            !comment.capabilities.public_comment_reply ||
            ["queued", "sending", "uncertain"].includes(
              comment.reply_state || "",
            )
          }
        >
          Enviar respuesta pública
        </Button>
      </form>
      {comment.channel === "tiktok" && (
        <p>Las reacciones de comentarios no están habilitadas por TikTok.</p>
      )}
    </section>
  );
}
