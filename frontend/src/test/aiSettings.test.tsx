import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import type { ReactNode } from "react";
import {
  act,
  fireEvent,
  render as renderReact,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { AiSettingsPanel } from "../modules/ai/components/AiSettingsPanel";
import type { AiSnapshot } from "../shared/aiSettings";

function render(ui: ReactNode) {
  return renderReact(ui, { wrapper: WorkspaceSessionProvider });
}
async function providerEditor(
  user: ReturnType<typeof userEvent.setup>,
  name = "Google / Gemini",
) {
  const add = screen.queryByRole("button", { name: `Añadir ${name}` });
  if (add) await user.click(add);
  else if (!screen.queryByRole("button", { name: `Ocultar ${name}` }))
    await user.click(
      await screen.findByRole("button", { name: `Añadir ${name}` }),
    );
  return within(screen.getByRole("heading", { name }).closest("article")!);
}

function initialSnapshot(): AiSnapshot {
  return {
    revision: 0,
    outbound_enabled: true,
    credential_revision: 0,
    credential_storage_available: true,
    providers: [
      {
        id: "gemini",
        configured: true,
        environment_variable: "GEMINI_API_KEY",
        credential_source: "environment",
      },
      {
        id: "xai",
        configured: true,
        environment_variable: "XAI_API_KEY",
        credential_source: "environment",
      },
      {
        id: "openrouter",
        configured: false,
        environment_variable: "OPENROUTER_API_KEY",
        credential_source: "none",
      },
    ],
    settings: {
      enabled: false,
      provider: "gemini",
      model: "",
      fallback_enabled: false,
      fallback_model: "",
      backup_provider: null,
      backup_model: "",
      backup_fallback_model: "",
      system_prompt: "Estilo ficticio",
      max_tokens: 700,
      temperature: 0.5,
      brief_responses: true,
      split_responses: true,
      wait_seconds: 6,
      typing_ms: 2600,
      chars_per_message: 180,
      fragment_delay_ms: 9000,
      output_tokens: 700,
      recent_messages: 16,
      history_chars: 1200,
      show_typing: true,
    },
  };
}

let stored: AiSnapshot;
const originalShowModal = Object.getOwnPropertyDescriptor(
  HTMLDialogElement.prototype,
  "showModal",
);
const originalClose = Object.getOwnPropertyDescriptor(
  HTMLDialogElement.prototype,
  "close",
);
afterAll(() => {
  for (const [name, descriptor] of [
    ["showModal", originalShowModal],
    ["close", originalClose],
  ] as const) {
    if (descriptor)
      Object.defineProperty(HTMLDialogElement.prototype, name, descriptor);
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name);
  }
});
let requests: { url: string; body?: Record<string, unknown>; method: string }[];
beforeEach(() => {
  // jsdom omits native dialog lifecycle; only open/close state is simulated.
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value(this: HTMLDialogElement) {
        this.open = true;
      },
    },
    close: {
      configurable: true,
      value(this: HTMLDialogElement) {
        this.open = false;
      },
    },
  });
  stored = initialSnapshot();
  requests = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input),
      method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    requests.push({ url, method, body });
    expect(init?.headers).toMatchObject({ "X-CRM-Local": "1" });
    let data: unknown = stored;
    if (url === "/api/v1/channels") data = { channels: [] };
    else if (url.endsWith("/conversation"))
      data = { conversation_id: "a".repeat(32) };
    else if (!url.startsWith("/api/ai/"))
      throw new Error(`Unexpected mocked route: ${url}`);
    if (method === "PUT" && url.endsWith("/settings")) {
      stored = {
        ...stored,
        settings: body.settings,
        revision: stored.revision + 1,
      };
      data = stored;
    }
    if (url.includes("credentials/")) {
      stored = {
        ...stored,
        credential_revision: stored.credential_revision + 1,
        providers: stored.providers.map((provider) =>
          url.endsWith(provider.id)
            ? { ...provider, configured: true, credential_source: "local" }
            : provider,
        ),
      };
      data = stored;
    }
    if (url.endsWith("/outbound")) {
      stored = {
        ...stored,
        credential_revision: stored.credential_revision + 1,
        outbound_enabled: body.enabled,
      };
      data = stored;
    }
    if (url.includes("models/") && !stored.outbound_enabled)
      return new Response(JSON.stringify({ code: "outbound_disabled" }), {
        status: 409,
      });
    if (url.includes("models/"))
      data = {
        models: [
          {
            id: "model-a",
            name: "Modelo A",
            output_limit: 8000,
            temperature: true,
            max_temperature: 2,
          },
          {
            id: "model-b",
            name: "Modelo B",
            output_limit: 8000,
            temperature: true,
            max_temperature: 2,
          },
        ],
      };
    if (url.endsWith("/test"))
      data = {
        revision: stored.revision,
        provider: stored.settings.provider,
        model: stored.settings.model,
        text: "Respuesta ficticia",
        attempts: [{ provider: "gemini", model: "model-a", status: "success" }],
        plan: [{ text: "Respuesta ficticia", after_ms: 8600 }],
        history_messages_used: 0,
        effective_output_tokens: 700,
        typing_requested: true,
        typing_available: false,
        delivered: false,
      };
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
});

