import { useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AgentVoiceSelect } from "../institution/AgentVoiceSelect";
import { AgentsPanel } from "../modules/agents/AgentsPanel";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
const response = (data: unknown) => new Response(JSON.stringify(data));
afterEach(() => vi.restoreAllMocks());

it("refreshes newly created voices without discarding an agent selection", async () => {
  let available = [{ id: "juampa", name: "Juampa · Admisiones", active: true }];
  const fetched = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () =>
      response({ profiles: available, schools: [] }),
    );
  function Form() {
    const [value, setValue] = useState("saved-unavailable");
    return <AgentVoiceSelect value={value} onChange={setValue} />;
  }
  render(<Form />);
  await screen.findByRole("option", { name: "Juampa · Admisiones" });
  expect(screen.getByLabelText("Perfil de voz para WhatsApp")).toHaveValue(
    "saved-unavailable",
  );
  available = [
    ...available,
    { id: "new", name: "Sarah · Salud", active: true },
  ];
  fireEvent.click(
    screen.getByRole("button", { name: "Actualizar voces disponibles" }),
  );
  await screen.findByRole("option", { name: "Sarah · Salud" });
  fireEvent.change(screen.getByLabelText("Perfil de voz para WhatsApp"), {
    target: { value: "new" },
  });
  expect(screen.getByLabelText("Perfil de voz para WhatsApp")).toHaveValue(
    "new",
  );
  expect(fetched.mock.calls.every(([, init]) => init?.method === "GET")).toBe(
    true,
  );
});

it("includes the chosen voice when creating an institutional agent", async () => {
  const catalog = {
    installed: true,
    institutional: true,
    agents: [],
    stages: [],
    sources: [],
    legacy_agents: [],
    counts: { total: 0, active: 0, programs: 0, pending_reviews: 0 },
    programs: { items: [], has_more: false, period: { id: 0, label: "CRM" } },
  };
  const fetched = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/voice/options"))
        return response({
          profiles: [
            { id: "juampa", name: "Juampa · Admisiones", active: true },
          ],
          schools: [],
        });
      if (init?.method === "PUT") return response({ confirmed: true });
      if (url.endsWith("/providers"))
        return response({
          current_provider: "gemini",
          providers: [
            {
              id: "gemini",
              configured: true,
              endpoint_ready: true,
              catalog_loaded: true,
              models: [
                { id: "saved-model", name: "Disponible", origin: "catalog" },
              ],
            },
          ],
        });
      return response(catalog);
    });
  render(<AgentsPanel />, { wrapper: WorkspaceSessionProvider });
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Crear agente personalizado" }),
    ).toBeEnabled(),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Crear agente personalizado" }),
  );
  await screen.findByRole("option", { name: "Juampa · Admisiones" });
  fireEvent.change(screen.getByLabelText("Nombre del agente"), {
    target: { value: "Agente de prueba" },
  });
  fireEvent.change(screen.getByLabelText("Modelo principal"), {
    target: { value: "saved-model" },
  });
  fireEvent.change(screen.getByLabelText("Instrucciones operativas"), {
    target: { value: "Orienta con datos revisados del programa." },
  });
  fireEvent.change(screen.getByLabelText("Perfil de voz para WhatsApp"), {
    target: { value: "juampa" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar configuración" }),
  );
  await waitFor(() =>
    expect(fetched.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(
      true,
    ),
  );
  const saved = fetched.mock.calls.find(([, init]) => init?.method === "PUT");
  expect(
    JSON.parse(String(saved?.[1]?.body)).configuration.voice_profile_id,
  ).toBe("juampa");
});
