import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  AnalysisConversation,
  AnalysisSettings,
} from "../modules/conversation-analysis/pages/ConversationAnalysis";
import {
  analysisApi,
  type AnalysisConfiguration,
  type AnalysisDetail,
} from "../modules/conversation-analysis/api/analysis";
import { InboxSessionProvider } from "../shared/inboxSession";
import { WorkspaceSessionProvider } from "../shared/workspaceSession";
import { ClientsError } from "../modules/clients/api/clientsApi";
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <WorkspaceSessionProvider>
    <InboxSessionProvider>{children}</InboxSessionProvider>
  </WorkspaceSessionProvider>
);
const configuration: AnalysisConfiguration = {
  revision: "0",
  policy: null,
  usage: { requests: 0, reservedOutputTokens: 0 },
  coverage: { conversations: 2, withContext: 0, processing: 0, failed: 0 },
  connection: {
    outbound: false,
    serverCredentials: true,
    providers: [{ id: "gemini", configured: false }],
  },
  worker: { state: "disabled", alive: true, lastCycleAt: null },
};
const detail: AnalysisDetail = {
  revision: "1",
  status: "current",
  context: {
    summary: [
      {
        text: "Registro del operador",
        kind: "declaration",
        subject: "operator",
        evidenceIds: ["11111111-1111-4111-8111-111111111111"],
      },
    ],
    intention: [],
    behavior: [],
    objections: [],
    commitments: [],
    nextAction: [],
  },
  stale: false,
  partial: false,
  totalMessages: 1,
  coveredMessages: 1,
  pendingReferences: 0,
  analyzedAt: "2026-10-16T12:00:00Z",
  errorCode: null,
  enabled: true,
  provenance: {
    provider: "gemini",
    model: "synthetic-model",
    promptVersion: "analysis-v1",
    policyRevision: 1,
    contextGeneration: 1,
  },
  evidence: [
    {
      id: "11111111-1111-4111-8111-111111111111",
      direction: "outgoing",
      createdAt: "2026-10-16T11:00:00Z",
    },
  ],
  feedback: [],
};
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});
it("starts without invented policy, budget or provider model", async () => {
  vi.spyOn(analysisApi, "read").mockResolvedValue(configuration);
  render(<AnalysisSettings />, { wrapper });
  expect(await screen.findByLabelText("Proveedor de análisis")).toHaveValue("");
  expect(screen.getByLabelText("Modelo de análisis")).toHaveValue("");
  expect(
    screen.getByLabelText("Máximo de solicitudes por día UTC"),
  ).toHaveValue(null);
  expect(
    screen.getByRole("button", { name: "Guardar política de análisis" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Cargar modelos del proveedor" }),
  ).toBeDisabled();
});
it("does not fabricate context when no inference exists", async () => {
  vi.spyOn(analysisApi, "read").mockResolvedValue({
    ...detail,
    context: null,
    provenance: null,
    status: "not_configured",
    enabled: false,
    coveredMessages: 0,
  });
  render(<AnalysisConversation conversationId="a" />, { wrapper });
  expect(await screen.findByText(/Sin análisis generado/)).toBeInTheDocument();
  expect(
    screen.queryByLabelText("Corrección humana del análisis"),
  ).not.toBeInTheDocument();
});
it("shows partial coverage and original provenance with readonly evidence", async () => {
  vi.spyOn(analysisApi, "read").mockResolvedValue({
    ...detail,
    stale: true,
    partial: true,
    coveredMessages: 6,
    totalMessages: 8,
    pendingReferences: 2,
  });
  render(<AnalysisConversation conversationId="a" />, { wrapper });
  expect(await screen.findByText(/Contexto parcial/)).toBeInTheDocument();
  expect(screen.getByText(/Mensajes cubiertos: 6 de 8/)).toBeInTheDocument();
  expect(screen.getByText(/gemini \/ synthetic-model/)).toBeInTheDocument();
  expect(screen.getByText(/Registro local del operador/)).toBeInTheDocument();
  expect(screen.getAllByText("Sin evidencia.")).toHaveLength(5);
});
it("polling preserves feedback baseline and a conflict preserves its draft", async () => {
  vi.useFakeTimers();
  let revision = "1";
  vi.spyOn(analysisApi, "read").mockImplementation(
    async () => ({ ...detail, revision }) as never,
  );
  const write = vi
    .spyOn(analysisApi, "write")
    .mockRejectedValue(new ClientsError(409));
  render(<AnalysisConversation conversationId="a" />, { wrapper });
  await act(async () => {});
  fireEvent.change(screen.getByLabelText("Corrección humana del análisis"), {
    target: { value: "Corrección sintética" },
  });
  revision = "2";
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10000);
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar corrección humana" }),
  );
  await act(async () => {});
  expect(write.mock.calls[0][1]).toMatchObject({
    expectedRevision: "1",
    text: "Corrección sintética",
  });
  expect(screen.getByLabelText("Corrección humana del análisis")).toHaveValue(
    "Corrección sintética",
  );
  expect(
    screen.getByText(/Los datos o la configuración cambiaron/),
  ).toBeInTheDocument();
});
it("late conversation response cannot replace the selected conversation", async () => {
  let resolve!: (value: AnalysisDetail) => void;
  vi.spyOn(analysisApi, "read")
    .mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      }),
    )
    .mockResolvedValue({ ...detail, context: null, status: "not_configured" });
  const view = render(<AnalysisConversation conversationId="a" />, { wrapper });
  view.rerender(<AnalysisConversation conversationId="b" />);
  await screen.findByText(/Sin análisis generado/);
  await act(async () => resolve(detail));
  expect(screen.queryByText("Registro del operador")).not.toBeInTheDocument();
});
it("preserves configuration draft across route navigation without activating", async () => {
  vi.spyOn(analysisApi, "read").mockResolvedValue(configuration);
  const write = vi.spyOn(analysisApi, "write");
  const view = render(<AnalysisSettings />, { wrapper });
  await screen.findByLabelText("Proveedor de análisis");
  fireEvent.change(screen.getByLabelText("Máximo de solicitudes por día UTC"), {
    target: { value: "4" },
  });
  view.rerender(<div />);
  view.rerender(<AnalysisSettings />);
  await waitFor(() =>
    expect(
      screen.getByLabelText("Máximo de solicitudes por día UTC"),
    ).toHaveValue(4),
  );
  expect(screen.getByLabelText("Activar análisis continuo")).not.toBeChecked();
  write.mockRestore();
});
