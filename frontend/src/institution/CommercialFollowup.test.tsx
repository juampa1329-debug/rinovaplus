import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CommercialFollowupReview } from "./CommercialFollowup";
const mock = vi.hoisted(() => ({ call: vi.fn(), actions: ["crm.write"] }));
vi.mock("./api", () => ({
  useInstitution: () => ({
    call: mock.call,
    session: { actions: mock.actions },
  }),
  ApiError: class extends Error {
    status = 409;
  },
}));
vi.mock("./drafts", () => ({ useDraftGuard: vi.fn() }));
vi.mock("./Settings", () => ({ useResource: () => ({ value: null }) }));
const person = {
  contact_id: "contact",
  name: "Ejemplo",
  stage: "Nuevo",
  signature: "signed",
  label: "Formulario enviado",
  next_action: "Ayudar con el formulario",
  quote: "Enlace oficial entregado",
  held: false,
  no_contact: false,
};
const review = { items: [person], ready: 1, review: 0 };
describe("Seguimiento según avance", () => {
  beforeEach(() => {
    mock.call.mockReset();
    mock.actions = ["crm.write"];
  });
  it("requires existing write permission without querying messages on render", () => {
    mock.actions = ["crm.read"];
    render(<CommercialFollowupReview changed={vi.fn()} />);
    expect(
      screen.queryByText("Seguimiento de interés y formularios"),
    ).toBeNull();
    expect(mock.call).not.toHaveBeenCalled();
  });
  it("reviews evidence before registering tasks and never sends messages", async () => {
    mock.call.mockImplementation(async (path: string) =>
      path.endsWith("preview") ? review : { updated: 1 },
    );
    render(<CommercialFollowupReview changed={vi.fn()} />);
    fireEvent.click(screen.getByText("Revisar interés y formularios"));
    await screen.findByText("Formulario enviado");
    expect(screen.getByText("Registrar seguimientos revisados")).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText("Registrar seguimientos revisados"));
    await screen.findByText(
      "Casos claros: 1 · Para revisión: 0 · Registrados: 1",
    );
    const sent = mock.call.mock.calls.find(([p]) => p.endsWith("apply"));
    expect(sent?.[2].items).toEqual([
      { contact_id: "contact", signature: "signed" },
    ]);
    expect(
      mock.call.mock.calls.some(([p]) => /messages|consent|activate/.test(p)),
    ).toBe(false);
  });
  it("does not include opted out or registered contacts in changes", async () => {
    mock.call.mockResolvedValue({
      items: [{ ...person, no_contact: true, suppressed: true }],
      ready: 0,
      review: 1,
    });
    render(<CommercialFollowupReview changed={vi.fn()} />);
    fireEvent.click(screen.getByText("Revisar interés y formularios"));
    await screen.findByText("Formulario enviado");
    fireEvent.click(screen.getByRole("checkbox"));
    expect(screen.getByText("Registrar seguimientos revisados")).toBeDisabled();
  });
  it("retains the same operation after an unconfirmed result", async () => {
    let fail = true;
    mock.call.mockImplementation(async (path: string) => {
      if (path.endsWith("preview")) return review;
      if (fail) {
        fail = false;
        throw Error("Resultado por confirmar");
      }
      return { updated: 1 };
    });
    render(<CommercialFollowupReview changed={vi.fn()} />);
    fireEvent.click(screen.getByText("Revisar interés y formularios"));
    await screen.findByText("Formulario enviado");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText("Registrar seguimientos revisados"));
    await screen.findByText("Resultado por confirmar");
    fireEvent.click(screen.getByText("Continuar registro de seguimientos"));
    await screen.findByText(
      "Casos claros: 1 · Para revisión: 0 · Registrados: 1",
    );
    const calls = mock.call.mock.calls.filter(([p]) => p.endsWith("apply"));
    expect(calls[0][2]).toEqual(calls[1][2]);
  });
});
