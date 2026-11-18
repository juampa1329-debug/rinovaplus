import { useEffect, useRef } from "react";
import { Icon } from "../shared/Icon";
import { Button } from "../shared/ui";
import { useInstitution, useIntent, useTask } from "./api";
import { ChannelLabel } from "./InboxPresentation";
import { useResource } from "./Settings";

type NewComments = {
  total: number;
  read_through: string;
  items: {
    id: string;
    author: string;
    body: string;
    channel: string;
    received_at: string;
  }[];
};

export function CommentNotifications() {
  const panel = useRef<HTMLDetailsElement>(null);
  const trigger = useRef<HTMLElement>(null);
  const { call, session } = useInstitution();
  const task = useTask();
  const intent = useIntent();
  const { value, error, reload } = useResource<NewComments>(
    "comments/notifications",
  );
  const refresh = () => void reload().catch(() => {});
  useEffect(() => {
    let timer: number | undefined;
    let disposed = false;
    async function poll() {
      try {
        if (!document.hidden) await reload();
      } catch {
        // The resource keeps the last successful count and exposes its error.
      } finally {
        if (!disposed) timer = window.setTimeout(() => void poll(), 15000);
      }
    }
    timer = window.setTimeout(() => void poll(), 15000);
    return () => {
      disposed = true;
      window.clearTimeout(timer);
    };
  }, [reload]);

  return (
    <details
      ref={panel}
      className="comment-notifications"
      onBlur={(event) => {
        if (
          event.relatedTarget instanceof Node &&
          !event.currentTarget.contains(event.relatedTarget)
        )
          event.currentTarget.open = false;
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && event.currentTarget.open) {
          event.currentTarget.open = false;
          trigger.current?.focus();
        }
      }}
      onToggle={(event) => {
        if (event.currentTarget.open) refresh();
      }}
    >
      <summary
        ref={trigger}
        className="button quiet"
        aria-label={`Notificaciones de comentarios${value ? `, ${value.total} nuevos` : ""}`}
      >
        <Icon name="bell" />
        {!!value?.total && (
          <span aria-hidden="true" className="comment-notification-count">
            {value.total > 99 ? "99+" : value.total}
          </span>
        )}
      </summary>
      <section
        className="comment-notification-panel"
        aria-label="Comentarios nuevos"
      >
        <header>
          <h2>Comentarios nuevos</h2>
          {value && <span>{value.total}</span>}
        </header>
        <Button
          variant="quiet"
          disabled={
            !value?.total ||
            !value.read_through ||
            task.busy ||
            !session.actions.includes("inbox.write")
          }
          onClick={() =>
            void task.run(async () => {
              if (!value) return;
              const body = { read_through: value.read_through };
              await call("comments/notifications/read", "POST", {
                ...body,
                operation_id: intent.get(body),
              });
              await reload();
            })
          }
        >
          Marcar todas como leídas
        </Button>
        {task.notices}
        {error && (
          <p role="status">No se pudieron actualizar los comentarios.</p>
        )}
        {!value && !error && <p role="status">Cargando comentarios…</p>}
        {value?.total === 0 && <p>Estás al día con los comentarios.</p>}
        {!!value?.items.length && (
          <ul>
            {value.items
              .slice(0, 8)
              .map(({ id, author, channel, body, received_at }) => (
                <li key={id}>
                  <a
                    href={`#/comments/${encodeURIComponent(id)}`}
                    onClick={() => {
                      if (panel.current) panel.current.open = false;
                    }}
                  >
                    <span>
                      <strong>{author || "Autor sin identificar"}</strong>
                      <ChannelLabel channel={channel} />
                    </span>
                    <span className="comment-notification-preview">{body}</span>
                    <time dateTime={received_at}>
                      {new Date(received_at).toLocaleString("es-CO", {
                        month: "short",
                        day: "numeric",
                        hour: "numeric",
                        minute: "2-digit",
                      })}
                    </time>
                  </a>
                </li>
              ))}
          </ul>
        )}
        <a
          href="#/comments"
          onClick={() => {
            if (panel.current) panel.current.open = false;
          }}
        >
          Ver todos los comentarios
        </a>
      </section>
    </details>
  );
}
