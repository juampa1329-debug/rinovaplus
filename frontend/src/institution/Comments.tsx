import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Icon } from "../shared/Icon";
import { Button, Field, Notice, SelectField, TextArea } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import type { Setting } from "./api";
import { ResourceState, useResource } from "./Settings";
import { allowNavigation, useDraftGuard } from "./drafts";
import { MetaAutomationHelp } from "./MetaAutomationHelp";
import { ChannelLabel } from "./InboxPresentation";
import { CommentEdit } from "./CommentEdit";
import type { CommentEditInfo } from "./CommentEdit";
import "./comments.css";

type PostPreview = {
  caption?: string;
  permalink?: string;
  media?: { type: "image" | "video"; url: string; poster?: string }[];
};

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
  preview?: PostPreview;
  source?: { status: string; checked_at: string; reason?: string };
  is_self?: boolean;
  edit?: CommentEditInfo | null;
  thread?: {
    id: string;
    post_id: string | null;
    comments: number;
    replies: number;
    unread: number;
    focus_id: string;
    unlinked_reply: boolean;
  };
  replies?: {
    id: string;
    author: string;
    body: string;
    received_at: string;
    state: string;
    edit?: CommentEditInfo;
  }[];
  capabilities: { public_comment_reply: boolean; comment_like: boolean };
};
const labels: Record<string, string> = {
  new: "Nuevo",
  read: "Leído",
  archived: "Archivado",
  deleted: "Eliminado",
  unavailable: "Fuente no disponible",
  queued: "En cola",
  sending: "Enviando",
  accepted: "Aceptado por el proveedor",
  sent: "Enviado",
  delivered: "Entregado",
  uncertain: "Resultado incierto",
  failed: "Fallido",
  cancelled: "Cancelado",
  published: "Publicado en Meta",
};

