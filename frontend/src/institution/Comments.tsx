import { useState } from "react";
import type { ReactNode } from "react";
import { Icon } from "../shared/Icon";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import type { Setting } from "./api";
import { ResourceState, useResource } from "./Settings";
import { allowNavigation, useDraftGuard } from "./drafts";
import { ChannelLabel } from "./InboxPresentation";
import "./comments.css";

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
  control_mode?: "ai" | "human";
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
  const hasFilters = !!(query || channel || state !== "all");
  return (
    <div
      className="institutional-comments"
      data-comment-open={!!comment || undefined}
    >
      <aside
        className="panel comments-directory"
        aria-label="Lista de comentarios"
      >
        <form
          className="comments-filters inbox-list-controls"
          onSubmit={(e) => {
            e.preventDefault();
            change(() => setQuery(q));
          }}
        >
          <div className="inbox-list-heading">
            <h2>Bandeja</h2>
            <Button variant="quiet" onClick={() => void data.reload()}>
              Actualizar
            </Button>
          </div>
          <Field
            id="comment-search"
            label="Buscar comentarios"
            value={q}
            maxLength={200}
            placeholder="Persona o comentario"
            onChange={(e) => setQ(e.target.value)}
          />
          <div className="comments-filter-pair">
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
          </div>
          <Button type="submit" variant="secondary">
            Buscar
          </Button>
        </form>
        {data.value && data.error && <Notice error>{data.error}</Notice>}
        {!data.value ? (
          <ResourceState error={data.error} />
        ) : (
          <>
            <p className="inbox-results-count" role="status">
              {data.value.total}{" "}
              {data.value.total === 1 ? "comentario" : "comentarios"}
            </p>
            {data.value.items.map((row) => (
              <button
                type="button"
                className="inbox-conversation"
                key={row.id}
                aria-pressed={row.id === selected}
                onClick={() => {
                  if (allowNavigation()) setSelected(row.id);
                }}
              >
                <span className="inbox-avatar" aria-hidden="true">
                  <Icon name="inbox" />
                </span>
                <span className="inbox-conversation-body">
                  <span className="inbox-row-heading">
                    <strong>{row.author || "Autor sin identificar"}</strong>
                    <ChannelLabel channel={row.channel} />
                  </span>
                  <span className="inbox-row-preview">{row.body}</span>
                  <small>
                    {row.account} · {labels[row.state] || row.state}
                  </small>
                </span>
              </button>
            ))}
            {!data.value.items.length && (
              <p className="comments-list-empty">
                {hasFilters
                  ? "No hay comentarios para estos filtros."
                  : "Aquí verás los comentarios de tus canales conectados."}
              </p>
            )}
            {(offset > 0 || data.value.has_more) && (
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
            )}
          </>
        )}
      </aside>
      {comment ? (
        <CommentDetail
          key={comment.id}
          comment={comment}
          done={data.reload}
          back={() => {
            if (allowNavigation()) setSelected("");
          }}
        />
      ) : (
        <section
          className="panel comments-center comments-idle"
          aria-label="Publicación"
        >
          <h2>Publicación</h2>
          <div className="comments-post comments-post-idle">
            <Icon name="inbox" />
            <h3>
              {data.value?.total === 0 && !hasFilters
                ? "Aún no hay comentarios"
                : "Selecciona un comentario"}
            </h3>
            <p>Abre un comentario para consultar qué se publicó y responder.</p>
          </div>
        </section>
      )}
      {!comment && <CommentAI />}
    </div>
  );
}
function CommentDetail({
  comment,
  done,
  back,
}: {
  comment: Comment;
  done: () => Promise<unknown>;
  back: () => void;
}) {
  const [reply, setReply] = useState(""),
    [suggestion, setSuggestion] = useState(""),
    [name, setName] = useState(""),
    { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  useDraftGuard(!!reply || !!name);
  const writable = session.actions.includes("inbox.write"),
    active = comment.state !== "deleted",
    human = comment.control_mode === "human";
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
    <>
      <section
        className="panel comments-center"
        aria-label="Publicación y comentario"
      >
        <Button variant="quiet" className="comments-back" onClick={back}>
          Volver a comentarios
        </Button>
        <div className="comments-heading">
          <h2>Publicación</h2>
          <div className="inbox-thread-heading comments-control">
            <ChannelLabel channel={comment.channel} />
            <Button
              variant="quiet"
              className="inbox-control-switch"
              role="switch"
              aria-label="Control humano del comentario"
              aria-checked={human}
              disabled={!writable || !active || task.busy}
              onClick={() => act(human ? "release" : "takeover")}
            >
              <span>IA</span>
              <i aria-hidden="true" />
              <span>Humano</span>
            </Button>
          </div>
        </div>
        {comment.synthetic_demo && (
          <Notice>
            Datos ficticios para explorar el CRM. Este ejemplo no realiza
            llamadas a proveedores.
          </Notice>
        )}
        {task.notices}
        <div className="comments-post">
          <strong>{comment.account}</strong>
          <p>
            {comment.preview?.caption ||
              "Todavía no tenemos el texto de la publicación."}
          </p>
          {safePostUrl(comment.preview?.permalink) && (
            <a
              href={safePostUrl(comment.preview?.permalink)}
              target="_blank"
              rel="noreferrer"
            >
              Abrir publicación original
            </a>
          )}
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
        </div>
        <div className="comments-original">
          <div className="comments-heading">
            <strong>{comment.author || "Autor sin identificar"}</strong>
            <time dateTime={comment.received_at}>
              {new Date(comment.received_at).toLocaleString("es-CO")}
            </time>
          </div>
          <p>{comment.body}</p>
          <small>
            {labels[comment.state] || comment.state}
            {comment.reply_state
              ? " · " + (labels[comment.reply_state] || comment.reply_state)
              : ""}
          </small>
        </div>
        <div className="institution-actions">
          {comment.capabilities.comment_like && (
            <Button
              variant="secondary"
              disabled={!writable || !active || task.busy}
              onClick={() => effect(comment.liked ? "unlike" : "like")}
            >
              {comment.liked ? "Quitar Me gusta" : "Me gusta"}
            </Button>
          )}
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
      <CommentAI>
        <h3>Respuesta sugerida</h3>
        {suggestion && (
          <div className="comments-suggestion">
            <p>{suggestion}</p>
            <Button variant="secondary" onClick={() => setReply(suggestion)}>
              Usar sugerencia
            </Button>
          </div>
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
              if (result.status !== "confirmed" || !result.draft)
                throw new Error(
                  "No se pudo preparar una sugerencia. Revisa la configuración de IA de esta cuenta.",
                );
              setSuggestion(result.draft);
            })
          }
        >
          Sugerir respuesta con IA
        </Button>
      </CommentAI>
    </>
  );
}

