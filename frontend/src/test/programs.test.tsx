import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PeriodCatalog } from "../modules/catalog/pages/PeriodCatalog";
import {
  fetchCatalog,
  fetchProgramFilterOptions,
  validateProgramPage,
} from "../modules/catalog/api/catalog";

const token = "SyntheticTestAccessKey01234567890123456789";
const page = { limit: 25, offset: 0, hasMore: false };
const program = { id: -4, label: null, schoolId: 0, modalityId: -2 };
const schools = {
  items: [
    { id: 0, label: "Synthetic school" },
    { id: 1, label: "Other school" },
  ],
  page,
};
const modalities = { items: [{ id: -2, label: "Synthetic modality" }], page };
const response = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), { status });

describe("program transport and bounded filter catalogs", () => {
  it("retains null labels and signed identities while rejecting wrong projections", () => {
    const value = { items: [program], page };
    expect(validateProgramPage(value, 0)).toEqual(value);
    expect(value.items[0].label).toBeNull();
    for (const item of [
      { ...program, schoolId: true },
      { ...program, modalityId: 1.5 },
      { ...program, label: undefined },
      { ...program, CodigoPrograma: "excluded" },
    ])
      expect(() => validateProgramPage({ items: [item], page }, 0)).toThrow();
  });
  it("keeps zero and negative filters in URL parameters only for programs", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async () => response({ items: [program], page }));
    await fetchCatalog("programs", token, 0, new AbortController().signal, {
      schoolId: 0,
      modalityId: -2,
    });
    expect(String(fetch.mock.calls[0][0])).toBe(
      "/api/v1/catalog/programs?limit=25&offset=0&schoolId=0&modalityId=-2",
    );
  });
  it("collects all filter pages sequentially before fetching modalities", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) => {
        const url = new URL(String(input), "http://127.0.0.1:4173");
        if (url.pathname.endsWith("modalities")) return response(modalities);
        const offset = Number(url.searchParams.get("offset"));
        return response({
          items: Array.from({ length: offset === 0 ? 25 : 1 }, (_, index) => ({
            id: offset + index,
            label: "Synthetic school",
          })),
          page: { ...page, offset, hasMore: offset === 0 },
        });
      });
    const result = await fetchProgramFilterOptions(
      token,
      new AbortController().signal,
    );
    expect(result.schools).toHaveLength(26);
    expect(result.modalities).toHaveLength(1);
    expect(
      fetch.mock.calls.map((call) => String(call[0]).split("/catalog/")[1]),
    ).toEqual([
      "schools?limit=25&offset=0",
      "schools?limit=25&offset=25",
      "modalities?limit=25&offset=0",
    ]);
  });
  it("fails closed at 1000 options instead of returning partial filters", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) => {
        const offset = Number(
          new URL(String(input), "http://127.0.0.1:4173").searchParams.get(
            "offset",
          ),
        );
        return response({
          items: Array.from({ length: 25 }, (_, index) => ({
            id: offset + index,
            label: "Synthetic school",
          })),
          page: { ...page, offset, hasMore: true },
        });
      });
    await expect(
      fetchProgramFilterOptions(token, new AbortController().signal),
    ).rejects.toThrow("exceeds local bound");
    expect(fetch).toHaveBeenCalledTimes(40);
  });
});

