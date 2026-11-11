import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PeriodCatalog } from "../modules/catalog/pages/PeriodCatalog";
import {
  catalogOrigin,
  fetchPeriods,
  fetchCatalog,
  validatePeriodPage,
  validateSchoolPage,
  validateModalityPage,
} from "../modules/catalog/api/catalog";

const token = "SyntheticTestAccessKey01234567890123456789";
const period = {
  id: -1,
  label: "Synthetic period",
  startDate: "2020-01-01",
  endDate: "2020-03-01",
  sourceState: false,
};
const page = {
  items: [period],
  page: { limit: 25, offset: 0, hasMore: false },
};
const response = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("schools and modalities", () => {
  const labels = {
    items: [
      { id: -1, label: "Same synthetic label" },
      { id: 5, label: "Same synthetic label" },
    ],
    page: page.page,
  };
  it("accepts duplicate labels with stable IDs and rejects wrong projections", () => {
    expect(validateSchoolPage(labels, 0)).toEqual(labels);
    expect(validateModalityPage(labels, 0)).toEqual(labels);
    for (const invalid of [
      page,
      { ...labels, items: [{ id: 1, label: null }] },
      {
        ...labels,
        items: [{ id: 1, label: "x", Correo: "private@example.invalid" }],
      },
      { ...labels, items: [{ id: 1, label: "x", DescripcionMod: "extra" }] },
      { ...labels, items: [labels.items[1], labels.items[0]] },
    ]) {
      expect(() => validateSchoolPage(invalid, 0)).toThrow();
      expect(() => validateModalityPage(invalid, 0)).toThrow();
    }
  });
  it("fetches only the selected fixed resource with the same protected transport", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => response(labels));
    const signal = new AbortController().signal;
    await expect(fetchCatalog("schools", token, 0, signal)).resolves.toEqual(
      labels,
    );
    await expect(fetchCatalog("modalities", token, 0, signal)).resolves.toEqual(
      labels,
    );
    expect(fetch.mock.calls.map((call) => call[0])).toEqual([
      "/api/v1/catalog/schools?limit=25&offset=0",
      "/api/v1/catalog/modalities?limit=25&offset=0",
    ]);
    for (const call of fetch.mock.calls)
      expect(call[1]?.headers).toEqual({
        "X-CRM-Local": "1",
        Authorization: `Bearer ${token}`,
      });
  });
  it("switches without auto load, keeps key only in memory and selects duplicate labels by ID", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => response(labels));
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "schools",
    );
    expect(fetch).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cargar escuelas" }));
    await user.selectOptions(await screen.findByLabelText("Escuela"), "5");
    expect(screen.getByLabelText("Escuela")).toHaveValue("5");
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "modalities",
    );
    expect(screen.queryByLabelText("Escuela")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Clave de acceso temporal")).toHaveValue(
      token,
    );
    expect(fetch).toHaveBeenCalledTimes(1);
    await user.click(
      screen.getByRole("button", { name: "Cargar modalidades" }),
    );
    expect(await screen.findByLabelText("Modalidad")).toHaveValue("");
    expect(localStorage.length).toBe(0);
  });
  it("aborts old resource responses and refuses stale results after switching", async () => {
    let resolve!: (value: Response) => void;
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementationOnce(
        () =>
          new Promise((done) => {
            resolve = done;
          }),
      )
      .mockImplementation(async () => response(labels));
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.click(screen.getByRole("button", { name: "Cargar períodos" }));
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "schools",
    );
    expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(true);
    await act(async () => {
      resolve(response(page));
    });
    expect(
      screen.queryByLabelText("Período académico"),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Escuela")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cargar escuelas" }));
    expect(await screen.findByLabelText("Escuela")).toBeVisible();
  });
  it("shows school unavailable, retries empty, and clears on modality switch", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ message: "private SQL" }, 503))
      .mockResolvedValueOnce(response({ items: [], page: page.page }));
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "schools",
    );
    await user.click(screen.getByRole("button", { name: "Cargar escuelas" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El catálogo no está disponible",
    );
    await user.click(
      screen.getByRole("button", { name: "Reintentar catálogo" }),
    );
    expect(
      await screen.findByText("No hay escuelas en esta página."),
    ).toBeVisible();
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "modalities",
    );
    expect(
      screen.queryByText("No hay escuelas en esta página."),
    ).not.toBeInTheDocument();
  });
  it("paginates modalities with the same bound and discards selection across pages", async () => {
    const first = {
      items: Array.from({ length: 25 }, (_, id) => ({
        id,
        label: "Synthetic modality",
      })),
      page: { ...page.page, hasMore: true },
    };
    const last = {
      items: [{ id: 30, label: "Last synthetic modality" }],
      page: { ...page.page, offset: 25 },
    };
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response(first))
      .mockResolvedValueOnce(response(last));
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "modalities",
    );
    await user.click(
      screen.getByRole("button", { name: "Cargar modalidades" }),
    );
    await user.selectOptions(await screen.findByLabelText("Modalidad"), "5");
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await screen.findByText("Página 2");
    expect(screen.getByLabelText("Modalidad")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
    expect(String(fetch.mock.calls[1][0])).toContain(
      "/modalities?limit=25&offset=25",
    );
  });
});

