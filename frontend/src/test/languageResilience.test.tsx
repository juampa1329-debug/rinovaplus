import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { LanguageResilience } from "../institution/LanguageResilience";

vi.mock("../modules/crm-configuration/hooks/useCrmConfiguration", () => ({
  useCrmConfiguration: () => ({
    ready: true,
    error: "",
    config: {
      stages: [
        { key: "nuevo", label: "Nuevo", active: true },
        { key: "objeciones", label: "Dudas y objeciones", active: true },
        { key: "old", label: "Inactiva", active: false },
      ],
    },
  }),
}));

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
  expect(
    screen.getByRole("checkbox", {
      name: "Habilitar respaldo en mensajes y comentarios automáticos",
    }),
  ).not.toBeChecked();
  expect(
    screen.getByRole("checkbox", {
      name: "Usar respaldo si el principal agota el tiempo de respuesta",
    }),
  ).toBeDisabled();
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

it("prepares timeout recovery explicitly without changing routes or saving automatically", () => {
  const change = vi.fn();
  const routes = [
    {
      provider: "openrouter",
      model: "fixture",
      input_usd_per_million: 0.4,
      output_usd_per_million: 1.6,
    },
  ];
  render(
    <LanguageResilience value={{ enabled: true, routes }} onChange={change} />,
  );
  fireEvent.click(
    screen.getByRole("checkbox", {
      name: "Usar respaldo si el principal agota el tiempo de respuesta",
    }),
  );
  expect(change).toHaveBeenCalledWith({
    enabled: true,
    routes,
    fallback_on_timeout: true,
  });
  expect(
    screen.queryByRole("button", { name: /^Guardar/ }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByText(/La solicitud original podría consumir tokens/),
  ).toBeInTheDocument();
});

it("selects a separate primary from the live catalog and saves only on request", () => {
  const change = vi.fn(),
    save = vi.fn(async () => {});
  const policy = {
    enabled: true,
    routes: [
      {
        provider: "openrouter",
        model: "backup",
        input_usd_per_million: 1,
        output_usd_per_million: 2,
      },
    ],
  };
  const { rerender } = render(
    <LanguageResilience value={policy} onChange={change} onSave={save} />,
  );
  fireEvent.click(
    screen.getByRole("checkbox", {
      name: "Elegir principal para mensajes y comentarios",
    }),
  );
  const next = change.mock.lastCall![0];
  expect(next.routes).toEqual(policy.routes);
  expect(next.primary.provider).toBe("openrouter");
  rerender(<LanguageResilience value={next} onChange={change} onSave={save} />);
  fireEvent.change(
    screen.getByLabelText("Modelo principal de conversaciones"),
    { target: { value: "google/fixture:free" } },
  );
  expect(change.mock.lastCall![0].primary.model).toBe("google/fixture:free");
  expect(save).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar motor y respaldos" }),
  );
  expect(save).toHaveBeenCalledTimes(1);
});

it("selects opening stages from CRM and edits the output envelope without saving or altering backups", () => {
  const change = vi.fn(),
    save = vi.fn(async () => {});
  const route = {
    provider: "openrouter" as const,
    model: "fixture",
    input_usd_per_million: 1,
    output_usd_per_million: 2,
  };
  const policy = {
    enabled: true,
    primary: route,
    routes: [{ ...route, model: "backup" }],
    opening: route,
    opening_stage_keys: [],
  };
  render(<LanguageResilience value={policy} onChange={change} onSave={save} />);
  fireEvent.click(screen.getByRole("checkbox", { name: "Nuevo" }));
  expect(change.mock.lastCall![0].opening_stage_keys).toEqual(["nuevo"]);
  expect(change.mock.lastCall![0].routes).toEqual(policy.routes);
  expect(
    screen.queryByRole("checkbox", { name: "Inactiva" }),
  ).not.toBeInTheDocument();
  fireEvent.change(
    screen.getByLabelText("Máximo de tokens por respuesta de los agentes"),
    { target: { value: "4000" } },
  );
  expect(change.mock.lastCall![0].reply_max_tokens).toBe(4000);
  expect(save).not.toHaveBeenCalled();
  expect(
    screen.getByText(/Financiación, objeciones, cierre y seguimiento/),
  ).toBeInTheDocument();
});
