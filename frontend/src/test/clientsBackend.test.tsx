import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import {
  clientsApi,
  ClientsError,
  type ClientSnapshot,
} from "../modules/clients/api/clientsApi";
import { seedClients } from "./legacyData";

const change = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
async function ready() {
  await screen.findByRole("button", { name: /Persona Demo A/ });
}

describe("Clients local backend integration", () => {
  it("shows loading and recoverable load errors, then accepts an empty server snapshot", async () => {
    window.location.hash = "/clients";
    vi.mocked(clientsApi.workspace).mockRejectedValueOnce(new ClientsError(0));
    render(<App />);
    expect(screen.getByText("Cargando información…")).toBeVisible();
    expect(screen.getByRole("button", { name: "Crear ficha" })).toBeDisabled();
    await screen.findByRole("button", { name: "Reintentar carga de clientes" });
    vi.mocked(clientsApi.workspace).mockResolvedValue({
      clients: [],
      threads: [],
      revision: "empty",
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Reintentar carga de clientes" }),
    );
    await screen.findByRole("heading", { name: "Sin coincidencias" });
    expect(screen.getByRole("button", { name: "Nuevo" })).toBeEnabled();
  });

  it("preserves every draft field on failure and navigation, confirms once, and shares the saved record with Inbox", async () => {
    window.location.hash = "/clients";
    const user = userEvent.setup();
    render(<App />);
    await ready();
    change("Nombre visible", "Synthetic renamed client");
    change("Notas internas", "Draft retained");
    vi.mocked(clientsApi.save).mockRejectedValueOnce(new ClientsError(422));
    await user.click(screen.getByRole("button", { name: "Guardar ficha" }));
    expect(await screen.findByText(/Revise los campos/)).toBeVisible();
    expect(screen.getByLabelText("Notas internas")).toHaveValue(
      "Draft retained",
    );
    await user.click(screen.getByRole("link", { name: "Resumen" }));
    await user.click(
      screen.getByRole("link", { name: "Clientes y prospectos" }),
    );
    expect(await screen.findByLabelText("Notas internas")).toHaveValue(
      "Draft retained",
    );
    await user.click(screen.getByRole("button", { name: "Guardar ficha" }));
    await screen.findByText(/Ficha guardada correctamente/);
    await user.click(screen.getByRole("button", { name: "Abrir en Inbox" }));
    expect(
      await screen.findByRole("button", { name: /Synthetic renamed client/ }),
    ).toBeVisible();
    expect(clientsApi.save).toHaveBeenCalledTimes(2);
  });

  it("creates a stable client, opens an empty demo thread, and reloads the confirmed client while the server remains alive", async () => {
    window.location.hash = "/clients";
    const user = userEvent.setup();
    const view = render(<App />);
    await ready();
    await user.click(screen.getByRole("button", { name: "Nuevo" }));
    change("Nombre visible", "New synthetic client");
    change("Teléfono", "DEMO-900");
    await user.selectOptions(screen.getByLabelText("Etapa"), "Nuevo");
    await user.click(screen.getByRole("button", { name: "Crear ficha" }));
    await screen.findByText(/Ficha guardada correctamente./);
    const submitted = vi.mocked(clientsApi.save).mock.calls[0][0];
    expect(submitted.id).toMatch(/^[0-9a-f-]{36}$/);
    await user.click(screen.getByRole("button", { name: "Abrir en Inbox" }));
    expect(
      await screen.findByRole("button", { name: /New synthetic client/ }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: /Persona Demo A/ }),
    ).toBeVisible();
    view.unmount();
    window.location.hash = "/clients";
    render(<App />);
    expect(
      await screen.findByRole("button", { name: /New synthetic client/ }),
    ).toBeVisible();
  });

  it("ignores an older search response and keeps the complete owner list available to Inbox", async () => {
    window.location.hash = "/clients";
    const user = userEvent.setup();
    render(<App />);
    await ready();
    let release!: (value: ClientSnapshot) => void;
    const original = vi.mocked(clientsApi.list).getMockImplementation()!;
    vi.mocked(clientsApi.list).mockImplementation((q = "", ...args) =>
      q === "old"
        ? new Promise((resolve) => {
            release = resolve;
          })
        : original(q, ...args),
    );
    change("Buscar clientes", "old");
    await waitFor(() => expect(release).toBeDefined());
    change("Buscar clientes", "Persona Demo B");
    await screen.findByRole("button", { name: /Persona Demo B/ });
    await act(async () =>
      release({ clients: [seedClients()[0]], threads: [], revision: "1" }),
    );
    expect(
      screen.queryByRole("button", { name: /Persona Demo A/ }),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Inbox" }));
    expect(
      await screen.findByRole("button", { name: /Persona Demo A/ }),
    ).toBeVisible();
  });

  it("debounces typing, combines filters and clears them without losing the selected draft", async () => {
    window.location.hash = "/clients";
    render(<App />);
    await ready();
    const item = seedClients()[0];
    change("Notas internas", "Preserved filter draft");
    const count = vi.mocked(clientsApi.list).mock.calls.length;
    change("Buscar clientes", "Pers");
    change("Buscar clientes", "Persona");
    expect(clientsApi.list).toHaveBeenCalledTimes(count);
    change("Filtrar ciudad", item.city.trim().toLowerCase());
    change("Filtrar tipo de contacto", item.type.trim().toLowerCase());
    change("Filtrar etapa", item.stage);
    change("Filtrar etiqueta", item.tags.split(",")[0].trim());
    change(
      "Filtrar programa de interés",
      `text:${item.program.trim().toLowerCase()}`,
    );
    await waitFor(() =>
      expect(clientsApi.list).toHaveBeenLastCalledWith(
        "Persona",
        item.stage,
        item.tags.split(",")[0].trim(),
        expect.any(AbortSignal),
        {
          city: item.city.trim().toLowerCase(),
          contactType: item.type.trim().toLowerCase(),
          program: item.program.trim(),
        },
      ),
    );
    expect(
      vi
        .mocked(clientsApi.list)
        .mock.calls.slice(count)
        .some((call) => call[0] === "Pers"),
    ).toBe(false);
    expect(screen.getByLabelText("Notas internas")).toHaveValue(
      "Preserved filter draft",
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Restablecer filtros de clientes" }),
    );
    await waitFor(() =>
      expect(clientsApi.list).toHaveBeenLastCalledWith(
        "",
        "Todas",
        "Todas",
        expect.any(AbortSignal),
        { city: "", contactType: "", program: "" },
      ),
    );
    expect(screen.getByLabelText("Notas internas")).toHaveValue(
      "Preserved filter draft",
    );
  });

  it("preserves a draft after conflict, reuses an uncertain intent, and exposes no reset", async () => {
    window.location.hash = "/clients";
    render(<App />);
    await ready();
    expect(
      screen.queryByRole("button", { name: "Restablecer demo" }),
    ).not.toBeInTheDocument();
    change("Notas internas", "Keep on conflict");
    vi.mocked(clientsApi.save).mockRejectedValueOnce(new ClientsError(409));
    fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
    await screen.findByText(/Los datos cambiaron/);
    expect(screen.getByLabelText("Notas internas")).toHaveValue(
      "Keep on conflict",
    );
    fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
    await screen.findByText(/Ficha guardada correctamente./);
    const calls = vi.mocked(clientsApi.save).mock.calls;
    expect(calls[0][3]).toBe(calls[1][3]);
  });
});

describe("Clients HTTP transport", () => {
  it("uses only the local JSON transport and never reflects server error contents", async () => {
    vi.restoreAllMocks();
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ clients: seedClients(), revision: "one" }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ password: "PRIVATE_SENTINEL" }),
      });
    vi.stubGlobal("fetch", fetch);
    expect(
      (await clientsApi.list("A & B", "Interés", "Demo")).clients,
    ).toHaveLength(4);
    expect(fetch.mock.calls[0][0]).toContain("q=A+%26+B");
    expect(fetch.mock.calls[0][1]).toMatchObject({
      method: "GET",
      headers: { "X-CRM-Local": "1" },
      cache: "no-store",
    });
    await expect(
      clientsApi.save(
        seedClients()[0],
        "one",
        false,
        crypto.randomUUID(),
        crypto.randomUUID(),
      ),
    ).rejects.toThrow("Revise los campos");
    expect(fetch.mock.calls[1][0]).toBe("/api/local/crm/clients/demo-1");
    expect(fetch.mock.calls[1][1]).toMatchObject({
      method: "PUT",
      headers: { "X-CRM-Local": "1", "Content-Type": "application/json" },
    });
  });
});
