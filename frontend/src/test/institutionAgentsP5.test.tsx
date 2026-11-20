import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AssistantChat } from "../modules/ai/pages/AgentAssistantChat";
import { AgentConversationPanel } from "../modules/agents/AgentConversationPanel";
import { blankConfiguration } from "../modules/agents/api";
import { bindInstitutionSession } from "../shared/institutionSession";
import { api } from "../modules/agents/api";

afterEach(() => {
  vi.restoreAllMocks();
  bindInstitutionSession("");
});
const ok = (v: unknown) =>
  new Response(JSON.stringify(v), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
const catalog = {
  installed: true,
  agents: [
    {
      id: "chosen",
      name: "Guía guardada",
      state: "active",
      enabled: true,
      level: "guide",
      version: 2,
      revision: 3,
      parent_id: null,
      configuration: {
        ...blankConfiguration(),
        primary_model: "saved-model",
        channels: ["local"],
        monthly_token_limit: 100000,
      },
    },
  ],
  stages: [],
  programs: {
    items: [],
    has_more: false,
    period: { id: 0, label: "Declarado" },
  },
  sources: [],
  legacy_agents: [],
};
it("institutional assistant requires a selected saved profile", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(ok(catalog));
  render(<AssistantChat active selectedOnly />);
  await screen.findByRole("option", { name: /Guía guardada/ });
  expect(
    screen.queryByRole("option", { name: /Asistente general/ }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByLabelText("Mensaje para el agente"),
  ).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Asistente para conversar"), {
    target: { value: "chosen" },
  });
  expect(screen.getByLabelText("Mensaje para el agente")).toBeInTheDocument();
});
it("agent transport preserves institutional CSRF and expires unauthorized session", async () => {
  const expired = vi.fn();
  bindInstitutionSession("csrf-test", expired);
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "session_required" }), {
      status: 401,
    }),
  );
  await expect(
    api("/simulate", "POST", { request_id: "owned" }),
  ).rejects.toThrow();
  expect(
    new Headers(fetcher.mock.calls[0][1]?.headers).get("X-CSRF-Token"),
  ).toBe("csrf-test");
  expect(expired).toHaveBeenCalledOnce();
});
it("read-only Inbox uses the reduced selection contract and disables assignment", async () => {
  const requests: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    requests.push(String(url));
    return ok(
      String(url).endsWith("/selection")
        ? catalog
        : {
            mode: "human",
            revision: 1,
            contexts: [],
            context_id: null,
            selection: null,
            blocked: "agents_human_control",
          },
    );
  });
  render(
    <AgentConversationPanel
      institutional
      canWrite={false}
      conversationId="conversation"
      refresh={0}
      onConfirmed={() => {}}
    />,
  );
  await screen.findByLabelText("Modalidad de atención");
  expect(screen.getByLabelText("Modalidad de atención")).toBeDisabled();
  expect(requests).toContain("/api/v1/agents/selection");
  expect(requests).not.toContain("/api/v1/agents");
  expect(
    screen.queryByLabelText("Identificador de la solicitud SIIE"),
  ).not.toBeInTheDocument();
});
it("paused institutional profile cannot consume AI", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    ok({
      ...catalog,
      agents: [{ ...catalog.agents[0], state: "paused", enabled: false }],
    }),
  );
  render(<AssistantChat active selectedOnly />);
  await screen.findByRole("option", { name: /Guía guardada/ });
  fireEvent.change(screen.getByLabelText("Asistente para conversar"), {
    target: { value: "chosen" },
  });
  fireEvent.change(screen.getByLabelText("Mensaje para el agente"), {
    target: { value: "Hola" },
  });
  expect(screen.getByRole("button", { name: "Enviar mensaje" })).toBeDisabled();
  await waitFor(() =>
    expect(
      fetcher.mock.calls.every(([, o]) => !o?.method || o.method === "GET"),
    ).toBe(true),
  );
});

it("live context refresh updates the selected specialist without discarding an assignment draft", async () => {
  let version = 1;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    ok(
      String(url).endsWith("/selection")
        ? catalog
        : {
            mode: "automatic",
            revision: version,
            contexts: [],
            context_id: null,
            selection: {
              agent_id: "chosen",
              supervisor_id: null,
              reason: "commercial_interest",
              version,
            },
            blocked: null,
          },
    ),
  );
  const view = render(
    <AgentConversationPanel
      institutional
      conversationId="live-refresh-test"
      refresh="one"
      onConfirmed={() => {}}
    />,
  );
  await screen.findByText(/versión 1\./);
  fireEvent.change(screen.getByLabelText("Modalidad de atención"), {
    target: { value: "manual" },
  });
  fireEvent.change(screen.getByLabelText("Motivo y evidencia de la decisión"), {
    target: { value: "Borrador sin confirmar" },
  });
  version = 2;
  view.rerender(
    <AgentConversationPanel
      institutional
      conversationId="live-refresh-test"
      refresh="two"
      onConfirmed={() => {}}
    />,
  );
  await screen.findByText(/versión 2\./);
  expect(screen.getByLabelText("Modalidad de atención")).toHaveValue("manual");
  expect(
    screen.getByLabelText("Motivo y evidencia de la decisión"),
  ).toHaveValue("Borrador sin confirmar");
});
