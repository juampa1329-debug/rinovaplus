import { useState } from "react";
import { useInboxDrafts, useInboxView } from "../shared/inboxSession";
import type { SocialComment } from "../shared/comments";
import { commentPlatforms, filterComments } from "../shared/comments";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Notice,
  SelectField,
  TextArea,
} from "../shared/ui";

export function CommentsInbox({
  comments,
  onReply,
  visible,
}: {
  comments: SocialComment[];
  onReply: (id: string, body: string) => void;
  visible: boolean;
}) {
  const [storedSelection, setSelected] = useInboxView("selectedComment");
  const selected = storedSelection || comments[0]?.id || "";
  const [query, setQuery] = useState("");
  const [platform, setPlatform] = useState("Todas");
  const [status, setStatus] = useState("Todos");
  const [drafts, setDrafts] = useInboxDrafts("comments");
  const [feedback, setFeedback] = useState("");
  const matches = filterComments(comments, query, platform, status);
  const comment = matches.find((item) => item.id === selected);
  const draft = comment ? (drafts[comment.id] ?? "") : "";
  return (
    <div hidden={!visible}>
      <div className="comments-grid">
        <section
          className="panel inbox-list"
          aria-label="Bandeja de comentarios"
        >
          <div className="panel-heading">
            <h2>
              Comentarios <span className="count">{matches.length}</span>
            </h2>
            <Badge>Solo local</Badge>
          </div>
          <Field
            id="comment-search"
            label="Buscar comentarios"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setFeedback("");
            }}
            placeholder="Perfil, publicación o comentario"
          />
          <SelectField
            id="comment-platform"
            label="Red social de comentarios"
            options={["Todas", ...commentPlatforms]}
            value={platform}
            onChange={(event) => {
              setPlatform(event.target.value);
              setFeedback("");
            }}
          />
          <SelectField
            id="comment-status"
            label="Estado del comentario local"
            options={["Todos", "Pendiente", "Respondido"]}
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setFeedback("");
            }}
          />
          <Button
            variant="quiet"
            onClick={() => {
              setQuery("");
              setPlatform("Todas");
              setStatus("Todos");
            }}
          >
            Restablecer filtros de comentarios
          </Button>
          <ul className="record-list">
            {matches.map((item) => (
              <li key={item.id}>
                <button
                  className={`record ${selected === item.id ? "selected" : ""}`}
                  aria-pressed={selected === item.id}
                  onClick={() => {
                    setSelected(item.id);
                    setFeedback("");
                  }}
                >
                  <span className="record-copy">
                    <strong>{item.author}</strong>
                    <span>{item.body}</span>
                    <small>
                      {item.platform} · {item.status} local
                    </small>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {!matches.length && (
            <EmptyState title="Sin comentarios coincidentes">
              Cambie la red, el estado o la búsqueda.
            </EmptyState>
          )}
          <p className="panel-footer">
            Facebook, Instagram y TikTok · Sin conectores. WhatsApp no tiene
            esta bandeja de comentarios públicos.
          </p>
        </section>
        <section
          className="panel conversation"
          aria-label="Detalle del comentario"
        >
          {feedback && (
            <div className="comment-feedback">
              <Notice>{feedback}</Notice>
            </div>
          )}
          {comment ? (
            <>
              <div className="conversation-heading">
                <div>
                  <h2>{comment.author}</h2>
                  <p>{comment.platform} · Proveedor no conectado</p>
                </div>
                <Badge>{comment.status} local</Badge>
              </div>
              <div className="post-context">
                <h3>Publicación de contexto</h3>
                <p>{comment.post}</p>
                <small>
                  Texto sintético; no se descarga contenido externo.
                </small>
              </div>
              <div
                className="message-log"
                role="log"
                aria-label="Comentario y respuestas locales"
              >
                <div className="message incoming">
                  <p>{comment.body}</p>
                  <small>Comentario ficticio</small>
                </div>
                {comment.replies.map((reply) => (
                  <div className="message outgoing" key={reply.id}>
                    <p>{reply.body}</p>
                    <small>No publicada · Solo local</small>
                  </div>
                ))}
              </div>
              <div className="composer">
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (!draft.trim() || draft.trim().length > 1500) return;
                    onReply(comment.id, draft);
                    setDrafts((items) => ({ ...items, [comment.id]: "" }));
                    setFeedback(
                      "Respuesta añadida solo localmente. No publicada en ninguna red.",
                    );
                  }}
                >
                  <TextArea
                    id="comment-draft"
                    label="Borrador de respuesta al comentario"
                    value={draft}
                    maxLength={1500}
                    aria-invalid={draft.trim().length > 1500}
                    aria-describedby="comment-draft-limit"
                    onChange={(event) =>
                      setDrafts((items) => ({
                        ...items,
                        [comment.id]: event.target.value,
                      }))
                    }
                  />
                  <p
                    id="comment-draft-limit"
                    className={
                      draft.trim().length > 1500
                        ? "field-error"
                        : "analysis-disclaimer"
                    }
                    aria-live="polite"
                  >
                    {draft.trim().length} / 1500 caracteres · Máximo local, sin
                    espacios al inicio o al final.
                    {draft.trim().length > 1500 &&
                      " Reduzca el texto para añadir la respuesta local."}
                  </p>
                  <div className="composer-footer">
                    <small>
                      Responder cambia el estado demo, no acredita publicación
                      ni entrega.
                    </small>
                    <Button
                      type="submit"
                      disabled={!draft.trim() || draft.trim().length > 1500}
                    >
                      Añadir respuesta local
                    </Button>
                  </div>
                </form>
              </div>
            </>
          ) : (
            <EmptyState title="Seleccione un comentario visible">
              Elija un registro de la bandeja o restablezca los filtros. Sus
              borradores locales se conservan al cambiar de selección o de modo.
            </EmptyState>
          )}
        </section>
      </div>
    </div>
  );
}
