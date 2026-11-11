import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
describe("actual local diagnostics", () => {
  it("shows the returned process mode without invented provider metrics", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "alive", mode: "local_sql_copy" }),
      }),
    );
    window.location.hash = "/settings";
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Diagnóstico" }));
    expect(await screen.findByText("Servicio disponible")).toBeVisible();
    expect(
      screen.queryByText(/Fixture|Proveedor no disponible/),
    ).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });
  it("reports unavailable health without replacing it with a stable scenario", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("private")));
    window.location.hash = "/settings";
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Diagnóstico" }));
    expect(
      await screen.findByText("No se pudo comprobar el estado."),
    ).toBeVisible();
    expect(screen.queryByText("private")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
