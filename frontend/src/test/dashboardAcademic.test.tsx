import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { Dashboard, dailySeries } from "../institution/Dashboard";
import type { DashboardData } from "../institution/Dashboard";
import { sourceGaps } from "../institution/siieGaps";
import { AcademicPrograms } from "../institution/AcademicPrograms";

const sample: DashboardData = {
  days: 7,
  start: "2026-11-13T05:00:00+00:00",
  end: "2026-11-19T20:00:00+00:00",
  generated_at: "2026-11-19T20:00:00+00:00",
  timezone: "America/Bogota",
  inbox: {
    conversations: 3,
    attended: 2,
    incoming: 10,
    sent: 4,
    ai_sent: 1,
    daily: [{ day: "2026-11-19", incoming: 10, sent: 4 }],
    channels: [{ channel: "whatsapp", count: 10 }],
    modes: [{ mode: "ai", count: 2 }],
  },
  followups: { completed: 1, pending: 5, overdue: 2 },
  comments: { received: 8 },
};

it("filters the local program library by school without changing any records", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        items: [
          {
            program_id: 1,
            name: "Software ficticio",
            school: "TIC",
            schedule: "Diurna",
          },
          {
            program_id: 2,
            name: "Salud ficticia",
            school: "Salud",
            schedule: "Nocturna",
          },
        ],
        has_more: false,
      }),
    ),
  );
  try {
    render(<AcademicPrograms />);
    await screen.findByRole("button", { name: /Software ficticio/ });
    fireEvent.change(screen.getByLabelText("Filtrar por escuela"), {
      target: { value: "Salud" },
    });
    expect(
      screen.queryByRole("button", { name: /Software ficticio/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Salud ficticia/ }),
    ).toBeVisible();
    expect(
      fetcher.mock.calls.every(
        ([, init]) => !init?.method || init.method === "GET",
      ),
    ).toBe(true);
  } finally {
    fetcher.mockRestore();
  }
});

it("fills quiet Bogotá calendar days without inventing activity and exposes chart data", async () => {
  expect(dailySeries(sample)).toHaveLength(7);
  expect(dailySeries(sample)[0]).toEqual({
    day: "2026-11-13",
    incoming: 0,
    sent: 0,
  });
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(new Response(JSON.stringify(sample)));
  try {
    render(<Dashboard name="Juan Pablo" />);
    expect(await screen.findByText(/Datos del CRM/)).toBeVisible();
    expect(
      screen.getByRole("link", { name: /Conversaciones atendidas/ }),
    ).toHaveTextContent("2");
    fireEvent.click(screen.getByText("Ver datos de la gráfica"));
    expect(screen.getByRole("table")).toBeVisible();
    expect(screen.getByRole("row", { name: "2026-11-19 10 4" })).toBeVisible();
  } finally {
    fetcher.mockRestore();
  }
});

it("does not flag unqueried finance as missing from a basic program snapshot", () => {
  const local = {
    name: "Prueba",
    commercial: {
      duration: "4 niveles",
      price_cop: 0,
      price_valid_until: "2027-04-01",
    },
  };
  const remote = { name: "Prueba", commercial: {} };
  expect(sourceGaps(local, remote, "program")).toEqual(["Duración"]);
  expect(sourceGaps(local, remote, "offer")).toEqual([
    "Duración",
    "Tarifa",
    "Vigencia final",
  ]);
});

it("identifies reviewed local academic content absent from the source snapshot", () => {
  expect(sourceGaps({commercial:{presentation:"Revisada",certification:"",accreditation:"",internships:"Por confirmar",career_outcomes:"Desarrollo de software"}}, {commercial:{}}, "program"))
    .toEqual(["Presentación", "Prácticas y condiciones", "Campo ocupacional"]);
});

it("reports locally completed installment dates and keeps zero amounts valid", () => {
  const local = {
    commercial: {
      financial_plans: [
        {
          external_id: "plan",
          name: "Prueba",
          initial_payment_cop: 0,
          installments: [
            { number: 1, amount_cop: 200, due_date: "2027-04-01" },
          ],
        },
      ],
    },
  };
  const remote = {
    commercial: {
      financial_plans: [
        {
          external_id: "plan",
          initial_payment_cop: 0,
          installments: [{ number: 1, amount_cop: 200, due_date: null }],
        },
      ],
    },
  };
  expect(sourceGaps(local, remote, "offer")).toEqual([
    "Plan Prueba · Cuota 1 · Fecha",
  ]);
});

it("prepares a linked program refresh without saving and retains manual fields", async () => {
  const commercial = {
    aliases: "",
    duration: "4 niveles, revisión local",
    modality: "",
    syllabus: "",
    requirements: "",
    price_cop: null,
    price_concept: "",
    price_valid_until: null,
    source_url: "",
    source_checked_at: "",
  };
  const draft = {
    name: "Programa de prueba",
    school: "TIC",
    schedule: "",
    commercial,
  };
  const source = {
    kind: "program",
    program_id: "143",
    offer_id: "",
    source_revision: "fixture",
    request: { program_id: "143", cursor: "" },
    checked_at: "2026-11-19T20:00:00Z",
    issues: [],
    values: { ...draft, commercial: { ...commercial, duration: "" } },
  };
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (path, init) => {
      if (String(path).includes("/programs?"))
        return new Response(
          JSON.stringify({
            items: [{ program_id: 1, name: draft.name, school: "TIC" }],
            has_more: false,
          }),
        );
      if (String(path).endsWith("/programs/1"))
        return new Response(
          JSON.stringify({
            revision: 2,
            program: {
              Name: draft.name,
              School: "TIC",
              Schedule: "",
              Active: true,
            },
            commercial,
            siie_source: source,
          }),
        );
      if (String(path).endsWith("/import-siie") && init?.method === "POST")
        return new Response(
          JSON.stringify({
            draft,
            source,
            local_program_id: 1,
            local_revision: 2,
            manual_fields_preserved: ["commercial.duration"],
          }),
        );
      throw new Error("Unexpected request");
    });
  try {
    render(<AcademicPrograms />);
    fireEvent.click(await screen.findByRole("button", { name: draft.name }));
    await waitFor(() =>
      expect(screen.getByLabelText("Duración")).toHaveValue(
        commercial.duration,
      ),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Sincronizar con SIIE" }),
    );
    expect(await screen.findByText(/Se conservaron 1 campos/)).toBeVisible();
    expect(screen.getByLabelText("Duración")).toHaveValue(commercial.duration);
    expect(fetcher.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(
      false,
    );
  } finally {
    fetcher.mockRestore();
  }
});
