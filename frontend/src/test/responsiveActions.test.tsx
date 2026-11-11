import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AgentsPanel } from "../modules/agents/AgentsPanel";
import * as agentsApi from "../modules/agents/api";
import { Clients } from "../modules/clients/pages/Clients";
import { OverviewQueue } from "../features/Overview";
import { seedCrmConfig } from "../shared/crm";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import { seedClients, seedThreads } from "./legacyData";

describe("Responsive create actions", () => {
  it("focuses the first invalid field after submit without saving or stealing subsequent typing", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <WorkspaceSessionProvider>
        <Clients
          clients={seedClients()}
          threads={seedThreads()}
          config={seedCrmConfig()}
          onSave={onSave}
          onInbox={vi.fn()}
          onConfigChange={vi.fn()}
          openRequest={0}
          ready
          busy={false}
          serverRevision="qa"
        />
      </WorkspaceSessionProvider>,
    );
    await user.click(screen.getByRole("button", { name: "Nuevo" }));
    await user.click(screen.getByRole("button", { name: "Crear ficha" }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Nombre visible")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByLabelText("Nombre visible")).toHaveFocus();
    await user.click(screen.getByLabelText("Teléfono"));
    await user.keyboard("QA-001");
    expect(screen.getByLabelText("Teléfono")).toHaveFocus();
    expect(onSave).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Crear ficha" }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Etapa")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(screen.getByLabelText("Etapa")).toHaveAccessibleDescription(
      "Seleccione una etapa configurada.",
    );
    expect(screen.getByLabelText("Etapa")).toHaveFocus();
  });

  it("focuses the agent name only after explicit creation, including a repeated action", async () => {
    vi.spyOn(agentsApi, "api")
      .mockResolvedValueOnce({
        installed: true,
        agents: [],
        stages: [],
        sources: [],
        counts: {},
        legacy_agents: [],
        programs: {
          items: [],
          has_more: false,
          period: { id: 1, label: "QA" },
        },
      } satisfies agentsApi.Catalog)
      .mockResolvedValueOnce({
        current_provider: "openrouter",
        credential_revision: 0,
        network_called: false,
        providers: [],
      } satisfies agentsApi.ProviderOptions);
    const user = userEvent.setup();
    render(<AgentsPanel />, { wrapper: WorkspaceSessionProvider });
    const create = await screen.findByRole("button", {
      name: "Crear agente personalizado",
    });
    await user.click(create);
    expect(screen.getByLabelText("Nombre del agente")).toHaveFocus();
    await user.click(screen.getByLabelText("Instrucciones operativas"));
    await user.keyboard("QA instructions");
    expect(screen.getByLabelText("Instrucciones operativas")).toHaveFocus();
    await user.click(create);
    expect(screen.getByLabelText("Nombre del agente")).toHaveFocus();
  });

  it("focuses a new client's name and reopens the existing draft without stealing field focus", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceSessionProvider>
        <Clients
          clients={seedClients()}
          threads={seedThreads()}
          config={seedCrmConfig()}
          onSave={vi.fn()}
          onInbox={vi.fn()}
          onConfigChange={vi.fn()}
          openRequest={0}
          ready
          busy={false}
          serverRevision="qa"
        />
      </WorkspaceSessionProvider>,
    );
    const create = screen.getByRole("button", { name: "Nuevo" });
    await user.click(create);
    expect(screen.getByLabelText("Nombre visible")).toHaveFocus();
    await user.keyboard("QA responsive draft");
    await user.click(screen.getByLabelText("Teléfono"));
    await user.keyboard("QA-001");
    expect(screen.getByLabelText("Teléfono")).toHaveFocus();
    await user.click(create);
    expect(screen.getByLabelText("Nombre visible")).toHaveFocus();
    expect(screen.getByLabelText("Nombre visible")).toHaveValue(
      "QA responsive draft",
    );
  });
});

describe("Overview queue avatar", () => {
  it("shows a single initial for a long name while retaining the adjacent full name", () => {
    const client = { ...seedClients()[0], name: "  Carla    admisiones" };
    const { container } = render(
      <OverviewQueue
        clients={[client]}
        threads={[{ ...seedThreads()[0], clientId: client.id }]}
        onOpen={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );
    expect(container.querySelector(".avatar")).toHaveTextContent(/^C$/);
    expect(screen.getByText("Carla admisiones")).toBeVisible();
  });
});
