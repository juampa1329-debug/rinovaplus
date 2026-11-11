import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AgentsPanel } from "./AgentsPanel";
import { WorkspaceSessionProvider } from "../../shared/workspaceSession";
import { blankConfiguration, type Agent, type Catalog } from "./api";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const ready = {
  ready: true,
  checks: [] as string[],
  version: 1,
  effective: {},
};
function setup(preflight = async () => ready, secondAgent = false) {
  const root: Agent = {
    id: crypto.randomUUID(),
    name: "Synthetic review root",
    level: "guide",
    parent_id: null,
    program_id: null,
    stage_id: null,
    state: "draft",
    version: 1,
    revision: 1,
    approved_version: null,
    configuration: {
      ...blankConfiguration(),
      provider: "gemini",
      primary_model: "synthetic-model",
      instructions: "Synthetic policy",
      monthly_token_limit: 10000,
    },
  };
  const other = {
    ...root,
    id: crypto.randomUUID(),
    name: "Other synthetic root",
  };
  const catalog: Catalog = {
    installed: true,
    agents: secondAgent ? [root, other] : [root],
    stages: [],
    sources: [],
    counts: { total: 1, active: 0, programs: 0, pending_reviews: 1 },
    legacy_agents: [],
    programs: {
      items: [],
      has_more: false,
      period: { id: 1, label: "Synthetic period" },
    },
  };
  const fetcher = vi.fn(async (url: string, options: RequestInit) => {
    let result: unknown;
    if (url.endsWith("/providers"))
      result = {
        current_provider: "gemini",
        providers: [],
        network_called: false,
        credential_revision: 1,
      };
    else if (url.endsWith("/preflight")) result = await preflight();
    else if (url.endsWith("/approve")) {
      expect(options.method).toBe("POST");
      expect(JSON.parse(String(options.body))).toMatchObject({
        revision: 1,
        confirmed: true,
        note: "Synthetic human evidence",
      });
      catalog.agents = catalog.agents.map((agent) =>
        agent.id === root.id
          ? { ...agent, approved_version: 1, revision: 2 }
          : agent,
      );
      result = { confirmed: true };
    } else {
      expect(url).toBe("/api/v1/agents");
      expect(options.method).toBe("GET");
      result = catalog;
    }
    return { ok: true, status: 200, json: async () => structuredClone(result) };
  });
  vi.stubGlobal("fetch", fetcher);
  render(<AgentsPanel />, { wrapper: WorkspaceSessionProvider });
  return { fetcher, root, other };
}
async function openReview() {
  fireEvent.click(
    await screen.findByRole("button", { name: /Synthetic review root/ }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Diagnóstico" }));
}

it("runs optional diagnosis without profile approval or paid effects", async () => {
  const { fetcher } = setup();
  await openReview();
  expect(
    screen.queryByRole("button", { name: /Aprobar versión/ }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Ejecutar diagnóstico" }));
  await screen.findByText("Configuración válida para su ámbito.");
  expect(
    fetcher.mock.calls.filter(([, o]) => o.method === "POST"),
  ).toHaveLength(0);
});
it("shows unresolved configuration without inventing an approval gate", async () => {
  setup(async () => ({
    ...ready,
    ready: false,
    checks: ["agents_incomplete_configuration"],
  }));
  await openReview();
  fireEvent.click(screen.getByRole("button", { name: "Ejecutar diagnóstico" }));
  await screen.findByText(
    "Complete instrucciones, modelo principal, canales y presupuesto.",
  );
  expect(
    screen.queryByRole("button", { name: /Aprobar versión/ }),
  ).not.toBeInTheDocument();
});
it("discards late diagnostic results after selecting another profile", async () => {
  let finish!: (value: typeof ready) => void;
  const pending = new Promise<typeof ready>((r) => {
    finish = r;
  });
  setup(async () => pending, true);
  await openReview();
  fireEvent.click(screen.getByRole("button", { name: "Ejecutar diagnóstico" }));
  fireEvent.click(screen.getByRole("button", { name: /Other synthetic root/ }));
  await act(async () => finish(ready));
  expect(
    screen.queryByText("Configuración válida para su ámbito."),
  ).not.toBeInTheDocument();
  expect(
    screen.getByText(/no corresponde al perfil o versión actual/),
  ).toBeInTheDocument();
});
it("preserves unsaved instructions and blocks diagnosis of a changed draft", async () => {
  const { fetcher } = setup();
  fireEvent.click(
    await screen.findByRole("button", { name: /Synthetic review root/ }),
  );
  fireEvent.change(screen.getByLabelText("Instrucciones operativas"), {
    target: { value: "Unsaved instructions" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Diagnóstico" }));
  expect(
    screen.getByRole("button", { name: "Ejecutar diagnóstico" }),
  ).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Mis agentes" }));
  expect(screen.getByLabelText("Instrucciones operativas")).toHaveValue(
    "Unsaved instructions",
  );
  expect(fetcher.mock.calls.some(([u]) => u.endsWith("/preflight"))).toBe(
    false,
  );
});
it("rejects diagnosis that describes a newer saved version", async () => {
  setup(async () => ({ ...ready, version: 2 }));
  await openReview();
  fireEvent.click(screen.getByRole("button", { name: "Ejecutar diagnóstico" }));
  await screen.findByText(/no corresponde al perfil o versión actual/);
  expect(
    screen.queryByText("Configuración válida para su ámbito."),
  ).not.toBeInTheDocument();
});
