import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useState } from "react";
import { BroadcastAudience } from "../institution/BroadcastAudience";
import type {
  AudienceFilters,
  DemographicFields,
} from "../institution/BroadcastAudience";
import { BroadcastAnalytics } from "../institution/BroadcastAnalytics";

afterEach(() => vi.restoreAllMocks());
function Audience() {
  const [filters, setFilters] = useState<AudienceFilters>({
      contact_ids: [],
      program_ids: [],
      stages: [],
      tags: [],
      cities: [],
    }),
    [mapping, setMapping] = useState<DemographicFields>({});
  return (
    <>
      <BroadcastAudience
        account="a"
        filters={filters}
        mapping={mapping}
        fields={[
          {
            key: "genero",
            label: "Género declarado",
            type: "List",
            options: ["Hombre", "Mujer"],
          },
          { key: "nacimiento", label: "Nacimiento", type: "Date", options: [] },
        ]}
        programs={[
          { program_id: 1, name: "Software" },
          { program_id: 2, name: "Enfermería" },
        ]}
        stages={["Contactado", "Remarketing"]}
        tags={["Admisiones", "Grupo nocturno"]}
        change={(f, m) => {
          setFilters(f);
          setMapping(m);
        }}
      />
      <output data-testid="filters">
        {JSON.stringify({ filters, mapping })}
      </output>
    </>
  );
}
it("combines several real programs, stages, groups and schedules without losing typed commas", () => {
  render(<Audience />);
  for (const name of ["Software", "Enfermería", "Contactado", "Grupo nocturno"])
    fireEvent.click(screen.getByRole("checkbox", { name }));
  const input = screen.getByLabelText("Jornadas, separadas por coma");
  for (const value of ["Nocturna", "Nocturna,", "Nocturna, Diurna"])
    fireEvent.change(input, { target: { value } });
  expect(input).toHaveValue("Nocturna, Diurna");
  const saved = JSON.parse(screen.getByTestId("filters").textContent || "{}");
  expect(saved.filters.program_ids).toEqual([1, 2]);
  expect(saved.filters.stages).toEqual(["Contactado"]);
  expect(saved.filters.schedules).toEqual(["Nocturna", "Diurna"]);
  expect(saved.filters.tags).toEqual(["Grupo nocturno"]);
});
it("requires explicit demographic sources and clears dependent filters when a source is removed", () => {
  render(<Audience />);
  expect(screen.getByLabelText("Edad mínima")).toBeDisabled();
  expect(screen.getByLabelText("Géneros, separados por coma")).toBeDisabled();
  fireEvent.change(
    screen.getByLabelText("Campo CRM para fecha de nacimiento"),
    { target: { value: "nacimiento" } },
  );
  fireEvent.change(screen.getByLabelText("Edad mínima"), {
    target: { value: "18" },
  });
  fireEvent.change(screen.getByLabelText("Campo CRM para género"), {
    target: { value: "genero" },
  });
  fireEvent.change(screen.getByLabelText("Géneros, separados por coma"), {
    target: { value: "Mujer" },
  });
  fireEvent.change(
    screen.getByLabelText("Campo CRM para fecha de nacimiento"),
    { target: { value: "" } },
  );
  const saved = JSON.parse(screen.getByTestId("filters").textContent || "{}");
  expect(saved.filters.age_min).toBeNull();
  expect(saved.filters.genders).toEqual(["Mujer"]);
  expect(saved.mapping).toEqual({ gender: "genero" });
});
it("shows actual aggregate numbers, unknown demographics and an accessible table", () => {
  render(
    <BroadcastAnalytics
      data={{
        totals: { total: 2, delivered: 1, read: 1, replied: 0, failed: 1 },
        dimensions: {
          gender: [
            {
              label: "Mujer",
              total: 1,
              delivered: 1,
              read: 1,
              replied: 0,
              failed: 0,
            },
            {
              label: "Sin dato",
              total: 1,
              delivered: 0,
              read: 0,
              replied: 0,
              failed: 1,
            },
          ],
          city: [],
        },
      }}
    />,
  );
  expect(
    within(screen.getByRole("figure")).getByText("Mujer"),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/1 destinatarios sin dato de género/),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByText("Ver tabla del desglose"));
  expect(
    screen.getByRole("table", { name: "Resultados por género" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/No existe una métrica independiente/),
  ).toBeInTheDocument();
});
