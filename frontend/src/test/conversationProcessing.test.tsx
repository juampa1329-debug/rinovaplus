import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  ConversationProcessing,
  eventApi,
  type EventStatus,
} from "../modules/conversation-events/pages/ConversationProcessing";
import { InboxSessionProvider } from "../shared/inboxSession";

const status: EventStatus = {
  counts: { pending: 2, leased: 0, prepared: 8, failed: 1 },
  uncaptured: { message: 3 },
  conversations: 2,
  preparedConversations: 2,
  lastPreparedAt: null,
  worker: { state: "storage_unavailable", alive: true, lastCycleAt: null },
};
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <InboxSessionProvider>{children}</InboxSessionProvider>
);
afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

it("shows gaps and historical technical coverage without claiming AI analysis", async () => {
  vi.spyOn(eventApi, "status").mockResolvedValue(status);
  render(<ConversationProcessing />, { wrapper });
  expect(
    await screen.findByText(/Almacenamiento no disponible/),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Referencias sin registrar").nextElementSibling,
  ).toHaveTextContent("3");
  expect(
    screen.getByText("Eventos pendientes").nextElementSibling,
  ).toHaveTextContent("2");
  expect(screen.getByText(/no genera contexto/)).toBeInTheDocument();
});

it("does not replace unavailable reads with fake zero counters", async () => {
  vi.spyOn(eventApi, "status").mockRejectedValue(new Error("offline"));
  render(<ConversationProcessing />, { wrapper });
  expect(await screen.findByText(/No se pudo consultar/)).toBeInTheDocument();
  expect(screen.queryByText("Eventos pendientes")).not.toBeInTheDocument();
});

it("refreshes automatically and ignores a late superseded response", async () => {
  vi.useFakeTimers();
  let resolveFirst!: (value: EventStatus) => void;
  vi.spyOn(eventApi, "status")
    .mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve;
      }),
    )
    .mockResolvedValue({ ...status, counts: { ...status.counts, pending: 0 } });
  render(<ConversationProcessing />, { wrapper });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10000);
  });
  expect(
    screen.getByText("Eventos pendientes").nextElementSibling,
  ).toHaveTextContent("0");
  await act(async () => resolveFirst(status));
  expect(
    screen.getByText("Eventos pendientes").nextElementSibling,
  ).toHaveTextContent("0");
});

it("retains an uncertain retry operation across route unmount and blocks double submit", async () => {
  vi.spyOn(eventApi, "status").mockResolvedValue(status);
  const retry = vi
    .spyOn(eventApi, "retry")
    .mockRejectedValueOnce(new Error("uncertain"))
    .mockResolvedValue({ retried: 1 });
  const view = render(<ConversationProcessing />, { wrapper });
  const button = await screen.findByRole("button", {
    name: /Reintentar hasta/,
  });
  fireEvent.click(button);
  fireEvent.click(button);
  await screen.findByText(/No se confirmó/);
  expect(retry).toHaveBeenCalledTimes(1);
  view.rerender(<div />);
  view.rerender(<ConversationProcessing />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Reintentar hasta/ }),
  );
  await waitFor(() => expect(retry).toHaveBeenCalledTimes(2));
  expect(retry.mock.calls[0][0]).toBe(retry.mock.calls[1][0]);
});
