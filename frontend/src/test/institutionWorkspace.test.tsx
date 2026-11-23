import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import { WorkspaceP3, RiskSummary } from "../institution/Workspace";
import {
  ConversationRow,
  inboxProgramCode,
} from "../institution/InboxPresentation";
import { explainInboxError } from "../institution/InboxDelivery";
import type { Risk } from "../institution/Workspace";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
import { RuntimeContext, featureNames } from "../shared/runtimeCapabilities";
import { crmConfigurationApi } from "../modules/crm-configuration/api/crmConfigurationApi";
import type { UiCapabilities } from "../shared/runtimeCapabilities";

const ids = [
    "00000000-0000-4000-8000-000000000001",
    "00000000-0000-4000-8000-000000000002",
  ],
  conv = [
    "00000000-0000-4000-8000-000000000003",
    "00000000-0000-4000-8000-000000000004",
  ];
const risk: Risk = {
  status: "unknown",
  level: "unknown",
  score: null,
  source: "not_evaluated",
  asOf: null,
  fresh: false,
  reasons: ["Sin evidencia suficiente."],
  nextAction: "Revisar la conversación.",
  trainedPrediction: false,
};

it.each([
  ["image", "[Adjunto]", "Foto"],
  ["image", "[image]", "Foto"],
  ["image", "Mira nuestro material", "Mira nuestro material"],
  ["video", "[Adjunto]", "Video"],
  ["video", "Recorrido por la sede", "Recorrido por la sede"],
  ["sticker", "[sticker]", "Sticker"],
  ["document", "[Adjunto]", "Documento"],
  ["document", "Guía de inscripción.pdf", "Guía de inscripción.pdf"],
  ["audio", "[Adjunto]", "Audio"],
  [null, "[video]", "Video"],
  [null, "[document]", "Documento"],
])(
  "shows the media icon and readable preview for %s: %s",
  (previewKind, preview, expected) => {
    const { container } = render(
      <ConversationRow
        selected={false}
        onSelect={() => {}}
        row={{
          name: "Contacto",
          phone: "",
          stage: "Nuevo",
          state: "open",
          unread: false,
          assignee: null,
          risk,
          previewKind,
          preview,
        }}
      />,
    );
    expect(screen.getByText(expected)).toBeVisible();
    expect(
      container.querySelector(".inbox-row-preview svg"),
    ).toBeInTheDocument();
    expect(container.querySelector(".inbox-row-preview")).not.toHaveTextContent(
      "[Adjunto]",
    );
  },
);
it("keeps voice-note duration beside the microphone", () => {
  render(
    <ConversationRow
      selected={false}
      onSelect={() => {}}
      row={{
        name: "Contacto",
        phone: "",
        stage: "Nuevo",
        state: "open",
        unread: false,
        assignee: null,
        risk,
        previewKind: "audio",
        preview: "[Adjunto]",
        previewDuration: "65",
      }}
    />,
  );
  expect(screen.getByText("1:05")).toBeVisible();
});
it("distinguishes the receiving account from the sender's phone", () => {
  render(
    <ConversationRow
      selected={false}
      onSelect={() => {}}
      row={{
        name: "Mismo contacto",
        phone: "+573001112244",
        stage: "Nuevo",
        state: "open",
        unread: false,
        assignee: null,
        risk,
        channel: "whatsapp",
        accountName: "WhatsApp · CBN",
        accountPhone: "+57 311 7207294",
      }}
    />,
  );
  expect(screen.getByTitle("Cuenta receptora: WhatsApp · CBN")).toBeVisible();
  expect(screen.queryByText(/311 7207294/)).not.toBeInTheDocument();
});
const config = {
  stages: [{ key: "new", label: "Nueva", probability: null, active: true }],
  tags: ["Interés"],
  fields: [],
};
const session: Session = {
  session_id: "p3-session",
  csrf_token: "csrf-p3",
  actions: [
    "crm.read",
    "crm.write",
    "inbox.read",
    "inbox.write",
    "settings.crm.read",
    "settings.crm.write",
  ],
  user: {
    id: ids[0],
    email: "qa@cbn.local",
    full_name: "Cuenta QA",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const caps: UiCapabilities = {
  version: "cbn-ui-capabilities-v1",
  profile: "foundation",
  mode: "local_foundation",
  modules: ["clients", "inbox", "settings"],
  scope: "isolated_test",
  features: Object.fromEntries(
    featureNames.map((name) => [name, false]),
  ) as UiCapabilities["features"],
};
let failWrite = 0;
let agentOperations = false;
let serverRevision = "1";
let failedDelivery = false;
let quotedReply = false;
let threadMode = "human";
let controlEpoch: string | undefined;
let emptyInbox = false;
let readOnOpen = false;
let firstUnread = true;
let socialProfileEnabled = false;
let followupSignals = false;
const assessedRisk: Risk = {
  ...risk,
  status: "known",
  level: "medium",
  score: 50,
  source: "channel_activity",
  fresh: true,
};
const calls: {
  path: string;
  method: string;
  body: Record<string, unknown> | null;
}[] = [];
function client(index: number) {
  return {
    id: ids[index],
    name: socialProfileEnabled && !index ? "123456789" : "Persona " + index,
    phone: "",
    city: "",
    programId: null,
    program: "",
    schedule: "",
    stage: "Nueva",
    tags: "",
    notes: "",
    type: "",
    interests: "",
    customValues: {},
  };
}
function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
beforeEach(() => {
  failWrite = 0;
  agentOperations = false;
  serverRevision = "1";
  failedDelivery = false;
  quotedReply = false;
  threadMode = "human";
  controlEpoch = undefined;
  emptyInbox = false;
  readOnOpen = false;
  firstUnread = true;
  socialProfileEnabled = false;
  followupSignals = false;
  calls.length = 0;
  vi.mocked(crmConfigurationApi.read).mockResolvedValue({
    config,
    revision: "1",
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input),
        method = init?.method ?? "GET",
        body = init?.body
          ? (JSON.parse(String(init.body)) as Record<string, unknown>)
          : null;
      calls.push({ path, method, body });
      if (path === "/api/v1/agents/selection")
        return response({
          installed: true,
          agents: [],
          stages: [],
          sources: [],
          programs: {
            items: [],
            has_more: false,
            period: { id: 0, label: "Declarado" },
          },
          legacy_agents: [],
        });
      if (path.startsWith("/api/v1/agents/conversations/"))
        return response({
          mode: "human",
          revision: 0,
          contexts: [],
          context_id: null,
          selection: null,
          blocked: "agents_human_control",
        });
      if (method === "PUT" && !failWrite && body?.mode)
        threadMode = String(body.mode);
      if (method === "PUT" && path.endsWith(`${conv[0]}/read`) && !failWrite)
        firstUnread = false;
      if (method !== "GET")
        return failWrite
          ? response(
              {
                detail:
                  failWrite === 409
                    ? "revision_conflict"
                    : "general_storage_unavailable",
              },
              failWrite,
            )
          : response({
              revision: "2",
              contactId: ids[0],
              conversationId: conv[0],
            });
      if (path === "/api/local/crm/configuration")
        return response({ config, revision: "1" });
      if (path.includes("/directory"))
        return response({
          items: [{ id: ids[0], name: "Cuenta QA" }],
          hasMore: false,
        });
      if (path.includes("/messages"))
        return response({
          items: [
            {
              id: ids[1],
              body: "Mensaje registrado",
              direction: "incoming",
              createdAt: "2026-10-26T12:00:00Z",
              sequence: "1",
            },
            ...(quotedReply
              ? [
                  {
                    id: "first-part",
                    body: "Primera idea completa",
                    direction: "outgoing",
                    createdAt: "2026-10-26T12:01:00Z",
                    sequence: "2",
                    replyTo: {
                      id: ids[1],
                      body: "Mensaje registrado",
                      direction: "incoming",
                    },
                  },
                  {
                    id: "next-part",
                    body: "Segunda idea completa",
                    direction: "outgoing",
                    createdAt: "2026-10-26T12:01:03Z",
                    sequence: "3",
                  },
                ]
              : []),
            ...(failedDelivery
              ? [
                  {
                    id: "failed-message",
                    body: "Estado de la solicitud",
                    direction: "outgoing",
                    createdAt: "2026-10-26T12:01:00Z",
                    sequence: "2",
                    deliveryState: "failed",
                    deliveryError: "whatsapp_billing_issue",
                  },
                ]
              : []),
          ],
          hasMore: false,
          before: null,
        });
      if (path.includes("/tasks?"))
        return response({
          items: [],
          total: 0,
          hasMore: false,
          revision: serverRevision,
        });
      if (
        path.endsWith("/groups") ||
        path.includes("/activity?") ||
        path.includes("/notes?")
      )
        return response({ items: [], hasMore: false });
      if (path.endsWith("/social-profile"))
        return response({
          profile: {
            name: "Ana de Messenger",
            username: "",
            avatarUrl: "https://scontent.example.fbcdn.net/avatar.jpg",
          },
        });
      if (path.includes("/conversations/") || path.includes("/detail")) {
        const index = path.includes(conv[1]) ? 1 : 0;
        return response({
          agentOperations,
          controlEpoch,
          readOnOpen,
          mediaAvailable: true,
          channelAccounts: socialProfileEnabled
            ? [{ id: "page", name: "Página de prueba", channel: "messenger" }]
            : undefined,
          client: client(index),
          thread: {
            ConversationId: conv[index],
            ContactId: ids[index],
            State: "open",
            Priority: "normal",
            ControlMode: threadMode,
            Unread: index ? true : firstUnread,
            UserId: null,
          },
          risk: followupSignals ? assessedRisk : risk,
          sla: followupSignals
            ? {
                status: "overdue",
                startedAt: "2026-10-26T12:00:00Z",
                dueAt: "2026-10-26T12:30:00Z",
                thresholdMinutes: 30,
              }
            : undefined,
          manual: null,
          members: [client(index)],
          notes: [],
          revision: serverRevision,
        });
      }
      if (emptyInbox && path.includes("/workspace/inbox?"))
        return response({ items: [], total: 0, hasMore: false, revision: "1" });
      if (
        path.includes("/workspace/clients?") ||
        path.includes("/workspace/inbox?")
      )
        return response({
          items: ids.map((id, index) => ({
            id,
            conversationId: conv[index],
            name: client(index).name,
            phone: "",
            stage: "Nueva",
            state: "open",
            mode: "human",
            unread: index ? true : firstUnread,
            assignee: null,
            channel: index
              ? "instagram"
              : socialProfileEnabled
                ? "messenger"
                : "whatsapp",
            preview: index ? "Consulta por Instagram" : "Hola desde WhatsApp",
            program: index
              ? "Desarrollo Multimedia y Comunicación Gráfica"
              : "Cocina Nacional",
            risk: followupSignals && !index ? assessedRisk : risk,
            slaStatus: followupSignals && !index ? "overdue" : undefined,
          })),
          total: 2,
          offset: 0,
          limit: 25,
          hasMore: false,
          revision: serverRevision,
          unreadByChannel: { whatsapp: Number(firstUnread), instagram: 1 },
          socialProfiles: socialProfileEnabled,
        });
      return response({ detail: "unexpected_test_request" }, 404);
    }),
  );
});
function open(page = "clients", actions = session.actions) {
  const tree = (shownPage: string | null) => (
    <SessionBoundary initial={{ ...session, actions }} expire={() => {}}>
      <RuntimeContext.Provider
        value={{
          status: "ready",
          capabilities: caps,
          reload: () => {},
          actions,
        }}
      >
        <WorkspaceSessionProvider>
          {shownPage && <WorkspaceP3 page={shownPage} />}
        </WorkspaceSessionProvider>
      </RuntimeContext.Provider>
    </SessionBoundary>
  );
  const view = render(tree(page));
  return {
    ...view,
    showWorkspace: (shownPage: string | null) => view.rerender(tree(shownPage)),
  };
}
it("shows a quote only on the reply part that includes the source reference", async () => {
  quotedReply = true;
  open("inbox");
  await select();
  expect(await screen.findByLabelText("Mensaje citado")).toHaveTextContent(
    "Mensaje registrado",
  );
  expect(screen.getAllByLabelText("Mensaje citado")).toHaveLength(1);
  expect(screen.getByText("Primera idea completa")).toBeVisible();
  expect(screen.getByText("Segunda idea completa")).toBeVisible();
});

