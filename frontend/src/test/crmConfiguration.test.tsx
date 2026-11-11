import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { crmConfigurationApi } from "../modules/crm-configuration/api/crmConfigurationApi";
import { ClientsError } from "../modules/clients/api/clientsApi";
import { validateCrmClient } from "../shared/crm";
import { seedClients } from "./legacyData";

describe("SQL CRM definitions and shared mini CRM", () => {
  it("opens and focuses configuration once from Inbox without losing the contact draft", async () => {
    window.location.hash = "/inbox";
    render(<App />);
    await screen.findByLabelText("Ciudad");
    fireEvent.change(screen.getByLabelText("Ciudad"), {
      target: { value: "Isolated city draft" },
    });
    await userEvent.click(
      screen.getByRole("button", {
        name: "Administrar etapas, etiquetas y campos",
      }),
    );
    const summary = await screen.findByText(
      "Configurar CRM local — etapas, etiquetas y campos",
    );
    await waitFor(() =>
      expect(summary.closest("details")).toHaveAttribute("open"),
    );
    expect(summary).toHaveFocus();
    expect(screen.getByLabelText("Ciudad")).toHaveValue("Isolated city draft");
    await userEvent.click(screen.getByRole("link", { name: "Inbox" }));
    await screen.findByLabelText("Ciudad");
    await userEvent.click(
      screen.getByRole("link", { name: "Clientes y prospectos" }),
    );
    await screen.findByLabelText("Ciudad");
    expect(
      screen
        .getByText("Configurar CRM local — etapas, etiquetas y campos")
        .closest("details"),
    ).not.toHaveAttribute("open");
  });
  it("confirms definitions through SQL API and reloads them across remount", async () => {
    window.location.hash = "/clients";
    const view = render(<App />);
    await screen.findByText("Revisión SQL: 1");
    fireEvent.click(
      screen.getByText("Configurar CRM local — etapas, etiquetas y campos"),
    );
    fireEvent.change(screen.getByLabelText("Clave de nuevo campo"), {
      target: { value: "delivery_note" },
    });
    fireEvent.change(screen.getByLabelText("Nombre de nuevo campo"), {
      target: { value: "Observación humana" },
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Añadir campo local" }),
    );
    await screen.findByText("Revisión SQL: 2");
    expect(crmConfigurationApi.save).toHaveBeenCalledWith(
      expect.objectContaining({
        fields: expect.arrayContaining([
          expect.objectContaining({
            key: "delivery_note",
            type: "Text",
            required: false,
          }),
        ]),
      }),
      "1",
      expect.any(String),
    );
    view.unmount();
    render(<App />);
    await screen.findByText("Revisión SQL: 2");
    fireEvent.click(
      screen.getByText("Configurar CRM local — etapas, etiquetas y campos"),
    );
    expect(screen.getByLabelText("Observación humana")).toBeInTheDocument();
    expect(screen.getByText(/Catálogo compartido en SQL/)).toBeInTheDocument();
  });

  it("retains the definition form when a concurrent revision is rejected", async () => {
    window.location.hash = "/clients";
    render(<App />);
    await screen.findByText("Revisión SQL: 1");
    fireEvent.click(
      screen.getByText("Configurar CRM local — etapas, etiquetas y campos"),
    );
    fireEvent.change(screen.getByLabelText("Clave de nueva etapa"), {
      target: { value: "reviewed" },
    });
    fireEvent.change(screen.getByLabelText("Nombre de nueva etapa"), {
      target: { value: "Revisión humana" },
    });
    vi.mocked(crmConfigurationApi.save).mockRejectedValueOnce(
      new ClientsError(409),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Añadir etapa local" }),
    );
    await screen.findByText(/Los datos cambiaron/);
    expect(screen.getByLabelText("Clave de nueva etapa")).toHaveValue(
      "reviewed",
    );
    expect(screen.getByLabelText("Nombre de nueva etapa")).toHaveValue(
      "Revisión humana",
    );
    expect(crmConfigurationApi.read).toHaveBeenCalledTimes(2);
    await userEvent.click(
      screen.getByRole("button", { name: "Añadir etapa local" }),
    );
    await waitFor(() =>
      expect(screen.getByLabelText("Clave de nueva etapa")).toHaveValue(""),
    );
    expect(
      screen.getByLabelText("Probabilidad configurada: Revisión humana (%)"),
    ).toHaveValue(null);
  });

  it("validates required fields and retains inactive stage and tags only on their original contact", () => {
    const client = seedClients()[0];
    const config = {
      stages: [
        {
          key: "retained",
          label: client.stage,
          probability: null,
          active: false,
        },
      ],
      tags: [client.tags],
      inactiveTags: [client.tags],
      fields: [
        {
          key: "required",
          label: "Dato",
          type: "Text" as const,
          options: [],
          active: true,
          required: true,
        },
      ],
    };
    expect(
      validateCrmClient(
        { ...client, customValues: { required: " " } },
        config,
        client,
      ).required,
    ).toBeTruthy();
    const completed = {
      ...client,
      customValues: { required: "Real value in isolated unit test" },
    };
    expect(validateCrmClient(completed, config, client)).toEqual({});
    expect(validateCrmClient(completed, config).stage).toBeTruthy();
  });
});
