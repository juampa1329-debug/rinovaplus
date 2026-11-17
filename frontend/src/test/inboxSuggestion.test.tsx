import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { InboxSuggestion } from "../institution/InboxSuggestion";
import { api } from "../modules/agents/api";

vi.mock("../modules/agents/api", () => ({ api: vi.fn() }));
beforeEach(() => {
  vi.clearAllMocks();
});

it("retains the same paid operation when recovering an unknown response", async () => {
  vi.mocked(api)
    .mockResolvedValueOnce({ revision: 1, selection: { version: 2 } })
    .mockRejectedValueOnce(new Error("La respuesta se interrumpió"))
    .mockResolvedValueOnce({ revision: 1, selection: { version: 2 } })
    .mockResolvedValueOnce({ text: "Resultado ya preparado" });
  render(
    <InboxSuggestion
      conversation="own"
      question="Software"
      incoming="one"
      epoch="1"
      onUseReply={() => {}}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Sugerir respuesta con IA" }),
  );
  await screen.findByText("La respuesta se interrumpió");
  fireEvent.click(
    screen.getByRole("button", { name: "Sugerir respuesta con IA" }),
  );
  await screen.findByText("Resultado ya preparado");
  const attempts = vi
    .mocked(api)
    .mock.calls.filter((call) => call[0]?.endsWith("/draft"));
  expect(attempts).toHaveLength(2);
  expect((attempts[0][2] as { request_id: string }).request_id).toBe(
    (attempts[1][2] as { request_id: string }).request_id,
  );
});

it("generates with the actual social channel and keeps the text as a reviewed draft", async () => {
  vi.mocked(api)
    .mockResolvedValueOnce({ revision: 3 })
    .mockResolvedValueOnce({ text: "Software dura tres semestres." });
  const useReply = vi.fn();
  render(
    <InboxSuggestion
      conversation="own"
      question="¿Cuánto dura Software?"
      incoming="latest"
      channel="messenger"
      onUseReply={useReply}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Sugerir respuesta con IA" }),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Usar en el mensaje" }),
  );
  expect(useReply).toHaveBeenCalledWith("Software dura tres semestres.");
  expect(api).toHaveBeenLastCalledWith(
    "/conversations/own/draft",
    "POST",
    expect.objectContaining({
      channel: "facebook",
      revision: 3,
      acknowledge_consumption: true,
    }),
  );
  expect(
    vi.mocked(api).mock.calls.some((call) => call[0]?.endsWith("/messages")),
  ).toBe(false);
});

it("discards late generation after a new incoming message", async () => {
  let complete!: (value: unknown) => void;
  vi.mocked(api)
    .mockResolvedValueOnce({ revision: 1 })
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          complete = resolve;
        }),
    );
  const { rerender } = render(
    <InboxSuggestion
      conversation="own"
      question="Hola"
      incoming="one"
      onUseReply={() => {}}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Sugerir respuesta con IA" }),
  );
  await vi.waitFor(() => expect(complete).toBeDefined());
  rerender(
    <InboxSuggestion
      conversation="own"
      question="Nuevo"
      incoming="two"
      onUseReply={() => {}}
    />,
  );
  complete({ text: "Respuesta obsoleta" });
  await vi.waitFor(() =>
    expect(screen.queryByText("Respuesta obsoleta")).not.toBeInTheDocument(),
  );
});
