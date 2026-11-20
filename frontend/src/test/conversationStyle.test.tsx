import {
  render,
  screen,
  fireEvent,
  cleanup,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useState } from "react";
import { CBNConversationPreset } from "../institution/CBNConversationPreset";
import { ProgramSalesSetup } from "../institution/ProgramSalesSetup";
import { AgentConfigurationExtras } from "../modules/agents/AgentConfigurationExtras";
import {
  blankConfiguration,
  type Agent,
  type Catalog,
} from "../modules/agents/api";

const mocks = vi.hoisted(() => ({ call: vi.fn(), agents: vi.fn() }));
vi.mock("../institution/api", async (original) => ({
  ...(await original<typeof import("../institution/api")>()),
  useInstitution: () => ({
    call: mocks.call,
    session: { actions: ["settings.ai.write"] },
  }),
}));
vi.mock("../modules/agents/api", async (original) => ({
  ...(await original<typeof import("../modules/agents/api")>()),
  api: mocks.agents,
}));
afterEach(cleanup);
beforeEach(() => {
  mocks.call.mockReset();
  mocks.agents.mockReset();
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
});

it("prepares a reviewed institutional draft without saving or changing the model and voice", async () => {
  mocks.call.mockResolvedValue({
    document: {
      system_prompt: "Prompt CBN revisado",
      wait_seconds: 3,
      chars_per_message: 350,
    },
    reviewed_at: "2026-11-19",
    sources: [],
  });
  function Editor() {
    const [draft, setDraft] = useState({
      model: "saved-model",
      voice: "Juampa",
      system_prompt: "Anterior",
      wait_seconds: 0,
    });
    return (
      <>
        <CBNConversationPreset
          disabled={false}
          apply={(value) => setDraft((old) => ({ ...old, ...value }))}
        />
        <output>{JSON.stringify(draft)}</output>
      </>
    );
  }
  render(<Editor />);
  fireEvent.click(
    screen.getByRole("button", { name: "Preparar prompt y cadencia CBN" }),
  );
  await screen.findByRole("alertdialog", {
    name: "Preparar el estilo institucional",
  });
  expect(screen.getByText(/"model":"saved-model"/)).toHaveTextContent(
    '"system_prompt":"Anterior"',
  );
  fireEvent.click(screen.getByRole("button", { name: "Usar en el borrador" }));
  expect(screen.getByText(/"model":"saved-model"/)).toHaveTextContent(
    '"voice":"Juampa"',
  );
  expect(screen.getByText(/"model":"saved-model"/)).toHaveTextContent(
    '"system_prompt":"Prompt CBN revisado"',
  );
  expect(mocks.call).toHaveBeenCalledWith("settings/ai/cbn-style");
  expect(mocks.call).toHaveBeenCalledTimes(1);
});

it("does not prepare changes for a read-only user", () => {
  render(<CBNConversationPreset disabled apply={() => {}} />);
  expect(
    screen.getByRole("button", { name: "Preparar prompt y cadencia CBN" }),
  ).toBeDisabled();
});

it("changes the presentation name independently from the selected voice", () => {
  function Editor() {
    const [configuration, set] = useState({
      ...blankConfiguration(),
      advisor_name: "Juan",
      voice_profile_id: "juampa",
    });
    return (
      <>
        <AgentConfigurationExtras
          draft={{ configuration, version: 1 } as unknown as Agent}
          configure={(value) => set((old) => ({ ...old, ...value }))}
          versions={[]}
        />
        <output>
          {configuration.advisor_name}:{configuration.voice_profile_id}
        </output>
      </>
    );
  }
  render(<Editor />);
  fireEvent.change(screen.getByLabelText("Nombre de atención"), {
    target: { value: "María" },
  });
  expect(screen.getByText("María:juampa")).toBeVisible();
});

it("reviews existing prompts and submits only the style operation", async () => {
  const catalog = {
    agents: [
      { id: "guide", name: "Admisiones", level: "guide", state: "active" },
    ],
    programs: { items: [] },
  } as unknown as Catalog;
  mocks.agents.mockImplementation(async (path) =>
    path.includes("preview")
      ? {
          mode: "style",
          guide_id: "guide",
          guide_name: "Admisiones",
          digest: "d".repeat(64),
          provider: "gemini",
          model: "saved-model",
          guide_changes: ["tono CBN"],
          items: [
            {
              program_id: 1,
              agent_id: "specialist",
              name: "Software",
              school: "TIC",
              schedule: "Diurna",
              action: "update",
              system_prompt: "Eres Juan, atención CBN",
              missing: [],
              price_pending: true,
            },
          ],
        }
      : { updated: 1, preserved: 0 },
  );
  render(
    <ProgramSalesSetup
      catalog={catalog}
      disabled={false}
      onSaved={async () => {}}
    />,
  );
  fireEvent.click(
    screen.getByText("Especialistas por programa y origen de anuncios"),
  );
  fireEvent.change(screen.getByLabelText("Orientador de Admisiones"), {
    target: { value: "guide" },
  });
  fireEvent.click(
    screen.getByRole("button", {
      name: "Revisar actualización de prompts y tono CBN",
    }),
  );
  await screen.findByText("Actualizar prompt generado");
  const update = screen.getByRole("button", {
    name: "Actualizar prompts revisados",
  });
  expect(update).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox", { name: /Revisé los prompts/ }));
  fireEvent.click(update);
  await waitFor(() =>
    expect(mocks.agents).toHaveBeenCalledWith(
      "/sales/style",
      "POST",
      expect.objectContaining({
        guide_id: "guide",
        confirmed: true,
        preview_digest: "d".repeat(64),
      }),
    ),
  );
  expect(
    mocks.agents.mock.calls.every(
      ([path]) => !String(path).includes("provision"),
    ),
  ).toBe(true);
});
