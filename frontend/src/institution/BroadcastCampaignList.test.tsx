import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { BroadcastCampaignList } from "./BroadcastCampaignList";

const campaigns = [
  { id: "draft", name: "Cocina por preparar", state: "draft" },
  { id: "done", name: "Logística noviembre", state: "completed" },
  { id: "live", name: "Aduanas en envío", state: "running" },
  { id: "scheduled", name: "Inglés diciembre", state: "scheduled" },
  { id: "paused", name: "Salud en revisión", state: "paused" },
  { id: "cancelled", name: "Convocatoria anterior", state: "cancelled" },
];

it("separates current, draft and finished campaigns without changing the open detail", () => {
  const select = vi.fn();
  render(
    <BroadcastCampaignList
      items={campaigns}
      selectedId="done"
      hidden={false}
      onSelect={select}
    />,
  );
  expect(
    within(
      screen.getByRole("region", { name: "Listado de campañas" }),
    ).getAllByRole("button")[0],
  ).toHaveAccessibleName("Aduanas en envío · En curso");
  fireEvent.click(screen.getByRole("button", { name: "Actuales 3" }));
  expect(screen.getByRole("button", { name: "Actuales 3" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(
    within(
      screen.getByRole("region", { name: "Listado de campañas" }),
    ).getAllByRole("button"),
  ).toHaveLength(3);
  expect(
    screen.queryByRole("button", { name: "Logística noviembre · Completada" }),
  ).toBeNull();
  expect(screen.getByText(/Su detalle sigue abierto/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Borradores 1" }));
  expect(
    screen.getByRole("button", { name: "Cocina por preparar · Borrador" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Finalizadas 2" }));
  expect(
    screen.getByRole("button", { name: "Logística noviembre · Completada" }),
  ).toHaveAttribute("aria-current", "true");
  expect(
    screen.getByRole("button", { name: "Convocatoria anterior · Cancelada" }),
  ).toBeInTheDocument();
  expect(select).not.toHaveBeenCalled();
});

it("searches across pages and accents, and clears an empty result", () => {
  const items = Array.from({ length: 100 }, (_, i) => ({
    id: String(i),
    name: i === 99 ? "Logística especial" : `Campaña ${i + 1}`,
    state: "draft",
  }));
  render(
    <BroadcastCampaignList items={items} hidden={false} onSelect={vi.fn()} />,
  );
  expect(screen.getByRole("status")).toHaveTextContent("1–25 de 100 campañas");
  fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
  expect(screen.getByRole("status")).toHaveTextContent("26–50 de 100 campañas");
  fireEvent.change(screen.getByRole("searchbox", { name: "Buscar campaña" }), {
    target: { value: "LOGISTICA" },
  });
  expect(screen.getByRole("status")).toHaveTextContent("1–1 de 1 campañas");
  expect(
    screen.getByRole("button", { name: "Logística especial · Borrador" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("navigation", { name: "Páginas de campañas" }),
  ).toBeNull();
  fireEvent.change(screen.getByRole("searchbox", { name: "Buscar campaña" }), {
    target: { value: "sin coincidencias" },
  });
  expect(
    screen.getByText("No hay campañas con estos filtros."),
  ).toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "Ver todas las campañas" }),
  );
  expect(screen.getByRole("status")).toHaveTextContent("1–25 de 100 campañas");
});

it("paginates 100 campaigns with all recipients reachable and clamps a refreshed shorter list", () => {
  const items = Array.from({ length: 100 }, (_, i) => ({
    id: String(i),
    name: `Campaña ${i + 1}`,
    state: "completed",
  }));
  const select = vi.fn();
  const { rerender } = render(
    <BroadcastCampaignList items={items} hidden={false} onSelect={select} />,
  );
  expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
  for (let page = 0; page < 3; page++)
    fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
  expect(screen.getByRole("status")).toHaveTextContent(
    "76–100 de 100 campañas",
  );
  expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
  expect(
    within(
      screen.getByRole("region", { name: "Listado de campañas" }),
    ).getAllByRole("button"),
  ).toHaveLength(25);
  fireEvent.click(
    screen.getByRole("button", { name: "Campaña 100 · Completada" }),
  );
  expect(select).toHaveBeenCalledExactlyOnceWith(items[99]);
  rerender(
    <BroadcastCampaignList
      items={items.slice(0, 30)}
      hidden={false}
      onSelect={select}
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent("26–30 de 30 campañas");
});

it("preserves filters while collapsed and supports name and recent activity order", () => {
  const select = vi.fn();
  const { rerender } = render(
    <BroadcastCampaignList
      items={campaigns}
      hidden={false}
      onSelect={select}
    />,
  );
  fireEvent.change(screen.getByLabelText("Ordenar campañas"), {
    target: { value: "recent" },
  });
  expect(
    within(
      screen.getByRole("region", { name: "Listado de campañas" }),
    ).getAllByRole("button")[0],
  ).toHaveAccessibleName("Cocina por preparar · Borrador");
  fireEvent.change(screen.getByLabelText("Ordenar campañas"), {
    target: { value: "name" },
  });
  expect(
    within(
      screen.getByRole("region", { name: "Listado de campañas" }),
    ).getAllByRole("button")[0],
  ).toHaveAccessibleName("Aduanas en envío · En curso");
  fireEvent.click(screen.getByRole("button", { name: "Finalizadas 2" }));
  rerender(
    <BroadcastCampaignList items={campaigns} hidden onSelect={select} />,
  );
  expect(
    screen.queryByRole("region", { name: "Explorar campañas" }),
  ).toBeNull();
  rerender(
    <BroadcastCampaignList
      items={campaigns}
      hidden={false}
      onSelect={select}
    />,
  );
  expect(screen.getByRole("button", { name: "Finalizadas 2" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(screen.getByLabelText("Ordenar campañas")).toHaveValue("name");
});
