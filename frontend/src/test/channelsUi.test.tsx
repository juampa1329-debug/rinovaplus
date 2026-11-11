import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "../App";
import {
  RuntimeProvider,
  channelCapabilityNames,
  featureNames,
  validateCapabilities,
  type ChannelsCapabilities,
} from "../shared/runtimeCapabilities";
import { channelKeys, type ChannelAccount } from "../shared/channels";
import { clientsApi } from "../modules/clients/api/clientsApi";
import { crmConfigurationApi } from "../modules/crm-configuration/api/crmConfigurationApi";

const manifest: ChannelsCapabilities = {
  version: "cbn-ui-capabilities-v2",
  profile: "channels",
  mode: "local_channels_ui",
  modules: ["settings"],
  scope: "restored_rehearsal_only",
  features: Object.fromEntries(
    featureNames.map((k) => [k, false]),
  ) as ChannelsCapabilities["features"],
  channels: Object.fromEntries(
    channelCapabilityNames.map((k) => [
      k,
      ["configuration", "stageOptions", "status", "comments"].includes(k),
    ]),
  ) as ChannelsCapabilities["channels"],
};
let accounts: ChannelAccount[];
let failPath: string;
let failPut: number;
let conflict: boolean;
let malformedSave: boolean;
const reply = (value: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(value), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
function fixture(caps = manifest) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === failPath) return new Response("{}", { status: 503 });
      if (path === "/api/local/runtime") return reply(caps);
      if (path === "/api/v1/channels") return reply({ channels: accounts });
      if (path === "/api/local/channels/stages")
        return reply({ stages: ["Nuevo", "En seguimiento"] });
      if (path === "/api/v1/channels/transport/status")
        return reply({
          outboundRecords: 1,
          receiptRecords: 1,
          transportEnabled: false,
          workersEnabled: false,
        });
      if (path.startsWith("/api/v1/social-comments"))
        return reply({
          comments: [
            {
              id: "c9-comment",
              channel: "instagram",
              body: "<script>synthetic</script>",
              receivedAt: "2026-10-25T12:00:00Z",
            },
          ],
        });
      const match = path.match(
        /^\/api\/v1\/channels\/(whatsapp|instagram|messenger|facebook|tiktok)(\/draft)?$/,
      );
      if (match) {
        const index = accounts.findIndex((a) => a.channel === match[1]);
        if (init?.method === "PUT") {
          if (failPut === -1) throw new TypeError("Failed to fetch");
          if (conflict) {
            accounts[index] = {
              ...accounts[index],
              revision: accounts[index].revision + 1,
            };
            return reply({ detail: "channel_configuration_changed" }, 409);
          }
          if (failPut)
            return reply({ detail: "channels_storage_unavailable" }, failPut);
          const body = JSON.parse(String(init.body));
          accounts[index] = {
            ...accounts[index],
            revision: accounts[index].revision + 1,
            configuration: body.configuration,
          };
          return reply(
            malformedSave
              ? { ...accounts[index], channel: "facebook" }
              : accounts[index],
          );
        }
        return reply(accounts[index]);
      }
      throw new Error("Unexpected request: " + path);
    }),
  );
}
const app = () =>
  render(
    <RuntimeProvider>
      <App />
    </RuntimeProvider>,
  );
async function openWhatsapp() {
  await screen.findByRole("heading", { name: "Meta WhatsApp Cloud" });
  fireEvent.click(
    screen.getAllByRole("button", { name: "Ver configuración" })[0],
  );
  return screen.getByRole("form", { name: "Configuración de WhatsApp" });
}
beforeEach(() => {
  window.location.hash = "/settings";
  failPath = "";
  failPut = 0;
  conflict = false;
  malformedSave = false;
  accounts = channelKeys.map((channel) => ({
    channel,
    configuration: {},
    revision: 0,
    state: "unconfigured",
    credentials: [],
    capabilities: {},
    lastError: null,
    verifiedAt: null,
  }));
  fixture();
});
afterEach(() => vi.unstubAllGlobals());

