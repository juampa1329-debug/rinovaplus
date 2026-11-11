import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { LearningWorkspace } from "../institution/LearningWorkspace";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";

const session: Session = {
  session_id: "s",
  csrf_token: "p10-csrf",
  actions: ["agents.manage", "crm.read", "settings.ai.write"],
  user: {
    id: "owner",
    email: "local@example.test",
    full_name: "Equipo",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const pack = {
  id: "p1",
  revision: 1,
  task: "lead_scoring",
  scope: "demo",
  document: {
    name: "Admisiones · ejemplo",
    task: "lead_scoring",
    scope: "demo",
    training_enabled: true,
  },
};
const metric = {
  n: 16,
  accuracy: 1,
  precision: 1,
  recall: 1,
  f1: 1,
  brier: 0.02,
  auc: 1,
  false_positives: 0,
  false_negatives: 0,
};
const evaluation = {
  candidate: metric,
  baseline: { ...metric, accuracy: 0.5, brier: 0.25, auc: 0.5 },
  eligible: true,
  train_ids: Array.from({ length: 48 }, (_, i) => String(i)),
  holdout_ids: Array.from({ length: 16 }, (_, i) => String(48 + i)),
  segments: {
    "general:new": {
      candidate: metric,
      baseline: { ...metric, accuracy: 0.5 },
    },
  },
};
afterEach(() => {
  vi.restoreAllMocks();
});
function fixture(actions = session.actions, morePacks = false) {
  const calls: { path: string; body: Record<string, unknown> | null }[] = [];
  let hold: ((value: Response) => void) | undefined;
  const mock = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = new URL(String(input), "http://cbn.local"),
        path = url.pathname.replace("/api/institution/", ""),
        body = init?.body ? JSON.parse(String(init.body)) : null;
      calls.push({ path, body });
      let result: unknown;
      if (body) result = { id: "new-pack", revision: 2 };
      else if (path === "learning/catalog")
        result = {
          tasks: [
            {
              id: "lead_scoring",
              features: ["message_count"],
              purpose: "educational_lead_scoring",
            },
          ],
          programs: [],
          stages: [{ id: "new", name: "Nuevo" }],
          contexts: [],
          campaigns: [],
        };
      else if (path === "learning/packs")
        result = {
          more: morePacks,
        items: [
            pack,
            {
              ...pack,
              id: "p2",
              document: { ...pack.document, name: "Seguimiento · ejemplo" },
            },
          ],
        };
      else if (path.endsWith("/artifacts"))
        result = {
          items: [
            {
              id: "artifact-1",
              document: { scope: "demo", evaluation },
              created_at: "2026-10-28T00:00:00Z",
              hash: "digest",
            },
          ],
          more: false,
        };
      else if (/^learning\/packs\/[^/]+$/.test(path))
        result = {
          pack: { ...pack, id: path.split("/").at(-1) },
          deployment: {
            revision: 1,
            state: "enabled",
            active_id: null,
            shadow_id: null,
            document: {},
          },
        };
      else result = { items: [], more: false };
      return new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
  const view = render(
    <SessionBoundary initial={{ ...session, actions }} expire={vi.fn()}>
      <LearningWorkspace />
    </SessionBoundary>,
  );
  return {
    calls,
    mock,
    view,
    pending: () =>
      new Promise<Response>((resolve) => {
        hold = resolve;
      }),
    release: (value: unknown) =>
      hold?.(
        new Response(JSON.stringify(value), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
  };
}
async function choose() {
  fireEvent.change(await screen.findByLabelText("Pack de aprendizaje"), {
    target: { value: "p1" },
  });
  await screen.findByRole("heading", { name: "Admisiones · ejemplo" });
}

it("shows temporal metrics, explicit synthetic scope and baseline", async () => {
  fixture();
  await choose();
  await screen.findByRole("table", {
    name: "Comparación en datos de validación",
  });
  expect(
    screen.getByText("Entrenamiento: 48 · Validación temporal: 16"),
  ).toBeVisible();
  expect(screen.getByText("Ejemplo ficticio")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Promover versión" }),
  ).toBeDisabled();
  expect(
    screen.getByText(/no acreditan resultados de la institución/),
  ).toBeInTheDocument();
});
it("packs use typed institutional defaults and CSRF-bound operations", async () => {
  const f = fixture();
  fireEvent.click(await screen.findByRole("button", { name: "Crear pack" }));
  fireEvent.change(screen.getByLabelText("Nombre del pack"), {
    target: { value: "Orientación institucional" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar pack" }));
  await waitFor(() =>
    expect(f.calls.some((v) => v.body && v.path === "learning/packs")).toBe(
      true,
    ),
  );
  const posted = f.calls.find(
    (v) => v.body && v.path === "learning/packs",
  )!.body!;
  expect(posted.document).toMatchObject({
    scope: "native",
    training_enabled: true,
  });
  expect(posted.operation_id).toBeTruthy();
  expect(posted).not.toHaveProperty("tenant_id");
});
it("purpose authorization is distinct from marketing and can be revoked", async () => {
  fixture();
  await choose();
  fireEvent.click(screen.getByRole("button", { name: "Autorizaciones" }));
  expect(
    await screen.findByText(
      /consentimiento comercial se administra por separado/,
    ),
  ).toBeVisible();
  expect(screen.getByLabelText("Autorizar esta finalidad")).toBeChecked();
  fireEvent.click(screen.getByLabelText("Autorizar esta finalidad"));
  expect(screen.getByLabelText("Autorizar esta finalidad")).not.toBeChecked();
});
it("hides promotion from a user lacking model-selection authority", async () => {
  fixture(["agents.manage", "crm.read"]);
  await choose();
  await screen.findByRole("table");
  expect(
    screen.queryByRole("button", { name: "Promover versión" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Pausar predicción" }),
  ).not.toBeInTheDocument();
});
it("a late artifact response cannot populate the grants tab", async () => {
  const f = fixture();
  const initial = f.mock.getMockImplementation()!;
  f.mock.mockImplementation((input, init) =>
    String(input).includes("/artifacts") ? f.pending() : initial(input, init),
  );
  await choose();
  fireEvent.click(screen.getByRole("button", { name: "Autorizaciones" }));
  await screen.findByRole("heading", { name: "Autorizar finalidad" });
  await act(async () => {
    f.release({
      items: [{ id: "late", document: { evaluation, scope: "demo" } }],
      more: false,
    });
  });
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Autorizar finalidad" }),
  ).toBeVisible();
});
it("a completed create after navigation cannot select an old pack", async () => {
  const f = fixture(),
    initial = f.mock.getMockImplementation()!;
  f.mock.mockImplementation((input, init) =>
    init?.method === "POST" ? f.pending() : initial(input, init),
  );
  fireEvent.click(await screen.findByRole("button", { name: "Crear pack" }));
  fireEvent.change(screen.getByLabelText("Nombre del pack"), {
    target: { value: "Nuevo local" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar pack" }));
  vi.spyOn(window, "confirm").mockReturnValue(true);
  fireEvent.change(screen.getByLabelText("Pack de aprendizaje"), {
    target: { value: "p2" },
  });
  await screen.findByRole("table");
  await act(async () => {
    f.release({ id: "late-new", revision: 1 });
  });
  expect(screen.getByLabelText("Pack de aprendizaje")).toHaveValue("p2");
});
it("lost acknowledgement reuses the exact operation identity on retry", async () => {
  const f = fixture(),
    initial = f.mock.getMockImplementation()!;
  let attempts = 0;
  f.mock.mockImplementation(async (input, init) => {
    if (init?.method === "POST") {
      attempts++;
      if (attempts === 1) {
        f.calls.push({
          path: "learning/packs",
          body: JSON.parse(String(init.body)),
        });
        throw new Error("Respuesta perdida");
      }
    }
    return initial(input, init);
  });
  fireEvent.click(await screen.findByRole("button", { name: "Crear pack" }));
  fireEvent.change(screen.getByLabelText("Nombre del pack"), {
    target: { value: "Datos revisados" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar pack" }));
  await screen.findByText("Respuesta perdida");
  fireEvent.click(screen.getByRole("button", { name: "Guardar pack" }));
  await waitFor(() => expect(f.calls.filter((v) => v.body).length).toBe(2));
  const posted = f.calls.filter((v) => v.body);
  expect(posted[0].body!.operation_id).toBe(posted[1].body!.operation_id);
});

it("pack selection can reach a later SQL page", async () => {
  const f = fixture(session.actions, true),
    initial = f.mock.getMockImplementation()!;
  f.mock.mockImplementation(async (input, init) => {
    const url = new URL(String(input), "http://cbn.local");
    if (url.pathname.endsWith("/learning/packs"))
      return new Response(
        JSON.stringify({
          items:
            url.searchParams.get("offset") === "50"
              ? [
                  {
                    ...pack,
                    id: "p51",
                    document: { ...pack.document, name: "Pack de otra página" },
                  },
                ]
              : [pack],
          more: url.searchParams.get("offset") !== "50",
        }),
        { headers: { "Content-Type": "application/json" } },
      );
    return initial(input, init);
  });
  await screen.findByLabelText("Pack de aprendizaje");
  // Refresh the initial selector through its actual next-page control.
  const button = screen.getByRole("button", { name: "Más packs" });
  await waitFor(() => expect(button).toBeEnabled());
  fireEvent.click(button);
  expect(
    await screen.findByRole("option", { name: "Pack de otra página" }),
  ).toHaveValue("p51");
});

it("sample authorization selection can reach records after the first fifty", async () => {
  const f = fixture(),
    initial = f.mock.getMockImplementation()!;
  f.mock.mockImplementation(async (input, init) => {
    const url = new URL(String(input), "http://cbn.local");
    if (url.pathname.endsWith("/grants"))
      return new Response(
        JSON.stringify({
          items: [
            {
              id: url.searchParams.get("offset") === "50" ? "g51" : "g1",
              state: "active",
              revision: 1,
              document: {
                reference:
                  url.searchParams.get("offset") === "50"
                    ? "REFERENCIA-51"
                    : "REFERENCIA-1",
              },
            },
          ],
          more: url.searchParams.get("offset") !== "50",
        }),
        { headers: { "Content-Type": "application/json" } },
      );
    return initial(input, init);
  });
  await choose();
  fireEvent.click(screen.getByRole("button", { name: "Muestras revisadas" }));
  await screen.findByRole("option", { name: /REFERENCIA-1/ });
  fireEvent.click(screen.getByRole("button", { name: "Más autorizaciones" }));
  expect(
    await screen.findByRole("option", { name: /REFERENCIA-51/ }),
  ).toHaveValue("g51");
});
