import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { BroadcastProspectSetup } from "./BroadcastProspectSetup";

const mock = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("./api", () => ({
  ApiError: class extends Error {},
  useInstitution: () => ({ call: mock.call, session: { actions: ["crm.write", "inbox.write"] } }),
}));
vi.mock("./drafts", () => ({ useDraftGuard: vi.fn() }));
const source = {
  version: "rinovaplus-whatsapp-prospects-v1", program: "logistica",
  contact_ids: ["f9cfcb75-d7f1-4c95-adea-63a0360e4a12"],
};
beforeEach(() => mock.call.mockReset());
async function fill() {
  const file = new File([JSON.stringify(source)], "revisados.json", { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => JSON.stringify(source) });
  fireEvent.change(screen.getByLabelText("Lote de preinscritos revisado"), { target: { files: [file] } });
  await screen.findByText("1 contactos · Logística");
  fireEvent.change(screen.getByLabelText("Evidencia de autorización del lote"), { target: { value: "Políticas confirmadas por el titular" } });
  fireEvent.change(screen.getByLabelText("Fuente de la autorización"), { target: { value: "Solicitud expresa" } });
  fireEvent.change(screen.getByLabelText("Vigencia para este seguimiento"), { target: { value: "2026-11-24T22:00" } });
}
it("requires explicit evidence and only calls onboarding, without activating or sending", async () => {
  mock.call.mockResolvedValue({ items: [], messages_sent: 0 });
  render(<BroadcastProspectSetup account="account" changed={vi.fn()} />);
  await fill();
  const submit = screen.getByText("Vincular y registrar autorización, sin enviar");
  expect(submit).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(submit);
  await screen.findByText(/Lote vinculado/);
  expect(mock.call).toHaveBeenCalledTimes(1);
  expect(mock.call.mock.calls[0][0]).toBe("broadcasts/accounts/account/prospects/setup");
  expect(mock.call.mock.calls[0][2].contact_ids).toEqual(source.contact_ids);
});
it("recovers the same pending operation after an interrupted response", async () => {
  mock.call.mockRejectedValueOnce(Error("Respuesta interrumpida")).mockResolvedValue({});
  render(<BroadcastProspectSetup account="account" changed={vi.fn()} />);
  await fill();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByText("Vincular y registrar autorización, sin enviar"));
  await screen.findByText(/Respuesta interrumpida/);
  const initial = mock.call.mock.calls[0][2];
  expect(screen.getByLabelText("Evidencia de autorización del lote")).toBeDisabled();
  fireEvent.click(screen.getByText("Vincular y registrar autorización, sin enviar"));
  await screen.findByText(/Lote vinculado/);
  expect(mock.call.mock.calls[1][2]).toEqual(initial);
});