describe("bounded local catalog transport", () => {
  it("validates source IDs, dates and page envelope", () => {
    expect(validatePeriodPage(page, 0)).toEqual(page);
    for (const bad of [
      null,
      { ...page, page: { ...page.page, offset: 25 } },
      { ...page, items: [{ ...period, id: NaN }] },
      { ...page, items: [{ ...period, id: 2147483648 }] },
      { ...page, items: [{ ...period, startDate: "2020-02-30" }] },
      { ...page, items: [{ ...period, sourceState: 1 }] },
      { ...page, items: [{ ...period, label: null }] },
      { ...page, items: [period, period] },
      { ...page, page: { ...page.page, hasMore: true } },
    ])
      expect(() => validatePeriodPage(bad, 0)).toThrow();
  });
  it("allows only loopback origins without credentials, paths or redirects", () => {
    expect(catalogOrigin("")).toBe("");
    expect(catalogOrigin("http://localhost:8013")).toBe(
      "http://localhost:8013",
    );
    for (const bad of [
      "https://example.com",
      "http://127.0.0.1:8000/path",
      "http://user:pass@localhost:8000",
      "http://localhost:8000?token=x",
      "http://localhost.evil:8000",
    ])
      expect(() => catalogOrigin(bad)).toThrow();
  });
  it("sends token only in Authorization with bounded parameters and abort signal", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(response(page));
    const controller = new AbortController();
    await expect(fetchPeriods(token, 0, controller.signal)).resolves.toEqual(
      page,
    );
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/catalog/periods?limit=25&offset=0",
      {
        method: "GET",
        headers: { "X-CRM-Local": "1", Authorization: `Bearer ${token}` },
        signal: controller.signal,
        credentials: "omit",
        redirect: "error",
        cache: "no-store",
      },
    );
  });
  it("does not disclose server error payload", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      response({ message: "private SQL server password" }, 503),
    );
    await expect(
      fetchPeriods(token, 0, new AbortController().signal),
    ).rejects.toThrow("El catálogo no está disponible");
  });
});

describe("isolated catalog UI", () => {
  it("has no auto fetch and permits local mode with an optional transient key", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(response(page));
    const user = userEvent.setup();
    const { unmount } = render(<PeriodCatalog />);
    expect(fetch).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Cargar períodos" }),
    ).toBeEnabled();
    expect(screen.getByLabelText("Clave de acceso temporal")).toHaveAttribute(
      "type",
      "password",
    );
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.click(screen.getByRole("button", { name: "Cargar períodos" }));
    await user.selectOptions(
      await screen.findByLabelText("Período académico"),
      "-1",
    );
    expect(screen.getByText(/Estado de origen: false/)).toBeVisible();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    unmount();
    render(<PeriodCatalog />);
    expect(screen.getByLabelText("Clave de acceso temporal")).toHaveValue("");
  });
  it("shows unavailable and retries without substituting demo data", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response({ message: "private SQL" }, 503))
      .mockResolvedValueOnce(response({ items: [], page: page.page }));
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.click(screen.getByRole("button", { name: "Cargar períodos" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El catálogo no está disponible",
    );
    expect(screen.queryByText("private SQL")).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Reintentar catálogo" }),
    );
    expect(
      await screen.findByText("No hay períodos en esta página."),
    ).toBeVisible();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it("supports next and previous pages by stable IDs", async () => {
    const first = {
      items: Array.from({ length: 25 }, (_, index) => ({
        ...period,
        id: index,
      })),
      page: { limit: 25, offset: 0, hasMore: true },
    };
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(response(first))
      .mockResolvedValueOnce(
        response({ ...page, page: { ...page.page, offset: 25 } }),
      )
      .mockResolvedValueOnce(response(first));
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.click(screen.getByRole("button", { name: "Cargar períodos" }));
    await screen.findByText("Página 1");
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await screen.findByText("Página 2");
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Anterior" }));
    await screen.findByText("Página 1");
    expect(fetch.mock.calls.map((call) => String(call[0]))).toEqual(
      [0, 25, 0].map(
        (offset) => `/api/v1/catalog/periods?limit=25&offset=${offset}`,
      ),
    );
  });
  it("discards responses after key changes and aborts on unmount", async () => {
    let resolve!: (value: Response) => void;
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const user = userEvent.setup();
    const { unmount } = render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.click(screen.getByRole("button", { name: "Cargar períodos" }));
    const firstSignal = fetch.mock.calls[0][1]?.signal;
    expect(screen.getByText("Cargando períodos…")).toBeVisible();
    await user.clear(screen.getByLabelText("Clave de acceso temporal"));
    expect(firstSignal?.aborted).toBe(true);
    await act(async () => {
      resolve(response(page));
    });
    expect(
      screen.queryByLabelText("Período académico"),
    ).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.click(screen.getByRole("button", { name: "Cargar períodos" }));
    const nextSignal = fetch.mock.calls[1][1]?.signal;
    unmount();
    expect(nextSignal?.aborted).toBe(true);
  });
});
