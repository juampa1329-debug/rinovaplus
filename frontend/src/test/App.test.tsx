import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { clientsApi, ClientsError } from "../modules/clients/api/clientsApi";
import { modules } from "../shared/navigation";

describe("local SQL application shell", () => {
  it("renders an actually empty workspace without synthetic fallback or reset", async () => {
    vi.mocked(clientsApi.workspace).mockResolvedValue({
      clients: [],
      threads: [],
      revision: "0",
    });
    window.location.hash = "/overview";
    render(<App />);
    await waitFor(() =>
      expect(
        screen.queryByText("Cargando información…"),
      ).not.toBeInTheDocument(),
    );
    expect(
      screen.getByLabelText("Resumen de datos confirmados"),
    ).toHaveTextContent("0");
    expect(screen.queryByText(/Persona Demo/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Restablecer demo" }),
    ).not.toBeInTheDocument();
    expect(document.title).toBe("Resumen de admisiones · CRM CBN");
  });
  it("does not present zero business totals when SQL loading fails", async () => {
    vi.mocked(clientsApi.workspace).mockRejectedValue(new ClientsError(503));
    window.location.hash = "/overview";
    render(<App />);
    await screen.findByRole("button", { name: "Reintentar carga de clientes" });
    expect(
      screen.queryByLabelText("Resumen de datos confirmados"),
    ).not.toBeInTheDocument();
  });
  it("keeps every navigation route and unknown-route recovery", async () => {
    const user = userEvent.setup();
    window.location.hash = "/overview";
    render(<App />);
    await user.click(screen.getByText("Otros módulos"));
    for (const module of modules)
      expect(screen.getByRole("link", { name: module.label })).toHaveAttribute(
        "href",
        `#/${module.path}`,
      );
    window.location.hash = "/missing";
    fireEvent(window, new HashChangeEvent("hashchange"));
    expect(
      await screen.findByRole("button", { name: "Volver al resumen" }),
    ).toBeVisible();
  });
  it("keeps accessible theme controls and collapsible navigation", async () => {
    const user = userEvent.setup();
    window.location.hash = "/overview";
    render(<App />);
    const theme = screen.getByRole("button", { name: /Cambiar a modo/ });
    const nextMode = theme.getAttribute("aria-label")!.includes("oscuro")
      ? "dark"
      : "light";
    await user.click(theme);
    expect(document.documentElement.dataset.theme).toBe(nextMode);
    expect(theme).toHaveAccessibleName(
      nextMode === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro",
    );
    await user.click(
      screen.getByRole("button", { name: "Abrir menú CRM CBN" }),
    );
    expect(
      screen
        .getAllByRole("button", { name: "Cerrar menú CRM CBN" })
        .find((button) => button.classList.contains("mobile-logo-toggle")),
    ).toHaveAttribute("aria-expanded", "true");
  });
  it("keeps all seven settings sections without inventing a user", async () => {
    const user = userEvent.setup();
    window.location.hash = "/settings";
    render(<App />);
    for (const name of [
      "IA",
      "Canales",
      "APIs",
      "Diagnóstico",
      "Usuarios",
      "Perfil",
      "Seguridad",
    ])
      expect(screen.getByRole("button", { name })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Usuarios" }));
    expect(
      screen.getByRole("heading", { name: "Identidad pendiente" }),
    ).toBeVisible();
    expect(screen.queryByText("Operador Demo")).not.toBeInTheDocument();
  });
});
