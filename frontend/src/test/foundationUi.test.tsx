import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import {
  RuntimeProvider,
  legacyCapabilities,
  featureNames,
  validateCapabilities,
  type UiCapabilities,
} from "../shared/runtimeCapabilities";
import { clientsApi } from "../modules/clients/api/clientsApi";
import { inboxApi } from "../modules/inbox/api/inboxApi";
import { crmConfigurationApi } from "../modules/crm-configuration/api/crmConfigurationApi";
import { contactMergeApi } from "../modules/contacts/api/contactMergeApi";
import { institutionalIdentityApi } from "../modules/contacts/api/institutionalIdentity";
import { contactActivityApi } from "../modules/contacts/api/contactActivity";
import { strategyApi } from "../modules/conversation-strategy/api/strategy";
import { workflowOf } from "../shared/workflow";

const foundation: UiCapabilities = {
  ...legacyCapabilities,
  profile: "foundation",
  mode: "local_foundation",
  scope: "restored_rehearsal_only",
  modules: ["overview", "clients", "inbox", "settings"],
  features: Object.fromEntries(
    featureNames.map((key) => [key, false]),
  ) as UiCapabilities["features"],
};

function fixture() {
  const workspace = vi.mocked(clientsApi.workspace).getMockImplementation()!;
  vi.mocked(clientsApi.workspace).mockImplementation(async (...args) => {
    const value = await workspace(...args);
    return {
      ...value,
      clients: value.clients.map((client) => ({
        ...client,
        programId: null,
        program: "",
        institutionalProfile: undefined,
      })),
    };
  });
  const detail = vi.mocked(inboxApi.detail).getMockImplementation()!;
  vi.mocked(inboxApi.detail).mockImplementation(async (...args) => {
    const value = await detail(...args);
    return {
      ...value,
      contactGroup: null,
      client: {
        ...value.client,
        programId: null,
        program: "",
        institutionalProfile: undefined,
      },
      thread: {
        ...value.thread,
        mode: "human",
        channel: "Local",
        unread: true,
        workflow: { ...workflowOf(value.thread), assignee: "Sin asignar" },
      },
      operation: null,
      miniCrm: {
        leadScore: null,
        temperature: null,
        takeover: true,
        assessmentSource: "not_evaluated",
        stateScope: "conversation",
      },
      destinations: [],
    };
  });
  return vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => structuredClone(foundation),
    }),
  );
}
const change = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
const app = () =>
  render(
    <RuntimeProvider>
      <App />
    </RuntimeProvider>,
  );

beforeEach(() => {
  window.location.hash = "/inbox";
  fixture();
});
afterEach(() => vi.unstubAllGlobals());

describe("restored foundation UI", () => {
  it.each([
    { ...foundation, profile: "unknown" },
    { ...foundation, mode: "local_sql_copy" },
    { ...foundation, modules: ["overview", "clients", "inbox", "agents"] },
    { ...foundation, features: { ...foundation.features, media: true } },
    { ...foundation, features: { ...foundation.features, hidden: true } },
    { ...legacyCapabilities, scope: "untrusted" },
  ])("rejects inconsistent capability manifests", (value) => {
    expect(() => validateCapabilities(value)).toThrow();
  });

  it("does not mount data owners before capabilities, and retries without a demo fallback", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("offline"));
    app();
    await screen.findByRole("button", { name: "Reintentar disponibilidad" });
    expect(clientsApi.workspace).not.toHaveBeenCalled();
    expect(inboxApi.list).not.toHaveBeenCalled();
    fireEvent.click(
      screen.getByRole("button", { name: "Reintentar disponibilidad" }),
    );
    await screen.findByLabelText("Nombre visible");
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("mounts one editable shared contact and avoids unavailable academic and AI modules", async () => {
    app();
    await screen.findByLabelText("Nombre visible");
    expect(screen.getAllByLabelText("Notas internas")).toHaveLength(1);
    expect(
      screen.queryByLabelText("Programa de interés"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText("Destino del mensaje"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Reservar para IA" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Comentarios" }),
    ).not.toBeInTheDocument();
    expect(institutionalIdentityApi.catalog).not.toHaveBeenCalled();
    expect(contactMergeApi.group).not.toHaveBeenCalled();
    expect(contactActivityApi.read).not.toHaveBeenCalled();
    expect(strategyApi.read).not.toHaveBeenCalled();
    expect(
      vi
        .mocked(fetch)
        .mock.calls.every(([url]) => url === "/api/local/runtime"),
    ).toBe(true);
  });

  it("changes conversation state without the unsupported sequence cursor", async () => {
    app();
    await screen.findByLabelText("Nombre visible");
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Marcar leído" }),
      ).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Marcar leído" }));
    await waitFor(() => expect(inboxApi.change).toHaveBeenCalledTimes(1));
    expect(vi.mocked(inboxApi.change).mock.calls[0][1]).not.toHaveProperty(
      "readThroughSequence",
    );
    expect(vi.mocked(inboxApi.change).mock.calls[0][1]).toMatchObject({
      mode: "human",
      assignee: "",
      unread: false,
    });
  });

  it("shares confirmed edits between CRM and Inbox without a second read-only card", async () => {
    window.location.hash = "/clients";
    app();
    await screen.findByLabelText("Nombre visible");
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Guardar ficha" }),
      ).toBeEnabled(),
    );
    change("Notas internas", "Shared foundation note");
    fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
    await screen.findByText("Ficha guardada correctamente.");
    fireEvent.click(screen.getByRole("button", { name: "Abrir en Inbox" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Notas internas")).toHaveValue(
        "Shared foundation note",
      ),
    );
    expect(screen.getAllByLabelText("Notas internas")).toHaveLength(1);
    change("Notas internas", "Edited from mini CRM");
    fireEvent.click(screen.getByRole("button", { name: "Guardar ficha" }));
    await screen.findByText("Ficha guardada correctamente.");
    fireEvent.click(screen.getByRole("button", { name: "Ver Clientes" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Notas internas")).toHaveValue(
        "Edited from mini CRM",
      ),
    );
    expect(clientsApi.save).toHaveBeenCalledTimes(2);
  });

  it("offers the same CRM configuration in Settings and blocks direct unsupported routes", async () => {
    window.location.hash = "/settings";
    app();
    await screen.findByRole("button", { name: "Añadir etapa local" });
    await waitFor(() => expect(crmConfigurationApi.read).toHaveBeenCalledTimes(1));
    expect(
      vi
        .mocked(fetch)
        .mock.calls.every(([url]) => url === "/api/local/runtime"),
    ).toBe(true);
    window.location.hash = "/campaigns";
    fireEvent(window, new Event("hashchange"));
    await screen.findByRole("heading", {
      name: "Función pendiente en esta copia",
    });
    expect(screen.getByRole("link", { name: "Campañas" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });
});
