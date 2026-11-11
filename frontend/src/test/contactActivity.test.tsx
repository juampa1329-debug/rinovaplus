import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { ContactActivity } from "../modules/contacts/components/ContactActivity";
import {
  contactActivityApi,
  type ContactActivityPage,
} from "../modules/contacts/api/contactActivity";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import { clientsApi } from "../modules/clients/api/clientsApi";

function page(contact = "first", count = 7): ContactActivityPage {
  return {
    items: [
      {
        id: "crm_operation:one",
        source: "crm_operation",
        sourceId: "one",
        occurredAt: "2026-10-16T12:00:00.0000001Z",
        kind: "contact",
        action: "edit_contact",
        actor: "local-operator",
        direction: null,
      },
    ],
    limit: 25,
    hasMore: false,
    nextCursor: null,
    metrics: {
      scope: "selected_contact_all_messages_current_tasks",
      calculatedAt: "2026-10-16T12:00:00.0000000Z",
      messages: {
        messages: count,
        incoming: 0,
        outgoing: count,
        lastMessageAt: null,
      },
      tasks: {
        pendingTasks: 0,
        completedTasks: 0,
        cancelledTasks: 0,
        overdueTasks: 0,
      },
      sla: { status: "not_configured", startedAt: null, dueAt: null },
    },
    historyScope: {
      contactId: contact,
      kind: "all",
      fromDate: null,
      toDate: null,
      dateZone: "America/Bogota",
      upperBound: "exclusive_next_day",
      timestamps: "UTC",
      fieldHistory: "not_recorded",
      actorIdentity: "local_label_not_authenticated",
      inboxAvailable: true,
    },
  };
}
function view(id = "first") {
  return (
    <WorkspaceSessionProvider>
      <ContactActivity contactId={id} />
    </WorkspaceSessionProvider>
  );
}
describe("C3 shared activity and independent current metrics", () => {
  it("keeps metrics through filter loading, invalid dates and failure, but never carries another contact's metrics", async () => {
    vi.mocked(contactActivityApi.read)
      .mockResolvedValueOnce(page())
      .mockImplementationOnce(() => new Promise(() => {}))
      .mockRejectedValueOnce(new Error("test failure"))
      .mockImplementation(() => new Promise(() => {}));
    const rendered = render(view());
    await screen.findByText("7 · 0 entrantes · 7 salientes locales");
    fireEvent.change(screen.getByLabelText("Clase de actividad"), {
      target: { value: "message" },
    });
    await waitFor(() =>
      expect(contactActivityApi.read).toHaveBeenCalledTimes(2),
    );
    expect(
      screen.getByText("7 · 0 entrantes · 7 salientes locales"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Actividad desde (Bogotá)"), {
      target: { value: "2026-10-20" },
    });
    fireEvent.change(
      screen.getByLabelText("Actividad hasta (Bogotá, inclusive)"),
      { target: { value: "2026-10-16" } },
    );
    expect(
      screen.getByText(
        "La fecha inicial debe ser anterior o igual a la final.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("7 · 0 entrantes · 7 salientes locales"),
    ).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Limpiar filtros de actividad" }),
    );
    await screen.findByRole("button", { name: "Reintentar actividad" });
    expect(
      screen.getByText("7 · 0 entrantes · 7 salientes locales"),
    ).toBeInTheDocument();
    rendered.rerender(view("second"));
    expect(
      screen.queryByText("7 · 0 entrantes · 7 salientes locales"),
    ).not.toBeInTheDocument();
  });

  it("cancels an obsolete AJAX page and does not show its records or metrics", async () => {
    let oldResolve!: (value: ContactActivityPage) => void;
    const current = page("first", 2);
    current.items[0].action = "create_contact";
    vi.mocked(contactActivityApi.read)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            oldResolve = resolve;
          }),
      )
      .mockResolvedValue(current);
    render(view());
    await waitFor(() =>
      expect(contactActivityApi.read).toHaveBeenCalledTimes(1),
    );
    const signal = vi.mocked(contactActivityApi.read).mock.calls[0][3];
    fireEvent.change(screen.getByLabelText("Clase de actividad"), {
      target: { value: "contact" },
    });
    await screen.findByText("Contacto creado");
    expect(signal?.aborted).toBe(true);
    oldResolve(page("first", 99));
    expect(screen.queryByText("Ficha confirmada")).not.toBeInTheDocument();
    expect(
      screen.getByText("2 · 0 entrantes · 2 salientes locales"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No disponible: no hay registros entrantes"),
    ).toBeInTheDocument();
  });

  it("passes opaque server cursors and keeps unavailable SLA explicit", async () => {
    const first = page();
    first.hasMore = true;
    first.nextCursor = "opaque-server-cursor";
    const second = page();
    second.items = [];
    second.metrics.tasks = null;
    second.metrics.sla.status = "unavailable";
    vi.mocked(contactActivityApi.read)
      .mockResolvedValueOnce(first)
      .mockResolvedValue(second);
    render(view());
    await screen.findByText("Ficha confirmada");
    await userEvent.click(
      screen.getByRole("button", { name: "Actividad anterior" }),
    );
    await screen.findByText(
      "Sin registros para estos filtros. La ficha y sus métricas completas se conservan.",
    );
    expect(vi.mocked(contactActivityApi.read).mock.calls.at(-1)?.[2]).toBe(
      "opaque-server-cursor",
    );
    expect(
      screen.getByText("No disponibles: fuente de tareas no instalada"),
    ).toBeInTheDocument();
    expect(screen.getByText("No disponible")).toBeInTheDocument();
  });

  it("shares history filters between Clients and Inbox without saving or dropping a contact draft", async () => {
    window.location.hash = "/inbox";
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Ciudad"), {
      target: { value: "Unpublished city draft" },
    });
    fireEvent.change(screen.getByLabelText("Clase de actividad"), {
      target: { value: "task" },
    });
    await userEvent.click(
      screen.getByRole("link", { name: "Clientes y prospectos" }),
    );
    expect(await screen.findByLabelText("Ciudad")).toHaveValue(
      "Unpublished city draft",
    );
    expect(screen.getByLabelText("Clase de actividad")).toHaveValue("task");
    expect(clientsApi.save).not.toHaveBeenCalled();
  });
});
