import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MasterclassInterests } from "./MasterclassInterests";

const mock = vi.hoisted(() => ({ call: vi.fn(), actions: ["crm.write"] }));
vi.mock("./api", () => ({
  useInstitution: () => ({
    call: mock.call,
    session: { actions: mock.actions },
  }),
}));
vi.mock("./drafts", () => ({ useDraftGuard: vi.fn() }));
const review = {
  groups: [
    {
      source: "MASTERCLASS TURISMO",
      programs: ["SERVICIOS HOTELEROS Y AGENCIAS TURISTICAS"],
      count: 1,
      review: 0,
      reason: "",
    },
  ],
  items: [{ contact_id: "contact", signature: "signed" }],
  ready: 1,
  review: 0,
};

describe("Relación comercial de masterclasses", () => {
  beforeEach(() => {
    mock.call.mockReset();
    mock.actions = ["crm.write"];
  });
  it("keeps review and changes behind existing CRM write permission", () => {
    mock.actions = ["crm.read"];
    render(<MasterclassInterests changed={vi.fn()} />);
    expect(
      screen.queryByText("Relacionar masterclasses con programas"),
    ).toBeNull();
    expect(mock.call).not.toHaveBeenCalled();
  });
  it("shows school choices before updating only the reviewed interests", async () => {
    mock.call.mockImplementation(async (path: string) =>
      path.endsWith("preview")
        ? review
        : { items: [{ contact_id: "contact", state: "updated" }] },
    );
    render(<MasterclassInterests changed={vi.fn()} />);
    fireEvent.click(screen.getByText("Revisar intereses de masterclass"));
    await screen.findByText("Listos: 1 · Para revisión: 0 · Actualizados: 0");
    expect(screen.getByText("Actualizar intereses revisados")).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText("Actualizar intereses revisados"));
    await screen.findByText("Listos: 1 · Para revisión: 0 · Actualizados: 1");
    expect(
      mock.call.mock.calls.find(([path]) => path.endsWith("apply"))?.[2].items,
    ).toEqual(review.items);
    expect(
      mock.call.mock.calls.some(([path]) =>
        /message|consent|campaign/.test(path),
      ),
    ).toBe(false);
  });
  it("preserves the same operation after an uncertain result instead of generating another", async () => {
    let fail = true;
    mock.call.mockImplementation(async (path: string) => {
      if (path.endsWith("preview")) return review;
      if (fail) {
        fail = false;
        throw new Error("La respuesta no quedó confirmada");
      }
      return { items: [{ contact_id: "contact", state: "updated" }] };
    });
    render(<MasterclassInterests changed={vi.fn()} />);
    fireEvent.click(screen.getByText("Revisar intereses de masterclass"));
    await screen.findByRole("checkbox");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByText("Actualizar intereses revisados"));
    await screen.findByText("La respuesta no quedó confirmada");
    fireEvent.click(screen.getByText("Actualizar intereses revisados"));
    await screen.findByText("Listos: 1 · Para revisión: 0 · Actualizados: 1");
    const calls = mock.call.mock.calls.filter(([path]) =>
      path.endsWith("apply"),
    );
    expect(calls[0][2]).toEqual(calls[1][2]);
  });
});
