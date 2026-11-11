import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { InboxOperationPanel } from "../modules/inbox/components/InboxOperationPanel";
import { InboxOperationSettings } from "../modules/inbox/components/InboxOperationSettings";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import { InboxSessionProvider } from "../shared/inboxSession";
import {
  inboxOperationsApi,
  type OperationDetail,
} from "../modules/inbox/api/inboxOperations";
import { ClientsError } from "../modules/clients/api/clientsApi";
import { App } from "../App";
import { inboxApi } from "../modules/inbox/api/inboxApi";
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <WorkspaceSessionProvider>
    <InboxSessionProvider>{children}</InboxSessionProvider>
  </WorkspaceSessionProvider>
);
const base: OperationDetail = {
  revision: "1",
  offset: 0,
  hasMore: false,
  tasks: [],
  assignment: {
    humanEmployeeId: null,
    aiAgentId: null,
    humanName: "",
    aiName: null,
    humanSelectable: false,
    aiSelectable: false,
    controlMode: "human",
    slaStatus: "not_configured",
    startedAt: null,
    dueAt: null,
    thresholdMinutes: null,
    firstResponseDueAt: null,
  },
};
let revision = "1";
beforeEach(() => {
  revision = "1";
  vi.mocked(inboxOperationsApi.read).mockImplementation(
    async <T,>(path: string): Promise<T> => {
      if (path.startsWith("/directory"))
        return { revision, offset: 0, hasMore: false, items: [] } as T;
      if (path === "/configuration") return { revision, policy: null } as T;
      return { ...base, revision } as T;
    },
  );
  vi.spyOn(inboxOperationsApi, "write").mockResolvedValue({ revision: "3" });
});
it("retains task draft base revision across periodic reads and conflict", async () => {
  const view = render(
    <InboxOperationPanel id="thread" refresh={0} onConfirmed={() => {}} />,
    { wrapper },
  );
  await screen.findByLabelText("Título de tarea");
  fireEvent.change(screen.getByLabelText("Título de tarea"), {
    target: { value: "Call back" },
  });
  fireEvent.change(screen.getByLabelText("Prioridad de tarea"), {
    target: { value: "high" },
  });
  revision = "2";
  view.rerender(
    <InboxOperationPanel id="thread" refresh={1} onConfirmed={() => {}} />,
  );
  await waitFor(() =>
    expect(inboxOperationsApi.read).toHaveBeenCalledWith(
      "/conversations/thread?offset=0",
      expect.anything(),
    ),
  );
  vi.mocked(inboxOperationsApi.write).mockRejectedValue(new ClientsError(409));
  fireEvent.click(screen.getByRole("button", { name: "Guardar tarea" }));
  await screen.findByText(/El borrador conserva su revisión original/);
  expect(inboxOperationsApi.write).toHaveBeenCalledWith(
    expect.stringContaining("/tasks/"),
    expect.objectContaining({ expectedRevision: "1", title: "Call back" }),
  );
  expect(screen.getByLabelText("Título de tarea")).toHaveValue("Call back");
});
it("clears read failure after retry without fabricated policy", async () => {
  vi.mocked(inboxOperationsApi.read).mockRejectedValueOnce(
    new ClientsError(503),
  );
  render(
    <InboxOperationPanel id="thread" refresh={0} onConfirmed={() => {}} />,
    { wrapper },
  );
  await screen.findByText(/No se pudo cargar la operación/);
  fireEvent.click(screen.getByRole("button", { name: "Reintentar operación" }));
  await screen.findByText("SLA no configurado");
  expect(
    screen.queryByText(/No se pudo cargar la operación/),
  ).not.toBeInTheDocument();
});
it("requires explicit SLA threshold and keeps policy base revision", async () => {
  const view = render(
    <InboxOperationSettings refresh={0} onConfirmed={() => {}} />,
    { wrapper },
  );
  await waitFor(() =>
    expect(
      screen.getByLabelText("Umbral SLA en minutos transcurridos"),
    ).toBeEnabled(),
  );
  const input = screen.getByLabelText("Umbral SLA en minutos transcurridos");
  expect(input).toHaveValue(null);
  fireEvent.submit(input.closest("form")!);
  expect(inboxOperationsApi.write).not.toHaveBeenCalled();
  fireEvent.change(input, { target: { value: "30" } });
  revision = "2";
  view.rerender(<InboxOperationSettings refresh={1} onConfirmed={() => {}} />);
  fireEvent.submit(input.closest("form")!);
  await waitFor(() =>
    expect(inboxOperationsApi.write).toHaveBeenCalledWith(
      "/policy",
      expect.objectContaining({
        expectedRevision: "1",
        thresholdMinutes: 30,
        enabled: false,
      }),
    ),
  );
});
it("sends SLA filter to server and resets it", async () => {
  window.location.hash = "/inbox";
  render(<App />);
  await screen.findByLabelText("Nombre visible");
  const field = screen.getByLabelText("Filtrar SLA de respuesta");
  fireEvent.change(field, { target: { value: "overdue" } });
  await waitFor(() =>
    expect(inboxApi.list).toHaveBeenLastCalledWith(
      expect.objectContaining({ sla: "overdue", offset: 0 }),
      expect.anything(),
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Restablecer filtros" }));
  await waitFor(() =>
    expect(inboxApi.list).toHaveBeenLastCalledWith(
      expect.objectContaining({ sla: "", humanId: "", aiId: "", offset: 0 }),
      expect.anything(),
    ),
  );
});
