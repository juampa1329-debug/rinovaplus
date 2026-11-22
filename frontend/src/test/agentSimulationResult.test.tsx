import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AgentsPanel } from "../modules/agents/AgentsPanel";
import * as transport from "../modules/agents/api";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";

afterEach(() => vi.restoreAllMocks());
vi.mock("../institution/LiveModelSelect", () => ({
  LiveModelSelect: ({
    label,
    onChange,
  }: {
    label: string;
    onChange: (model: string) => void;
  }) => (
    <select
      aria-label={label}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">Seleccionar</option>
      <option value="google/fixture:free">Modelo gratuito</option>
    </select>
  ),
}));

it.each([false, true])(
  "keeps a successful response when only activity refresh fails; isolated route %s never edits the agent",
  async (override) => {
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
    const request = vi
      .spyOn(transport, "api")
      .mockImplementation(async function <T>(path = "") {
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
          result = {
            providers: [{ id: "openrouter", configured: true, models: [] }],
            current_provider: "gemini",
          };
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
    fireEvent.change(screen.getByLabelText("Historial ficticio de la prueba"), {
      target: {
        value:
          "Cliente: Soy Alex y quiero emprender.\nAsesor: Podemos orientarte.",
      },
    });
    if (override) {
      fireEvent.change(screen.getByLabelText("Skills completas para esta prueba"), {
        target: { value: "negotiation" },
      });
      fireEvent.change(screen.getByLabelText("Proveedor para esta prueba"), {
        target: { value: "openrouter" },
      });
      expect(
        screen.getByRole("button", { name: "Probar respuesta" }),
      ).toBeDisabled();
      fireEvent.change(screen.getByLabelText("Modelo para esta prueba"), {
        target: { value: "google/fixture:free" },
      });
      fireEvent.change(screen.getByLabelText("Límite de salida de esta prueba"), {
        target: { value: "2000" },
      });
    }
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
    const sent = request.mock.calls.find(
      ([path]) => path === "/simulate",
    )?.[2] as Record<string, unknown>;
    expect(sent.provider_override).toBe(override ? "openrouter" : undefined);
    expect(sent.output_tokens_override).toBe(override ? 2000 : undefined);
    expect(sent.skill_focus).toBe(override ? "negotiation" : undefined);
    expect(sent.model_override).toBe(
      override ? "google/fixture:free" : undefined,
    );
    expect(sent.history).toEqual([
      { role: "user", content: "Soy Alex y quiero emprender." },
      { role: "assistant", content: "Podemos orientarte." },
    ]);
    expect(
      request.mock.calls.filter(([, method]) => method === "PUT"),
    ).toHaveLength(0);
  },
);
