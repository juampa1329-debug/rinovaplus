import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ConversationStrategy } from "../modules/conversation-strategy/pages/ConversationStrategy";
import {
  strategyApi,
  type StrategyDetail,
} from "../modules/conversation-strategy/api/strategy";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import { InboxSessionProvider } from "../shared/inboxSession";
import { ClientsError } from "../modules/clients/api/clientsApi";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <WorkspaceSessionProvider>
    <InboxSessionProvider>{children}</InboxSessionProvider>
  </WorkspaceSessionProvider>
);
function detail(id = "one", planId = "plan-one"): StrategyDetail {
  return {
    revision: "1",
    conversationId: id,
    autonomy: {
      requested: false,
      effective: false,
      globalPaused: false,
      planCurrent: true,
      reasons: ["not_requested"],
    },
    metrics: { tasksCreated: 0, feedback: 0, useful: 0 },
    plan: {
      index: 1,
      signals: [
        {
          criterion: "next_step",
          text: "Siguiente paso documentado",
          evidenceIds: ["reference-one"],
        },
      ],
      churn: { level: "unknown", text: "", evidenceIds: [] },
      noContact: false,
      recommendations: [],
      objections: [],
      remarketing: [],
      drafts: [],
    },
    provenance: {
      id: planId,
      revision: 1,
      generation: 1,
      provider: "gemini",
      model: "synthetic-model",
      promptVersion: "synthetic",
      createdAt: "2026-10-16T12:00:00Z",
    },
  };
}
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});
it("replays the exact uncertain write after polling advances the global revision", async () => {
  const read = vi.spyOn(strategyApi, "read").mockResolvedValue(detail());
  const write = vi
    .spyOn(strategyApi, "write")
    .mockRejectedValueOnce(new Error("uncertain response"))
    .mockResolvedValue({ revision: "2" });
  render(<ConversationStrategy conversationId="one" />, { wrapper });
  await screen.findByText("Siguiente paso documentado", { exact: false });
  fireEvent.click(screen.getByText("Evaluar esta propuesta"));
  fireEvent.change(screen.getByLabelText("Corrección o comentario"), {
    target: { value: "Review retained" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar evaluación de propuesta" }),
  );
  await screen.findByText(/No se pudo confirmar la operación/);
  read.mockResolvedValue({ ...detail(), revision: "2" });
  fireEvent.click(
    screen.getByRole("button", { name: "Actualizar estrategia" }),
  );
  await waitFor(() => expect(read).toHaveBeenCalledTimes(2));
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar evaluación de propuesta" }),
  );
  await waitFor(() => expect(write).toHaveBeenCalledTimes(2));
  expect(write.mock.calls[1]).toEqual(write.mock.calls[0]);
});
it("shows unknown instead of fake probabilities and separates requested from effective", async () => {
  vi.spyOn(strategyApi, "read").mockResolvedValue({
    ...detail(),
    plan: null,
    provenance: null,
  });
  render(<ConversationStrategy conversationId="one" />, { wrapper });
  expect(await screen.findByText("No evaluable")).toBeVisible();
  expect(screen.getByText("Desconocido")).toBeVisible();
  expect(
    screen.getByText(/Solicitada: No. Estado efectivo: Pausada/),
  ).toBeVisible();
  expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument();
});
it("ignores a late response from the previous contact", async () => {
  let resolveOld!: (v: StrategyDetail) => void;
  vi.spyOn(strategyApi, "read").mockImplementation((id) =>
    id === "one"
      ? new Promise((resolve) => {
          resolveOld = resolve;
        })
      : Promise.resolve({ ...detail("two"), plan: null, provenance: null }),
  );
  const view = render(<ConversationStrategy conversationId="one" />, {
    wrapper,
  });
  view.rerender(<ConversationStrategy conversationId="two" />);
  await screen.findByText("No evaluable");
  await act(async () => resolveOld(detail()));
  expect(
    screen.queryByText("Siguiente paso documentado"),
  ).not.toBeInTheDocument();
});
it("accepts only the latest polling request in the same conversation", async () => {
  vi.useFakeTimers();
  const resolvers: ((v: StrategyDetail) => void)[] = [];
  vi.spyOn(strategyApi, "read").mockImplementation(
    () => new Promise((resolve) => resolvers.push(resolve)),
  );
  render(<ConversationStrategy conversationId="one" />, { wrapper });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10000);
  });
  await act(async () =>
    resolvers[1]({ ...detail(), plan: null, provenance: null }),
  );
  await act(async () => resolvers[0](detail()));
  expect(screen.getByText("No evaluable")).toBeVisible();
  expect(
    screen.queryByText("Siguiente paso documentado"),
  ).not.toBeInTheDocument();
});
it("keeps a write conflict and draft after a successful background read", async () => {
  vi.spyOn(strategyApi, "read").mockResolvedValue(detail());
  vi.spyOn(strategyApi, "write").mockRejectedValue(new ClientsError(409));
  render(<ConversationStrategy conversationId="one" />, { wrapper });
  await screen.findByText("Siguiente paso documentado", { exact: false });
  fireEvent.click(screen.getByText("Evaluar esta propuesta"));
  fireEvent.change(screen.getByLabelText("Corrección o comentario"), {
    target: { value: "Conservar este borrador" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar evaluación de propuesta" }),
  );
  await screen.findByText(/La conversación o el plan cambió/);
  fireEvent.click(
    screen.getByRole("button", { name: "Actualizar estrategia" }),
  );
  await waitFor(() => expect(strategyApi.read).toHaveBeenCalledTimes(2));
  expect(screen.getByText(/La conversación o el plan cambió/)).toBeVisible();
  expect(screen.getByLabelText("Corrección o comentario")).toHaveValue(
    "Conservar este borrador",
  );
});
it("does not attach an old outcome or correction to a new plan without explicit reset", async () => {
  const read = vi.spyOn(strategyApi, "read").mockResolvedValue(detail());
  vi.spyOn(strategyApi, "write").mockRejectedValue(new ClientsError(409));
  render(<ConversationStrategy conversationId="one" />, { wrapper });
  await screen.findByText("Siguiente paso documentado", { exact: false });
  fireEvent.click(screen.getByText("Evaluar esta propuesta"));
  fireEvent.change(screen.getByLabelText("Corrección o comentario"), {
    target: { value: "Old review" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar evaluación de propuesta" }),
  );
  await screen.findByText(/La conversación o el plan cambió/);
  read.mockResolvedValue(detail("one", "plan-two"));
  fireEvent.click(
    screen.getByRole("button", { name: "Actualizar estrategia" }),
  );
  await screen.findByText(/El borrador pertenece a un plan anterior/);
  fireEvent.change(screen.getByLabelText("Utilidad"), {
    target: { value: "not_useful" },
  });
  expect(
    screen.getByRole("button", { name: "Guardar evaluación de propuesta" }),
  ).toBeDisabled();
  expect(screen.getByLabelText("Corrección o comentario")).toHaveValue(
    "Old review",
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Empezar evaluación del plan actual" }),
  );
  expect(screen.getByLabelText("Corrección o comentario")).toHaveValue("");
  expect(
    screen.getByLabelText("Resultado observado por el operador"),
  ).toHaveValue("not_observed");
  expect(
    screen.getByRole("button", { name: "Guardar evaluación de propuesta" }),
  ).toBeEnabled();
});