it("combines Inbox filters on the server and explains a failed delivery in plain Spanish", async () => {
  const dialog = HTMLDialogElement.prototype;
  if (!dialog.showModal) {
    dialog.showModal = function () {
      this.open = true;
    };
    dialog.close = function () {
      this.open = false;
    };
  }
  failedDelivery = true;
  open("inbox");
  expect(await screen.findByText("Hola desde WhatsApp")).toBeVisible();
  fireEvent.click(screen.getByText("Filtros", { exact: true }));
  fireEvent.change(screen.getByLabelText("Canal", { exact: true }), {
    target: { value: "whatsapp" },
  });
  fireEvent.change(screen.getByLabelText("Temperatura", { exact: true }), {
    target: { value: "cold" },
  });
  fireEvent.change(screen.getByLabelText("Estado", { exact: true }), {
    target: { value: "open" },
  });
  fireEvent.change(
    screen.getByLabelText("Riesgo de abandono", { exact: true }),
    { target: { value: "high" } },
  );
  await waitFor(() =>
    expect(
      calls.some(
        ({ path }) =>
          path.includes("channel=whatsapp") &&
          path.includes("temperature=cold") &&
          path.includes("state=open") &&
          path.includes("riskLevel=high"),
      ),
    ).toBe(true),
  );
  await select();
  fireEvent.click(await screen.findByRole("button", { name: "No enviado" }));
  expect(await screen.findByRole("alertdialog")).toHaveTextContent(
    "saldo insuficiente",
  );
  fireEvent.click(screen.getByRole("button", { name: "Cerrar aviso" }));
  fireEvent.click(screen.getByRole("button", { name: "Elegir emoji" }));
  fireEvent.change(screen.getByRole("searchbox", { name: "Buscar emojis" }), {
    target: { value: "sonrisa" },
  });
  fireEvent.click(
    await screen.findByRole("button", { name: "cara sonriendo" }),
  );
  expect(screen.getByLabelText("Mensaje local")).toHaveValue("😀");
  fireEvent.click(screen.getByRole("button", { name: "Adjuntar archivo" }));
  expect(screen.getByRole("button", { name: "Sticker" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Video" })).toBeVisible();
});

it("keeps the CRM panel collapsed across threads and shows each program code", async () => {
  open("inbox");
  expect(await screen.findByText("CN")).toBeVisible();
  expect(screen.getByText("DMC")).toBeVisible();
  await select();
  fireEvent.click(screen.getByRole("button", { name: "Ocultar ficha CRM" }));
  expect(screen.getByLabelText("Nombre visible")).not.toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: /^Persona 1/ }));
  const show = await screen.findByRole("button", { name: "Ver ficha CRM" });
  expect(show).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(show);
  expect(await screen.findByLabelText("Nombre visible")).toBeVisible();
});

