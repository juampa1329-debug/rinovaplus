import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Comments } from "../institution/Comments";
import { ChannelRuntime } from "../institution/ChannelOperations";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";

const base: Session = {
  session_id: "owned",
  csrf_token: "memory-only",
  actions: [
    "inbox.read",
    "inbox.write",
    "crm.write",
    "settings.webhooks.write",
  ],
  user: {
    id: "person",
    email: "person@cbn.invalid",
    full_name: "Persona",
    active: true,
    role: "owner",
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const comment = {
  id: "comment-one",
  integration_id: "account-one",
  account: "Cuenta CBN",
  channel: "facebook",
  body: "Consulta sobre admisiones",
  author: "Autor",
  state: "new",
  row_version: "0000000000000001",
  received_at: "2026-10-26T12:00:00Z",
  capabilities: { public_comment_reply: true, comment_like: true },
};
const ok = (body: unknown) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
function mount(children: React.ReactNode, session = base) {
  render(
    <SessionBoundary initial={session} expire={() => {}}>
      {children}
    </SessionBoundary>,
  );
}
beforeEach(() => {
  vi.restoreAllMocks();
});

it("labels persisted examples and disables external effects without disabling CRM review", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValue(
      ok({
        items: [
          {
            ...comment,
            synthetic_demo: true,
            capabilities: { public_comment_reply: false, comment_like: false },
          },
        ],
        total: 1,
        has_more: false,
      }),
    );
  mount(<Comments />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Cuenta CBN · Nuevo/ }),
  );
  expect(screen.getByText(/Datos ficticios para explorar/)).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Sugerir respuesta con IA" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Actualizar publicación" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Crear contacto en CRM" }),
  ).toBeEnabled();
  expect(
    fetcher.mock.calls.every(
      ([, init]) => !init?.method || init.method === "GET",
    ),
  ).toBe(true);
});

it("keeps a reply draft when refreshing comments", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    ok({ items: [comment], total: 1, has_more: false }),
  );
  mount(<Comments />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Cuenta CBN · Nuevo/ }),
  );
  const box = screen.getByLabelText("Respuesta pública");
  fireEvent.change(box, { target: { value: "Borrador humano" } });
  fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Respuesta pública")).toHaveValue(
      "Borrador humano",
    ),
  );
});

it("a read-only viewer cannot start effects", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    ok({ items: [comment], total: 1, has_more: false }),
  );
  mount(<Comments />, { ...base, actions: ["inbox.read"] });
  fireEvent.click(
    await screen.findByRole("button", { name: /Cuenta CBN · Nuevo/ }),
  );
  expect(screen.getByRole("button", { name: "Me gusta" })).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Sugerir respuesta con IA" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Crear contacto en CRM" }),
  ).toBeDisabled();
});

it("saves the trusted callback origin with revision and a fresh operation id", async () => {
  const initial = {
    revision: 3,
    public_base_url: "",
    ingress_enabled: false,
    outbound_enabled: false,
    receipt_retention_days: 7,
  };
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (_url, init) =>
      ok(init?.method === "PUT" ? { saved: true } : initial),
    );
  mount(<ChannelRuntime />);
  fireEvent.change(await screen.findByLabelText("URL pública HTTPS"), {
    target: { value: "https://cbn.example.test" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar" }));
  await waitFor(() =>
    expect(fetcher.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(
      true,
    ),
  );
  const [, request] = fetcher.mock.calls.find(
    ([, init]) => init?.method === "PUT",
  )!;
  expect(JSON.parse(String(request?.body))).toMatchObject({
    revision: 3,
    public_base_url: "https://cbn.example.test",
    outbound_enabled: false,
    operation_id: expect.any(String),
  });
});
