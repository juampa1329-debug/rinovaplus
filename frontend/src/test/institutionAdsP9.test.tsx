import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AdsWorkspace } from "../institution/AdsWorkspace";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
const account = {
  id: "a1",
  revision: 1,
  provider: "meta",
  external_account_id: "123",
  name: "Admisiones local",
  status: "connected",
  currency: "COP",
  timezone: "America/Bogota",
  integration_id: null,
  program_id: null,
  initial_stage_key: "new",
  form_ids: [],
  has_access_token: false,
};
const session: Session = {
  session_id: "s",
  csrf_token: "p9-csrf",
  actions: [
    "ads.manage",
    "crm.read",
    "crm.write",
    "inbox.read",
    "inbox.write",
    "settings.channels.write",
  ],
  user: {
    id: "owner",
    email: "u@cbn.local",
    full_name: "Equipo",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
afterEach(() => {
  vi.restoreAllMocks();
});
function mount(actions = session.actions) {
  const accounts = [{ ...account }],
    leads: Record<string, unknown>[] = [],
    calls: {
      path: string;
      init: RequestInit;
      body: Record<string, unknown> | null;
    }[] = [];
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const url = new URL(String(input), "http://cbn.local"),
        path = url.pathname.replace("/api/institution/", "");
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      calls.push({ path, init: init || {}, body });
      let result: unknown;
      if (path === "ads/options")
        result = {
          accounts,
          integrations: [],
          programs: [{ program_id: 1, name: "Programa declarado" }],
          stages: [{ key: "new", label: "Nuevo" }],
        };
      else if (path.startsWith("ads/summary"))
        result = {
          summary: {
            accounts: accounts.length,
            campaigns: 0,
            open_leads: leads.length,
            open_comments: 0,
            webhook_events: 0,
            conversations: 0,
          },
          as_of: "2026-10-27T12:00:00Z",
        };
      else if (path === "ads/accounts" && init?.method === "POST") {
        const row = { ...(body.document as object), id: "a2", revision: 1 };
        accounts.push(row as typeof account);
        result = row;
      } else if (path === "ads/leads/import") {
        const row = {
          ...(body.document as object),
          id: "l1",
          revision: 2,
          status: "converted",
          origin: "operator",
          contact_id: "contact1",
          conversation_id: "conversation1",
        };
        leads.push(row);
        result = row;
      } else if (path.includes("/credential"))
        result = { stored: true, provider_verified: false, revision: 2 };
      else if (path === "ads/accounts")
        result = { items: accounts, has_more: false };
      else if (path === "ads/leads") result = { items: leads, has_more: false };
      else if (path.includes("/history"))
        result = { items: [], has_more: false };
      else result = { items: [], has_more: false };
      return new Response(JSON.stringify(result), {
        headers: { "Content-Type": "application/json" },
      });
    });
  render(
    <SessionBoundary initial={{ ...session, actions }} expire={() => {}}>
      <AdsWorkspace />
    </SessionBoundary>,
  );
  return { calls, fetcher };
}
it("loads the scoped local indicators through GET and exposes no spending action", async () => {
  const { calls } = mount();
  await screen.findByRole("button", { name: "Importar lead" });
  expect(screen.getByText("Webhooks firmados")).toBeInTheDocument();
  expect(calls.every((v) => !v.init.method || v.init.method === "GET")).toBe(
    true,
  );
  expect(
    screen.queryByRole("button", { name: /Publicar anuncio|Activar gasto/ }),
  ).not.toBeInTheDocument();
});
it("saves a typed account with CSRF and without provider verification claims", async () => {
  const { calls } = mount();
  await screen.findByRole("button", { name: "Cuentas publicitarias" });
  fireEvent.click(
    screen.getByRole("button", { name: "Cuentas publicitarias" }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Agregar cuenta" }),
  );
  fireEvent.change(screen.getByLabelText("ID de cuenta publicitaria"), {
    target: { value: "456" },
  });
  fireEvent.change(screen.getByLabelText("Nombre de cuenta"), {
    target: { value: "Orientación local" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar registro" }));
  await waitFor(() =>
    expect(
      calls.some((v) => v.path === "ads/accounts" && v.init.method === "POST"),
    ).toBe(true),
  );
  const sent = calls.find(
    (v) => v.path === "ads/accounts" && v.init.method === "POST",
  )!;
  expect(new Headers(sent.init.headers).get("X-CSRF-Token")).toBe("p9-csrf");
  expect(
    (sent.body!.document as Record<string, unknown>).provider_verified,
  ).toBeUndefined();
});
it("imports a lead into a local CRM context and links the exact conversation", async () => {
  const { calls } = mount();
  fireEvent.click(await screen.findByRole("button", { name: "Importar lead" }));
  fireEvent.change(screen.getByLabelText("Cuenta publicitaria"), {
    target: { value: "a1" },
  });
  fireEvent.change(screen.getByLabelText("ID del lead"), {
    target: { value: "external1" },
  });
  fireEvent.change(screen.getByLabelText("Nombre del contacto"), {
    target: { value: "Aspirante ficticio" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar registro" }));
  const link = await screen.findByRole("link", { name: "Abrir conversación" });
  expect(link).toHaveAttribute("href", "#/inbox/conversation1");
  expect(screen.getByRole("link", { name: "Ver ficha CRM" })).toHaveAttribute(
    "href",
    "#/clients/conversation1",
  );
  const body = calls.find((v) => v.path === "ads/leads/import")!.body!;
  expect(body.create_conversation).toBe(true);
  expect((body.document as Record<string, unknown>).consent).toBeUndefined();
});
it("keeps unsaved data when navigation is declined", async () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "Importar lead" }));
  fireEvent.change(screen.getByLabelText("Nombre del contacto"), {
    target: { value: "Borrador" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Cuentas publicitarias" }),
  );
  expect(confirm).toHaveBeenCalled();
  expect(screen.getByLabelText("Nombre del contacto")).toHaveValue("Borrador");
});
it("does not process receipts from an unbound account", async () => {
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "Procesamiento" }));
  expect(
    screen.getByRole("button", { name: "Procesar siguiente evento" }),
  ).toBeDisabled();
});
it("hides credential editing from a role without channel settings authority", async () => {
  mount(["ads.manage", "crm.read"]);
  fireEvent.click(
    await screen.findByRole("button", { name: "Cuentas publicitarias" }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /Admisiones local/ }),
  );
  expect(
    screen.queryByLabelText("Token de acceso publicitario"),
  ).not.toBeInTheDocument();
});
it("keeps the same operation id when retrying an unchanged save after a lost response", async () => {
  const { calls, fetcher } = mount();
  await screen.findByRole("button", { name: "Cuentas publicitarias" });
  fireEvent.click(
    screen.getByRole("button", { name: "Cuentas publicitarias" }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Agregar cuenta" }),
  );
  fireEvent.change(screen.getByLabelText("ID de cuenta publicitaria"), {
    target: { value: "456" },
  });
  fireEvent.change(screen.getByLabelText("Nombre de cuenta"), {
    target: { value: "Reintento" },
  });
  fetcher.mockImplementationOnce(async (_input, init) => {
    calls.push({
      path: "lost-save",
      init: init || {},
      body: JSON.parse(String(init?.body)),
    });
    throw new Error("Respuesta perdida");
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar registro" }));
  await screen.findByText("Respuesta perdida");
  fireEvent.click(screen.getByRole("button", { name: "Guardar registro" }));
  await waitFor(() =>
    expect(
      calls.some((v) => v.path === "ads/accounts" && v.init.method === "POST"),
    ).toBe(true),
  );
  expect(calls.find((v) => v.path === "lost-save")!.body!.operation_id).toBe(
    calls.find((v) => v.path === "ads/accounts" && v.init.method === "POST")!
      .body!.operation_id,
  );
});

it("keeps comments visible when a previous lead refresh arrives late", async () => {
  mount();
  await screen.findByRole("button", { name: "Importar lead" });
  let release: (value: Response) => void = () => {};
  const original = vi.mocked(fetch).getMockImplementation()!;
  let defer = false,
    started = false;
  vi.mocked(fetch).mockImplementation((input, init) => {
    const path = String(input);
    if (path.includes("ads/leads?") && defer) {
      defer = false;
      started = true;
      return new Promise<Response>((r) => {
        release = r;
      });
    }
    if (path.includes("ads/comments?"))
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: [
              {
                id: "comment",
                revision: 1,
                external_id: "comment",
                contact_name: "Comentario correcto",
                account_id: "a1",
              },
            ],
            has_more: false,
          }),
          { status: 200 },
        ),
      );
    return original(input, init);
  });
  defer = true;
  fireEvent.click(
    screen.getByRole("button", {
      name: "Actualizar datos locales",
    }),
  );
  await waitFor(() => expect(started).toBe(true));
  fireEvent.click(
    screen.getByRole("button", {
      name: "Comentarios de anuncios",
    }),
  );
  await screen.findByRole("button", { name: /Comentario correcto/ });
  await act(async () => {
    release(
      new Response(
        JSON.stringify({
          items: [{ id: "late", revision: 1, contact_name: "Lead atrasado" }],
          has_more: false,
        }),
        { status: 200 },
      ),
    );
  });
  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: /Lead atrasado/ }),
    ).not.toBeInTheDocument(),
  );
  expect(
    screen.getByRole("button", { name: /Comentario correcto/ }),
  ).toBeInTheDocument();
});

