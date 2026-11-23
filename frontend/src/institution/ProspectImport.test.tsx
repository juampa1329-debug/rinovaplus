import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProspectImport } from "./ProspectImport";

const mock = vi.hoisted(() => ({
  call: vi.fn(),
  actions: ["crm.write", "settings.crm.write"],
}));
vi.mock("./api", () => ({
  useInstitution: () => ({
    call: mock.call,
    session: { actions: mock.actions },
  }),
}));
vi.mock("./drafts", () => ({ useDraftGuard: vi.fn() }));

const source = {
  version: "rinovaplus-prospects-v1",
  batch_id: "batch",
  entries: [
    { ref: "clear", name: "Contacto claro", review: [] },
    { ref: "held", name: "Contacto dudoso", review: ["Compartido"] },
  ],
};
async function upload() {
  const file = new File([JSON.stringify(source)], "lote.json", {
    type: "application/json",
  });
  Object.defineProperty(file, "text", {
    value: async () => JSON.stringify(source),
  });
  fireEvent.change(
    screen.getByLabelText("Lote JSON de preinscritos revisado"),
    { target: { files: [file] } },
  );
  await screen.findByText("2 contactos en el lote.");
}
describe("Importación revisada", () => {
  beforeEach(() => {
    mock.call.mockReset();
    mock.actions = ["crm.write", "settings.crm.write"];
  });
  it("requires both contact and configuration permissions", () => {
    mock.actions = ["crm.write"];
    render(<ProspectImport changed={vi.fn()} />);
    expect(screen.queryByText("Importar preinscritos al CRM")).toBeNull();
  });
  it("holds doubtful people and only submits the clear rows after confirmation", async () => {
    mock.call.mockImplementation(async (path: string) => {
      if (path.endsWith("preview"))
        return {
          items: [
            { ref: "clear", state: "ready", reason: "Claro" },
            { ref: "held", state: "review", reason: "Compartido" },
          ],
        };
      if (path.endsWith("fields")) return { added: [] };
      return { items: [{ ref: "clear", state: "imported", reason: "Creado" }] };
    });
    render(<ProspectImport changed={vi.fn()} />);
    await upload();
    fireEvent.click(screen.getByText("Contrastar con CRM"));
    await screen.findByText("Listos: 1 · Para revisión: 1 · Importados: 0");
    expect(screen.getByText("Importar contactos revisados")).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText("Importar contactos revisados"));
    await screen.findByText("Listos: 0 · Para revisión: 1 · Importados: 1");
    const commit = mock.call.mock.calls.find(([path]) =>
      path.endsWith("commit"),
    );
    expect(commit?.[2].entries.map((e: { ref: string }) => e.ref)).toEqual([
      "clear",
    ]);
    expect(
      mock.call.mock.calls.some(([path]) => /message|consent/.test(path)),
    ).toBe(false);
  });
  it("reuses an uncertain commit attempt and keeps the reviewed rows", async () => {
    let failed = false;
    mock.call.mockImplementation(async (path: string) => {
      if (path.endsWith("preview"))
        return {
          items: [
            { ref: "clear", state: "ready", reason: "Claro" },
            { ref: "held", state: "review", reason: "Compartido" },
          ],
        };
      if (path.endsWith("fields")) return { added: [] };
      if (!failed) {
        failed = true;
        throw Error("Respuesta interrumpida");
      }
      return {
        items: [{ ref: "clear", state: "imported", reason: "Ya registrado" }],
      };
    });
    render(<ProspectImport changed={vi.fn()} />);
    await upload();
    fireEvent.click(screen.getByText("Contrastar con CRM"));
    await screen.findByText("Listos: 1 · Para revisión: 1 · Importados: 0");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText("Importar contactos revisados"));
    await screen.findByText(/Respuesta interrumpida/);
    await waitFor(() =>
      expect(screen.getByText("Importar contactos revisados")).toBeEnabled(),
    );
    fireEvent.click(screen.getByText("Importar contactos revisados"));
    await screen.findByText("Listos: 0 · Para revisión: 1 · Importados: 1");
    const attempts = mock.call.mock.calls.filter(([path]) =>
      path.endsWith("commit"),
    );
    expect(attempts[0][2]).toEqual(attempts[1][2]);
  });
});
