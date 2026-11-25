import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { BroadcastProspectSetup } from "./BroadcastProspectSetup";

const mock = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("./api", () => ({
  ApiError: class extends Error {},
  useInstitution: () => ({
    call: mock.call,
    session: { actions: ["crm.write", "inbox.write"] },
  }),
}));
vi.mock("./drafts", () => ({ useDraftGuard: vi.fn() }));
const source = {
  version: "rinovaplus-whatsapp-prospects-v1",
  program: "logistica",
  contact_ids: ["f9cfcb75-d7f1-4c95-adea-63a0360e4a12"],
};
beforeEach(() => mock.call.mockReset());
async function fill(value = source) {
  const file = new File([JSON.stringify(value)], "revisados.json", {
    type: "application/json",
  });
  Object.defineProperty(file, "text", {
    value: async () => JSON.stringify(value),
  });
  fireEvent.change(screen.getByLabelText("Lote de preinscritos revisado"), {
    target: { files: [file] },
  });
  await screen.findByText("1 contactos · Logística");
  fireEvent.change(
    screen.getByLabelText("Evidencia de autorización del lote"),
    { target: { value: "Políticas confirmadas por el titular" } },
  );
  fireEvent.change(screen.getByLabelText("Fuente de la autorización"), {
    target: { value: "Solicitud expresa" },
  });
  fireEvent.change(screen.getByLabelText("Vigencia para este seguimiento"), {
    target: { value: "2026-11-24T22:00" },
  });
}
it("requires explicit evidence and only calls onboarding, without activating or sending", async () => {
  mock.call.mockResolvedValue({ items: [], messages_sent: 0 });
  render(<BroadcastProspectSetup account="account" changed={vi.fn()} />);
  await fill();
  const submit = screen.getByText(
    "Vincular y registrar autorización, sin enviar",
  );
  expect(submit).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(submit);
  await screen.findByText(/Lote vinculado/);
  expect(mock.call).toHaveBeenCalledTimes(1);
  expect(mock.call.mock.calls[0][0]).toBe(
    "broadcasts/accounts/account/prospects/setup",
  );
  expect(mock.call.mock.calls[0][2].contact_ids).toEqual(source.contact_ids);
});

it("keeps additional phones explicit and exports only completed native routes", async () => {
  const contact = source.contact_ids[0];
  const primary = "01234567-89ab-4def-8123-0123456789ab";
  const additional = "12345678-89ab-4def-8123-0123456789ab";
  mock.call.mockResolvedValue({
    items: [{ contact_id: contact, identity_id: primary }],
    additional_items: [{ contact_id: contact, identity_id: additional }],
    held: [],
    messages_sent: 0,
  });
  render(<BroadcastProspectSetup account="account" changed={vi.fn()} />);
  await fill({
    ...source,
    additional_phones: { [contact]: "+573119876543" },
  } as typeof source);
  expect(
    screen.queryByText("Descargar destinos alternativos revisados"),
  ).toBeNull();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(
    screen.getByText("Vincular y registrar autorización, sin enviar"),
  );
  await screen.findByText("Descargar destinos alternativos revisados");
  expect(mock.call.mock.calls[0][2].additional_phones).toEqual({
    [contact]: "+573119876543",
  });
  expect(
    mock.call.mock.calls.some(([path]) => /activate|send$/.test(path)),
  ).toBe(false);
});
it("recovers the same pending operation after an interrupted response", async () => {
  mock.call
    .mockRejectedValueOnce(Error("Respuesta interrumpida"))
    .mockResolvedValue({});
  render(<BroadcastProspectSetup account="account" changed={vi.fn()} />);
  await fill();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(
    screen.getByText("Vincular y registrar autorización, sin enviar"),
  );
  await screen.findByText(/Respuesta interrumpida/);
  const initial = mock.call.mock.calls[0][2];
  expect(
    screen.getByLabelText("Evidencia de autorización del lote"),
  ).toBeDisabled();
  fireEvent.click(
    screen.getByText("Vincular y registrar autorización, sin enviar"),
  );
  await screen.findByText(/Lote vinculado/);
  expect(mock.call.mock.calls[1][2]).toEqual(initial);
});

it("loads every CRM program once and only enables reviewed contacts without sending", async () => {
  mock.call
    .mockResolvedValueOnce({ ...source, program: "all", review_count: 2 })
    .mockResolvedValueOnce({ items: [source.contact_ids[0]], held: [] });
  render(<BroadcastProspectSetup account="account" changed={vi.fn()} />);
  fireEvent.click(screen.getByText("Cargar todos los preinscritos del CRM"));
  await screen.findByText("1 contactos · Todos los programas");
  fireEvent.change(
    screen.getByLabelText("Evidencia de autorización del lote"),
    { target: { value: "Políticas confirmadas por el titular" } },
  );
  fireEvent.change(screen.getByLabelText("Fuente de la autorización"), {
    target: { value: "Solicitud expresa" },
  });
  fireEvent.change(screen.getByLabelText("Vigencia para este seguimiento"), {
    target: { value: "2026-11-24T22:00" },
  });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(
    screen.getByText("Vincular y registrar autorización, sin enviar"),
  );
  await screen.findByText(/1 habilitados · 2 para revisión/);
  expect(mock.call.mock.calls[0][0]).toBe(
    "broadcasts/accounts/account/prospects",
  );
  expect(mock.call.mock.calls[1][2].program).toBe("all");
  expect(
    mock.call.mock.calls.some(([path]) => /activate|send$/.test(path)),
  ).toBe(false);
});
