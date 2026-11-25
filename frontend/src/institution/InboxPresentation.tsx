import { useId, useRef } from "react";
import type { ReactNode } from "react";
import type { Client } from "../shared/demo";
import { Button, Field, SelectField } from "../shared/ui";
import { Icon } from "../shared/Icon";
import type { Risk } from "./Workspace";
import { clockTime } from "./VoiceNote";

const channels = {
  local: "Web",
  whatsapp: "WhatsApp",
  facebook: "Facebook",
  messenger: "Messenger",
  instagram: "Instagram",
  tiktok: "TikTok",
};
const temperatures = { cold: "Frío", warm: "Tibio", hot: "Caliente" };
const riskLevels = { low: "Bajo", medium: "Medio", high: "Alto" };
const states = { open: "Abierta", waiting: "En espera", closed: "Cerrada" };
const programJoiners = new Set([
  "a",
  "con",
  "de",
  "del",
  "e",
  "el",
  "en",
  "la",
  "las",
  "los",
  "para",
  "por",
  "y",
]);

export function RiskBadge({ risk, inList = false }: { risk: Risk; inList?: boolean }) {
  const level = risk.status === "known" && risk.fresh ? labelFor(riskLevels, risk.level) : "";
  const label = level || (risk.status === "not_applicable" ? "No aplica" : "Sin evaluación");
  return (
    <span className="inbox-signal" data-risk={level ? risk.level : undefined}>
      {inList ? `Abandono ${label.toLowerCase()}` : label}
      {inList && level && risk.score != null && ` · ${risk.score}/100`}
    </span>
  );
}

export function inboxProgramCode(name: string) {
  const words =
    name
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLowerCase()
      .match(/\p{L}+/gu) ?? [];
  if (words.join(" ") === "desarrollo multimedia y comunicacion grafica")
    return "DMC";
  const initials = words
    .filter((word) => !programJoiners.has(word))
    .map((word) => word[0]);
  return initials.join("").toUpperCase();
}

export type InboxFilters = {
  q: string;
  queue: string;
  stage: string;
  channel: string;
  state: string;
  temperature: string;
  riskLevel: string;
};
export const initialInboxFilters: InboxFilters = {
  q: "",
  queue: "all",
  stage: "",
  channel: "",
  state: "",
  temperature: "",
  riskLevel: "",
};

type Option = { value: string; label: string };
const opts = (labels: Record<string, string>, all: string): Option[] => [
  { value: "", label: all },
  ...Object.entries(labels).map(([value, label]) => ({ value, label })),
];
const labelFor = (
  labels: Record<string, string>,
  value: string | null | undefined,
) => (value && Object.hasOwn(labels, value) ? labels[value] : "");

export function ChannelLabel({ channel }: { channel?: string | null }) {
  const label = labelFor(channels, channel);
  return (
    <span
      className="inbox-channel-label"
      data-channel={label ? channel : undefined}
    >
      <i aria-hidden="true" />
      {label || "Canal sin identificar"}
    </span>
  );
}

