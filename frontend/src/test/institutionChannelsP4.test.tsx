import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Comments } from "../institution/Comments";
import { CommentNotifications } from "../institution/CommentNotifications";
import { ChannelWebhooks } from "../institution/Channels";
import {
  ChannelOperations,
  ChannelRuntime,
} from "../institution/ChannelOperations";
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

it("issues and copies the callback and token together for the chosen account", async () => {
  const endpoint = {
    id: "endpoint-one",
    path: "/hooks/channels/ep_test",
    callback_url: "https://crm.example.test/hooks/channels/ep_test",
    public_origin_required: false,
    active: false,
    row_version: "0000000000000001",
    challenge_verified_at: null,
    last_seen_at: null,
  };
  const clipboard = vi.fn().mockResolvedValue(undefined);
  const originalClipboard = Object.getOwnPropertyDescriptor(
    navigator,
    "clipboard",
  );
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText: clipboard },
    configurable: true,
  });
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path, init) => {
    if (String(path).endsWith("messenger-one/webhook/rotate")) {
      expect(JSON.parse(String(init?.body)).row_version).toBe(
        endpoint.row_version,
      );
      return ok({ webhook: endpoint, verify_token: "issued-only-once" });
    }
    return ok({
      items: [
        {
          id: "messenger-one",
          channel: "messenger",
          display_name: "Página de prueba",
          verified_status: "verified",
          webhook: endpoint,
        },
      ],
    });
  });
  try {
    mount(<ChannelWebhooks />, {
      ...base,
      actions: [...base.actions, "settings.channels.read"],
    });
    fireEvent.change(await screen.findByLabelText("Cuenta para el webhook"), {
      target: { value: "messenger-one" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generar webhook" }));
    expect(
      await screen.findByRole("heading", { name: "Valores para Meta" }),
    ).toBeVisible();
    expect(screen.getByLabelText("URL de callback")).toHaveValue(
      endpoint.callback_url,
    );
    expect(screen.getByLabelText("Token de verificación")).toHaveValue(
      "issued-only-once",
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Copiar URL de callback" }),
    );
    expect(await screen.findByText("URL de callback copiada.")).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: "Copiar token de verificación" }),
    );
    expect(
      await screen.findByText("Token de verificación copiado."),
    ).toBeVisible();
    expect(clipboard.mock.calls).toEqual([
      [endpoint.callback_url],
      ["issued-only-once"],
    ]);
    fireEvent.click(screen.getByRole("button", { name: "Ocultar token" }));
    expect(
      screen.queryByLabelText("Token de verificación"),
    ).not.toBeInTheDocument();
  } finally {
    if (originalClipboard)
      Object.defineProperty(navigator, "clipboard", originalClipboard);
    else Reflect.deleteProperty(navigator, "clipboard");
  }
});

it("opens Facebook authorization from the Messenger account and loads the selected Page on return", async () => {
  const authorization = "https://www.facebook.com/v26.0/dialog/oauth";
  const open = vi.spyOn(window, "open").mockReturnValue(null);
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (path, init) => {
      if (String(path).endsWith("routing-options")) return ok({ stages: [] });
      if (String(path).endsWith("account-one/history"))
        return ok({ queue: [], events: [], operations: [] });
      if (String(path).endsWith("account-one/oauth")) {
        const body = JSON.parse(String(init?.body));
        expect(body.scopes).toEqual([
          "pages_show_list",
          "pages_manage_metadata",
          "pages_read_engagement",
          "pages_manage_engagement",
          "pages_messaging",
        ]);
        return ok({
          authorization_url: authorization,
          oauth_session_id: "oauth-one",
        });
      }
      return ok({
        status: "assets_ready",
        items: [
          {
            id: "page-asset",
            name: "Página de prueba",
            external_id: "123",
            kind: "facebook_page",
          },
        ],
      });
    });
  mount(
    <ChannelOperations
      account={{
        id: "account-one",
        channel: "messenger",
        issuer_profile: "facebook_login",
        application_id: "app-one",
        display_name: "Messenger de prueba",
        oauth_ready: true,
        oauth_callback: "https://example.invalid/hooks/oauth/app-one",
        revision: 1,
        row_version: "version",
        application_version: "version",
        verified_status: "unverified",
        fields: {},
      }}
      done={async () => {}}
    />,
    {
      ...base,
      actions: [...base.actions, "settings.channels.write"],
    },
  );
  expect(screen.getByLabelText("URL de retorno de OAuth")).toHaveValue(
    "https://example.invalid/hooks/oauth/app-one",
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Conectar con Facebook" }),
  );
  await waitFor(() =>
    expect(open).toHaveBeenCalledWith(
      authorization,
      "_blank",
      "noopener,noreferrer",
    ),
  );
  expect(
    screen.getByRole("link", { name: "Abrir Facebook en otra pestaña" }),
  ).toHaveAttribute("href", authorization);
  fireEvent(window, new Event("focus"));
  expect(
    await screen.findByRole("button", { name: "Usar esta página" }),
  ).toBeVisible();
  expect(
    fetcher.mock.calls.some(([path]) =>
      String(path).endsWith("oauth-one/assets"),
    ),
  ).toBe(true);
});

