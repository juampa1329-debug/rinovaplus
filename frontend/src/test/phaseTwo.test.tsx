import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { clientsApi } from "../modules/clients/api/clientsApi";
describe("confirmed client data and temporary field definitions", () => {
  it("starts with no invented tag, custom field or probability", async () => {
    window.location.hash = "/clients";
    render(<App />);
    await screen.findByRole("button", { name: /Persona Demo A/ });
    fireEvent.click(
      screen.getByText("Configurar CRM local — etapas, etiquetas y campos"),
    );
    expect(
      screen.getByLabelText("Probabilidad configurada: Interés (%)"),
    ).toHaveValue(null);
    expect(
      screen.queryByLabelText("Correo de ejemplo"),
    ).not.toBeInTheDocument();
  });
  it("validates typed custom fields and preserves inactive saved values", async () => {
    const user = userEvent.setup();
    window.location.hash = "/clients";
    render(<App />);
    await screen.findByRole("button", { name: /Persona Demo A/ });
    await user.click(
      screen.getByText("Configurar CRM local — etapas, etiquetas y campos"),
    );
    fireEvent.change(screen.getByLabelText("Clave de nuevo campo"), {
      target: { value: "email" },
    });
    fireEvent.change(screen.getByLabelText("Nombre de nuevo campo"), {
      target: { value: "Correo" },
    });
    await user.selectOptions(
      screen.getByLabelText("Tipo de nuevo campo"),
      "Email",
    );
    await user.click(
      screen.getByRole("button", { name: "Añadir campo local" }),
    );
    fireEvent.change(screen.getByLabelText("Correo"), {
      target: { value: "invalid" },
    });
    await user.click(screen.getByRole("button", { name: "Guardar ficha" }));
    expect(screen.getByLabelText("Correo")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    fireEvent.change(screen.getByLabelText("Correo"), {
      target: { value: "contact@example.invalid" },
    });
    await user.click(screen.getByRole("button", { name: "Guardar ficha" }));
    await screen.findByText(/Ficha guardada correctamente./);
    await user.click(screen.getByRole("button", { name: "Desactivar Correo" }));
    fireEvent.click(
      screen.getByText("Valores de campos inactivos conservados"),
    );
    expect(screen.getByText("contact@example.invalid")).toBeVisible();
  });
  it("does not save drafts or store business records in browser storage", async () => {
    const storage = vi.spyOn(Storage.prototype, "setItem");
    window.location.hash = "/clients";
    render(<App />);
    await screen.findByRole("button", { name: /Persona Demo A/ });
    fireEvent.change(screen.getByLabelText("Notas internas"), {
      target: { value: "Draft only" },
    });
    expect(clientsApi.save).not.toHaveBeenCalled();
    expect(storage).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Notas internas")).not.toHaveValue(
        "Draft only",
      ),
    );
  });
});
