import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AgentsPanel } from "../modules/agents/AgentsPanel";
import * as transport from "../modules/agents/api";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";

afterEach(() => vi.restoreAllMocks());

it("keeps a successful model response when only the activity refresh fails and never generates twice", async () => {
  let generated = 0;
  const config = {
    ...transport.blankConfiguration(),
    provider: "gemini",
    instructions: "Orienta con datos revisados",
    primary_model: "saved-model",
  };
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    Response.json({ profiles: [], schools: [] }),
  );
  const request = vi.spyOn(transport, "api").mockImplementation(async function <
    T,
  >(path = "") {
    let result: unknown;
    if (path === "/simulate") {
      generated++;
      result = {
        text: "Respuesta real conservada",
        handoff: false,
        sources: [],
        network_called: true,
      };
    } else if (path.endsWith("/console")) {
      if (generated) throw Error("Activity temporarily unavailable");
      result = {
        installed: true,
        metrics: null,
        runs: [],
        notes: [],
        actions: [],
        versions: [],
      };
    } else if (path === "/providers")
      result = { providers: [], current_provider: "gemini" };
    else if (path === "/sales/skills") result = { items: [] };
    else
      result = {
        installed: true,
        agents: [
          {
            id: "guide",
            name: "Guía",
            level: "guide",
            state: "active",
            enabled: true,
            version: 1,
            revision: 1,
            parent_id: null,
            program_id: null,
            stage_id: null,
            configuration: config,
          },
        ],
        counts: {},
        programs: { items: [] },
        stages: [],
        sources: [],
        legacy_agents: [],
      };
    return result as T;
  });
  render(<AgentsPanel />, { wrapper: WorkspaceSessionProvider });
  await screen.findByRole("button", { name: "Simulador" });
  fireEvent.click(screen.getByRole("button", { name: "Simulador" }));
  fireEvent.change(screen.getByLabelText("Mensaje de prueba"), {
    target: { value: "Información del programa" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Probar respuesta" }));
  await screen.findByText("Respuesta real conservada");
  await screen.findByText(/La prueba terminó y su resultado se conserva/);
  expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  await waitFor(() =>
    expect(
      request.mock.calls.filter(([path]) => path === "/simulate"),
    ).toHaveLength(1),
  );
  expect(generated).toBe(1);
});