export function Comments({
  initialComment = "",
}: { initialComment?: string } = {}) {
  const [channel, setChannel] = useState(""),
    [state, setState] = useState("all"),
    [q, setQ] = useState(""),
    [query, setQuery] = useState(""),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState(initialComment);
  const data = useResource<{
    items: Comment[];
    total: number;
    has_more: boolean;
    view?: string;
  }>(
    "comments?" +
      new URLSearchParams({
        channel,
        view: "threads",
        state,
        q: query,
        offset: String(offset),
        ...(initialComment && selected === initialComment
          ? { comment_id: initialComment }
          : {}),
      }),
  );
  const comment =
    data.value?.items.find(
      (v) => (v.thread?.id || v.id) === selected || v.id === selected,
    ) ||
    (initialComment && selected === initialComment
      ? data.value?.items[0]
      : undefined);
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
          {initialComment && selected === initialComment && (
            <a href="#/comments">Ver todos los comentarios</a>
          )}
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
                ...["new", "read", "archived", "deleted", "unavailable"].map(
                  (value) => ({
                    value,
                    label: labels[value],
                  }),
                ),
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
              {data.value.view === "threads"
                ? data.value.total === 1
                  ? "hilo"
                  : "hilos"
                : data.value.total === 1
                  ? "comentario"
                  : "comentarios"}
              {data.value.items.some((v) => v.thread) &&
                " · por persona y publicación"}
            </p>
            {data.value.items.map((row) => (
              <button
                type="button"
                className="inbox-conversation"
                key={row.thread?.id || row.id}
                aria-pressed={row === comment}
                onClick={() => {
                  if (allowNavigation()) setSelected(row.thread?.id || row.id);
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
                  {row.thread && (
                    <small className="comments-group-count">
                      {row.thread.unlinked_reply
                        ? "Respuesta de la cuenta · contexto no recibido"
                        : `${row.thread.comments} ${row.thread.comments === 1 ? "comentario" : "comentarios"} · ${row.thread.replies} ${row.thread.replies === 1 ? "respuesta" : "respuestas"}`}
                      {!!row.thread.unread &&
                        ` · ${row.thread.unread} sin leer`}
                    </small>
                  )}
                  {row.thread?.post_id && (
                    <small
                      className="comments-post-ref"
                      title={`Publicación ${row.thread.post_id}`}
                    >
                      Publicación {row.thread.post_id}
                    </small>
                  )}
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
        <CommentWorkspace
          key={comment.thread?.id || comment.id}
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

function CommentWorkspace(props: {
  comment: Comment;
  done: () => Promise<unknown>;
  back: () => void;
}) {
  return props.comment.thread ? (
    <ThreadedCommentDetail {...props} />
  ) : (
    <CommentDetail {...props} />
  );
}

function ThreadedCommentDetail({
  comment,
  done,
  back,
}: {
  comment: Comment;
  done: () => Promise<unknown>;
  back: () => void;
}) {
  const { session } = useInstitution();
  const [anchor] = useState(comment.thread?.focus_id || comment.id);
  const [targetId, setTargetId] = useState("");
  const [offset, setOffset] = useState(0);
  const thread = useResource<{
    items: Comment[];
    total: number;
    has_more: boolean;
    focus_id: string;
    unlinked_reply: boolean;
  }>(`comments/${anchor}/thread?offset=${offset}`);
  if (!thread.value)
    return (
      <section className="panel comments-center">
        <ResourceState error={thread.error} />
      </section>
    );
  const target =
    thread.value.items.find(
      (v) => v.id === (targetId || thread.value?.focus_id),
    ) || thread.value.items[0];
  if (!target)
    return (
      <section className="panel comments-center">
        <Button variant="quiet" className="comments-back" onClick={back}>
          Volver a comentarios
        </Button>
        <h2>Respuesta de {comment.account}</h2>
        <p>{comment.body}</p>
        <CommentEdit
          identity={comment.id}
          body={comment.body}
          edit={comment.edit}
          done={done}
        />
        <Notice>
          El comentario original aún no llegó desde Meta. Conservamos esta
          respuesta, pero no la vinculamos a otra persona sin evidencia.
        </Notice>
      </section>
    );
  const refresh = async () => {
    await thread.reload();
    await done();
  };
  return (
    <CommentDetail
      key={target.id}
      comment={{ ...target, preview: target.preview || comment.preview }}
      done={refresh}
      back={back}
      focusComposer={!!targetId}
      threadContent={
        <section
          className="comments-person-thread"
          aria-label={`Comentarios de ${target.author} en esta publicación`}
        >
          <header>
            <h3>{target.author} en esta publicación</h3>
            <p>
              {thread.value.total}{" "}
              {thread.value.total === 1 ? "comentario" : "comentarios"} ·
              Respuestas de {comment.account}
            </p>
            {comment.channel === "instagram" && (
              <small>
                Instagram permite responder, pero su API todavía no permite
                editar el texto de una respuesta publicada.
              </small>
            )}
          </header>
          {thread.error && (
            <Notice error>
              {thread.error} Conservamos el hilo que estabas consultando.
            </Notice>
          )}
          {thread.value.items.map((entry) => (
            <article
              key={entry.id}
              className="comments-thread-entry"
              data-reply-target={entry.id === target.id || undefined}
              aria-label={`Comentario de ${entry.author}`}
            >
              <div className="comments-heading">
                <strong>{entry.author}</strong>
                <time dateTime={entry.received_at}>
                  {new Date(entry.received_at).toLocaleString("es-CO")}
                </time>
              </div>
              <p>{entry.body}</p>
              <div className="comments-heading">
                <small>
                  {labels[entry.state] || entry.state}
                  {entry.id === target.id ? " · Comentario seleccionado" : ""}
                </small>
                <Button
                  variant="quiet"
                  aria-label={`Responder al comentario: ${entry.body.slice(0, 80)}`}
                  disabled={
                    !session.actions.includes("inbox.write") ||
                    ["deleted", "unavailable"].includes(entry.state)
                  }
                  onClick={() => {
                    if (entry.id === target.id) {
                      document.getElementById("comment-public-reply")?.focus();
                      return;
                    }
                    if (allowNavigation()) setTargetId(entry.id);
                  }}
                >
                  Responder
                </Button>
              </div>
              {!!entry.replies?.length && (
                <ol
                  className="comments-thread-replies"
                  aria-label={`Respuestas a: ${entry.body.slice(0, 80)}`}
                >
                  {entry.replies.map((response) => (
                    <li key={response.id}>
                      <div className="comments-heading">
                        <strong>
                          {response.author} <small>Cuenta conectada</small>
                        </strong>
                        <time dateTime={response.received_at}>
                          {new Date(response.received_at).toLocaleString(
                            "es-CO",
                          )}
                        </time>
                      </div>
                      <p>{response.body}</p>
                      <small>{labels[response.state] || response.state}</small>
                      <CommentEdit
                        identity={response.id}
                        body={response.body}
                        edit={response.edit}
                        done={refresh}
                      />
                    </li>
                  ))}
                </ol>
              )}
            </article>
          ))}
          {(offset > 0 || thread.value.has_more) && (
            <div className="institution-actions">
              <Button
                variant="secondary"
                disabled={!thread.value.has_more}
                onClick={() => {
                  if (allowNavigation()) setOffset(offset + 25);
                }}
              >
                Comentarios anteriores
              </Button>
              <Button
                variant="secondary"
                disabled={!offset}
                onClick={() => {
                  if (allowNavigation()) setOffset(Math.max(0, offset - 25));
                }}
              >
                Más recientes
              </Button>
            </div>
          )}
        </section>
      }
    />
  );
}

function CommentDetail({
  comment,
  done,
  back,
  threadContent,
  focusComposer = false,
}: {
  comment: Comment;
  done: () => Promise<unknown>;
  back: () => void;
  threadContent?: ReactNode;
  focusComposer?: boolean;
}) {
  const [reply, setReply] = useState(""),
    [suggestion, setSuggestion] = useState(""),
    [name, setName] = useState(""),
    { call, session } = useInstitution(),
    task = useTask(),
    intent = useIntent();
  useDraftGuard(!!reply || !!name);
  useEffect(() => {
    if (focusComposer) document.getElementById("comment-public-reply")?.focus();
  }, [focusComposer, comment.id]);
  const writable = session.actions.includes("inbox.write"),
    active =
      !comment.is_self && !["deleted", "unavailable"].includes(comment.state),
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
        {comment.state === "unavailable" && (
          <Notice>
            Meta no permite consultar este comentario. Puede haberse eliminado o
            haber cambiado su acceso. Conservamos el historial y pausamos las
            respuestas sobre este comentario. Revisa la publicación y los
            permisos de la cuenta; después pulsa «Sincronizar comentario».
          </Notice>
        )}
        {["facebook", "instagram"].includes(comment.channel) && (
          <div className="institution-actions">
            <Button
              variant="secondary"
              disabled={
                !writable ||
                task.busy ||
                comment.state === "deleted" ||
                comment.synthetic_demo
              }
              onClick={() => effect("reconcile")}
            >
              Sincronizar comentario
            </Button>
            {comment.source?.checked_at && (
              <small>
                Última consulta:{" "}
                {new Date(comment.source.checked_at).toLocaleString("es-CO")}
              </small>
            )}
          </div>
        )}
        <CommentPost comment={comment} />
        {threadContent || (
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
        )}
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
          {threadContent && (
            <p className="comments-reply-target">
              Respondiendo a <strong>{comment.author}</strong>:{" "}
              {comment.body.slice(0, 180)}
            </p>
          )}
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

function safePostMediaUrl(value?: string) {
  const safe = safePostUrl(value);
  if (!safe) return undefined;
  const host = new URL(safe).hostname;
  return [
    "fbcdn.net",
    "cdninstagram.com",
    "fbsbx.com",
    "facebook.com",
    "instagram.com",
  ].some((domain) => host === domain || host.endsWith("." + domain))
    ? safe
    : undefined;
}

function CommentPost({ comment }: { comment: Comment }) {
  const { call } = useInstitution();
  const [resource, setResource] = useState<{
      key: string;
      preview?: PostPreview;
      error: string;
    }>({ key: "", error: "" }),
    [revision, setRevision] = useState(0);
  const enabled =
    !comment.synthetic_demo &&
    ["facebook", "instagram"].includes(comment.channel);
  const requestKey = `${comment.id}:${revision}`;
  const loading = enabled && resource.key !== requestKey;
  const error = resource.key === requestKey ? resource.error : "";
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    void call<PostPreview>(`comments/${comment.id}/preview`)
      .then((value) => {
        if (active)
          setResource({
            key: requestKey,
            preview:
              typeof value.caption === "string" || Array.isArray(value.media)
                ? value
                : undefined,
            error: "",
          });
      })
      .catch((failure: unknown) => {
        if (active)
          setResource((previous) => ({
            ...previous,
            key: requestKey,
            error:
              failure instanceof Error
                ? failure.message
                : "No se pudo cargar la publicación.",
          }));
      });
    return () => {
      active = false;
    };
  }, [call, comment.id, enabled, requestKey]);
  const current = resource.preview ?? comment.preview;
  const media = (current?.media ?? []).filter((item) =>
    safePostMediaUrl(item.url),
  );
  return (
    <div
      className="comments-post"
      aria-label="Vista previa de la publicación"
      aria-busy={loading}
    >
      <strong>{comment.account}</strong>
      {media.length > 0 && (
        <div
          className="comments-post-media"
          aria-label="Contenido de la publicación"
        >
          {media.map((item, index) => (
            <PostMedia
              key={`${item.url}:${revision}`}
              item={item}
              index={index}
            />
          ))}
        </div>
      )}
      {current?.caption && <p>{current.caption}</p>}
      {loading && !current && <p role="status">Cargando publicación…</p>}
      {!loading && !current?.caption && media.length === 0 && !error && (
        <p>El proveedor todavía no devuelve contenido de esta publicación.</p>
      )}
      {error && <Notice error>{error}</Notice>}
      {safePostUrl(current?.permalink) && (
        <a
          href={safePostUrl(current?.permalink)}
          target="_blank"
          rel="noreferrer"
        >
          Abrir publicación original
        </a>
      )}
      <Button
        variant="secondary"
        disabled={!enabled || loading}
        onClick={() => setRevision((v) => v + 1)}
      >
        Actualizar publicación
      </Button>
    </div>
  );
}

function PostMedia({
  item,
  index,
}: {
  item: NonNullable<PostPreview["media"]>[number];
  index: number;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <figure>
      {failed ? (
        <figcaption>
          Este archivo no está disponible. Actualiza la publicación para volver
          a consultarlo.
        </figcaption>
      ) : item.type === "video" ? (
        <video
          controls
          playsInline
          preload="metadata"
          src={safePostMediaUrl(item.url)}
          poster={safePostMediaUrl(item.poster)}
          aria-label={`Video ${index + 1} de la publicación`}
          onError={() => setFailed(true)}
        />
      ) : (
        <img
          src={safePostMediaUrl(item.url)}
          alt={`Imagen ${index + 1} de la publicación`}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      )}
    </figure>
  );
}

function CommentAI({ children }: { children?: ReactNode }) {
  const { session } = useInstitution();
  return (
    <aside className="panel comments-ai" aria-label="IA para comentarios">
      <h2>IA para comentarios</h2>
      <MetaAutomationHelp />
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
            label="Ejemplo de bienvenida (opcional)"
            value={reply}
            maxLength={400}
            rows={3}
            disabled={!canWrite || task.busy}
            onChange={(event) => setReply(event.target.value)}
            aria-describedby="comments-auto-description"
          />
          <p className="scope-text" id="comments-auto-description">
            Gemini redacta una respuesta personalizada con estas instrucciones y
            la información vigente de Académico y Conocimiento. Este ejemplo no
            es una respuesta fija. Las consultas que requieren un asesor quedan
            para revisión.
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
