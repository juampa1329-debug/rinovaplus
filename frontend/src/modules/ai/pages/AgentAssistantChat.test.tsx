import { useState } from "react";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  api,
  blankConfiguration,
  type Agent,
  type Catalog,
} from "../../agents/api";
import { AssistantChat } from "./AgentAssistantChat";

vi.mock("../../agents/api", async (original) => ({
  ...(await original<typeof import("../../agents/api")>()),
  api: vi.fn(),
}));
vi.mock("./AssistantChat", () => ({
  AssistantChat: ({ active }: { active: boolean }) => {
    const [draft, setDraft] = useState("");
    return active ? (
      <input
        aria-label="Generic draft"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
      />
    ) : null;
  },
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function setup(state = "active") {
  const agent: Agent = {
    id: crypto.randomUUID(),
    name: "Synthetic advisor",
    level: "guide",
    parent_id: null,
    program_id: null,
    stage_id: null,
    state,
    version: 2,
    revision: 3,
    approved_version: null,
    configuration: {
      ...blankConfiguration(),
      provider: "gemini",
      primary_model: "profile-model",
      monthly_token_limit: 10000,
      channels: ["local"],
    },
  };
  const catalog = { agents: [agent] } as Catalog;
  const requests: Record<string, unknown>[] = [];
  vi.mocked(api).mockImplementation(async (path, _method, body) => {
    if (!path) return structuredClone(catalog);
    requests.push(body as Record<string, unknown>);
    return {
      agent_id: agent.id,
      config_version: agent.version,
      text: "Synthetic response",
      model: "profile-model",
      sources: [],
      handoff: true,
    };
  });
  return { agent, catalog, requests };
}

async function select(agent: Agent) {
  await waitFor(() =>
    expect(
      screen.getByLabelText("Asistente para conversar"),
    ).not.toBeDisabled(),
  );
  fireEvent.change(screen.getByLabelText("Asistente para conversar"), {
    target: { value: agent.id },
  });
}

it("shows archived profile and blocks generation without silently using generic", async () => {
  const { agent, requests } = setup("archived");
  render(<AssistantChat active />);
  await select(agent);
  expect(
    screen.getByText(/Este agente está pausado, archivado/),
  ).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Mensaje para el agente"), {
    target: { value: "Hello" },
  });
  expect(screen.getByRole("button", { name: "Enviar mensaje" })).toBeDisabled();
  expect(
    screen.getByRole("link", { name: "Configurar o restaurar en Mis agentes" }),
  ).toHaveAttribute("href", "#/agents");
  expect(requests).toHaveLength(0);
  expect(screen.queryByLabelText("Generic draft")).not.toBeInTheDocument();
});

it("uses profile version and bounded previous turns while preserving generic draft", async () => {
  const { agent, requests } = setup();
  render(<AssistantChat active />);
  fireEvent.change(screen.getByLabelText("Generic draft"), {
    target: { value: "Retained generic draft" },
  });
  await select(agent);
  const send = async (text: string) => {
    fireEvent.change(screen.getByLabelText("Mensaje para el agente"), {
      target: { value: text },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar mensaje" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Mensaje para el agente")).toHaveValue(""),
    );
  };
  await send("First turn");
  await send("Second turn");
  expect(requests[1]).toMatchObject({
    agent_id: agent.id,
    config_version: 2,
    channel: "local",
    call_provider: true,
    acknowledge_consumption: true,
    history: [
      { role: "user", content: "First turn" },
      { role: "assistant", content: "Synthetic response" },
    ],
  });
  fireEvent.change(screen.getByLabelText("Asistente para conversar"), {
    target: { value: "" },
  });
  expect(screen.getByLabelText("Generic draft")).toHaveValue(
    "Retained generic draft",
  );
  await select(agent);
  expect(screen.queryByText("First turn")).not.toBeInTheDocument();
});

it("discards a pending response when switching profiles", async () => {
  const { agent } = setup();
  let finish: (value: unknown) => void = () => {};
  const base = vi.mocked(api).getMockImplementation()!;
  vi.mocked(api).mockImplementation((path, method, body) =>
    path === "/simulate"
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : base(path, method, body),
  );
  render(<AssistantChat active />);
  await select(agent);
  fireEvent.change(screen.getByLabelText("Mensaje para el agente"), {
    target: { value: "Pending" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Enviar mensaje" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Esperando respuesta…" }),
    ).toBeDisabled(),
  );
  await waitFor(() =>
    expect(
      vi.mocked(api).mock.calls.some(([path]) => path === "/simulate"),
    ).toBe(true),
  );
  fireEvent.change(screen.getByLabelText("Asistente para conversar"), {
    target: { value: "" },
  });
  await act(async () => {
    finish({
      agent_id: agent.id,
      config_version: 2,
      text: "Stale answer",
      model: "profile-model",
      sources: [],
    });
  });
  expect(screen.queryByText("Stale answer")).not.toBeInTheDocument();
});
