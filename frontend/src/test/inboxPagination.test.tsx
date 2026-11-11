import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { inboxApi, type InboxPage } from "../modules/inbox/api/inboxApi";
import { clientsApi, ClientsError } from "../modules/clients/api/clientsApi";
beforeEach(() => {
  window.location.hash = "/inbox";
});
const change = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });

describe("paginated Inbox owner", () => {
  it("measures available height in document coordinates after resize while scrolled", async () => {
    const { container } = render(<App />);
    await screen.findByLabelText("Nombre visible");
    const grid = container.querySelector<HTMLElement>(".paginated-inbox")!;
    const previousHeight = window.innerHeight;
    const previousScroll = window.scrollY;
    const box = vi.spyOn(grid, "getBoundingClientRect");
    try {
      Object.defineProperty(window, "innerHeight", {
        configurable: true,
        value: 844,
      });
      Object.defineProperty(window, "scrollY", {
        configurable: true,
        value: 100,
      });
      box.mockReturnValue({ top: 300 } as DOMRect);
      fireEvent(window, new Event("resize"));
      expect(grid.style.getPropertyValue("--inbox-height")).toBe("420px");
      Object.defineProperty(window, "scrollY", {
        configurable: true,
        value: 0,
      });
      box.mockReturnValue({ top: 400 } as DOMRect);
      fireEvent(window, new Event("resize"));
      expect(grid.style.getPropertyValue("--inbox-height")).toBe("420px");
    } finally {
      Object.defineProperty(window, "innerHeight", {
        configurable: true,
        value: previousHeight,
      });
      Object.defineProperty(window, "scrollY", {
        configurable: true,
        value: previousScroll,
      });
    }
  });

  it("operates and edits exact contact when the global snapshot fails; retains the draft after conflict", async () => {
    vi.mocked(clientsApi.workspace).mockRejectedValue(new ClientsError(503));
    render(<App />);
    await screen.findByLabelText("Nombre visible");
    const contact = vi.mocked(inboxApi.detail).mock.calls.at(-1)![0];
    change("Nombre visible", "Scoped contact");
    change("Programa de interés", "");
    vi.mocked(inboxApi.saveContact).mockRejectedValueOnce(
      new ClientsError(409),
    );
    fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
    await waitFor(() => expect(inboxApi.saveContact).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(screen.getByLabelText("Nombre visible")).toHaveValue(
        "Scoped contact",
      ),
    );
    expect(vi.mocked(inboxApi.saveContact).mock.calls[0][0]).toBe(contact);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Guardar ficha" }),
      ).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
    await screen.findByText("Ficha guardada correctamente.");
    await waitFor(() =>
      expect(screen.getByLabelText("Nombre visible")).toHaveValue(
        "Scoped contact",
      ),
    );
    const calls = vi.mocked(inboxApi.saveContact).mock.calls;
    expect((calls[0][1] as { operationId: string }).operationId).toBe(
      (calls[1][1] as { operationId: string }).operationId,
    );
  });
  it("debounces name, combines persisted filters and resets the server page", async () => {
    const original = vi.mocked(inboxApi.list).getMockImplementation()!;
    vi.mocked(inboxApi.list).mockImplementation(async (...args) => ({
      ...(await original(...args)),
      hasMore: true,
    }));
    const user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Nombre visible");
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await waitFor(() =>
      expect(vi.mocked(inboxApi.list).mock.calls.at(-1)![0].offset).toBe(25),
    );
    await user.click(screen.getByText("Más filtros"));
    change("Estado operativo", "Abierta");
    change("Vista rápida", "Humano");
    change("Asignación", "assigned");
    const before = vi.mocked(inboxApi.list).mock.calls.length;
    change("Buscar conversaciones", "absent");
    expect(inboxApi.list).toHaveBeenCalledTimes(before);
    await waitFor(() =>
      expect(vi.mocked(inboxApi.list).mock.calls.at(-1)![0]).toMatchObject({
        q: "absent",
        offset: 0,
        state: "open",
        mode: "human",
        assignment: "assigned",
      }),
    );
    await screen.findByText("Bandeja sin coincidencias");
  });
  it("ignores an older query even when its transport resolves after abort", async () => {
    const original = vi.mocked(inboxApi.list).getMockImplementation()!;
    let release!: (page: InboxPage) => void;
    let stale: InboxPage | undefined;
    vi.mocked(inboxApi.list).mockImplementation(async (...args) => {
      if (args[0].q === "slow") {
        stale = await original({ ...args[0], q: "" }, args[1]);
        return new Promise((resolve) => {
          release = resolve;
        });
      }
      return original(...args);
    });
    render(<App />);
    await screen.findByLabelText("Nombre visible");
    change("Buscar conversaciones", "slow");
    await waitFor(() => expect(release).toBeTypeOf("function"));
    change("Buscar conversaciones", "impossible");
    await screen.findByText("Bandeja sin coincidencias");
    await act(async () => release(stale!));
    expect(
      screen.queryByRole("button", { name: /Persona Demo A/ }),
    ).not.toBeInTheDocument();
  });
  it("shares contact drafts with Clientes and preserves message drafts across route changes", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByLabelText("Nombre visible");
    change("Nombre visible", "Shared draft");
    change("Borrador del mensaje", "Unsent body");
    await user.click(screen.getByRole("button", { name: "Ver Clientes" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Nombre visible")).toHaveValue(
        "Shared draft",
      ),
    );
    await user.click(screen.getByRole("link", { name: "Inbox" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Borrador del mensaje")).toHaveValue(
        "Unsent body",
      ),
    );
    expect(screen.getByLabelText("Nombre visible")).toHaveValue("Shared draft");
  });
});
