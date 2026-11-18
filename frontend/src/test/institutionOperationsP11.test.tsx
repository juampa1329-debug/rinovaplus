import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
import { OperationsWorkspace } from "../institution/OperationsWorkspace";
import { useResource } from "../institution/Settings";

const session: Session = {
  session_id: "s",
  csrf_token: "p11-csrf",
  actions: ["users.manage"],
  user: {
    id: "u",
    email: "local@cbn.test",
    full_name: "Equipo",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
function mount(child: React.ReactNode) {
  return render(
    <SessionBoundary
      initial={session}
      expire={() => {}}
    >
      {child}
    </SessionBoundary>,
  );
}
function resource() {
  return {
    scope: "local",
    sql: {
      state: "verified",
      engine: 2019,
      tables: 185,
      academic_access: false,
    },
    workers: {
      alive: true,
      ready: true,
      stages: [
        {
          stage: "events",
          state: "ready",
          last_success_age_seconds: 1,
          consecutive_failures: 0,
        },
      ],
    },
    queues: { outbound: { uncertain: 32 } },
    backup: { state: "missing", restore_verified: false },
    local_ready: true,
    online: { state: "pending", phase: "P12" },
    observed_at: 1000,
  };
}
afterEach(() => vi.restoreAllMocks());

it("reports PostgreSQL and the configured HTTPS origin without claiming SQL Server or an external restore", async () => {
  const value = resource();
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
    ...value, scope: "postgres_deployment",
    sql: { ...value.sql, product: "PostgreSQL", version: "16.16", engine: 16, tables: 155 },
    infrastructure: { queue_backend: "postgresql", redis: "not_used" },
    backup: { state: "missing", restore_verified: false },
    online: { state: "configured", phase: "P12", public_origin: "https://app.example.test" },
  })));
  mount(<OperationsWorkspace />);
  expect(await screen.findByText(/PostgreSQL 16.16/)).toBeVisible();
  expect(screen.queryByText(/SQL Server 16/)).not.toBeInTheDocument();
  expect(screen.getByText(/Redis no se utiliza/)).toBeVisible();
  expect(screen.getByText(/URL HTTPS configurada: https:\/\/app.example.test/)).toBeVisible();
  expect(screen.getByText("Sin verificación registrada")).toBeVisible();
});

it("a dated restored-file receipt is distinct from continuous and off-server backup coverage", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
    ...resource(), backup: { state: "verified", restore_verified: true, verified_at: 1000, ready_blobs: 19 },
  })));
  mount(<OperationsWorkspace />);
  expect(await screen.findByText("Verificado")).toBeVisible();
  expect(screen.getByText(/19 archivos conservados/)).toBeVisible();
  expect(screen.getByText(/no verifica continuamente los archivos/)).toBeVisible();
});

it("distinguishes loading, missing backup, global counts and online scope", async () => {
  let resolve!: (r: Response) => void;
  vi.spyOn(globalThis, "fetch").mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  mount(<OperationsWorkspace />);
  expect(screen.getByText("Cargando información…")).toBeVisible();
  expect(
    screen.queryByText("Sin verificación registrada"),
  ).not.toBeInTheDocument();
  await act(async () => resolve(new Response(JSON.stringify(resource()))));
  expect(await screen.findByText("Sin verificación registrada")).toBeVisible();
  expect(screen.getByText("uncertain: 32")).toBeVisible();
  expect(screen.getByText(/se configurará en P12/)).toBeVisible();
});

it("shows refresh failures while preserving the last observation", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify(resource())))
    .mockResolvedValue(
      new Response(JSON.stringify({ detail: "local_storage_unavailable" }), {
        status: 503,
      }),
    );
  mount(<OperationsWorkspace />);
  await screen.findByText("Sin verificación registrada");
  fireEvent.click(screen.getByRole("button", { name: "Actualizar estado" }));
  expect(
    await screen.findByText(/Se conserva la última consulta/),
  ).toBeVisible();
  expect(screen.getByText("uncertain: 32")).toBeVisible();
});

it("never renders a prior section while a different section loads or fails", async () => {
  const pending = new Map<string, (r: Response) => void>();
  vi.spyOn(globalThis, "fetch").mockImplementation(
    (input) => new Promise((resolve) => pending.set(String(input), resolve)),
  );
  function View({ path }: { path: string }) {
    const data = useResource<{ label: string }>(path);
    return <p>{data.value?.label ?? data.error ?? "Loading"}</p>;
  }
  const view = mount(<View path="settings/ai" />);
  await act(async () =>
    pending.get("/api/institution/settings/ai")!(
      new Response(JSON.stringify({ label: "AI A" })),
    ),
  );
  expect(screen.getByText("AI A")).toBeVisible();
  view.rerender(
    <SessionBoundary
      initial={session}
      expire={() => {}}
    >
      <View path="settings/institution" />
    </SessionBoundary>,
  );
  expect(screen.queryByText("AI A")).not.toBeInTheDocument();
  await act(async () =>
    pending.get("/api/institution/settings/institution")!(
      new Response(JSON.stringify({ detail: "denied" }), { status: 403 }),
    ),
  );
  expect(screen.queryByText("AI A")).not.toBeInTheDocument();
});