it("does not select a lead in Comments when its discarded editor finishes saving late", async () => {
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "Importar lead" }));
  fireEvent.change(screen.getByLabelText("Cuenta publicitaria"), {
    target: { value: "a1" },
  });
  fireEvent.change(screen.getByLabelText("ID del lead"), {
    target: { value: "pending" },
  });
  fireEvent.change(screen.getByLabelText("Nombre del contacto"), {
    target: { value: "Lead pendiente" },
  });
  const original = vi.mocked(fetch).getMockImplementation()!;
  let release: (value: Response) => void = () => {};
  let started = false;
  vi.mocked(fetch).mockImplementation((input, init) => {
    if (String(input).endsWith("/ads/leads/import")) {
      started = true;
      return new Promise<Response>((r) => {
        release = r;
      });
    }
    return original(input, init);
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar registro" }));
  await waitFor(() => expect(started).toBe(true));
  vi.spyOn(window, "confirm").mockReturnValue(true);
  fireEvent.click(
    screen.getByRole("button", { name: "Comentarios de anuncios" }),
  );
  await screen.findByRole("button", { name: "Importar comentario" });
  await act(async () => {
    release(
      new Response(
        JSON.stringify({
          id: "late",
          revision: 1,
          external_id: "pending",
          contact_name: "Lead pendiente",
          account_id: "a1",
        }),
        { status: 200 },
      ),
    );
  });
  expect(screen.queryByLabelText("Nombre del autor")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Lead pendiente" }),
  ).not.toBeInTheDocument();
});

