import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MissingReplies } from "../institution/MissingReplies";
const mocks = vi.hoisted(() => ({
  call: vi.fn(),
  reload: vi.fn(),
  read: vi.fn(),
}));
vi.mock("../institution/api", async (original) => ({
  ...(await original<typeof import("../institution/api")>()),
  useInstitution: () => ({
    call: mocks.call,
    session: { actions: ["inbox.write", "settings.channels.write"] },
  }),
}));
vi.mock("../institution/Settings", () => ({
  useResource: (path: string) => {
    mocks.read(path);
    return {
      value: {
        items: [
          {
            id: "input",
            conversation_id: "thread",
            name: "Persona de ensayo",
            account: "Cuenta Meta",
            channel: "whatsapp",
            at: "2026-11-23T12:00:00Z",
            proof: "a".repeat(64),
          },
        ],
      },
      error: "",
      reload: mocks.reload,
    };
  },
  ResourceState: () => null,
}));
afterEach(cleanup);
it("requires selection and a concrete review before scheduling original inputs without resend", async () => {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
  mocks.call.mockResolvedValue({ queued: 1 });
  render(<MissingReplies conversation="thread" />);
  expect(mocks.call).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", {
      name: "Revisar entradas sin solicitud de IA",
    }),
  );
  expect(mocks.read).toHaveBeenCalledWith(
    "reply-recovery?conversation_id=thread",
  );
  expect(
    screen.getByRole("button", { name: "Revisar 0 respuestas pendientes" }),
  ).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox", { name: /Persona de ensayo/ }));
  fireEvent.click(
    screen.getByRole("button", { name: "Revisar 1 respuestas pendientes" }),
  );
  expect(
    await screen.findByRole("alertdialog", {
      name: "Preparar las respuestas pendientes",
    }),
  ).toHaveTextContent("No se reenvían mensajes anteriores");
  expect(mocks.call).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Poner respuestas en preparación" }),
  );
  await waitFor(() =>
    expect(mocks.call).toHaveBeenCalledWith("reply-recovery", "POST", {
      operation_id: expect.any(String),
      confirmed: true,
      inputs: [{ id: "input", proof: "a".repeat(64) }],
    }),
  );
  await waitFor(() => expect(mocks.reload).toHaveBeenCalled());
});


it("reviews automatic advisor handoffs separately and explains restoring IA", async () => {
  mocks.call.mockClear();
  mocks.call.mockResolvedValue({ queued: 1 });
  render(<MissingReplies advisor />);
  fireEvent.click(screen.getByRole("button", { name: "Revisar solicitudes del botón comercial" }));
  expect(mocks.read).toHaveBeenCalledWith("advisor-recovery");
  fireEvent.click(screen.getByRole("checkbox", { name: /Persona de ensayo/ }));
  fireEvent.click(screen.getByRole("button", { name: "Revisar 1 respuestas pendientes" }));
  expect(await screen.findByRole("alertdialog", { name: "Recuperar atención comercial" })).toHaveTextContent("único cambio a Humano");
  fireEvent.click(screen.getByRole("button", { name: "Poner respuestas en preparación" }));
  await waitFor(() => expect(mocks.call).toHaveBeenCalledWith("advisor-recovery", "POST", expect.objectContaining({confirmed: true})));
});