it("explains an empty Inbox without offering unavailable pages", async () => {
  emptyInbox = true;
  open("inbox");
  expect(await screen.findByText("Aún no hay conversaciones")).toBeVisible();
  expect(
    screen.getByText("Aquí aparecerán las conversaciones de tus canales."),
  ).toBeVisible();
  expect(screen.queryByRole("button", { name: "Siguiente" })).toBeNull();
});

it("returns from the chat to the list and preserves its unsent draft", async () => {
  open("inbox");
  await select();
  fireEvent.change(screen.getByLabelText("Mensaje local"), {
    target: { value: "Borrador antes de volver" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Volver a conversaciones" }));
  expect(screen.queryByRole("region", { name: "Conversación seleccionada" })).toBeNull();
  expect(screen.getByRole("complementary", { name: "Conversaciones" })).toBeInTheDocument();
  await select();
  expect(screen.getByLabelText("Mensaje local")).toHaveValue("Borrador antes de volver");
  expect(calls.filter(c => c.method === "POST" && c.path.endsWith("/messages"))).toHaveLength(0);
});

it("sends with Enter and the button, inserts a line at the caret with Alt+Enter", async () => {
  open("inbox");
  await select();
  const editor = screen.getByLabelText<HTMLTextAreaElement>("Mensaje local");
  const sent = () =>
    calls.filter(
      ({ method, path }) => method === "POST" && path.endsWith("/messages"),
    );
  fireEvent.keyDown(editor, { key: "Enter" });
  expect(sent()).toHaveLength(0);
  fireEvent.change(editor, { target: { value: "Hola mundo" } });
  editor.setSelectionRange(4, 5);
  fireEvent.keyDown(editor, { key: "Enter", altKey: true });
  expect(editor).toHaveValue("Hola\nmundo");
  expect(editor.selectionStart).toBe(5);
  fireEvent.keyDown(editor, { key: "Enter", isComposing: true });
  expect(sent()).toHaveLength(0);
  fireEvent.keyDown(editor, { key: "Enter" });
  await waitFor(() => expect(editor).toHaveValue(""));
  expect(sent()).toHaveLength(1);
  expect(sent()[0].body?.body).toBe("Hola\nmundo");
  fireEvent.change(editor, { target: { value: "Con el botón" } });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar mensaje local" }),
  );
  await waitFor(() => expect(editor).toHaveValue(""));
  expect(sent()).toHaveLength(2);
  expect(sent()[1].body?.body).toBe("Con el botón");
});

it("shows the chat and CRM skeleton and switches ownership without submitting the priority draft", async () => {
  threadMode = "ai";
  open("inbox");
  expect(
    screen.getByRole("region", { name: "Espacio de conversación" }),
  ).toBeVisible();
  expect(
    screen.getByRole("complementary", { name: "Ficha CRM" }),
  ).toBeVisible();
  await select();
  const toggle = screen.getByRole("switch", { name: "Control humano" });
  expect(toggle).toHaveAttribute("aria-checked", "false");
  expect(screen.getByLabelText("Mensaje local")).toBeDisabled();
  fireEvent.click(screen.getByText("Gestión de conversación"));
  fireEvent.change(screen.getByLabelText("Prioridad"), {
    target: { value: "urgent" },
  });
  fireEvent.click(toggle);
  await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "true"));
  expect(calls.find((call) => call.method === "PUT")?.body?.priority).toBe(
    "normal",
  );
  expect(screen.getByLabelText("Prioridad")).toHaveValue("urgent");
  expect(screen.getByLabelText("Mensaje local")).toBeEnabled();
});

