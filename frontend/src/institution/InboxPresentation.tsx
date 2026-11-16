import type { ReactNode } from "react";
import { Button, Field, SelectField } from "../shared/ui";
import { Icon } from "../shared/Icon";
import type { Risk } from "./Workspace";

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

export function InboxIdle({ showContact }: { showContact: boolean }) {
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
            <h2>Selecciona una conversación</h2>
            <p>Abre un hilo de la bandeja para atenderlo.</p>
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
        <Button variant="quiet" onClick={refresh}>
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

export function ConversationRow({
  row,
  selected,
  onSelect,
  timestamp,
}: {
  row: {
    name: string;
    phone: string;
    stage: string;
    state: string;
    unread: boolean;
    assignee: string | null;
    channel?: string;
    preview?: string | null;
    temperature?: string | null;
    leadScore?: number | null;
    program?: string | null;
    risk: Risk;
  };
  selected: boolean;
  onSelect: () => void;
  timestamp?: ReactNode;
}) {
  const name = row.name || row.phone || "Contacto sin nombre";
  const initials = row.name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
  const temperature = labelFor(temperatures, row.temperature);
  const program = row.program?.trim();
  const programCode = program ? inboxProgramCode(program) : "";
  const risk =
    row.risk.fresh && row.risk.status === "known"
      ? labelFor(riskLevels, row.risk.level)
      : "";
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
          {row.preview?.trim() || "Sin mensajes"}
        </span>
        <span className="inbox-row-meta inbox-row-signals">
          {temperature && (
            <span data-temperature={row.temperature}>
              {temperature}
              {row.leadScore != null ? ` · ${row.leadScore}` : ""}
            </span>
          )}
          <span data-risk={risk ? row.risk.level : undefined}>
            {risk
              ? `Abandono: ${risk.toLowerCase()}`
              : row.risk.status === "not_applicable"
                ? "Abandono: no aplica"
                : "Abandono: sin evaluación"}
          </span>
        </span>
        <span className="inbox-row-owner">
          {[row.stage, row.assignee || "Sin asignar"]
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
