import { useState } from "react";
import { Button, Field, SelectField } from "../shared/ui";

export const campaignStateLabels: Record<string, string> = {
  draft: "Borrador",
  scheduled: "Programada",
  running: "En curso",
  paused: "Pausada",
  cancelled: "Cancelada",
  completed: "Completada",
};

type CampaignItem = { id: string; name: string; state: string };
type Group = "all" | "current" | "draft" | "finished";
const groups: { value: Group; label: string; states?: string[] }[] = [
  { value: "all", label: "Todas" },
  {
    value: "current",
    label: "Actuales",
    states: ["running", "scheduled", "paused"],
  },
  { value: "draft", label: "Borradores", states: ["draft"] },
  {
    value: "finished",
    label: "Finalizadas",
    states: ["completed", "cancelled"],
  },
];
const priority = [
  "running",
  "scheduled",
  "paused",
  "completed",
  "draft",
  "cancelled",
];
const pageSize = 25;
const normalize = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("es");

export function BroadcastCampaignList<T extends CampaignItem>({
  items,
  selectedId,
  hidden,
  onSelect,
}: {
  items: T[];
  selectedId?: string;
  hidden: boolean;
  onSelect: (item: T) => void;
}) {
  const [group, setGroup] = useState<Group>("all"),
    [search, setSearch] = useState(""),
    [order, setOrder] = useState("state"),
    [page, setPage] = useState(0);
  const query = normalize(search.trim());
  const states = groups.find((g) => g.value === group)?.states;
  const filtered = items
    .filter(
      (item) =>
        (!states || states.includes(item.state)) &&
        normalize(item.name).includes(query),
    )
    .sort((a, b) => {
      if (order === "name")
        return a.name.localeCompare(b.name, "es", { numeric: true });
      if (order === "recent") return 0; // The API returns latest activity first.
      const rank = (state: string) => {
        const index = priority.indexOf(state);
        return index === -1 ? priority.length : index;
      };
      return rank(a.state) - rank(b.state);
    });
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil(filtered.length / pageSize) - 1),
  );
  const start = currentPage * pageSize;
  const visible = filtered.slice(start, start + pageSize);
  const clear = () => {
    setGroup("all");
    setSearch("");
    setPage(0);
  };

  return (
    <section
      className="panel broadcast-campaign-list"
      id="broadcast-campaign-list"
      aria-label="Explorar campañas"
      hidden={hidden}
    >
      <h3>
        Tus campañas <span>{items.length}</span>
      </h3>
      <Field
        id="broadcast-campaign-search"
        label="Buscar campaña"
        type="search"
        placeholder="Nombre o programa"
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(0);
        }}
      />
      <div
        className="broadcast-campaign-groups"
        role="group"
        aria-label="Filtrar campañas por estado"
      >
        {groups.map((g) => (
          <Button
            key={g.value}
            variant="quiet"
            aria-pressed={group === g.value}
            onClick={() => {
              setGroup(g.value);
              setPage(0);
            }}
          >
            {g.label}{" "}
            <span>
              {g.states
                ? items.filter((c) => g.states?.includes(c.state)).length
                : items.length}
            </span>
          </Button>
        ))}
      </div>
      {group === "current" && (
        <p className="broadcast-campaign-hint">
          En curso, programadas y pausadas.
        </p>
      )}
      {group === "finished" && (
        <p className="broadcast-campaign-hint">Completadas y canceladas.</p>
      )}
      <SelectField
        id="broadcast-campaign-order"
        label="Ordenar campañas"
        value={order}
        options={[
          { value: "state", label: "Estado y actividad reciente" },
          { value: "recent", label: "Actividad reciente" },
          { value: "name", label: "Nombre de A a Z" },
        ]}
        onChange={(e) => {
          setOrder(e.target.value);
          setPage(0);
        }}
      />
      <p className="broadcast-campaign-count" role="status">
        {filtered.length === 0
          ? "0 campañas"
          : `${start + 1}–${Math.min(start + pageSize, filtered.length)} de ${filtered.length} campañas`}
      </p>
      {selectedId && !filtered.some((item) => item.id === selectedId) && (
        <p className="broadcast-campaign-hint">
          La campaña abierta queda fuera de estos filtros. Su detalle sigue
          abierto.
        </p>
      )}
      {items.length === 0 ? (
        <p>
          Aún no hay campañas. Crea una para seleccionar la cuenta, la plantilla
          y los destinatarios.
        </p>
      ) : filtered.length === 0 ? (
        <div className="broadcast-campaign-empty">
          <p>No hay campañas con estos filtros.</p>
          <Button variant="quiet" onClick={clear}>
            Ver todas las campañas
          </Button>
        </div>
      ) : (
        <div
          key={`${group}:${search}:${order}:${currentPage}`}
          className="broadcast-campaign-scroll"
          role="region"
          aria-label="Listado de campañas"
          tabIndex={0}
        >
          <ul>
            {visible.map((item) => (
              <li key={item.id}>
                <Button
                  variant="quiet"
                  className="broadcast-campaign-item"
                  aria-label={`${item.name} · ${campaignStateLabels[item.state] || item.state}`}
                  aria-current={selectedId === item.id ? "true" : undefined}
                  title={item.name}
                  onClick={() => onSelect(item)}
                >
                  <span className="broadcast-campaign-name">{item.name}</span>
                  <span
                    className={`broadcast-campaign-state state-${item.state}`}
                  >
                    {campaignStateLabels[item.state] || item.state}
                  </span>
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {filtered.length > pageSize && (
        <nav
          className="broadcast-campaign-pages"
          aria-label="Páginas de campañas"
        >
          <Button
            variant="quiet"
            disabled={currentPage === 0}
            onClick={() => setPage(currentPage - 1)}
          >
            Anterior
          </Button>
          <span>
            {currentPage + 1} / {Math.ceil(filtered.length / pageSize)}
          </span>
          <Button
            variant="quiet"
            disabled={start + pageSize >= filtered.length}
            onClick={() => setPage(currentPage + 1)}
          >
            Siguiente
          </Button>
        </nav>
      )}
    </section>
  );
}