describe("manual program filtering", () => {
  it("distinguishes duplicate program labels visibly and preserves selected IDs", async () => {
    const items = [
      { ...program, id: -5, label: "Duplicate synthetic program" },
      { ...program, id: 9, label: "Duplicate synthetic program" },
    ];
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      response({ items, page }),
    );
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "programs",
    );
    await user.click(screen.getByRole("button", { name: "Cargar programas" }));
    const selector = await screen.findByLabelText("Programa");
    expect(
      screen.getByRole("option", {
        name: "ID -5 · Duplicate synthetic program",
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("option", {
        name: "ID 9 · Duplicate synthetic program",
      }),
    ).toBeVisible();
    await user.selectOptions(selector, "9");
    expect(selector).toHaveValue("9");
    expect(items[0].label).toBe("Duplicate synthetic program");
    expect(items[1].label).toBe("Duplicate synthetic program");
  });
  it("loads filters manually and selects nullable program by ID with zero/negative filters", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) => {
        const url = String(input);
        return response(
          url.includes("/schools?")
            ? schools
            : url.includes("/modalities?")
              ? modalities
              : { items: [program], page },
        );
      });
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "programs",
    );
    expect(fetch).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cargar filtros" }));
    await screen.findByRole("option", { name: "Synthetic modality" });
    await user.selectOptions(screen.getByLabelText("Filtrar por escuela"), "0");
    await user.selectOptions(
      screen.getByLabelText("Filtrar por modalidad"),
      "-2",
    );
    expect(fetch).toHaveBeenCalledTimes(2);
    await user.click(screen.getByRole("button", { name: "Cargar programas" }));
    await user.selectOptions(await screen.findByLabelText("Programa"), "-4");
    expect(screen.getByLabelText("Programa")).toHaveValue("-4");
    expect(
      screen.getByRole("option", { name: "ID -4 · Sin nombre" }),
    ).toBeVisible();
    expect(String(fetch.mock.calls[2][0])).toContain(
      "schoolId=0&modalityId=-2",
    );
  });
  it("retains filters when paging and resets page/selection after changing a filter", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(async (input) => {
        const url = new URL(String(input), "http://127.0.0.1:4173");
        if (url.pathname.endsWith("schools")) return response(schools);
        if (url.pathname.endsWith("modalities")) return response(modalities);
        const offset = Number(url.searchParams.get("offset"));
        return response({
          items: Array.from({ length: offset === 0 ? 25 : 1 }, (_, index) => ({
            ...program,
            id: offset + index,
          })),
          page: { ...page, offset, hasMore: offset === 0 },
        });
      });
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "programs",
    );
    await user.click(screen.getByRole("button", { name: "Cargar filtros" }));
    await screen.findByRole("option", { name: "Synthetic modality" });
    await user.selectOptions(screen.getByLabelText("Filtrar por escuela"), "0");
    await user.click(screen.getByRole("button", { name: "Cargar programas" }));
    await screen.findByText("Página 1");
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await screen.findByText("Página 2");
    expect(String(fetch.mock.calls[3][0])).toContain("offset=25&schoolId=0");
    await user.selectOptions(screen.getByLabelText("Filtrar por escuela"), "1");
    expect(screen.queryByText("Página 2")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cargar programas" }));
    await screen.findByText("Página 1");
    expect(String(fetch.mock.calls[4][0])).toContain("offset=0&schoolId=1");
  });
  it("aborts filter loading on key changes and never caches previous credentials/options", async () => {
    let resolve!: (value: Response) => void;
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "programs",
    );
    await user.click(screen.getByRole("button", { name: "Cargar filtros" }));
    expect(
      screen.getByRole("button", { name: "Cargar programas" }),
    ).toBeDisabled();
    const signal = fetch.mock.calls[0][1]?.signal;
    await user.clear(screen.getByLabelText("Clave de acceso temporal"));
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      resolve(response(schools));
    });
    expect(
      screen.queryByRole("option", { name: "Synthetic school" }),
    ).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(localStorage.length).toBe(0);
  });
  it("shows empty and retries a program authentication error without fallback", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockImplementationOnce(async () => response({}, 401))
      .mockImplementation(async () => response({ items: [], page }));
    const user = userEvent.setup();
    render(<PeriodCatalog />);
    await user.type(screen.getByLabelText("Clave de acceso temporal"), token);
    await user.selectOptions(
      screen.getByLabelText("Catálogo académico"),
      "programs",
    );
    await user.click(screen.getByRole("button", { name: "Cargar programas" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Revise la clave de acceso temporal.",
    );
    await user.click(
      screen.getByRole("button", { name: "Reintentar catálogo" }),
    );
    expect(
      await screen.findByText("No hay programas en esta página."),
    ).toBeVisible();
  });
});
