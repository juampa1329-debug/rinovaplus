import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CampaignWorkspace } from "../institution/CampaignWorkspace";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
const session: Session = {
  session_id: "s",
  csrf_token: "csrf-p8",
  actions: ["campaigns.manage", "crm.read", "inbox.write"],
  user: {
    id: "u",
    email: "u@cbn.local",
    full_name: "Admisiones",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const doc = {
  channel: "whatsapp",
  integration_id: "a",
  objective: "Admisiones",
  entry_conditions: {},
  scheduled_local: null,
  timezone: "America/Bogota",
  quiet_hours: {
    enabled: false,
    timezone: "America/Bogota",
    start_time: "21:00",
    end_time: "08:00",
    days: [0, 1, 2, 3, 4, 5, 6],
  },
  exit_on_response: true,
  steps: [{ kind: "wait", wait_minutes: 60 }],
  ab_test: { enabled: false, a_percent: 50, label: "Seguimiento" },
  cooldown_minutes: 1440,
};
const campaign = {
  id: "c",
  kind: "campaign",
  name: "Admisiones CBN",
  state: "draft",
  revision: 2,
  version: 1,
  epoch: 1,
  document: doc,
};
const ok = (v: unknown, status = 200) =>
  new Response(JSON.stringify(v), {
    status,
    headers: { "Content-Type": "application/json" },
  });
function setup(
  extra?: (p: string, i?: RequestInit) => Response | undefined,
  actions = session.actions,
) {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (url, init) => {
      const p = String(url),
        v = extra?.(p, init);
      if (v) return v;
      if (p.endsWith("/options"))
        return ok({
          accounts: [
            {
              id: "a",
              name: "WhatsApp CBN",
              channel: "whatsapp",
              verified_status: "verified",
            },
          ],
          templates: [],
          stages: ["Interesado"],
          programs: [{ program_id: 7, name: "Programa CRM" }],
        });
      if (p.endsWith("/campaigns")) return ok({ items: [campaign] });
      if (p.includes("/runs?"))
        return ok({ items: [], total: 0, has_more: false });
      if (p.endsWith("/metrics")) return ok({ variants: [] });
      return ok({});
    });
  render(
    <SessionBoundary initial={{ ...session, actions }} expire={() => {}}>
      <CampaignWorkspace />
    </SessionBoundary>,
  );
  return fetcher;
}
afterEach(() => vi.restoreAllMocks());
it("keeps shortening behind review and preflight and sends the saved revision without editing the flow", async () => {
  const flow = {...campaign, kind: "flow", state: "active", name: "Silencio consultivo", revision: 6,
    document: {...doc, followup_only: true, steps: [
      {kind:"send"}, {kind:"wait",wait_minutes:1680}, {kind:"send"},
      {kind:"wait",wait_minutes:1440}, {kind:"send"},
      {kind:"wait",wait_minutes:26640}, {kind:"send"},
    ]}};
  const f = setup((p) => p.endsWith("/campaigns") ? ok({items:[flow]}) :
    p.endsWith("/preflight") ? ok({id:"checked",valid:true,issues:[]}) :
    p.endsWith("/shorten_closure") ? ok({...flow,version:4}) : undefined);
  fireEvent.click(await screen.findByRole("button",{name:"Flujos"}));
  fireEvent.click(await screen.findByRole("button",{name:/Silencio consultivo/}));
  const shorten = screen.getByRole("button",{name:"Cerrar a los 7 días y conservar seguimientos en espera"});
  expect(shorten).toBeDisabled();
  fireEvent.click(screen.getByLabelText("Revisé el contenido, las versiones y el alcance de esta acción"));
  expect(shorten).toBeDisabled();
  fireEvent.click(screen.getByRole("button",{name:"Comprobar configuración"}));
  await waitFor(()=>expect(shorten).toBeEnabled());
  fireEvent.click(shorten);
  await waitFor(()=>expect(f.mock.calls.some(([url])=>String(url).endsWith("/shorten_closure"))).toBe(true));
  const request = f.mock.calls.find(([url])=>String(url).endsWith("/shorten_closure"))![1]!;
  expect(JSON.parse(String(request.body))).toMatchObject({revision:6, confirmed:true, preflight_id:"checked", closure_days:7});
  expect(f.mock.calls.some(([, init])=>init?.method === "PUT")).toBe(false);
});
it("loads one integrated list and keeps activation behind preflight and human review", async () => {
  setup();
  fireEvent.click(
    await screen.findByRole("button", { name: /Admisiones CBN/ }),
  );
  expect(screen.getByRole("button", { name: "Activar" })).toBeDisabled();
  expect(screen.getByLabelText("Esperar minutos")).toHaveValue(60);
  expect(
    screen.getByRole("button", { name: "Guardar borrador" }),
  ).toBeEnabled();
  expect(await screen.findByText(/No hay ejecuciones/)).toBeInTheDocument();
});
it("retains an edited flow after CAS conflict and submits its actual revision with CSRF", async () => {
  const f = setup((_p, i) =>
    i?.method === "PUT" ? ok({ detail: "revision_conflict" }, 409) : undefined,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Admisiones CBN/ }),
  );
  fireEvent.change(screen.getByLabelText("Nombre"), {
    target: { value: "Mi seguimiento" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));
  expect(
    await screen.findByText(/Hay una versión más reciente/),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Nombre")).toHaveValue("Mi seguimiento");
  const request = f.mock.calls.find(([, i]) => i?.method === "PUT")!;
  expect(JSON.parse(String(request[1]?.body)).revision).toBe(2);
  expect(new Headers(request[1]?.headers).get("X-CSRF-Token")).toBe("csrf-p8");
  expect(screen.getByRole("button", { name: "Activar" })).toBeDisabled();
});
it("provides structured condition/wait editors and ordered steps without activating on save", async () => {
  const f = setup();
  fireEvent.click(
    await screen.findByRole("button", { name: /Admisiones CBN/ }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Agregar paso" }));
  expect(screen.getAllByLabelText("Esperar minutos")).toHaveLength(2);
  fireEvent.change(screen.getAllByLabelText("Acción del paso")[1], {
    target: { value: "condition" },
  });
  expect(screen.getByLabelText("Si no coincide")).toHaveValue("stop");
  fireEvent.change(
    screen.getByLabelText("Programas de interés", {
      selector: "#step-1-programs",
    }),
    { target: { value: "7" } },
  );
  expect(f.mock.calls.filter(([, i]) => i?.method === "POST")).toHaveLength(0);
});
it("explains CRM templates and exposes typed variable bindings rather than fake approval", async () => {
  setup();
  fireEvent.click(
    await screen.findByRole("button", { name: "Plantillas CRM" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Crear plantilla" }));
  expect(
    screen.getByText(/no representa aprobación de Meta/),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Variable nombre")).toHaveValue(
    "customer_first_name",
  );
  expect(
    screen.queryByRole("button", { name: "Activar" }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Agregar bloque" }));
  expect(screen.getByLabelText("Tipo de bloque")).toHaveValue("text");
});
it("simulation is an explicit no-send command and displays a real timeline", async () => {
  const f = setup((p) =>
    p.endsWith("/simulate")
      ? ok({
          timeline: [
            {
              index: 0,
              kind: "wait",
              at: "2026-10-27T20:00:00Z",
              text: "Espera persistida",
            },
          ],
          provider_POSTs: 0,
        })
      : undefined,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Admisiones CBN/ }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Simular" }));
  expect(await screen.findByText("Espera persistida")).toBeInTheDocument();
  expect(
    f.mock.calls.filter(
      ([p, i]) => i?.method === "POST" && String(p).endsWith("/simulate"),
    ),
  ).toHaveLength(1);
  expect(f.mock.calls.some(([p]) => String(p).endsWith("/activate"))).toBe(
    false,
  );
});
it("current role without inbox.write cannot activate a sending flow", async () => {
  setup(
    (p) =>
      p.endsWith("/preflight")
        ? ok({ id: "pf", valid: true, issues: [] })
        : undefined,
    ["campaigns.manage", "crm.read"],
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Admisiones CBN/ }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Comprobar configuración" }),
  );
  await screen.findByText(/Configuración revisada/);
  fireEvent.click(screen.getByLabelText(/Revisé el contenido/));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Activar" })).toBeDisabled(),
  );
});
