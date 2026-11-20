import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { AgentsPanel } from "./AgentsPanel";
import { WorkspaceSessionProvider } from "../../shared/workspaceSession";
import { AgentConversationPanel } from "./AgentConversationPanel";
import { ProgramSelector, filterPrograms } from "./ProgramSelector";
import { api, message } from "./api";
import type { Catalog, Program, ProviderOptions } from "./api";

const programs: Program[] = [
  {
    program_id: 1,
    name: "Program one",
    school_id: 10,
    school: "School one",
    schedule_id: 1,
    schedule: "Morning",
  },
  {
    program_id: 2,
    name: "Program two",
    school_id: 10,
    school: "School one",
    schedule_id: 2,
    schedule: "Evening",
  },
  {
    program_id: 3,
    name: "Program three",
    school_id: 20,
    school: "School two",
    schedule_id: 2,
    schedule: "Evening",
  },
];
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it.each([
  ["provider_response_timeout", "tardó demasiado"],
  ["provider_temporary_failure", "temporalmente indisponible"],
  ["provider_rate_limited", "límite temporal"],
  ["provider_timeout_or_network", "conexión"],
  ["admissions_context_limit", "un programa concreto"],
])(
  "explains the provider failure %s without blaming the prompt",
  (code, reason) => {
    expect(message(code)).toContain(reason);
    expect(message(code)).not.toContain("No se pudo completar la operación.");
  },
);

it.each([
  {
    fields: ["operation_id"],
    expected: "Revise estos campos: Identificador de operación.",
  },
  {
    fields: ["configuration.max_tokens", "name"],
    expected: "Revise estos campos: Máximo de tokens de salida, Nombre.",
  },
  {
    fields: ["untrusted_field_name", "constructor", "__proto__", 12],
    expected: "Revise los campos y límites del formulario.",
  },
])(
  "shows sanitized validation labels for $fields",
  async ({ fields, expected }) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 422,
        json: async () => ({
          code: "invalid_request",
          fields,
          input: "do not echo",
          msg: "do not echo",
        }),
      })),
    );
    await expect(
      api("/profiles/" + crypto.randomUUID(), "PUT", {}),
    ).rejects.toThrow(expected);
  },
);

it("does not carry an unconfirmed program into another conversation", async () => {
  const catalog = {
    installed: true,
    agents: [],
    stages: [],
    sources: [],
    counts: {},
    legacy_agents: [],
    programs: {
      items: programs,
      has_more: false,
      period: { id: 1, label: "Synthetic period" },
    },
  };
  const detail = {
    mode: "automatic",
    context_id: null,
    revision: 0,
    reason: "",
    contexts: [],
    blocked: null,
    selection: null,
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: true,
      status: 200,
      json: async () => (url.includes("/conversations/") ? detail : catalog),
    })),
  );
  const view = render(
    <AgentConversationPanel
      conversationId="first"
      refresh={0}
      onConfirmed={() => {}}
    />,
  );
  await screen.findByLabelText("Programa confirmado");
  fireEvent.change(screen.getByLabelText("Programa confirmado"), {
    target: { value: "2" },
  });
  expect(screen.getByLabelText("Programa confirmado")).toHaveValue("2");
  view.rerender(
    <AgentConversationPanel
      conversationId="second"
      refresh={0}
      onConfirmed={() => {}}
    />,
  );
  await screen.findByLabelText("Programa confirmado");
  expect(screen.getByLabelText("Programa confirmado")).toHaveValue("");
});

describe("Program dimensions", () => {
  it("combines school and schedule without changing the source catalog", () => {
    expect(
      filterPrograms(programs, "10", "2").map((p) => p.program_id),
    ).toEqual([2]);
    expect(programs).toHaveLength(3);
  });
  it("retains a valid selection and clears one excluded by a changed filter", () => {
    const changed = vi.fn();
    function Example() {
      const [value, setValue] = useState("2");
      return (
        <ProgramSelector
          id="program"
          label="Program"
          programs={programs}
          value={value}
          onChange={(v) => {
            changed(v);
            setValue(v);
          }}
        />
      );
    }
    render(<Example />);
    fireEvent.change(screen.getByLabelText("Escuela"), {
      target: { value: "10" },
    });
    expect(screen.getByLabelText("Program")).toHaveValue("2");
    expect(changed).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Jornada"), {
      target: { value: "1" },
    });
    expect(screen.getByLabelText("Program")).toHaveValue("");
    expect(
      within(screen.getByLabelText("Program")).getAllByRole("option"),
    ).toHaveLength(2);
    expect(changed).toHaveBeenCalledWith("");
  });
});