it.each([
  { ...manifest, version: "cbn-ui-capabilities-v1" },
  { ...manifest, mode: "local_channels" },
  { ...manifest, modules: ["settings", "inbox"] },
  { ...manifest, scope: "institutional" },
  { ...manifest, extra: true },
  { ...manifest, features: { ...manifest.features, academic: true } },
  ...[
    "credentials",
    "providerActions",
    "externalDelivery",
    "publicWebhooks",
    "workers",
  ].map((k) => ({
    ...manifest,
    channels: { ...manifest.channels, [k]: true },
  })),
  { ...manifest, channels: { ...manifest.channels, extra: false } },
  { ...manifest, channels: { ...manifest.channels, status: "yes" } },
])("rejects unsafe v2 capability manifest %#", (value) =>
  expect(() => validateCapabilities(value)).toThrow(),
);
it("accepts the exact UI-only manifest", () =>
  expect(validateCapabilities(manifest)).toEqual(manifest));
it("keeps the Scentra connection groups visible without enabling provider requests", async () => {
  app();
  const form = await openWhatsapp();
  expect(screen.getByText("Verificar número WhatsApp")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Instagram Business" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Facebook Messenger" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Webhooks")).toBeInTheDocument();
  const pending = within(form).getByText(
    "Conexión, credenciales y diagnóstico",
  );
  fireEvent.click(pending);
  const action = within(form).getByRole("button", {
    name: "Guardar integración y credenciales",
  });
  expect(action).toBeDisabled();
  const count = vi.mocked(fetch).mock.calls.length;
  fireEvent.click(action);
  expect(vi.mocked(fetch).mock.calls.length).toBe(count);
});
it("skips to main content without changing the route", async () => {
  app();
  await screen.findByRole("heading", { name: /^Canales$/ });
  fireEvent.click(screen.getByRole("link", { name: "Saltar al contenido" }));
  expect(document.activeElement).toBe(document.getElementById("channels-main"));
  expect(window.location.hash).toBe("#/settings");
});
it("selects the channels shell before mounting CRM owners", async () => {
  app();
  await openWhatsapp();
  expect(clientsApi.workspace).not.toHaveBeenCalled();
  expect(crmConfigurationApi.read).not.toHaveBeenCalled();
  expect(screen.queryByLabelText(/token|secret/i)).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", {
      name: /Validar acceso|Enviar prueba|Suscribir/i,
    }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("<script>synthetic</script>")).toBeInTheDocument();
  expect(document.querySelector("script")).not.toBeInTheDocument();
});
it("sends only the configuration draft and reads back saved revision", async () => {
  app();
  const form = await openWhatsapp();
  fireEvent.change(within(form).getByLabelText("Meta App ID"), {
    target: { value: "C9_TEST" },
  });
  fireEvent.click(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  );
  await screen.findByText("Configuración guardada en la copia de ensayo.");
  const call = vi
    .mocked(fetch)
    .mock.calls.find(([, init]) => init?.method === "PUT")!;
  const body = JSON.parse(String(call[1]?.body));
  expect(Object.keys(body).sort()).toEqual(["configuration", "revision"]);
  expect(Object.keys(body.configuration)).not.toContain("accessToken");
  expect(body.revision).toBe(0);
  expect(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  ).toBeDisabled();
});
it("retains a conflicting draft until explicit discard", async () => {
  conflict = true;
  app();
  const form = await openWhatsapp();
  fireEvent.change(within(form).getByLabelText("Meta App ID"), {
    target: { value: "KEEP_ME" },
  });
  fireEvent.click(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  );
  await screen.findByText(/Hay una versión más reciente/);
  expect(within(form).getByLabelText("Meta App ID")).toHaveValue("KEEP_ME");
  expect(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  ).toBeDisabled();
  fireEvent.click(
    within(form).getByRole("button", {
      name: "Descartar borrador y cargar datos guardados",
    }),
  );
  expect(within(form).getByLabelText("Meta App ID")).toHaveValue("");
});
it("retains an offline draft and permits retry after confirmed unchanged revision", async () => {
  failPut = 503;
  app();
  const form = await openWhatsapp();
  fireEvent.change(within(form).getByLabelText("Meta App ID"), {
    target: { value: "KEEP_ME" },
  });
  fireEvent.click(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  );
  await screen.findByText(/No se pudo acceder a los canales/);
  expect(within(form).getByLabelText("Meta App ID")).toHaveValue("KEEP_ME");
  expect(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  ).toBeEnabled();
});
it("explains a network failure in Spanish while retaining the draft", async () => {
  failPut = -1;
  app();
  const form = await openWhatsapp();
  fireEvent.change(within(form).getByLabelText("Meta App ID"), {
    target: { value: "KEEP_ME" },
  });
  fireEvent.click(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  );
  await screen.findByText(/No se pudo acceder al servicio/);
  expect(within(form).getByLabelText("Meta App ID")).toHaveValue("KEEP_ME");
});
it("blocks retry when an uncertain write cannot be read back", async () => {
  failPut = 503;
  failPath = "/api/v1/channels/whatsapp";
  app();
  const form = await openWhatsapp();
  fireEvent.change(within(form).getByLabelText("Meta App ID"), {
    target: { value: "KEEP_ME" },
  });
  fireEvent.click(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  );
  await screen.findByText(/No se pudo confirmar la versión/);
  expect(within(form).getByLabelText("Meta App ID")).toHaveValue("KEEP_ME");
  expect(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  ).toBeDisabled();
});
it("rejects a save response for a different account and keeps draft", async () => {
  malformedSave = true;
  app();
  const form = await openWhatsapp();
  fireEvent.change(within(form).getByLabelText("Meta App ID"), {
    target: { value: "KEEP_ME" },
  });
  fireEvent.click(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  );
  await screen.findByText(/La respuesta de Canales no es válida/);
  expect(within(form).getByLabelText("Meta App ID")).toHaveValue("KEEP_ME");
  expect(
    within(form).getByRole("button", { name: "Guardar configuración" }),
  ).toBeDisabled();
});
it.each([
  "/api/v1/channels",
  "/api/local/channels/stages",
  "/api/v1/channels/transport/status",
  "/api/v1/social-comments?offset=0&limit=25",
])("shows section failure for %s", async (path) => {
  failPath = path;
  app();
  await waitFor(() =>
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0),
  );
});
it("respects disabled optional capabilities and configuration", async () => {
  fixture({
    ...manifest,
    channels: {
      ...manifest.channels,
      configuration: false,
      stageOptions: false,
      status: false,
      comments: false,
    },
  });
  app();
  const form = await openWhatsapp();
  expect(
    within(form).queryByRole("button", { name: "Guardar configuración" }),
  ).not.toBeInTheDocument();
  expect(within(form).getByLabelText("Meta App ID")).toBeDisabled();
  expect(vi.mocked(fetch).mock.calls.map(([path]) => String(path))).toEqual([
    "/api/local/runtime",
    "/api/v1/channels",
  ]);
});
it("blocks deep links without mounting CRM or channels owners", async () => {
  window.location.hash = "/inbox";
  app();
  await screen.findByText("Sección no habilitada");
  expect(clientsApi.workspace).not.toHaveBeenCalled();
  expect(vi.mocked(fetch).mock.calls).toHaveLength(1);
});
it("keeps collapsed drafts through refresh", async () => {
  app();
  const form = await openWhatsapp();
  fireEvent.change(within(form).getByLabelText("Meta App ID"), {
    target: { value: "KEEP_ME" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
  fireEvent.click(screen.getByRole("button", { name: "Actualizar datos" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Actualizar datos" }),
    ).toBeEnabled(),
  );
  fireEvent.click(
    screen.getAllByRole("button", { name: "Ver configuración" })[0],
  );
  expect(within(form).getByLabelText("Meta App ID")).toHaveValue("KEEP_ME");
});
