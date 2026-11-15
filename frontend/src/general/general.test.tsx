import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GeneralPreview, validateGeneral } from "./GeneralPreview";

vi.mock("../App", () => ({
  App: () => (
    <div
      ref={() => {
        document.title = "Ruta no disponible · RinovaPlus";
      }}
    >
      CRM aceptado
      <input aria-label="Borrador C13" defaultValue="" />
    </div>
  ),
}));

const sections = [
  "admissions",
  "overview",
  "clients",
  "inbox",
  "channels",
  "assistant",
  "agents",
  "knowledge",
  "memory",
  "broadcasts",
  "campaigns",
  "ads",
  "intelligence",
  "settings",
].map((path) => ({
  path,
  label: path,
  phase: "P4",
  available: ["overview", "clients", "inbox", "channels", "settings"].includes(
    path,
  ),
  status: ["overview", "clients", "inbox", "channels", "settings"].includes(
    path,
  )
    ? "local_subset"
    : "pending_integration",
}));
const manifest = {
  version: "cbn-general-preview-c13-v1",
  profile: "general_preview",
  scope: "isolated_local_preview",
  sections,
  features: {
    providers: false,
    institutional_auth: false,
    provider_workers: false,
    public_webhooks: false,
  },
};
afterEach(() => {
  vi.unstubAllGlobals();
  window.location.hash = "";
});

describe("C13 capabilities", () => {
  it("requires the new independent contract", () => {
    expect(validateGeneral(manifest)).toEqual(manifest);
    expect(() =>
      validateGeneral({ ...manifest, version: "cbn-ui-capabilities-v1" }),
    ).toThrow();
  });
  it.each([
    "providers",
    "institutional_auth",
    "provider_workers",
    "public_webhooks",
  ])("rejects activation of %s", (key) => {
    expect(() =>
      validateGeneral({
        ...manifest,
        features: { ...manifest.features, [key]: true },
      }),
    ).toThrow();
  });
  it("rejects missing or promoted sections", () => {
    expect(() =>
      validateGeneral({ ...manifest, sections: sections.slice(1) }),
    ).toThrow();
    expect(() =>
      validateGeneral({
        ...manifest,
        sections: sections.map((s) =>
          s.path === "agents" ? { ...s, available: true } : s,
        ),
      }),
    ).toThrow();
  });
  it("waits for bootstrap and validation before mounting CRM", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({ ok: true, json: async () => manifest }),
    );
    render(<GeneralPreview />);
    expect(screen.queryByText("CRM aceptado")).not.toBeInTheDocument();
    expect(await screen.findByText("CRM aceptado")).toBeInTheDocument();
  });
  it("shows all sections without mounting pending products", async () => {
    window.location.hash = "/agents";
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({ ok: true, json: async () => manifest }),
    );
    render(<GeneralPreview />);
    expect(
      await screen.findByText("Avance de esta sección"),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(16);
    expect(screen.getByText("CRM aceptado")).not.toBeVisible();
    expect(document.title).toBe("RinovaPlus · Vista general");
  });
  it("malformed contract keeps the app unmounted", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ ...manifest, profile: "legacy" }),
        }),
    );
    render(<GeneralPreview />);
    expect(
      await screen.findByText(
        "No se pudo comprobar la disponibilidad de esta copia.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("CRM aceptado")).not.toBeInTheDocument();
  });
  it("keeps the core draft mounted while reviewing another section", async () => {
    window.location.hash = "/clients";
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({ ok: true })
        .mockResolvedValueOnce({ ok: true, json: async () => manifest }),
    );
    render(<GeneralPreview />);
    const draft = await screen.findByLabelText("Borrador C13");
    fireEvent.change(draft, {
      target: { value: "Borrador que debe conservarse" },
    });
    act(() => {
      window.location.hash = "/agents";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(draft).not.toBeVisible();
    act(() => {
      window.location.hash = "/clients";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(screen.getByLabelText("Borrador C13")).toBe(draft);
    expect(draft).toHaveValue("Borrador que debe conservarse");
  });
  it("passes bounded cancellation to bootstrap", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("offline"));
    vi.stubGlobal("fetch", fetcher);
    render(<GeneralPreview />);
    await waitFor(() => expect(fetcher).toHaveBeenCalled());
    expect(fetcher.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
  });
});
