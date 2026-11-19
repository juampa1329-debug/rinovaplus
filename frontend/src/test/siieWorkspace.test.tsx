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

it("copies a reviewed page with missing period metadata only after the explicit local-copy action", async () => {
  const saved = vi.fn(async () => {});
  const writes: Record<string, unknown>[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      if (input.includes("/siie/programs"))
        return response({
          source_revision: "fixture-revision",
          period_id: null,
          next_cursor: null,
          items: [
            { program_id: "143", name: "Programa ficticio", school: null },
          ],
        });
      if (input.endsWith("/sync-siie-page")) {
        writes.push(JSON.parse(String(init?.body)));
        return new Response(JSON.stringify({ count: 1, saved: true }));
      }
      throw new Error("Unexpected request " + input);
    }),
  );
  render(<SiieWorkspace onSaved={saved} />);
  click("Abrir SIIE");
  click("Obtener programas de SIIE");
  await screen.findByText("Programa ficticio");
  expect(screen.getByText(/Catálogo base disponible/)).toBeVisible();
  expect(writes).toHaveLength(0);
  click("Copiar esta página a RinovaPlus");
  await screen.findByText("1 programa guardado en el catálogo local.");
  expect(writes[0]).toMatchObject({
    source_revision: "fixture-revision",
    cursor: "",
    period_id: "",
  });
  expect(saved).toHaveBeenCalledTimes(1);
});

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
          period_id: "2",
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
  expect(
    within(review).getByText(/sin presentar lo pendiente como confirmado/),
  ).toBeTruthy();
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
          idPeriodoOfrecido: 1,
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
  click("Estudiantes y matrículas");
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
  click("Estudiantes y matrículas");
  expect(
    screen.getByRole("button", {
      name: "Obtener período ofrecido de estudiantes",
    }),
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
        new Response(JSON.stringify({ code: "siie_not_configured" }), {
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
    expect(dialog.textContent).toContain(
      "clave original única en SIIE_API_TOKEN",
    );
    expect(within(dialog).queryByText(/grupo correspondiente/)).toBeNull();
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

it("shows a single API credential and distinguishes configuration from verified access", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            api_configured: true,
            catalog_configured: true,
            admissions_configured: true,
            credential_mode: "unified",
          }),
        ),
    ),
  );
  render(<SiieWorkspace />);
  click("Abrir SIIE");
  click("Comprobar conexión configurada");
  expect(
    await screen.findByText(/API de SIIE: clave configurada/),
  ).toBeTruthy();
  expect(screen.getByText(/Una sola clave para programas/)).toBeTruthy();
  expect(
    screen.getByText(/La configuración no confirma el acceso/),
  ).toBeTruthy();
  expect(screen.queryByText(/Admisiones: clave/)).toBeNull();
});

it("uses the offered period instead of a different academically active period", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      response({
        items: [
          { id: 7, nombre: "Ofrecido futuro", activo: false },
          { id: 6, nombre: "Académico anterior", activo: true },
        ],
        idPeriodoOfrecido: 7,
        idPeriodoActivo: 6,
        requiereSeleccion: false,
      }),
    ),
  );
  render(<SiieWorkspace />);
  click("Abrir SIIE");
  click("Aspirantes y seguimiento");
  click("Obtener períodos de admisiones");
  const selected = await screen.findByLabelText("Período de aspirantes");
  expect((selected as HTMLSelectElement).value).toBe("7");
  expect(
    screen.getByRole("option", { name: "Ofrecido futuro · Ofrecido" }),
  ).toBeTruthy();
});

it("pins the catalog period across cursors and offer requests", async () => {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string) => {
      calls.push(String(input));
      if (input.includes("/offers"))
        return response({ period_id: "7", items: [], next_cursor: null });
      return response({
        period_id: "7",
        offered_period_id: "7",
        items: [{ program_id: "3", name: "Programa fixture" }],
        next_cursor: "cursor-fixture",
      });
    }),
  );
  render(<SiieWorkspace />);
  click("Abrir SIIE");
  click("Obtener programas de SIIE");
  await screen.findByRole("button", { name: /Programa fixture/ });
  click("Más programas");
  await waitFor(() => expect(calls.at(-1)).toContain("period_id=7"));
  await waitFor(() =>
    expect(
      screen
        .getByRole("button", { name: "Más programas" })
        .hasAttribute("disabled"),
    ).toBe(false),
  );
  fireEvent.click(screen.getByRole("button", { name: /Programa fixture/ }));
  await waitFor(() => expect(calls.at(-1)).toContain("/offers?program_id=3"));
  expect(calls.at(-1)).toContain("period_id=7");
});

it("reads students using state zero and displays contact and enrollment without merging identities", async () => {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      calls.push(String(input));
      expect(init?.method).toBe("GET");
      if (input.includes("/periods"))
        return response({
          items: [{ id: 7, nombre: "Ofrecido fixture", activo: false }],
          idPeriodoOfrecido: 7,
          idPeriodoActivo: 6,
          requiereSeleccion: false,
        });
      if (input.includes("/student_filters"))
        return response({
          programas: [],
          jornadas: [],
          niveles: [],
          estadosMatricula: [{ idEstadoMatricula: 0, nombre: "Inscrito" }],
        });
      if (input.includes("/student?"))
        return response({
          estudiante: {
            idEstudiante: 9,
            nombre: "Persona fixture",
            correo: "student@example.invalid",
            telefono: null,
            celular: null,
            idPersona: null,
            idAspirante: null,
            estadoMatricula: "Inscrito",
          },
          matriculas: [
            {
              idMatricula: 8,
              idPeriodo: 7,
              periodo: "Ofrecido fixture",
              programa: "Programa fixture",
              jornada: null,
              nivel: 1,
            },
          ],
        });
      return response({
        idPeriodo: 7,
        items: [
          {
            idEstudiante: 9,
            idMatricula: 8,
            nombre: "Persona fixture",
            idEstadoMatricula: 0,
            estadoMatricula: "Inscrito",
          },
        ],
        offset: 0,
        limit: 25,
        hasMore: false,
      });
    }),
  );
  render(<SiieWorkspace />);
  click("Abrir SIIE");
  click("Estudiantes y matrículas");
  click("Obtener período ofrecido de estudiantes");
  const period = await screen.findByLabelText("Período de estudiantes");
  expect((period as HTMLSelectElement).value).toBe("7");
  click("Obtener filtros de estudiantes");
  await screen.findByRole("option", { name: "Inscrito" });
  fireEvent.change(screen.getByLabelText("Estado actual del estudiante"), {
    target: { value: "0" },
  });
  click("Buscar estudiantes en SIIE");
  const person = await screen.findByRole("button", { name: /Persona fixture/ });
  expect(calls.at(-1)).toContain("idEstadoMatricula=0");
  expect(calls.at(-1)).toContain("idPeriodo=7");
  fireEvent.click(person);
  const detail = await screen.findByRole("article", {
    name: "Ficha de estudiante SIIE",
  });
  expect(within(detail).getByText("student@example.invalid")).toBeTruthy();
  expect(
    within(detail).getByText(/no acredita un vínculo con aspirantes/),
  ).toBeTruthy();
  expect(calls.at(-1)).toContain("idEstudiante=9");
  expect(calls.at(-1)).toContain("idPeriodo=7");
});