function safePostUrl(value?: string) {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password
      ? url.href
      : undefined;
  } catch {
    return undefined;
  }
}

function CommentAI({ children }: { children?: ReactNode }) {
  const { session } = useInstitution();
  return (
    <aside className="panel comments-ai" aria-label="IA para comentarios">
      <h2>IA para comentarios</h2>
      {children}
      {session.actions.includes("settings.ai.read") && <CommentAISettings />}
    </aside>
  );
}

function CommentAISettings() {
  const data = useResource<Setting>("settings/ai");
  return data.value ? (
    <>
      {data.error && <Notice error>{data.error}</Notice>}
      <CommentAIEditor
        key={data.value.revision}
        saved={data.value}
        reload={data.reload}
      />
    </>
  ) : (
    <ResourceState error={data.error} />
  );
}

function CommentAIEditor({
  saved,
  reload,
}: {
  saved: Setting;
  reload: () => Promise<Setting>;
}) {
  const { session, call } = useInstitution();
  const task = useTask(),
    intent = useIntent();
  const savedRules = String(saved.document.comment_prompt ?? ""),
    savedReply = String(saved.document.comment_auto_reply ?? ""),
    savedMode = saved.document.comment_mode === "manual" ? "manual" : "auto";
  const [rules, setRules] = useState(savedRules),
    [reply, setReply] = useState(savedReply),
    [mode, setMode] = useState(savedMode);
  const dirty =
    rules !== savedRules || reply !== savedReply || mode !== savedMode;
  const canWrite = session.actions.includes("settings.ai.write");
  useDraftGuard(dirty);
  return (
    <form
      className="comments-rules"
      onSubmit={(event) => {
        event.preventDefault();
        if (!canWrite || !dirty) return;
        void task.run(async () => {
          const body = {
            revision: saved.revision,
            document: {
              ...saved.document,
              comment_prompt: rules,
              comment_mode: mode,
              comment_auto_reply: reply.trim(),
            },
          };
          await call("settings/ai", "PUT", {
            ...body,
            operation_id: intent.get(body),
          });
          await reload();
        });
      }}
    >
      <TextArea
        id="comments-ai-instructions"
        label="Instrucciones de respuesta"
        value={rules}
        disabled={!canWrite || task.busy}
        maxLength={1600}
        rows={5}
        placeholder="Ej. Responde en español, con un tono cercano. Remite preguntas personales al equipo de admisiones."
        onChange={(event) => setRules(event.target.value)}
      />
      <SelectField
        id="comments-ai-mode"
        label="Modo de respuesta"
        value={mode}
        disabled={!canWrite || task.busy}
        options={[
          { value: "manual", label: "Sugerencias con revisión" },
          { value: "auto", label: "Responder automáticamente" },
        ]}
        onChange={(event) =>
          setMode(event.target.value === "auto" ? "auto" : "manual")
        }
      />
      {mode === "auto" && (
        <>
          <TextArea
            id="comments-auto-reply"
            label="Respuesta pública aprobada"
            value={reply}
            maxLength={400}
            rows={3}
            disabled={!canWrite || task.busy}
            onChange={(event) => setReply(event.target.value)}
            aria-describedby="comments-auto-description"
          />
          <p className="scope-text" id="comments-auto-description">
            {reply.trim()
              ? "Gemini decide si este texto aplica a un comentario nuevo. Los demás quedan para revisión."
              : "Escribe el texto autorizado para que Gemini pueda publicar respuestas automáticas."}
          </p>
        </>
      )}
      {task.notices}
      {canWrite && (
        <Button type="submit" disabled={!dirty || task.busy}>
          Guardar instrucciones
        </Button>
      )}
    </form>
  );
}
