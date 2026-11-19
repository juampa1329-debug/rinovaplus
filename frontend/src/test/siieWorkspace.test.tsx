import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SiieWorkspace } from "../institution/SiieWorkspace";

afterEach(() => vi.unstubAllGlobals());
const response = (data: unknown) =>
  new Response(JSON.stringify({ data, correlation_id: "fixture-request" }));
const click = (name: string) =>
  fireEvent.click(screen.getByRole("button", { name }));

it("inspects an incomplete offer and its finance without saving or exposing it to agents", async () => {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      calls.push(String(input));
      expect(init?.method).toBe("GET");
      if (input.includes("/siie/programs"))
        return response({
          items: [
            {
              program_id: "12",
              name: "Software de prueba",
              school: "Escuela de prueba",
              duration_levels: 3,
            },
          ],
          next_cursor: null,
        });
      if (input.includes("/siie/offers"))
        return response({
          items: [
            {
              offer_id: "45-n1",
              period_name: "Período fixture",
              level: 1,
              quotable: false,
            },
          ],
          next_cursor: null,
        });
      return response({
        quotable: false,
        complete: false,
        data_quality: [{ field: "campus_id", message: "Falta confirmar sede" }],
        offer: {
          name: "Software de prueba",
          level: 1,
          offer_id: "45-n1",
          commercial: {
            price_cop: 1000000,
            requirements: null,
            financial_plans: [
              null,
              {
                name: "Plan de origen",
                initial_payment_cop: 200000,
                installments: [
                  { number: 1, amount_cop: 400000, due_date: "2025-02-01" },
                ],
              },
            ],
          },
        },
      });
    }),
  );
  render(<SiieWorkspace />);
  click("Abrir SIIE");
  click("Obtener programas de SIIE");
  fireEvent.click(
    await screen.findByRole("button", { name: /Software de prueba/ }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Período fixture/ }),
  );
  const review = await screen.findByRole("article", {
    name: "Revisión de oferta SIIE",
  });
  expect(within(review).getByText(/Falta confirmar sede/)).toBeTruthy();
  expect(within(review).getByText(/no disponible para cotizar/)).toBeTruthy();
  expect(within(review).getByRole("table")).toBeTruthy();
  expect(within(review).getByText("2025-02-01")).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: /Aplicar|Publicar|Guardar/ }),
  ).toBeNull();
  expect(calls).toHaveLength(3);
});

it("keeps the original filters when paginating applicants after an unsaved search change", async () => {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string) => {
      calls.push(String(input));
      if (input.includes("/periods"))
        return response({
          items: [{ id: 1, nombre: "Período uno", activo: true }],
          requiereSeleccion: false,
          idPeriodoActivo: 1,
        });
      if (input.includes("/applicant?"))
        return response({
          aspirante: {
            idAspirante: 2,
            idPeriodo: 1,
            nombre: "Persona fixture",
            programa: "Programa fixture",
          },
        });
      return response({
        items: [{ idAspirante: 2, idPeriodo: 1, nombre: "Persona fixture" }],
        offset: input.includes("offset=25") ? 25 : 0,
        limit: 25,
        hasMore: true,
      });
    }),
  );
  render(<SiieWorkspace />);
  click("Abrir SIIE");
  click("Aspirantes y seguimiento");
  click("Obtener períodos de admisiones");
  await screen.findByLabelText("Buscar aspirante");
  fireEvent.change(screen.getByLabelText("Buscar aspirante"), {
    target: { value: "original" },
  });
  click("Buscar en SIIE");
  await screen.findByRole("button", { name: /Persona fixture/ });
  fireEvent.change(screen.getByLabelText("Buscar aspirante"), {
    target: { value: "sin aplicar" },
  });
  click("Más aspirantes");
  await waitFor(() => expect(calls.at(-1)).toContain("offset=25"));
  expect(calls.at(-1)).toContain("q=original");
  expect(calls.at(-1)).not.toContain("sin+aplicar");
});

it("ignores a late response after switching away from the source context", async () => {
  let resolve!: (value: Response) => void;
  vi.stubGlobal(
    "fetch",
    vi.fn(
      () =>
        new Promise<Response>((r) => {
          resolve = r;
        }),
    ),
  );
  render(<SiieWorkspace />);
  click("Abrir SIIE");
  click("Obtener programas de SIIE");
  click("Estudiantes y cartera");
  await act(async () => {
    resolve(
      response({
        items: [{ program_id: "1", name: "Respuesta antigua" }],
        next_cursor: null,
      }),
    );
  });
  click("Programas y finanzas");
  expect(screen.queryByText("Respuesta antigua")).toBeNull();
  click("Estudiantes y cartera");
  expect(
    screen.getByText(/todavía no expone estudiantes matriculados/),
  ).toBeTruthy();
});

it("requires explicit period selection when SIIE reports ambiguity", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      response({
        items: [
          { id: 1, nombre: "Uno" },
          { id: 2, nombre: "Dos" },
        ],
        requiereSeleccion: true,
        idPeriodoActivo: null,
      }),
    ),
  );
  render(<SiieWorkspace />);
  click("Abrir SIIE");
  click("Aspirantes y seguimiento");
  click("Obtener períodos de admisiones");
  const period = await screen.findByLabelText("Período de aspirantes");
  expect((period as HTMLSelectElement).value).toBe("");
  expect(
    screen
      .getByRole("button", { name: "Buscar en SIIE" })
      .hasAttribute("disabled"),
  ).toBe(true);
});

it("explains missing source credentials in the RinovaPlus modal", async () => {
  const originalShow = Object.getOwnPropertyDescriptor(
    HTMLDialogElement.prototype,
    "showModal",
  );
  const originalClose = Object.getOwnPropertyDescriptor(
    HTMLDialogElement.prototype,
    "close",
  );
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute("open");
    },
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(JSON.stringify({ code: "siie_catalog_not_configured" }), {
          status: 409,
        }),
    ),
  );
  const rendered = render(<SiieWorkspace />);
  try {
    click("Abrir SIIE");
    click("Obtener programas de SIIE");
    const dialog = await screen.findByRole("alertdialog", {
      name: "No se pudo consultar SIIE",
    });
    expect(
      within(dialog).getByText(/Guarda las variables sólo en Runtime/),
    ).toBeTruthy();
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Cerrar aviso" }),
    );
    expect(screen.queryByRole("alertdialog")).toBeNull();
  } finally {
    rendered.unmount();
    for (const [key, descriptor] of [
      ["showModal", originalShow],
      ["close", originalClose],
    ] as const) {
      if (descriptor)
        Object.defineProperty(HTMLDialogElement.prototype, key, descriptor);
      else Reflect.deleteProperty(HTMLDialogElement.prototype, key);
    }
  }
});