it("does not show a late processing result inside the lead editor after navigation", async () => {
  mount();
  await screen.findByRole("button", { name: "Importar lead" });
  const original = vi.mocked(fetch).getMockImplementation()!;
  let release: (value: Response) => void = () => {};
  let started = false;
  vi.mocked(fetch).mockImplementation((input, init) => {
    if (String(input).includes("ads/options"))
      return Promise.resolve(
        new Response(
          JSON.stringify({
            accounts: [{ ...account, integration_id: "channel" }],
            integrations: [],
            programs: [],
            stages: [],
          }),
          { status: 200 },
        ),
      );
    if (String(input).endsWith("/ads/accounts/a1/process")) {
      started = true;
      return new Promise<Response>((r) => {
        release = r;
      });
    }
    return original(input, init);
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Actualizar datos locales" }),
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Actualizar datos locales" }),
    ).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText("Cuenta", { selector: "select" }), {
    target: { value: "a1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Procesamiento" }));
  const process = await screen.findByRole("button", {
    name: "Procesar siguiente evento",
  });
  await waitFor(() => expect(process).toBeEnabled());
  fireEvent.click(process);
  await waitFor(() => expect(started).toBe(true));
  fireEvent.click(screen.getByRole("button", { name: "Leads" }));
  await screen.findByRole("button", { name: "Importar lead" });
  await act(async () => {
    release(
      new Response(
        JSON.stringify({
          id: "run1",
          account_id: "a1",
          revision: 1,
          state: "processed",
        }),
        { status: 200 },
      ),
    );
  });
  expect(screen.queryByLabelText("ID del lead")).not.toBeInTheDocument();
});
