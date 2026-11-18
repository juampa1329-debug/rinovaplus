import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Comments } from "../institution/Comments";
import { CommentNotifications } from "../institution/CommentNotifications";
import { ChannelWebhooks } from "../institution/Channels";
import {
  ChannelOperations,
  ChannelRuntime,
} from "../institution/ChannelOperations";
import { SessionBoundary } from "../institution/api";
import { Credentials } from "../institution/Settings";
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
  const dialog = HTMLDialogElement.prototype;
  if (!dialog.showModal) {
    dialog.showModal = function () { this.open = true; };
    dialog.close = function () { this.open = false; };
  }
});

it("recovers only the chosen identified event when multiple events need review", async () => {
  const events = [
    {
      id: "event-message",
      state: "quarantined",
      row_version: "0000000000000001",
      kind: "message",
      created_at: "2026-11-17T12:00:00Z",
      body_preview: "Prueba de recuperación DM",
    },
    {
      id: "event-comment",
      state: "quarantined",
      row_version: "0000000000000002",
      kind: "comment",
      created_at: "2026-11-17T12:01:00Z",
      body_preview: "Prueba de recuperación comentario",
    },
  ];
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (path, init) => {
      if (String(path).endsWith("routing-options")) return ok({ stages: [] });
      if (String(path).endsWith("account-one/history"))
        return ok({ queue: [], events, operations: [] });
      if (init?.method === "POST")
        return ok({ saved: true, provider_resend: false });
      return ok({});
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
        verified_status: "verified",
        fields: {},
      }}
      done={async () => {}}
    />,
    { ...base, actions: [...base.actions, "settings.channels.write"] },
  );
  fireEvent.click(screen.getByText("Actividad y recuperación"));
  const commentEvent = await screen.findByRole("group", {
    name: "Evento event-comment",
  });
  expect(
    within(commentEvent).getByText("Prueba de recuperación comentario"),
  ).toBeVisible();
  expect(within(commentEvent).getByText("Comentario")).toBeVisible();
  expect(within(commentEvent).getByText("event-comment")).toBeVisible();
  expect(
    screen.getByRole("group", { name: "Evento event-message" }),
  ).toHaveTextContent("Prueba de recuperación DM");
  fireEvent.click(
    within(commentEvent).getByRole("button", {
      name: "Reprocesar con la configuración actual",
    }),
  );
  await waitFor(() =>
    expect(fetcher.mock.calls.some(([, init]) => init?.method === "POST")).toBe(
      true,
    ),
  );
  const writes = fetcher.mock.calls.filter(
    ([, init]) => init?.method === "POST",
  );
  expect(writes).toHaveLength(1);
  expect(JSON.parse(String(writes[0][1]?.body))).toMatchObject({
    resource_id: "event-comment",
    row_version: "0000000000000002",
    action: "reprocess_event",
  });
});

it("confirms recovery inside the app and cancelling creates no retry", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (init?.method === "POST") return ok({ saved: true });
    if (String(url).endsWith("routing-options")) return ok({ stages: [] });
    return ok({ queue: [{ id: "failed-media", state: "failed", attempts: 1,
      row_version: "0000000000000001", body_preview: "[Adjunto]" }], events: [], operations: [] });
  });
  mount(<ChannelOperations account={{
    id: "account-one", application_id: "app-one", channel: "instagram",
    issuer_profile: "facebook_login", display_name: "Instagram de prueba",
    revision: 1, row_version: "version", application_version: "version",
    verified_status: "verified", fields: {},
  }} done={async () => {}} />,
  { ...base, actions: [...base.actions, "settings.channels.write"] });
  fireEvent.click(await screen.findByText("Actividad y recuperación"));
  fireEvent.click(await screen.findByRole("button", { name: "Reintentar envío rechazado" }));
  let dialog = await screen.findByRole("alertdialog", { name: "Confirmar recuperación" });
  expect(fetcher.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  fireEvent.click(within(dialog).getByRole("button", { name: "Cancelar" }));
  expect(fetcher.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Reintentar envío rechazado" }));
  dialog = await screen.findByRole("alertdialog", { name: "Confirmar recuperación" });
  fireEvent.click(within(dialog).getByRole("button", { name: "Confirmar recuperación" }));
  await waitFor(() => expect(fetcher.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1));
  const write = fetcher.mock.calls.find(([, init]) => init?.method === "POST");
  expect(JSON.parse(String(write?.[1]?.body))).toMatchObject({ resource_id: "failed-media", action: "retry_send" });
});