it("sends only the expected control epoch and mode when the chat advertises scoped control", async () => {
  controlEpoch = "7";
  open("inbox");
  await select();
  const toggle = screen.getByRole("switch", { name: "Control humano" });
  expect(toggle).toHaveAttribute("aria-checked", "true");
  serverRevision = "13";
  fireEvent.click(toggle);
  await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "false"));
  const command = calls.find((call) => call.method === "PUT");
  expect(command?.path).toBe(
    `/api/institution/workspace/conversations/${conv[0]}/control`,
  );
  expect(command?.body).toEqual({
    expectedEpoch: "7",
    mode: "ai",
    operationId: expect.any(String),
  });
});

it("opens the contact profile in a labeled dialog", async () => {
  const dialog = HTMLDialogElement.prototype;
  if (!dialog.showModal)
    dialog.showModal = function () {
      this.open = true;
    };
  open("inbox");
  await select();
  fireEvent.click(screen.getByRole("button", { name: "Ver perfil" }));
  const profile = screen.getByRole("dialog", { name: "Persona 0" });
  expect(within(profile).getByText("Nueva")).toBeVisible();
  expect(
    within(profile).getByRole("button", { name: "Cerrar perfil" }),
  ).toBeVisible();
});

it.each([
  ["Cocina Nacional", "CN"],
  ["Desarrollo Multimedia y Comunicación Gráfica", "DMC"],
  ["Salud Oral", "SO"],
  ["Servicios Hoteleros y Agencias Turísticas", "SHAT"],
  ["Auxiliar de Enfermería", "AE"],
])("uses the institution's initials for %s", (program, code) => {
  expect(inboxProgramCode(program)).toBe(code);
});
async function select(index = 0) {
  fireEvent.click(
    await screen.findByRole("button", {
      name: new RegExp(`^Persona ${index}`),
    }),
  );
  await screen.findByLabelText("Nombre visible");
}

