import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { SiiePreicfes } from "./SiiePreicfes";
const mock = vi.hoisted(() => ({ call: vi.fn() }));
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  useInstitution: () => ({ call: mock.call }),
}));
const environment = {
  base_url: "https://siie.example.test/Test/",
  fingerprint: "a".repeat(64),
};
beforeEach(() => mock.call.mockReset());
it("does not write on mount and keeps another environment's work read-only", async () => {
  mock.call.mockResolvedValue({
    id: "fixture",
    revision: 1,
    state: "pending_review",
    environment,
    environment_current: false,
    writes_enabled: true,
    pending: "pending-fixture",
  });
  render(<SiiePreicfes environment={environment} editable />);
  expect(mock.call).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Trabajo guardado para consultar"), {
    target: { value: "fixture" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Consultar trabajo" }));
  await screen.findByText(/Este trabajo pertenece a otro entorno/);
  fireEvent.click(screen.getByRole("checkbox"));
  expect(
    screen.getByRole("button", { name: "Crear o renovar vínculo" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Consultar operación pendiente" }),
  ).toBeDisabled();
  expect(mock.call.mock.calls).toEqual([
    ["siie-registration/preicfes/fixture"],
  ]);
});
it("requires explicit plan and message selection instead of automatically choosing a plan", async () => {
  mock.call.mockResolvedValue({
    id: "fixture",
    revision: 2,
    state: "confirmed",
    environment,
    environment_current: true,
    writes_enabled: true,
    plans: {
      options: [
        {
          planId: 1,
          mode: "CONTADO",
          quoteRevisionId: "a".repeat(64),
          amountCop: 800000,
          expiresAtUtc: "2099-01-01T00:00:00Z",
          installments: [],
        },
      ],
    },
  });
  render(<SiiePreicfes environment={environment} editable />);
  fireEvent.change(screen.getByLabelText("Trabajo guardado para consultar"), {
    target: { value: "fixture" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Consultar trabajo" }));
  await screen.findByRole("button", { name: "Asignar plan confirmado" });
  fireEvent.click(screen.getByRole("checkbox"));
  expect(screen.getByLabelText("Plan elegido por el aspirante")).toHaveValue(
    "",
  );
  expect(
    screen.getByRole("button", { name: "Asignar plan confirmado" }),
  ).toBeDisabled();
  expect(mock.call).toHaveBeenCalledTimes(1);
});