it("reuses a saved App Secret by reference and lists only compatible applications", async () => {
  const sourceId = "11223344-0000-4000-8000-000000000001";
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (_path, init) => {
    if (init?.method === "PUT") return ok({ configured: true, version: 1 });
    return ok({ items: [
      { id: sourceId, owner: "application:other", kind: "app_secret", version: 2,
        configured: true, verified: false, application: { name: "CBN", client_id: "123",
          provider: "meta", issuer_profile: "meta_whatsapp" } },
      { id: "different-app", owner: "application:unrelated", kind: "app_secret", version: 1,
        application: { name: "Otra app", client_id: "999", provider: "meta", issuer_profile: "facebook_login" } },
      { id: "different-login", owner: "application:instagram", kind: "app_secret", version: 1,
        application: { name: "Instagram independiente", client_id: "123", provider: "meta", issuer_profile: "instagram_login" } },
    ] });
  });
  mount(<Credentials scope="channel" owner="application:target"
    application={{ clientId: "123", provider: "meta", issuerProfile: "facebook_login" }}
    kinds={[{ id: "app_secret", label: "App Secret" }]} />,
    { ...base, actions: [...base.actions, "settings.channels.write"] });
  const select = await screen.findByRole("combobox", { name: "App Secret guardado" });
  expect(within(select).getAllByRole("option")).toHaveLength(2);
  fireEvent.change(select, { target: { value: sourceId } });
  fireEvent.click(screen.getByRole("button", { name: "Usar App Secret guardado" }));
  await screen.findByText("App Secret guardado reutilizado en esta aplicación.");
  const request = fetcher.mock.calls.find(([, init]) => init?.method === "PUT");
  const body = JSON.parse(String(request?.[1]?.body));
  expect(body.source_secret_id).toBe(sourceId);
  expect(body.owner).toBe("application:target");
  expect(body).not.toHaveProperty("value");
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
  const result = await screen.findByRole("dialog", { name: "Autorización completada" });
  fireEvent.click(within(result).getByRole("button", { name: "Ver opciones" }));
  expect(await screen.findByText("Tienda de prueba")).toBeVisible();
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
  const result = await screen.findByRole("alertdialog", { name: "No se pudo completar la autorización" });
  expect(within(result).getByText(/Meta rechazó el App Secret/)).toBeVisible();
  expect(screen.queryByRole("button", { name: "Usar este número" })).toBeNull();
});

it("confirms WhatsApp discovery and confirms the saved number only after selection", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    if (String(path).endsWith("routing-options")) return ok({ stages: [] });
    if (String(path).endsWith("account-one/history"))
      return ok({ queue: [], events: [], operations: [] });
    if (String(path).endsWith("/select")) return ok({ status: "completed" });
    expect(String(path)).toMatch(/oauth\/return-one\/assets$/);
    return ok({
      status: "assets_ready",
      items: [{ id: "phone", name: "CBN · +15555550100", external_id: "321", kind: "whatsapp_phone" }],
    });
  });
  mount(
    <ChannelOperations account={{
      id: "account-one", application_id: "app-one", channel: "whatsapp",
      issuer_profile: "meta_whatsapp", display_name: "WhatsApp de prueba",
      revision: 1, row_version: "version", application_version: "version",
      verified_status: "unverified", fields: {},
    }} returnedOAuth="return-one" done={async () => {}} />,
    { ...base, actions: [...base.actions, "settings.channels.write"] },
  );
  expect(screen.getByRole("button", { name: "Sincronizar números de WhatsApp" })).toBeDisabled();
  const discovery = await screen.findByRole("dialog", { name: "Números de WhatsApp disponibles" });
  expect(fetcher.mock.calls.some(([url]) => String(url).endsWith("/select"))).toBe(false);
  fireEvent.click(within(discovery).getByRole("button", { name: "Ver números" }));
  const choose = screen.getByRole("button", { name: "Usar este número" });
  expect(choose).toHaveFocus();
  fireEvent.click(choose);
  const saved = await screen.findByRole("dialog", { name: "Número agregado a RinovaPlus" });
  expect(within(saved).getByText(/CBN · \+15555550100/)).toBeVisible();
  expect(within(saved).getByText(/Verificar token y cuenta/)).toBeVisible();
});

