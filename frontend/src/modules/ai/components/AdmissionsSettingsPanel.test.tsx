import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AdmissionsSettingsPanel } from "./AdmissionsPanel";

vi.mock("../pages/AssistantChat", () => ({ AudioReply: () => null }));

const snapshot = {
  revision: 7,
  enabled: false,
  openrouter_configured: true,
  global_ai_enabled: true,
  outbound_enabled: true,
  settings: {
    primary_model: "synthetic/previous",
    fallback_model: "synthetic/previous-fallback",
    temperature: 0.3,
    system_prompt: "Saved policy instruction",
    max_tokens: 700,
  },
};
const catalog = [
  { id: "synthetic/a", name: "Catalog A" },
  { id: "synthetic/b", name: "Catalog B" },
];
const response = (data: unknown, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => data,
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("loads real catalog contracts and preserves saved selections and unsaved edits on refresh", async () => {
  let resolveCatalog!: (value: ReturnType<typeof response>) => void;
  const pending = new Promise<ReturnType<typeof response>>((resolve) => {
    resolveCatalog = resolve;
  });
  let modelCalls = 0;
  const fetcher = vi.fn(async (url: string, options: RequestInit) => {
    if (url === "/api/v1/ai/settings") {
      expect(options.method ?? "GET").toBe("GET");
      return response(snapshot);
    }
    expect(url).toBe("/api/ai/models/openrouter");
    expect(options.method).toBe("POST");
    expect(options.body).toBe("{}");
    return ++modelCalls === 1
      ? pending
      : response({ models: catalog.slice(1) });
  });
  vi.stubGlobal("fetch", fetcher);
  render(<AdmissionsSettingsPanel />);
  const primary = await screen.findByLabelText(
    "Modelo principal de OpenRouter",
  );
  await waitFor(() => expect(primary).toBeDisabled());
  expect(primary).toHaveValue(snapshot.settings.primary_model);
  expect(screen.getByText(/Consultando el catálogo/)).toBeInTheDocument();
  fireEvent.change(
    screen.getByLabelText("Instrucción institucional de admisiones"),
    { target: { value: "Unsaved local draft" } },
  );
  await act(async () => resolveCatalog(response({ models: catalog })));
  await waitFor(() => expect(primary).toBeEnabled());
  expect(
    within(primary).getByRole("option", { name: /Catalog A/ }),
  ).toHaveValue("synthetic/a");
  expect(primary).toHaveValue(snapshot.settings.primary_model);
  expect(screen.getByLabelText("Modelo de respaldo de OpenRouter")).toHaveValue(
    snapshot.settings.fallback_model,
  );
  fireEvent.change(primary, { target: { value: "synthetic/a" } });
  fireEvent.change(screen.getByLabelText("Modelo de respaldo de OpenRouter"), {
    target: { value: "synthetic/b" },
  });
  const automatic = screen.getByLabelText(
    "Responder automáticamente a mensajes externos nuevos con control IA",
  );
  fireEvent.click(automatic);
  fireEvent.click(
    screen.getByRole("button", { name: "Actualizar modelos de OpenRouter" }),
  );
  await waitFor(() =>
    expect(screen.getByText(/1 modelo de texto recibido/)).toBeInTheDocument(),
  );
  expect(primary).toHaveValue("synthetic/a");
  expect(
    within(primary).getByRole("option", {
      name: /selección actual; no figura/,
    }),
  ).toHaveValue("synthetic/a");
  expect(screen.getByLabelText("Modelo de respaldo de OpenRouter")).toHaveValue(
    "synthetic/b",
  );
  expect(
    screen.getByLabelText("Instrucción institucional de admisiones"),
  ).toHaveValue("Unsaved local draft");
  expect(automatic).toBeChecked();
  expect(fetcher).toHaveBeenCalledTimes(3);
});

it("explains missing credentials and an empty catalog without clearing current models", async () => {
  const fetcher = vi.fn(async (url: string) =>
    response(
      url.endsWith("/settings")
        ? { ...snapshot, openrouter_configured: false }
        : { models: [] },
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  render(<AdmissionsSettingsPanel />);
  await screen.findByLabelText("Modelo principal de OpenRouter");
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(
    screen.getByText(/El catálogo todavía no se consultó/),
  ).toBeInTheDocument();
  fireEvent.click(
    screen.getByRole("button", { name: "Cargar modelos de OpenRouter" }),
  );
  await screen.findByText(/no devolvió modelos de texto compatibles/);
  expect(screen.getByLabelText("Modelo principal de OpenRouter")).toHaveValue(
    snapshot.settings.primary_model,
  );
  expect(screen.getByLabelText("Modelo de respaldo de OpenRouter")).toHaveValue(
    snapshot.settings.fallback_model,
  );
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it("shows a safe catalog error and retries without saving policy or losing its draft", async () => {
  let attempts = 0;
  const fetcher = vi.fn(async (url: string, options: RequestInit) => {
    if (url.endsWith("/settings")) return response(snapshot);
    expect(options.method).toBe("POST");
    return ++attempts === 1
      ? response({ code: "provider_key_missing" }, 409)
      : response({ models: catalog });
  });
  vi.stubGlobal("fetch", fetcher);
  render(<AdmissionsSettingsPanel />);
  await screen.findByText(/Guarde la API key de este proveedor/);
  fireEvent.change(
    screen.getByLabelText("Instrucción institucional de admisiones"),
    { target: { value: "Draft survives retry" } },
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Cargar modelos de OpenRouter" }),
  );
  await screen.findByText(/2 modelos de texto recibidos/);
  expect(screen.queryByText(/Guarde la API key de este proveedor/)).toBeNull();
  expect(
    screen.getByLabelText("Instrucción institucional de admisiones"),
  ).toHaveValue("Draft survives retry");
  expect(screen.getByLabelText("Modelo principal de OpenRouter")).toHaveValue(
    snapshot.settings.primary_model,
  );
  expect(fetcher).toHaveBeenCalledTimes(3);
});