it("shows the same measured risk beside the chat and the SLA in its CRM panel", async () => {
  followupSignals = true;
  open("inbox");
  expect(await screen.findByText("Abandono medio · 50/100")).toHaveAttribute(
    "data-risk",
    "medium",
  );
  expect(screen.getByText("SLA vencido")).toBeInTheDocument();
  await select();
  const sla = within(
    screen.getByRole("region", { name: "Tiempo de respuesta (SLA)" }),
  );
  expect(sla.getByText("Vencido")).toHaveAttribute("data-sla", "overdue");
  expect(sla.getByText("Plazo institucional de 30 min")).toBeInTheDocument();
  expect(
    sla.getByRole("link", { name: "Configurar plazo institucional" }),
  ).toHaveAttribute("href", "#/settings/crm");
  expect(
    screen.getByRole("meter", { name: "Puntaje de abandono" }),
  ).toHaveAttribute("value", "50");
});

it("mounts the P5 agent selector in the actual institutional Inbox", async () => {
  agentOperations = true;
  open("inbox");
  await select();
  await screen.findByRole("heading", {
    name: "Agentes de admisiones",
  });
  expect(calls.some((c) => c.path === "/api/v1/agents/selection")).toBe(true);
  expect(screen.getAllByLabelText("Nombre visible")).toHaveLength(1);
});

