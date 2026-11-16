import { useState } from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { AcademicPrograms } from "../institution/AcademicPrograms";
import { LiveModelSelect } from "../institution/LiveModelSelect";
import { SessionBoundary } from "../institution/api";

function mount(child: React.ReactNode) {
  render(
    <SessionBoundary
      expire={() => {}}
      initial={{
        session_id: "editor",
        csrf_token: "fixture-token",
        actions: ["agents.manage", "settings.providers.read"],
        user: {
          id: "editor",
          email: "editor@example.invalid",
          full_name: "Editor",
          active: true,
          role: "owner",
          revision: 1,
          profile: {},
          mfa_state: "disabled",
        },
      }}
    >
      {child}
    </SessionBoundary>,
  );
}

const response = (body: unknown) => new Response(JSON.stringify(body));

it("keeps extracted facts in a draft until the editor applies, reviews and saves", async () => {
  const source = "https://institution.example/enfermeria";
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, options) => {
      const path = String(input);
      if (path.includes("/programs?"))
        return response({
          items: [{ program_id: 37, name: "Software", school: "Tecnología" }],
          has_more: false,
        });
      if (path.endsWith("/import")) {
        expect(JSON.parse(String(options?.body))).toEqual({ url: source });
        return response({
          name: "Auxiliar de Enfermería",
          school: "Salud",
          schedule: "",
          commercial: {
            duration: "Tres semestres",
            price_cop: 200000,
            price_concept: "Matrícula",
            price_valid_until: null,
            source_url: source,
          },
        });
      }
      return response({ program_id: 38, revision: 1 });
    });
  try {
    mount(<AcademicPrograms />);
    expect(
      await screen.findByRole("heading", { name: "Tecnología" }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Enlace oficial del programa"), {
      target: { value: source },
    });
    fireEvent.click(screen.getByRole("button", { name: "Extraer con IA" }));
    const apply = await screen.findByRole("button", {
      name: "Aplicar al borrador",
    });
    expect(screen.getByLabelText("Nombre oficial")).toHaveValue("");
    fireEvent.click(apply);
    expect(screen.getByLabelText("Duración")).toHaveValue("Tres semestres");
    fireEvent.change(screen.getByLabelText("Precio en COP"), {
      target: { value: "250000" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Guardar programa" }));
    await waitFor(() =>
      expect(screen.getByText("Programa guardado.")).toBeInTheDocument(),
    );
    const save = fetcher.mock.calls.find(
      ([path, options]) =>
        String(path).endsWith("/programs") && options?.method === "POST",
    );
    expect(JSON.parse(String(save?.[1]?.body))).toMatchObject({
      school: "Salud",
      commercial: {
        duration: "Tres semestres",
        price_cop: 250000,
        source_url: source,
      },
    });
  } finally {
    fetcher.mockRestore();
  }
});

it("queries the chosen provider and filters available OpenRouter models by family", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    response({
      items: [
        { id: "google/gemma-fixture", name: "Gemma" },
        { id: "google/gemini-fixture", name: "Gemini" },
        { id: "anthropic/claude-fixture", name: "Claude" },
      ],
    }),
  );
  function Picker() {
    const [value, setValue] = useState("");
    return (
      <LiveModelSelect
        provider="openrouter"
        category="text"
        value={value}
        onChange={setValue}
      />
    );
  }
  try {
    mount(<Picker />);
    const families = await screen.findByLabelText("Familia de modelos");
    expect(fetcher.mock.calls[0][0]).toBe(
      "/api/institution/provider-catalog/openrouter/text",
    );
    fireEvent.change(families, { target: { value: "Gemma" } });
    const picker = screen.getByLabelText("Seleccionar modelo");
    expect(
      within(picker).queryByText(/google\/gemini-fixture/),
    ).not.toBeInTheDocument();
    fireEvent.change(picker, { target: { value: "google/gemma-fixture" } });
    expect(picker).toHaveValue("google/gemma-fixture");
  } finally {
    fetcher.mockRestore();
  }
});