describe("local AI settings", () => {
  it("finishes an in-flight save after route return but cannot repopulate a reset session owner", async () => {
    const respond = vi.mocked(fetch).getMockImplementation()!;
    let finish: (() => Promise<void>) | undefined;
    vi.mocked(fetch).mockImplementation((input, init) => {
      if (init?.method !== "PUT") return respond(input, init);
      return new Promise<Response>((resolve) => {
        finish = async () => resolve(await respond(input, init));
      });
    });
    const user = userEvent.setup();
    const view = render(<AiSettingsPanel section="IA" active />);
    fireEvent.change(
      await screen.findByLabelText("System prompt · Instrucciones de estilo"),
      { target: { value: "First explicit save" } },
    );
    await user.click(
      screen.getByRole("button", {
        name: /^(Guardar ajustes IA|Validar y guardar IA)$/,
      }),
    );
    view.rerender(null);
    view.rerender(<AiSettingsPanel section="IA" active />);
    expect(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
    ).toBeDisabled();
    await act(async () => {
      await finish!();
    });
    await waitFor(() =>
      expect(
        screen.getByLabelText("System prompt · Instrucciones de estilo"),
      ).toBeEnabled(),
    );
    expect(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
    ).toHaveValue("First explicit save");
    expect(stored.revision).toBe(1);
    fireEvent.change(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
      { target: { value: "Second explicit save" } },
    );
    await user.click(
      screen.getByRole("button", {
        name: /^(Guardar ajustes IA|Validar y guardar IA)$/,
      }),
    );
    view.unmount();
    render(<AiSettingsPanel section="IA" active />);
    fireEvent.change(
      await screen.findByLabelText("System prompt · Instrucciones de estilo"),
      { target: { value: "New session draft" } },
    );
    await act(async () => {
      await finish!();
    });
    expect(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
    ).toHaveValue("New session draft");
    expect(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
    ).toBeEnabled();
    expect(stored.revision).toBe(2);
  });
  it("retains pending IA configuration and catalog across route unmounts without writing or testing implicitly", async () => {
    const user = userEvent.setup();
    const view = render(<AiSettingsPanel section="IA" active />);
    fireEvent.change(
      await screen.findByLabelText("System prompt · Instrucciones de estilo"),
      { target: { value: "Pending style in RAM" } },
    );
    fireEvent.change(screen.getByLabelText("Mensaje"), {
      target: { value: "Pending synthetic prompt" },
    });
    view.rerender(null);
    const leave = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(leave);
    expect(leave.defaultPrevented).toBe(true);
    view.rerender(<AiSettingsPanel section="IA" active />);
    expect(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
    ).toHaveValue("Pending style in RAM");
    expect(screen.getByLabelText("Mensaje")).toHaveValue(
      "Pending synthetic prompt",
    );
    view.rerender(<AiSettingsPanel section="APIs" active />);
    await user.click(
      (await providerEditor(user)).getByRole("button", {
        name: "Cargar modelos",
      }),
    );
    await screen.findByRole("option", { name: /Modelo A/ });
    view.rerender(null);
    view.rerender(<AiSettingsPanel section="APIs" active />);
    expect(screen.queryByLabelText("Modelo")).not.toBeInTheDocument();
    await providerEditor(user);
    expect(
      screen.getByRole("option", { name: /Modelo A/ }),
    ).toBeInTheDocument();
    expect(
      requests.filter((item) => item.url.includes("models/")),
    ).toHaveLength(1);
    expect(
      requests.filter((item) => item.url.endsWith("/settings")),
    ).toHaveLength(4);
    expect(
      requests.some(
        (item) => item.method === "PUT" || item.url.endsWith("/test"),
      ),
    ).toBe(false);
    view.rerender(<AiSettingsPanel section="IA" active />);
    await user.click(
      screen.getByRole("button", { name: "Descartar cambios IA" }),
    );
    expect(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
    ).toHaveValue(stored.settings.system_prompt);
    expect(JSON.stringify(localStorage)).not.toContain("Pending style in RAM");
  });
  it("loads every screenshot control and saves nonsecret configuration across remount", async () => {
    const user = userEvent.setup();
    const view = render(<AiSettingsPanel section="IA" active />);
    const prompt = await screen.findByLabelText(
      "System prompt · Instrucciones de estilo",
    );
    fireEvent.change(prompt, { target: { value: "Texto sintético" } });
    expect(screen.getByText(/15 \/ 8000 caracteres/)).toBeVisible();
    for (const label of [
      "Máximo de tokens por solicitud",
      "Temperatura",
      "Espera antes de responder (seg)",
      "Tiempo de escritura antes del primer envío (ms)",
      "Caracteres por mensaje",
      "Espera entre fragmentos (ms)",
      "Máximo de tokens de salida",
      "Mensajes recientes",
      "Caracteres por mensaje histórico",
    ])
      expect(screen.getByLabelText(label)).toBeVisible();
    await user.click(
      screen.getByRole("button", {
        name: /^(Guardar ajustes IA|Validar y guardar IA)$/,
      }),
    );
    expect(
      await screen.findByText(/Ajustes guardados\. IA permanece deshabilitada/),
    ).toBeVisible();
    view.unmount();
    render(<AiSettingsPanel section="IA" active />);
    expect(
      await screen.findByLabelText("System prompt · Instrucciones de estilo"),
    ).toHaveValue("Texto sintético");
    expect(stored.settings.enabled).toBe(false);
    expect(requests.filter((item) => item.method === "PUT")).toHaveLength(1);
    expect(JSON.stringify(requests)).not.toContain("api_key");
  });
  it("loads actual catalog options, shares IA/APIs draft, then tests only saved config", async () => {
    const user = userEvent.setup();
    const view = render(<AiSettingsPanel section="APIs" active />);
    await user.click(
      (await providerEditor(user)).getByRole("button", {
        name: "Cargar modelos",
      }),
    );
    await user.selectOptions(await screen.findByLabelText("Modelo"), "model-a");
    await user.click(
      (await providerEditor(user)).getByRole("button", {
        name: "Guardar modelo",
      }),
    );
    await waitFor(() => expect(stored.settings.model).toBe("model-a"));
    view.rerender(<AiSettingsPanel section="IA" active />);
    await user.click(
      screen.getByRole("checkbox", {
        name: "IA habilitada para el Asistente",
      }),
    );
    await user.click(
      screen.getByRole("checkbox", {
        name: "Permitir fallback por modelo y proveedor de respaldo",
      }),
    );
    await user.selectOptions(
      screen.getByLabelText("Fallback del modelo principal"),
      "model-b",
    );
    expect(
      screen.getByRole("button", { name: "Probar IA con ajustes guardados" }),
    ).toBeDisabled();
    await user.click(
      screen.getByRole("button", {
        name: /^(Guardar ajustes IA|Validar y guardar IA)$/,
      }),
    );
    fireEvent.change(screen.getByLabelText("Mensaje"), {
      target: { value: "Explicit test input" },
    });
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Probar IA con ajustes guardados" }),
      ).toBeEnabled(),
    );
    await user.click(
      screen.getByRole("button", { name: "Probar IA con ajustes guardados" }),
    );
    expect(
      await screen.findByRole("heading", {
        name: "Plan de fragmentos",
      }),
    ).toBeVisible();
    expect(screen.getByText("8.6 s")).toBeVisible();
    expect(screen.getByText(/2 mensajes en el historial/)).toBeVisible();
    expect(requests.at(-1)?.body).toMatchObject({ revision: 2, history: [] });
    fireEvent.change(screen.getByLabelText("Temperatura"), {
      target: { value: "0.8" },
    });
    expect(screen.queryByText("Respuesta ficticia")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Probar IA con ajustes guardados" }),
    ).toBeDisabled();
  });
  it("clears incompatible model choices on provider change and warns before reload", async () => {
    const user = userEvent.setup();
    stored.settings.model = "old-model";
    render(<AiSettingsPanel section="IA" active />);
    await user.selectOptions(
      await screen.findByLabelText("Proveedor principal"),
      "xai",
    );
    expect(screen.queryByText("old-model")).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Recargar ajustes IA" }),
    );
    expect(
      screen.getByRole("button", { name: "Confirmar recarga" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Conservar cambios" }));
    expect(screen.getByLabelText("Proveedor principal")).toHaveValue("xai");
    await user.click(
      screen.getByRole("button", { name: "Descartar cambios IA" }),
    );
    expect(screen.getByLabelText("Proveedor principal")).toHaveValue("gemini");
  });
  it("shows sanitized conflict error and retains unsaved values", async () => {
    const user = userEvent.setup();
    render(<AiSettingsPanel section="IA" active />);
    fireEvent.change(
      await screen.findByLabelText("System prompt · Instrucciones de estilo"),
      { target: { value: "Retener texto" } },
    );
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          code: "settings_revision_conflict",
          secret: "never-display",
        }),
        { status: 409 },
      ),
    );
    await user.click(
      screen.getByRole("button", {
        name: /^(Guardar ajustes IA|Validar y guardar IA)$/,
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La configuración cambió",
    );
    expect(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
    ).toHaveValue("Retener texto");
    expect(screen.queryByText("never-display")).not.toBeInTheDocument();
  });
  it("keeps discovery explicit and surfaces the server outbound permission gate", async () => {
    stored.outbound_enabled = false;
    const user = userEvent.setup();
    render(<AiSettingsPanel section="APIs" active />);
    const editor = await providerEditor(user);
    expect(requests.some((request) => request.url.includes("models/"))).toBe(
      false,
    );
    expect(
      screen.getByRole("checkbox", {
        name: "Permitir consultas y diagnósticos externos",
      }),
    ).not.toBeChecked();
    await user.click(editor.getByRole("button", { name: "Cargar modelos" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Autorice las consultas externas",
    );
    expect(
      screen.queryByRole("option", { name: /Modelo A/ }),
    ).not.toBeInTheDocument();
    expect(stored.settings.enabled).toBe(false);
    expect(
      requests.filter((request) => request.url.includes("models/")),
    ).toHaveLength(1);
    expect(
      requests.some(
        (request) =>
          request.url.endsWith("/test") ||
          request.url.endsWith("/credentials/gemini"),
      ),
    ).toBe(false);
  });
  it("disables credential writes when storage is server managed", async () => {
    stored.credential_storage_available = false;
    stored.outbound_enabled = false;
    const user = userEvent.setup();
    render(<AiSettingsPanel section="APIs" active />);
    const editor = await providerEditor(user);
    expect(editor.getByRole("button", { name: "Agregar" })).toBeDisabled();
    expect(screen.queryByLabelText("Nuevo valor")).not.toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", { name: /Permitir consultas/ }),
    ).toBeDisabled();
    expect(requests.every((request) => request.method === "GET")).toBe(true);
  });
  it("saves a masked key, clears it, preserves drafts and requires explicit outbound consent", async () => {
    const user = userEvent.setup();
    stored.outbound_enabled = false;
    stored.providers[0].configured = false;
    stored.providers[0].credential_source = "none";
    const localStorageSpy = vi.spyOn(Storage.prototype, "setItem");
    const view = render(<AiSettingsPanel section="IA" active />);
    fireEvent.change(
      await screen.findByLabelText("System prompt · Instrucciones de estilo"),
      { target: { value: "Borrador sin guardar" } },
    );
    view.rerender(<AiSettingsPanel section="APIs" active />);
    await user.click(
      (await providerEditor(user)).getByRole("button", { name: "Agregar" }),
    );
    const key = screen.getByLabelText("Nuevo valor");
    expect(key).toHaveAttribute("type", "password");
    await user.type(key, "synthetic-key");
    await user.click(screen.getByRole("button", { name: "Guardar cifrado" }));
    expect(
      await screen.findByText(
        /Credencial de Google \/ Gemini guardada cifrada/,
      ),
    ).toBeVisible();
    expect(screen.queryByLabelText("Nuevo valor")).not.toBeInTheDocument();
    expect(requests.at(-1)?.body).toEqual({
      revision: 0,
      api_key: "synthetic-key",
    });
    expect(requests.some((request) => request.url.includes("models/"))).toBe(
      false,
    );
    expect(stored.outbound_enabled).toBe(false);
    expect(stored.settings.enabled).toBe(false);
    await user.click(
      screen.getByRole("checkbox", {
        name: "Permitir consultas y diagnósticos externos",
      }),
    );
    await waitFor(() => expect(stored.outbound_enabled).toBe(true));
    expect(requests.at(-1)?.body).toEqual({ revision: 1, enabled: true });
    await user.click(
      (await providerEditor(user)).getByRole("button", {
        name: "Cargar modelos",
      }),
    );
    await user.selectOptions(await screen.findByLabelText("Modelo"), "model-a");
    await user.click(
      (await providerEditor(user)).getByRole("button", {
        name: "Guardar modelo",
      }),
    );
    await waitFor(() => expect(stored.settings.model).toBe("model-a"));
    expect(stored.settings.enabled).toBe(false);
    view.rerender(<AiSettingsPanel section="IA" active />);
    expect(
      screen.getByLabelText("System prompt · Instrucciones de estilo"),
    ).toHaveValue("Borrador sin guardar");
    expect(localStorageSpy).not.toHaveBeenCalled();
  });
  it("clears rejected credentials and never displays raw server errors", async () => {
    const user = userEvent.setup();
    const view = render(<AiSettingsPanel section="APIs" active />);
    await user.click(
      (await providerEditor(user)).getByRole("button", { name: "Agregar" }),
    );
    const key = screen.getByLabelText("Nuevo valor");
    await user.type(key, "synthetic-secret");
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          code: "credential_storage_unavailable",
          secret: "synthetic-secret",
        }),
        { status: 503 },
      ),
    );
    await user.click(screen.getByRole("button", { name: "Guardar cifrado" }));
    await waitFor(() =>
      expect(screen.getAllByRole("alert")[0]).toHaveTextContent(
        "almacén de credenciales",
      ),
    );
    expect(key).toHaveValue("");
    expect(screen.queryByText("synthetic-secret")).not.toBeInTheDocument();
    await user.type(key, "unsent-secret");
    view.rerender(<AiSettingsPanel section="IA" active />);
    view.rerender(<AiSettingsPanel section="APIs" active />);
    await user.click(
      (await providerEditor(user)).getByRole("button", { name: "Agregar" }),
    );
    expect(screen.getByLabelText("Nuevo valor")).toHaveValue("");
  });
});
