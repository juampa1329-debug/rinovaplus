import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { clientsApi } from "../modules/clients/api/clientsApi";
describe("review connected scope", () => {
  it("shows unavailable academic integration without seeded applicants or fake confirmation", async () => {
    vi.mocked(clientsApi.workspace).mockResolvedValue({
      clients: [],
      threads: [],
      revision: "0",
    });
    window.location.hash = "/review";
    render(<App />);
    expect(
      await screen.findByRole("heading", {
        name: "Integración académica pendiente",
      }),
    ).toBeVisible();
    expect(screen.queryByText(/Aspirante Demo/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: /Confirmar|Registrar|Validar formulario/,
      }),
    ).not.toBeInTheDocument();
    expect(clientsApi.save).not.toHaveBeenCalled();
  });
});