it("shows unknown safely and identifies a current rule without probability", () => {
  const view = render(<RiskSummary risk={risk} />);
  expect(screen.getByText("Sin evaluación")).toBeInTheDocument();
  expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
  view.rerender(
    <RiskSummary
      risk={{
        ...risk,
        status: "known",
        fresh: true,
        level: "high",
        score: 80,
        source: "rule",
        asOf: "2026-10-26T12:00:00Z",
      }}
    />,
  );
  expect(screen.getByText("Alto")).toBeInTheDocument();
  expect(screen.getByText("Rúbrica de seguimiento")).toBeInTheDocument();
  expect(
    screen.getByRole("meter", { name: "Puntaje de abandono" }),
  ).toHaveAttribute("value", "80");
  expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
});

it("explains RinovaPlus request throttling without blaming the channel", () => {
  const guidance = explainInboxError({
    code: "rate_limited",
    status: 429,
    message: "",
  });
  expect(guidance.title).toBe("Límite temporal de solicitudes");
  expect(guidance.nextStep).toMatch(/pulsa Enviar de nuevo/);
});
it("sends filters to the paginated API and never loads the old workspace snapshot", async () => {
  open();
  await select();
  fireEvent.change(screen.getByLabelText("Buscar", { exact: true }), {
    target: { value: "Última persona" },
  });
  await waitFor(() =>
    expect(
      calls.some((call) => call.path.includes("q=%C3%9Altima+persona")),
    ).toBe(true),
  );
  expect(calls.some((call) => call.path === "/api/local/crm")).toBe(false);
});
it("preserves the contact draft on a conflict and when selecting another contact", async () => {
  open();
  await select();
  const input = screen.getByLabelText("Nombre visible");
  fireEvent.change(input, { target: { value: "Borrador conservado" } });
  failWrite = 409;
  fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
  await screen.findByText(/Hay una versión más reciente/);
  expect(input).toHaveValue("Borrador conservado");
  await select(1);
  await select(0);
  expect(screen.getByLabelText("Nombre visible")).toHaveValue(
    "Borrador conservado",
  );
});
it("retains message and control drafts and the same command after an uncertain response", async () => {
  const view = open("inbox");
  await select();
  fireEvent.change(screen.getByLabelText("Mensaje local"), {
    target: { value: "Mensaje pendiente" },
  });
  fireEvent.change(screen.getByLabelText("Prioridad", { exact: true }), {
    target: { value: "high" },
  });
  failWrite = 503;
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar mensaje local" }),
  );
  await screen.findByText(/No se pudo validar el acceso/);
  const first = calls.find(
    (call) => call.method === "POST" && call.path.endsWith("/messages"),
  )!;
  serverRevision = "2";
  view.showWorkspace(null);
  view.showWorkspace("inbox");
  await select(0);
  expect(screen.getByLabelText("Mensaje local")).toHaveValue(
    "Mensaje pendiente",
  );
  expect(screen.getByLabelText("Prioridad", { exact: true })).toHaveValue(
    "high",
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar mensaje local" }),
  );
  await waitFor(() =>
    expect(
      calls.filter(
        (call) => call.method === "POST" && call.path.endsWith("/messages"),
      ),
    ).toHaveLength(2),
  );
  const last = calls
    .filter((call) => call.method === "POST" && call.path.endsWith("/messages"))
    .at(-1)!;
  expect(last.body?.operationId).toBe(first.body?.operationId);
  expect(first.body?.revision).toBe("1");
  expect(last.body?.revision).toBe("1");
});
it("keeps a ficha draft across unmount and explicitly rebases a rejected conflict", async () => {
  const view = open();
  await select();
  fireEvent.change(screen.getByLabelText("Nombre visible"), {
    target: { value: "Edición conservada" },
  });
  failWrite = 409;
  fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
  await screen.findByText(/Hay una versión más reciente/);
  const first = calls.find(
    (call) => call.method === "PUT" && call.path.includes("/clients/"),
  )!;
  serverRevision = "2";
  view.showWorkspace(null);
  view.showWorkspace("clients");
  await select();
  expect(screen.getByLabelText("Nombre visible")).toHaveValue(
    "Edición conservada",
  );
  failWrite = 0;
  fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
  await waitFor(() =>
    expect(
      calls.filter(
        (call) => call.method === "PUT" && call.path.includes("/clients/"),
      ),
    ).toHaveLength(2),
  );
  const last = calls
    .filter((call) => call.method === "PUT" && call.path.includes("/clients/"))
    .at(-1)!;
  expect(last.body?.operationId).not.toBe(first.body?.operationId);
  expect(last.body?.revision).toBe("2");
});
it("creates only with the institution's configured stage and a valid visible name", async () => {
  open();
  await screen.findByRole("button", { name: /^Persona 0/ });
  fireEvent.click(
    await screen.findByRole("button", { name: "Nuevo contacto" }),
  );
  const save = await screen.findByRole("button", {
    name: "Guardar ficha",
  });
  fireEvent.click(save);
  expect(calls.some((call) => call.method !== "GET")).toBe(false);
  fireEvent.change(screen.getByLabelText("Nombre visible"), {
    target: { value: "Persona nueva" },
  });
  expect(
    within(save.closest("form")!).getByLabelText("Etapa", { exact: true }),
  ).toHaveValue("Nueva");
  expect(save).toBeEnabled();
  fireEvent.click(save);
  await waitFor(() =>
    expect(
      calls.some(
        (call) =>
          call.method === "POST" &&
          (call.body?.client as { stage: string })?.stage === "Nueva",
      ),
    ).toBe(true),
  );
});
it("disables mutations for a read only human session", async () => {
  open("inbox", ["crm.read", "inbox.read", "settings.crm.read"]);
  await select();
  expect(screen.getByLabelText("Nombre visible")).toBeDisabled();
  fireEvent.click(screen.getByText("Gestión de conversación"));
  expect(screen.getByRole("switch", { name: "Control humano" })).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Guardar mensaje local" }),
  ).toBeDisabled();
});
it("marks read through the actual loaded message sequence", async () => {
  open("inbox");
  await select();
  await screen.findByText("Mensaje registrado");
  fireEvent.click(screen.getByText("Gestión de conversación"));
  fireEvent.click(screen.getByRole("button", { name: "Marcar como leída" }));
  await waitFor(() =>
    expect(
      calls.some(
        (call) =>
          call.method === "PUT" &&
          call.body?.readThrough === "1" &&
          call.body?.unread === false,
      ),
    ).toBe(true),
  );
});
it("clears the selected conversation and unread counter when its messages load", async () => {
  readOnOpen = true;
  open("inbox");
  expect(await screen.findByText("2 sin leer")).toBeVisible();
  const row = await screen.findByRole("button", { name: /^Persona 0/ });
  expect(row).toHaveAttribute("data-unread");
  fireEvent.click(row);
  await screen.findByText("Mensaje registrado");
  expect(await screen.findByText("1 sin leer")).toBeVisible();
  expect(row).not.toHaveAttribute("data-unread");
  expect(row).not.toHaveTextContent("Sin leer");
  expect(screen.getByRole("button", { name: /^Persona 1/ })).toHaveAttribute(
    "data-unread",
  );
  const writes = calls.filter((call) => call.method === "PUT");
  expect(writes).toHaveLength(1);
  expect(writes[0].path).toMatch(/\/read$/);
  expect(writes[0].body).toEqual({
    operationId: expect.any(String),
    readThrough: "1",
  });
});
it("shows the Meta profile in an opened conversation and its Inbox row", async () => {
  socialProfileEnabled = true;
  open("inbox");
  fireEvent.click(
    await screen.findByRole("button", { name: /^Contacto de Messenger/ }),
  );
  await screen.findByRole("heading", { name: "Ana de Messenger" });
  const row = screen.getByRole("button", { name: /^Ana de Messenger/ });
  expect(row.querySelector("img")).toHaveAttribute(
    "src",
    "https://scontent.example.fbcdn.net/avatar.jpg",
  );
});
it("shows one editable ficha without a duplicated read only contact block", async () => {
  open("inbox");
  await select();
  expect(screen.getAllByLabelText("Nombre visible")).toHaveLength(1);
  expect(
    screen.getAllByRole("heading", { name: "Ficha del contacto" }),
  ).toHaveLength(1);
  expect(
    within(
      screen.getByRole("region", { name: "Riesgo de abandono" }),
    ).getByText("Sin evaluación"),
  ).toBeInTheDocument();
});
