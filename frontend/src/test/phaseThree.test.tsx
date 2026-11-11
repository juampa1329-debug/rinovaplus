import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { clientsApi, ClientsError } from "../modules/clients/api/clientsApi";
beforeEach(() => {
  window.location.hash = "/inbox";
});
describe("persistent local conversation", () => {
  it("confirms control/state on the server and blocks a closed composer", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: "Tomar control" }),
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Reservar para IA" }),
      ).toBeEnabled(),
    );
    fireEvent.change(screen.getByLabelText("Borrador del mensaje"), {
      target: { value: "Local message" },
    });
    await user.selectOptions(
      screen.getByLabelText("Estado del hilo local"),
      "Cerrada",
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Estado del hilo local")).toHaveValue(
        "Cerrada",
      ),
    );
    expect(
      screen.getByRole("button", { name: "Guardar mensaje" }),
    ).toBeDisabled();
    await user.selectOptions(
      screen.getByLabelText("Estado del hilo local"),
      "Abierta",
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Guardar mensaje" }),
      ).toBeEnabled(),
    );
    expect(clientsApi.conversation).toHaveBeenCalledTimes(3);
  });
  it("retains failed message draft across navigation and retries the same operation", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("button", { name: /Persona Demo B/ });
    await user.click(screen.getByRole("button", { name: /Persona Demo B/ }));
    await screen.findByLabelText("Borrador del mensaje");
    fireEvent.change(screen.getByLabelText("Borrador del mensaje"), {
      target: { value: "Keep until confirmed" },
    });
    vi.mocked(clientsApi.message).mockRejectedValueOnce(new ClientsError(0));
    await user.click(screen.getByRole("button", { name: "Guardar mensaje" }));
    expect(await screen.findByText(/No se pudo confirmar/)).toBeVisible();
    await user.click(screen.getByRole("link", { name: "Resumen" }));
    await user.click(screen.getByRole("link", { name: "Inbox" }));
    expect(await screen.findByLabelText("Borrador del mensaje")).toHaveValue(
      "Keep until confirmed",
    );
    await user.click(screen.getByRole("button", { name: "Guardar mensaje" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Borrador del mensaje")).toHaveValue(""),
    );
    expect(screen.getAllByText("Keep until confirmed").length).toBeGreaterThan(
      0,
    );
    const calls = vi.mocked(clientsApi.message).mock.calls;
    expect(calls[0][1]).toEqual(calls[1][1]);
  });
  it("preserves text typed while a save is in flight", async () => {
    render(<App />);
    fireEvent.click(
      await screen.findByRole("button", { name: /Persona Demo B/ }),
    );
    await screen.findByLabelText("Borrador del mensaje");
    let release!: () => void;
    const original = vi.mocked(clientsApi.message).getMockImplementation()!;
    vi.mocked(clientsApi.message).mockImplementation(async (...args) => {
      await new Promise<void>((resolve) => {
        release = resolve;
      });
      return original(...args);
    });
    fireEvent.change(screen.getByLabelText("Borrador del mensaje"), {
      target: { value: "Submitted" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar mensaje" }));
    fireEvent.change(screen.getByLabelText("Borrador del mensaje"), {
      target: { value: "New draft" },
    });
    release();
    await screen.findByText("Mensaje guardado correctamente.");
    expect(screen.getByLabelText("Borrador del mensaje")).toHaveValue(
      "New draft",
    );
  });
  it("uses stable directory assignment instead of a free-text label", async () => {
    render(<App />);
    await screen.findByLabelText("Responsable humano");
    expect(
      screen.queryByLabelText("Responsable local"),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText("Agente IA asignado")).toBeInTheDocument();
    expect(clientsApi.conversation).not.toHaveBeenCalled();
  });
  it("does not fabricate template responses, tasks or social comments", async () => {
    render(<App />);
    await screen.findByRole("button", { name: /Persona Demo A/ });
    expect(
      screen.queryByRole("button", { name: "Generar ejemplo local" }),
    ).not.toBeInTheDocument();
    expect(
      await screen.findByText("No hay tareas registradas en esta página."),
    ).toBeVisible();
    fireEvent.click(
      within(
        screen.getByRole("navigation", { name: "Subsecciones de Inbox" }),
      ).getByRole("button", { name: "Comentarios" }),
    );
    expect(
      screen.getByRole("heading", { name: "Comentarios no conectados" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Añadir respuesta local" }),
    ).not.toBeInTheDocument();
  });
});
