import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { LanguageRehearsal } from "../institution/LanguageRehearsal";

const api = vi.hoisted(() => vi.fn());
vi.mock("../institution/api", () => ({
  useInstitution: () => ({ call: api }),
  useTask: () => ({
    busy: false,
    notices: null,
    run: async (fn: () => Promise<void>) => fn(),
  }),
}));

it("runs one synthetic-failure rehearsal then recovers its result only with GET", async () => {
  api.mockReset();
  api.mockResolvedValue({
    state: "passed",
    operation_id: "fixture",
    case: "unavailable",
    real_backup: true,
    provider_calls: 1,
    text: "Respuesta de respaldo",
    trace: {
      attempts: [
        {
          provider: "openrouter",
          model: "fixture:free",
          state: "completed",
          role: "fallback",
        },
      ],
    },
  });
  render(<LanguageRehearsal revision={27} enabled dirty={false} />);
  fireEvent.click(
    screen.getByRole("button", { name: "Ejecutar simulación controlada" }),
  );
  await screen.findByText("Ensayo superado");
  expect(api).toHaveBeenCalledWith(
    "language-rehearsals",
    "POST",
    expect.objectContaining({
      revision: 27,
      case: "unavailable",
      audience: "message",
    }),
  );
  expect(
    screen.getByRole("button", { name: "Ejecutar simulación controlada" }),
  ).toBeDisabled();
  fireEvent.click(
    screen.getByRole("button", { name: "Consultar resultado sin repetir" }),
  );
  await waitFor(() => expect(api.mock.calls).toHaveLength(2));
  expect(api.mock.calls[1][0]).toMatch(/^language-rehearsals\//);
  expect(api.mock.calls[1][1]).toBeUndefined();
  expect(api.mock.calls.filter((args) => args[1] === "POST")).toHaveLength(1);
});

it("blocks a rehearsal while the AI settings draft is unsaved", () => {
  render(<LanguageRehearsal revision={27} enabled dirty />);
  expect(
    screen.getByRole("button", { name: "Ejecutar simulación controlada" }),
  ).toBeDisabled();
});
