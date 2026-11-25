import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SiieGeography } from "./SiieGeography";

afterEach(cleanup);
const countries = [
  { value: 1, label: "País uno" },
  { value: 2, label: "País dos" },
];
const page = (value = 47001, more = false) => ({
  departments: [{ value: 47, label: "Departamento real" }],
  department_values: [{ id: 47, value: "Nombre nativo del departamento" }],
  municipalities: [{ value, label: "Municipio real" }],
  municipal_text: [{ value: String(value), label: "Municipio real" }],
  has_more: more,
  next_offset: more ? 100 : null,
});

it("retains country, department and search across municipal pages and clears old values on country change", async () => {
  const calls: URLSearchParams[] = [];
  const changed = vi.fn();
  const call = async <T,>(path: string): Promise<T> => {
    const query = new URL(path, "https://crm.test/").searchParams;
    calls.push(query);
    return page(
      query.get("offset") === "100" ? 47002 : 47001,
      query.has("idDepartamento") && query.get("offset") !== "100",
    ) as T;
  };
  render(
    <SiieGeography
      id="city"
      draftId="draft"
      label="Residencia"
      value=""
      numeric
      departmentOnly={false}
      countries={countries}
      disabled={false}
      call={call}
      onChange={changed}
    />,
  );
  fireEvent.change(screen.getByLabelText("País · Residencia"), {
    target: { value: "1" },
  });
  await screen.findByRole("option", { name: "Departamento real" });
  fireEvent.change(screen.getByLabelText("Departamento · Residencia"), {
    target: { value: "47" },
  });
  await screen.findByRole("option", { name: "Municipio real" });
  fireEvent.change(screen.getByLabelText("Buscar municipio · Residencia"), {
    target: { value: "Santa" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Buscar municipios · Residencia" }),
  );
  await waitFor(() => expect(calls.at(-1)?.get("q")).toBe("Santa"));
  await screen.findByRole("option", { name: "Municipio real" });
  fireEvent.click(
    screen.getByRole("button", { name: "Más municipios · Residencia" }),
  );
  await waitFor(() => expect(calls.at(-1)?.get("offset")).toBe("100"));
  const last = calls.at(-1)!;
  expect(Object.fromEntries(last)).toMatchObject({
    draft_id: "draft",
    idPais: "1",
    idDepartamento: "47",
    q: "Santa",
    offset: "100",
  });
  await screen.findByRole("option", { name: "Municipio real" });
  fireEvent.change(screen.getByLabelText("Municipio · Residencia"), {
    target: { value: "47002" },
  });
  expect(changed).toHaveBeenLastCalledWith("47002", {
    idPais: 1,
    idDepartamento: 47,
    q: "Santa",
    offset: 100,
  });
  fireEvent.change(screen.getByLabelText("País · Residencia"), {
    target: { value: "2" },
  });
  expect(changed).toHaveBeenLastCalledWith("", { idPais: 2 });
  expect(screen.getByLabelText("Buscar municipio · Residencia")).toHaveValue(
    "",
  );
  expect(
    calls
      .filter((q) => q.has("offset"))
      .every((q) => q.has("idPais") && q.has("idDepartamento")),
  ).toBe(true);
});

it("does not let a late response restore the departments of the previous country", async () => {
  let old: ((value: unknown) => void) | undefined;
  const call = async <T,>(path: string): Promise<T> => {
    const query = new URL(path, "https://crm.test/").searchParams;
    if (query.get("idPais") === "1")
      return (await new Promise<unknown>((resolve) => {
        old = resolve;
      })) as T;
    return {
      ...page(),
      departments: [{ value: 99, label: "Departamento país dos" }],
    } as T;
  };
  render(
    <SiieGeography
      id="city"
      draftId="draft"
      label="Residencia"
      value=""
      numeric
      departmentOnly={false}
      countries={countries}
      disabled={false}
      call={call}
      onChange={vi.fn()}
    />,
  );
  fireEvent.change(screen.getByLabelText("País · Residencia"), {
    target: { value: "1" },
  });
  fireEvent.change(screen.getByLabelText("País · Residencia"), {
    target: { value: "2" },
  });
  await screen.findByRole("option", { name: "Departamento país dos" });
  await act(async () => old?.(page()));
  expect(
    screen.queryByRole("option", { name: "Departamento real" }),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("País · Residencia")).toHaveValue("2");
});

it("uses the department's native text value for employment and performs no writes", async () => {
  const changed = vi.fn();
  const call = async <T,>(): Promise<T> => page() as T;
  render(
    <SiieGeography
      id="work"
      draftId="draft"
      label="Trabajo"
      value=""
      numeric={false}
      departmentOnly
      countries={countries}
      disabled={false}
      call={call}
      onChange={changed}
    />,
  );
  fireEvent.change(screen.getByLabelText("País · Trabajo"), {
    target: { value: "1" },
  });
  await screen.findByRole("option", { name: "Departamento real" });
  fireEvent.change(screen.getByLabelText("Departamento · Trabajo"), {
    target: { value: "47" },
  });
  expect(changed).toHaveBeenLastCalledWith("Nombre nativo del departamento", {
    idPais: 1,
    idDepartamento: 47,
  });
  expect(
    screen.queryByLabelText("Municipio · Trabajo"),
  ).not.toBeInTheDocument();
});