export function InboxUnread({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  return (
    <span className="inbox-unread-summary">
      <span>{total} sin leer</span>
      {total > 0 && (
        <span
          className="inbox-unread-channels"
          role="group"
          aria-label="Sin leer por canal"
        >
          {Object.entries(channels)
            .filter(([channel]) => counts[channel] > 0)
            .map(([channel, label]) => (
              <span
                className="inbox-channel-label"
                data-channel={channel}
                key={channel}
                title={label}
              >
                <Icon
                  name={
                    channel === "local"
                      ? "monitor"
                      : "channel" + channel[0].toUpperCase() + channel.slice(1)
                  }
                />
                <span className="sr-only">{label} </span>
                {counts[channel]}
              </span>
            ))}
        </span>
      )}
    </span>
  );
}

export type SocialProfile = {
  name: string;
  username: string;
  avatarUrl: string;
};

export function genericSocialName(name: string) {
  return !name || /^\d+$|^contacto(?: de)? (instagram|messenger|facebook)$|^dm sender$|^usuario de (instagram|facebook)$/i.test(name.trim());
}

export function inboxDisplayName(
  name: string,
  phone: string,
  channel?: string,
  profile?: SocialProfile,
) {
  if (
    (channel === "facebook" || channel === "messenger" || channel === "instagram") &&
    genericSocialName(name)
  ) {
    return (
      profile?.name ||
      (profile?.username && `@${profile.username}`) ||
      `Contacto de ${channels[channel]}`
    );
  }
  return name || phone || "Contacto sin nombre";
}

function SocialAvatar({ src }: { src: string }) {
  return src ? (
    <img
      src={src}
      alt=""
      referrerPolicy="no-referrer"
      onError={(event) => {
        event.currentTarget.hidden = true;
      }}
    />
  ) : null;
}

export function InboxContactProfile({
  client,
  accounts,
  profile,
}: {
  client: Client;
  accounts: { id: string; name: string; channel: string }[];
  profile?: SocialProfile;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useId();
  const name = client.name?.trim();
  const contactName = inboxDisplayName(
    name,
    client.phone,
    accounts[0]?.channel,
    profile,
  );
  const initials = name
    ?.match(/\p{L}[\p{L}\p{M}]*/gu)
    ?.slice(0, 2)
    .map((part) => Array.from(part)[0].toLocaleUpperCase("es"))
    .join("");
  const fields = [
    ["Nombre del perfil", profile?.name === contactName ? "" : profile?.name],
    ["Usuario", profile?.username ? `@${profile.username}` : ""],
    ["Teléfono", client.phone],
    ["Ciudad", client.city],
    ["Programa", client.program],
    ["Etapa", client.stage],
  ].filter(([, value]) => value?.trim());
  return (
    <>
      <Button
        variant="quiet"
        aria-haspopup="dialog"
        onClick={() => dialog.current?.showModal()}
      >
        Ver perfil
      </Button>
      <dialog
        ref={dialog}
        className="inbox-contact-profile"
        aria-labelledby={title}
      >
        <div className="inbox-contact-profile-content">
          <span
            className="inbox-avatar inbox-contact-profile-avatar"
            aria-hidden="true"
          >
            {initials || <Icon name="clients" />}
            {profile && <SocialAvatar src={profile.avatarUrl} />}
          </span>
          <h2 id={title}>{contactName}</h2>
          <div className="inbox-row-meta">
            {accounts.length ? (
              accounts.map((account) => (
                <ChannelLabel key={account.id} channel={account.channel} />
              ))
            ) : (
              <ChannelLabel channel="local" />
            )}
          </div>
          {fields.length > 0 && (
            <dl>
              {fields.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          )}
          {accounts.some(({ channel }) => channel === "whatsapp") && (
            <p className="scope-text">
              WhatsApp no comparte la foto de perfil del contacto con
              RinovaPlus.
            </p>
          )}
          <form method="dialog">
            <Button type="submit" variant="secondary">
              Cerrar perfil
            </Button>
          </form>
        </div>
      </dialog>
    </>
  );
}

export function InboxIdle({
  showContact,
  empty,
}: {
  showContact: boolean;
  empty: boolean;
}) {
  return (
    <section
      className="p3-person p3-inbox-person inbox-idle"
      data-contact-hidden={!showContact || undefined}
    >
      <section
        className="panel p3-thread inbox-idle-thread"
        aria-label="Espacio de conversación"
      >
        <div className="inbox-idle-header" aria-hidden="true">
          <i className="inbox-idle-avatar" />
          <i className="inbox-idle-line" />
        </div>
        <div className="inbox-idle-chat">
          <div className="inbox-idle-bubbles" aria-hidden="true">
            <i />
            <i />
            <i />
          </div>
          <div className="inbox-idle-message">
            <Icon name="inbox" />
            <h2>
              {empty
                ? "Aún no hay conversaciones"
                : "Selecciona una conversación"}
            </h2>
            {!empty && <p>Abre un hilo de la bandeja para atenderlo.</p>}
          </div>
        </div>
        <div className="inbox-idle-composer" aria-hidden="true">
          <i />
          <i />
          <i className="inbox-idle-line" />
        </div>
      </section>
      {showContact && (
        <aside
          className="panel p3-ficha inbox-idle-ficha"
          aria-label="Ficha CRM"
        >
          <h2 className="inbox-crm-title">Ficha CRM</h2>
          <div className="inbox-idle-profile" aria-hidden="true">
            <i className="inbox-idle-avatar" />
            <div>
              <i className="inbox-idle-line" />
              <i className="inbox-idle-line" />
            </div>
          </div>
          <div className="inbox-idle-fields" aria-hidden="true">
            <i className="inbox-idle-line" />
            <i className="inbox-idle-line" />
            <i className="inbox-idle-line" />
          </div>
        </aside>
      )}
    </section>
  );
}

export function InboxListControls({
  filters,
  set,
  stages,
  queues,
  comments,
  refresh,
  children,
}: {
  filters: InboxFilters;
  set: (value: InboxFilters) => void;
  stages: Option[];
  queues: Option[];
  comments: boolean;
  refresh: () => void;
  children?: ReactNode;
}) {
  const update = (key: keyof InboxFilters, value: string) =>
    set({ ...filters, [key]: value });
  const count = Object.entries(filters).filter(
    ([key, value]) =>
      key !== "q" && value !== initialInboxFilters[key as keyof InboxFilters],
  ).length;
  return (
    <div className="inbox-list-controls">
      <div className="inbox-list-heading">
        <h2>Conversaciones</h2>
        <Button variant="quiet" onClick={refresh} aria-label="Actualizar bandeja manualmente">
          Actualizar
        </Button>
      </div>
      {comments && (
        <nav className="inbox-mode-tabs" aria-label="Tipo de conversación">
          <a aria-current="page" href="#/inbox">
            Mensajes
          </a>
          <a href="#/comments">Comentarios</a>
        </nav>
      )}
      <Field
        id="p3-search"
        label="Buscar conversaciones"
        type="search"
        placeholder="Nombre, teléfono o mensaje"
        value={filters.q}
        maxLength={200}
        onChange={(event) => update("q", event.target.value)}
      />
      <div
        className="inbox-queue-quick"
        role="group"
        aria-label="Vistas rápidas"
      >
        {[
          { value: "all", label: "Todas" },
          { value: "unread", label: "Sin leer" },
          { value: "mine", label: "Mías" },
          { value: "churn", label: "Abandono alto" },
          { value: "comment_pending", label: "Desde comentarios" },
        ].map(({ value, label }) => (
          <Button
            key={value}
            variant="quiet"
            aria-pressed={filters.queue === value}
            onClick={() =>
              set({
                ...filters,
                queue: value,
                riskLevel: value === "churn" ? "" : filters.riskLevel,
              })
            }
          >
            {label}
          </Button>
        ))}
      </div>
      {filters.queue === "comment_pending" && (
        <p className="scope-text">Privados iniciados desde un comentario. Cuando la persona responda, su chat aparecerá en el Inbox principal.</p>
      )}
      <details className="inbox-filters">
        <summary>Filtros {count > 0 && <span>{count} activos</span>}</summary>
        <div className="inbox-filter-fields">
          <SelectField
            id="p3-channel"
            label="Canal"
            value={filters.channel}
            options={opts(channels, "Todos")}
            onChange={(event) => update("channel", event.target.value)}
          />
          <SelectField
            id="p3-queue"
            label="Bandeja"
            value={filters.queue}
            options={queues}
            onChange={(event) => {
              const queue = event.target.value;
              set({
                ...filters,
                queue,
                riskLevel: queue === "churn" ? "" : filters.riskLevel,
              });
            }}
          />
          <SelectField
            id="p3-state-filter"
            label="Estado"
            value={filters.state}
            options={opts(states, "Todos")}
            onChange={(event) => update("state", event.target.value)}
          />
          <SelectField
            id="p3-stage"
            label="Etapa"
            value={filters.stage}
            options={stages}
            onChange={(event) => update("stage", event.target.value)}
          />
          <SelectField
            id="p3-temperature-filter"
            label="Temperatura"
            value={filters.temperature}
            options={opts(temperatures, "Todas")}
            onChange={(event) => update("temperature", event.target.value)}
          />
          <SelectField
            id="p3-risk-filter"
            label="Riesgo de abandono"
            value={filters.riskLevel}
            options={opts(riskLevels, "Todos")}
            onChange={(event) =>
              set({
                ...filters,
                riskLevel: event.target.value,
                queue: filters.queue === "churn" ? "all" : filters.queue,
              })
            }
          />
        </div>
        <Button
          variant="quiet"
          disabled={!count && !filters.q}
          onClick={() => set(initialInboxFilters)}
        >
          Restablecer filtros
        </Button>
      </details>
      {children}
    </div>
  );
}

const previewMedia = {
  image: { icon: "image", label: "Foto" },
  video: { icon: "video", label: "Video" },
  sticker: { icon: "sticker", label: "Sticker" },
  document: { icon: "application", label: "Documento" },
  audio: { icon: "microphone", label: "Audio" },
};

function ConversationPreview({ preview, kind, duration }: {
  preview?: string | null;
  kind?: string | null;
  duration?: string | null;
}) {
  const text = preview?.trim() || "";
  if (text === "[reaction]") return "Reacción a un mensaje";
  const marker = /^\[(audio|image|video|sticker|document)\]$/i.exec(text)?.[1]?.toLowerCase();
  const media = previewMedia[(kind || marker || "") as keyof typeof previewMedia];
  if (!media) return text || "Sin mensajes";
  const caption = text && !/^\[(adjunto|audio|image|imagen|photo|foto|video|sticker|document|documento)\]$/i.test(text)
    ? text : "";
  const seconds = Number(duration);
  const label = media === previewMedia.audio && Number.isFinite(seconds) && seconds > 0
    ? clockTime(seconds) : caption || media.label;
  return <><Icon name={media.icon} className="inbox-preview-media" />{label}</>;
}

export function ConversationRow({
  row,
  selected,
  onSelect,
  timestamp,
  profile,
}: {
  row: {
    name: string;
    phone: string;
    stage: string;
    state: string;
    unread: boolean;
    assignee: string | null;
    channel?: string;
    accountName?: string | null;
    accountPhone?: string | null;
    commentOrigin?: boolean;
    commentPending?: boolean;
    preview?: string | null;
    previewKind?: string | null;
    previewDuration?: string | null;
    temperature?: string | null;
    leadScore?: number | null;
    program?: string | null;
    slaStatus?: string;
    risk: Risk;
  };
  selected: boolean;
  onSelect: () => void;
  timestamp?: ReactNode;
  profile?: SocialProfile;
}) {
  const name = inboxDisplayName(row.name, row.phone, row.channel, profile);
  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  const temperature = labelFor(temperatures, row.temperature);
  const program = row.program?.trim();
  const programCode = program ? inboxProgramCode(program) : "";
  return (
    <button
      type="button"
      className="inbox-conversation"
      aria-pressed={selected}
      data-unread={row.unread || undefined}
      onClick={onSelect}
    >
      <span className="inbox-avatar" aria-hidden="true">
        {initials || "•"}
        {profile && <SocialAvatar src={profile.avatarUrl} />}
      </span>
      <span className="inbox-conversation-body">
        <span className="inbox-row-heading">
          <strong>{name}</strong>
          {timestamp && <small>{timestamp}</small>}
        </span>
        <span className="inbox-row-meta">
          <ChannelLabel channel={row.channel} />
          {row.unread && <span className="inbox-unread">Sin leer</span>}
          <span>{labelFor(states, row.state)}</span>
        </span>
        <span className="inbox-row-preview">
          <ConversationPreview preview={row.preview} kind={row.previewKind} duration={row.previewDuration} />
        </span>
        {(row.accountName || row.commentOrigin) && (
          <span className="inbox-row-source">
          {row.accountName && <span className="inbox-row-account" title={`Cuenta receptora: ${row.accountName}`}>
            <Icon name="channels" className="inbox-preview-media" />
            {row.accountName}
          </span>}
          {!!row.commentOrigin && <span className="inbox-comment-origin" title={row.commentPending ? "Privado iniciado desde un comentario; esperando respuesta" : "Esta conversación comenzó desde un comentario"}>
            <Icon name="comments" />Desde comentario
          </span>}
          </span>
        )}
        <span className="inbox-row-meta inbox-row-signals">
          {temperature && (
            <span data-temperature={row.temperature}>
              {temperature}
              {row.leadScore != null ? ` · ${row.leadScore}` : ""}
            </span>
          )}
          <RiskBadge risk={row.risk} inList />
          {row.slaStatus === "overdue" && (
            <span className="inbox-signal" data-sla="overdue">SLA vencido</span>
          )}
          {row.slaStatus === "on_time" && (
            <span className="inbox-signal" data-sla="on_time">SLA en plazo</span>
          )}
        </span>
        <span className="inbox-row-owner">
          {[row.stage, row.assignee || "Responsable sin asignar"]
            .filter(Boolean)
            .join(" · ")}
        </span>
        {program && (
          <span className="inbox-row-program" title={program}>
            {programCode && <b>{programCode}</b>}
            <span>{program}</span>
          </span>
        )}
      </span>
    </button>
  );
}