it("loads the authorized Instagram account immediately after the OAuth redirect", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    if (String(path).endsWith("routing-options")) return ok({ stages: [] });
    if (String(path).endsWith("account-one/history"))
      return ok({ queue: [], events: [], operations: [] });
    expect(String(path)).toMatch(/oauth\/return-one\/assets$/);
    return ok({
      status: "assets_ready",
      items: [
        {
          id: "shop",
          name: "Tienda de prueba",
          external_id: "321",
          kind: "instagram_account",
        },
      ],
    });
  });
  mount(
    <ChannelOperations
      account={{
        id: "account-one",
        application_id: "app-one",
        channel: "instagram",
        issuer_profile: "instagram_login",
        display_name: "Instagram de prueba",
        revision: 1,
        row_version: "version",
        application_version: "version",
        verified_status: "unverified",
        fields: {},
      }}
      returnedOAuth="return-one"
      done={async () => {}}
    />,
    { ...base, actions: [...base.actions, "settings.channels.write"] },
  );
  expect(await screen.findByText("Tienda de prueba · 321")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Usar esta cuenta" }),
  ).toBeVisible();
});

it("explains a Meta App Secret rejection after returning from WhatsApp OAuth", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    if (String(path).endsWith("routing-options")) return ok({ stages: [] });
    if (String(path).endsWith("account-one/history"))
      return ok({ queue: [], events: [], operations: [] });
    expect(String(path)).toMatch(/oauth\/return-one\/assets$/);
    return ok({ status: "failed", code: "meta_app_secret_rejected", items: [] });
  });
  mount(
    <ChannelOperations
      account={{
        id: "account-one",
        application_id: "app-one",
        channel: "whatsapp",
        issuer_profile: "meta_whatsapp",
        display_name: "WhatsApp de prueba",
        revision: 1,
        row_version: "version",
        application_version: "version",
        verified_status: "unverified",
        fields: {},
      }}
      returnedOAuth="return-one"
      done={async () => {}}
    />,
    { ...base, actions: [...base.actions, "settings.channels.write"] },
  );
  expect(await screen.findByText(/Meta rechazó el App Secret/)).toBeVisible();
  expect(screen.queryByRole("button", { name: "Usar este número" })).toBeNull();
});

it("shows new comments in the notification menu and links to the exact comment", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => ok({ total: 3, items: [comment] }));
  mount(<CommentNotifications />);
  fireEvent.click(
    await screen.findByLabelText("Notificaciones de comentarios, 3 nuevos"),
  );
  const link = await screen.findByRole("link", {
    name: /Consulta sobre admisiones/,
  });
  expect(link).toHaveAttribute("href", "#/comments/comment-one");
  expect(
    fetcher.mock.calls.every(([url]) =>
      String(url).endsWith("/comments?state=new"),
    ),
  ).toBe(true);
});

it("labels persisted examples and disables external effects without disabling CRM review", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(
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

it("shows source and channel, keeps the suggestion separate, and saves comment instructions", async () => {
  const saved = {
    revision: 3,
    document: { enabled: true, comment_prompt: "Cálido" },
  };
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (path) => {
      if (String(path).endsWith("/settings/ai")) return ok(saved);
      if (String(path).endsWith("/suggest"))
        return ok({ status: "confirmed", draft: "Gracias por escribirnos." });
      return ok({
        items: [
          {
            ...comment,
            preview: {
              caption: "Inscripciones abiertas",
              permalink: "https://www.facebook.com/example",
            },
          },
        ],
        total: 1,
        has_more: false,
      });
    });
  mount(<Comments />, {
    ...base,
    actions: [...base.actions, "settings.ai.read", "settings.ai.write"],
  });
  const row = await screen.findByRole("button", { name: /Cuenta CBN · Nuevo/ });
  expect(row.querySelector("[data-channel='facebook']")).toHaveTextContent(
    "Facebook",
  );
  fireEvent.click(row);
  expect(screen.getByText("Inscripciones abiertas")).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Abrir publicación original" }),
  ).toHaveAttribute("href", "https://www.facebook.com/example");
  fireEvent.click(
    screen.getByRole("button", { name: "Sugerir respuesta con IA" }),
  );
  const apply = await screen.findByRole("button", { name: "Usar sugerencia" });
  expect(screen.getByLabelText("Respuesta pública")).toHaveValue("");
  fireEvent.click(apply);
  expect(screen.getByLabelText("Respuesta pública")).toHaveValue(
    "Gracias por escribirnos.",
  );
  fireEvent.change(await screen.findByLabelText("Instrucciones de respuesta"), {
    target: { value: "Breve y amable" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar instrucciones" }),
  );
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(
        ([path, request]) =>
          String(path).endsWith("/settings/ai") &&
          request?.method === "PUT" &&
          JSON.parse(String(request.body)).document.comment_prompt ===
            "Breve y amable",
      ),
    ).toBe(true),
  );
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
