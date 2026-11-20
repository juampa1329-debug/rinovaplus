import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { LanguageResilience } from "../institution/LanguageResilience";

vi.mock("../institution/LiveModelSelect", () => ({
  LiveModelSelect: ({
    label,
    onChange,
  }: {
    label: string;
    onChange: (model: string) => void;
  }) => (
    <select
      aria-label={label}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">Seleccionar</option>
      <option value="google/fixture:free">Modelo gratuito verificado</option>
    </select>
  ),
}));

it("prepares an explicit free backup without enabling or saving the policy", () => {
  const change = vi.fn();
  const { rerender } = render(
    <LanguageResilience value={undefined} onChange={change} />,
  );
  expect(screen.getByRole("checkbox")).not.toBeChecked();
  fireEvent.click(
    screen.getByRole("button", { name: "Añadir modelo de respaldo" }),
  );
  const policy = change.mock.calls[0][0];
  expect(policy).toEqual({
    enabled: false,
    routes: [
      {
        provider: "openrouter",
        model: "",
        input_usd_per_million: 0,
        output_usd_per_million: 0,
      },
    ],
  });
  rerender(<LanguageResilience value={policy} onChange={change} />);
  fireEvent.change(screen.getByLabelText("Modelo del respaldo 1"), {
    target: { value: "google/fixture:free" },
  });
  expect(change.mock.lastCall?.[0].routes[0].model).toBe("google/fixture:free");
  expect(
    screen.queryByRole("button", { name: /^Guardar/ }),
  ).not.toBeInTheDocument();
});