it("syncs the saved WhatsApp account and registers its selected number only on request", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (path, init) => {
    if (String(path).endsWith("routing-options")) return ok({ stages: [] });
    if (String(path).endsWith("account-one/history"))
      return ok({ queue: [], events: [], operations: [] });
    if (String(path).endsWith("/register")) {
      expect(JSON.parse(String(init?.body)).pin).toBe("123456");
      return ok({ status: "confirmed", result: { confirmed: true } });
    }
    expect(String(path)).toMatch(/account-one\/actions\/numbers$/);
    return ok({ status: "confirmed", result: { numbers: [
      { id: "321", display_phone_number: "+15555550100", verified_name: "CBN" },
      { id: "222", display_phone_number: "+15555550101", verified_name: "CBN Dos" },
    ] } });
  });
  mount(
    <ChannelOperations account={{
      id: "account-one", application_id: "app-one", channel: "whatsapp",
      issuer_profile: "meta_whatsapp", display_name: "WhatsApp de prueba",
      revision: 1, row_version: "version", application_version: "version",
      verified_status: "unverified",
      fields: { "meta:whatsapp_phone_number_id": "321", "meta:whatsapp_business_account_id": "123" },
    }} done={async () => {}} />,
    { ...base, actions: [...base.actions, "settings.channels.write"] },
  );
  fireEvent.click(screen.getByRole("button", { name: "Sincronizar números de WhatsApp" }));
  expect(await screen.findByText("Meta devolvió 2 números para esta cuenta.")).toBeVisible();
  expect(screen.getByText("Guardado en este canal")).toBeVisible();
  expect(screen.getByRole("button", { name: "Usar este número" })).toBeDisabled();
  expect(fetcher.mock.calls.some(([url]) => String(url).endsWith("/register"))).toBe(false);
  fireEvent.click(screen.getByText("Registrar número en WhatsApp Cloud API"));
  fireEvent.change(screen.getByLabelText("PIN de seis dígitos"), { target: { value: "123456" } });
  fireEvent.click(screen.getByRole("button", { name: /^Registrar número$/ }));
  expect(await screen.findByRole("dialog", { name: "Número registrado en WhatsApp" })).toBeVisible();
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
      String(url).endsWith("/comments/notifications"),
    ),
  ).toBe(true);
});

it("acknowledges the notification snapshot without changing comments or their AI mode", async () => {
  let acknowledged = false;
  const cutoff = "2026-11-18T12:00:00Z";
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (init?.method === "POST") {
      expect(String(url)).toMatch(/comments\/notifications\/read$/);
      expect(JSON.parse(String(init.body))).toEqual({ read_through: cutoff, operation_id: expect.any(String) });
      acknowledged = true;
      return ok({ saved: true });
    }
    return ok({ total: acknowledged ? 0 : 3, items: acknowledged ? [] : [comment], read_through: cutoff });
  });
  mount(<CommentNotifications />);
  fireEvent.click(await screen.findByLabelText("Notificaciones de comentarios, 3 nuevos"));
  fireEvent.click(screen.getByRole("button", { name: "Marcar todas como leídas" }));
  expect(await screen.findByText("Estás al día con los comentarios.")).toBeVisible();
  expect(fetcher.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
});

it("shows inaccessible comments honestly and allows source reconciliation without external replies", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, init) => {
    if (init?.method === "POST") return ok({ status: "confirmed", result: { source: { status: "unavailable" } } });
    return ok({ items: [{ ...comment, state: "unavailable" }], total: 1, has_more: false });
  });
  mount(<Comments />);
  fireEvent.click(await screen.findByRole("button", { name: /Cuenta CBN · Fuente no disponible/ }));
  expect(screen.getByText(/Meta no permite consultar este comentario/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Sugerir respuesta con IA" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Enviar respuesta pública" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Sincronizar comentario" }));
  await waitFor(() => expect(fetcher.mock.calls.some(([url, init]) => init?.method === "POST" && String(url).endsWith("/comment-one/effects/reconcile"))).toBe(true));
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

it("automatically loads a publication preview without changing the comment or requiring write access", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    if (String(path).endsWith("/preview")) return ok({
      caption: "Conoce nuestros programas", permalink: "https://www.instagram.com/p/test/",
      media: [
        { type: "image", url: "https://scontent.cdninstagram.com/test.jpg" },
        { type: "image", url: "https://untrusted.example/image.jpg" },
      ],
    });
    return ok({ items: [{ ...comment, channel: "instagram" }], total: 1, has_more: false });
  });
  mount(<Comments />, { ...base, actions: ["inbox.read"] });
  fireEvent.click(await screen.findByRole("button", { name: /Cuenta CBN · Nuevo/ }));
  expect(await screen.findByText("Conoce nuestros programas")).toBeVisible();
  expect(screen.getByRole("img", { name: "Imagen 1 de la publicación" })).toHaveAttribute(
    "src", "https://scontent.cdninstagram.com/test.jpg",
  );
  expect(screen.getAllByRole("img")).toHaveLength(1);
  expect(screen.getByRole("link", { name: "Abrir publicación original" })).toHaveAttribute(
    "href", "https://www.instagram.com/p/test/",
  );
  expect(fetcher.mock.calls.some(([, init]) => init?.method && init.method !== "GET")).toBe(false);
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