it("selects configured providers and their models while keeping a root supervisor optional", async () => {
  const catalog: Catalog = {
    installed: true,
    agents: [],
    stages: [],
    sources: [],
    counts: { total: 0, active: 0, programs: 0, pending_reviews: 0 },
    legacy_agents: [],
    programs: {
      items: programs,
      has_more: false,
      period: { id: 1, label: "Synthetic period" },
    },
  };
  const providers: ProviderOptions = {
    current_provider: "gemini",
    credential_revision: 1,
    network_called: false,
    providers: [
      {
        id: "gemini",
        configured: true,
        endpoint_ready: true,
        catalog_loaded: false,
        models: [
          {
            id: "saved-model",
            name: "Saved model",
            origin: "saved_configuration",
          },
        ],
      },
      {
        id: "openai",
        configured: false,
        endpoint_ready: true,
        catalog_loaded: false,
        models: [],
      },
    ],
  };
  const fetcher = vi.fn(async (url: string, options: RequestInit) => ({
    ok: true,
    status: 200,
    json: async () => {
      if (options.method === "PUT") return { confirmed: true };
      expect(options.method).toBe("GET");
      return url.endsWith("/providers") ? providers : catalog;
    },
  }));
  vi.stubGlobal("fetch", fetcher);
  render(<AgentsPanel />, { wrapper: WorkspaceSessionProvider });
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Crear agente personalizado" }),
    ).toBeEnabled(),
  );
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  fireEvent.click(
    screen.getByRole("button", { name: "Crear agente personalizado" }),
  );
  expect(screen.getByLabelText("Agente supervisor (opcional)")).toBeDisabled();
  expect(screen.getByLabelText("Proveedor de IA")).toHaveValue("gemini");
  fireEvent.change(screen.getByLabelText("Modelo principal"), {
    target: { value: "saved-model" },
  });
  expect(screen.getByLabelText("Modelo principal")).toHaveValue("saved-model");
  const longText = "Complete institutional guidance. ".repeat(2500);
  const configurationFields = [
    "Instrucciones operativas",
    "Tono y personalidad",
    "Objetivos, uno por línea",
    "Reglas, una por línea",
  ];
  for (const label of configurationFields) {
    const field = screen.getByLabelText(label);
    expect(field).not.toHaveAttribute("maxlength");
    fireEvent.change(field, { target: { value: longText } });
    expect(field).toHaveValue(longText);
  }
  expect(screen.getByLabelText("Nombre del agente")).toHaveAttribute(
    "maxlength",
    "100",
  );
  fireEvent.change(screen.getByLabelText("Nombre del agente"), {
    target: { value: "Synthetic draft" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar configuración" }),
  );
  await screen.findByText(
    "Configuración guardada. El agente está disponible; las conexiones y el control humano conservan sus ajustes.",
  );
  const saved = fetcher.mock.calls.find(
    ([, options]) => options.method === "PUT",
  );
  expect(saved).toBeDefined();
  expect(JSON.parse(String(saved![1].body)).configuration).toMatchObject({
    instructions: longText,
    tone: longText,
    objectives: [longText],
    rules: [longText],
  });
  fireEvent.change(screen.getByLabelText("Proveedor de IA"), {
    target: { value: "openai" },
  });
  expect(screen.getByLabelText("Modelo principal")).toHaveValue("");
  expect(
    within(screen.getByLabelText("Modelo principal")).queryByRole("option", {
      name: /Saved model/,
    }),
  ).toBeNull();
  fireEvent.change(screen.getByLabelText("Responsabilidad"), {
    target: { value: "program" },
  });
  expect(
    screen.getByLabelText("Agente supervisor (obligatorio)"),
  ).toBeRequired();
  expect(fetcher).toHaveBeenCalledTimes(5);
});
