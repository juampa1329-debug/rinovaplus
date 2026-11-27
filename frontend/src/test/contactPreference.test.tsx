import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ContactPreference } from "../institution/ContactPreference";
const state = vi.hoisted(() => ({
  blocked: true,
  error: "",
  actions: ["crm.write"],
  call: vi.fn(),
  reload: vi.fn(),
}));
vi.mock("../institution/Settings", () => ({
  useResource: () => ({
    value: { no_contact: state.blocked },
    error: state.error,
    reload: state.reload,
  }),
}));
vi.mock("../institution/api", async (original) => ({
  ...(await original<typeof import("../institution/api")>()),
  useInstitution: () => ({
    session: { actions: state.actions },
    call: state.call,
  }),
}));
beforeEach(() => {
  state.blocked = true;
  state.error = "";
  state.actions = ["crm.write"];
  state.call.mockReset().mockResolvedValue({ no_contact: true });
  state.reload.mockReset().mockResolvedValue(undefined);
});
afterEach(cleanup);
it("shows explicit no-contact status separately from sales stage", () => {
  render(<ContactPreference id="contact" />);
  expect(screen.getByText("No contactar")).toBeInTheDocument();
  expect(
    screen.getByText(/excluye de campañas y seguimientos/),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Registrar No contactar" }),
  ).not.toBeInTheDocument();
});
it("never presents a missing preference as permission to send", () => {
  state.blocked = false;
  render(<ContactPreference id="other" />);
  expect(
    screen.getByText(/verifica por separado el consentimiento/),
  ).toBeInTheDocument();
});
it("does not show an allowed state if the preference query fails", () => {
  state.error = "unavailable";
  render(<ContactPreference id="other" />);
  expect(screen.getByText(/No se pudo consultar/)).toBeInTheDocument();
  expect(screen.queryByText(/Sin solicitud/)).not.toBeInTheDocument();
});
it("only allows an explicit request with a reason and never submits the parent contact form", async () => {
  state.blocked = false;
  const submit = vi.fn((e) => e.preventDefault());
  render(
    <form onSubmit={submit}>
      <ContactPreference id="contact" />
      <button type="submit">Guardar ficha</button>
    </form>,
  );
  fireEvent.click(screen.getByText("Registrar solicitud de No contactar"));
  const button = screen.getByRole("button", { name: "Registrar No contactar" });
  expect(button).toBeDisabled();
  const reason = screen.getByRole("textbox", {
    name: "Motivo de No contactar",
  });
  fireEvent.change(reason, {
    target: { value: "La persona pidió no recibir mensajes." },
  });
  expect(button).toBeDisabled();
  expect(fireEvent.keyDown(reason, { key: "Enter" })).toBe(false);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(button);
  await waitFor(() => expect(state.reload).toHaveBeenCalledTimes(1));
  expect(submit).not.toHaveBeenCalled();
  expect(state.call).toHaveBeenCalledTimes(1);
  expect(state.call).toHaveBeenCalledWith(
    "workspace/contact-preference/contact",
    "POST",
    {
      reason: "La persona pidió no recibir mensajes.",
      confirmed: true,
      operationId: expect.any(String),
    },
  );
});
it("hides manual writes without CRM write permission", () => {
  state.blocked = false;
  state.actions = ["crm.read"];
  render(<ContactPreference id="contact" />);
  expect(
    screen.queryByText("Registrar solicitud de No contactar"),
  ).not.toBeInTheDocument();
});
it("preserves the same operation after an uncertain response and isolates another contact", async () => {
  state.blocked = false;
  state.call.mockRejectedValueOnce(new Error("network unavailable"));
  const view = render(<ContactPreference id="contact" />);
  fireEvent.click(screen.getByText("Registrar solicitud de No contactar"));
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "Solicitud confirmada por el asesor." },
  });
  fireEvent.click(screen.getByRole("checkbox"));
  const button = screen.getByRole("button", { name: "Registrar No contactar" });
  fireEvent.click(button);
  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(state.call).toHaveBeenCalledTimes(1);
  fireEvent.click(button);
  await waitFor(() => expect(state.reload).toHaveBeenCalledTimes(1));
  expect(state.call.mock.calls[0][2].operationId).toBe(
    state.call.mock.calls[1][2].operationId,
  );
  state.call.mockRejectedValueOnce(new Error("network unavailable"));
  fireEvent.click(button);
  await waitFor(() => expect(state.call).toHaveBeenCalledTimes(3));
  await waitFor(() => expect(button).toBeEnabled());
  view.rerender(<ContactPreference id="other" />);
  fireEvent.click(
    screen.getByRole("button", { name: "Registrar No contactar" }),
  );
  await waitFor(() => expect(state.call).toHaveBeenCalledTimes(4));
  expect(state.call.mock.calls[2][2].operationId).not.toBe(
    state.call.mock.calls[3][2].operationId,
  );
});
