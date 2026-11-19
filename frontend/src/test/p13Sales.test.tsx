import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { useState } from "react";
import { AgentSalesSkills } from "../institution/AgentSalesSkills";
import { ProgramSalesSetup } from "../institution/ProgramSalesSetup";
import { ConversationSalesMemory } from "../institution/ConversationSalesMemory";
import { blankConfiguration, type Catalog } from "../modules/agents/api";

const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("../modules/agents/api", async (original) => ({
  ...(await original<typeof import("../modules/agents/api")>()),
  api: mocks.api,
}));
afterEach(cleanup);
beforeEach(() => mocks.api.mockReset());

test("skills are selectable and disabling memory also stops automatic CRM writes", async () => {
  mocks.api.mockResolvedValue({
    items: [
      {
        id: "recall",
        name: "Recuperar contexto",
        category: "Memoria",
        procedure: "Sólo hechos",
      },
      {
        id: "close-plan",
        name: "Cerrar con un paso",
        category: "Cierre",
        procedure: "Sin presión",
      },
    ],
  });
  function Editor() {
    const [configuration, set] = useState({
      ...blankConfiguration(),
      sales_memory_enabled: true,
      auto_sales_crm: true,
    });
    return (
      <>
        <AgentSalesSkills
          configuration={configuration}
          guide
          onChange={(value) => set((old) => ({ ...old, ...value }))}
        />
        <output>
          {JSON.stringify(configuration.sales_skill_ids)}:
          {String(configuration.auto_sales_crm)}
        </output>
      </>
    );
  }
  render(<Editor />);
  await screen.findByText("Recuperar contexto");
  fireEvent.click(
    screen.getByRole("button", { name: "Seleccionar las 20 skills" }),
  );
  expect(
    screen.getByRole("checkbox", { name: /Recuperar contexto/ }),
  ).toBeChecked();
  fireEvent.click(
    screen.getByRole("checkbox", { name: /Conservar memoria comercial/ }),
  );
  expect(
    screen.getByRole("checkbox", { name: /Completar datos comerciales/ }),
  ).not.toBeChecked();
  expect(
    screen.getByRole("checkbox", { name: /Completar datos comerciales/ }),
  ).toBeDisabled();
});

test("skill catalog can recover after a deployment without changing the saved selection", async () => {
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.removeAttribute("open");
    },
  });
  mocks.api
    .mockRejectedValueOnce(new Error("Servicio en actualización"))
    .mockResolvedValue({
      items: [
        {
          id: "recall",
          name: "Recuperar contexto",
          category: "Memoria",
          procedure: "Sólo hechos",
        },
      ],
    });
  const change = vi.fn();
  render(
    <AgentSalesSkills
      configuration={{ ...blankConfiguration(), sales_skill_ids: ["recall"] }}
      guide
      onChange={change}
    />,
  );
  await screen.findByRole("alertdialog", {
    name: "No se pudieron cargar las skills",
  });
  fireEvent.click(screen.getByRole("button", { name: "Cerrar aviso" }));
  fireEvent.click(screen.getByRole("button", { name: "Actualizar skills" }));
  await screen.findByText("1 de 1 activas");
  expect(
    screen.getByRole("checkbox", { name: /Recuperar contexto/ }),
  ).toBeChecked();
  expect(change).not.toHaveBeenCalled();
});

test("specialists require a reviewed preview, and preserve existing agents", async () => {
  const guide = {
    id: "guide",
    name: "Admisiones",
    level: "guide",
    state: "active",
  };
  const catalog = {
    agents: [guide],
    programs: { items: [] },
  } as unknown as Catalog;
  const plan = {
    guide_id: "guide",
    guide_name: "Admisiones",
    digest: "d".repeat(64),
    provider: "gemini",
    model: "saved-model",
    guide_changes: ["20 skills"],
    items: [
      {
        program_id: 1,
        name: "Software",
        school: "TIC",
        schedule: "Diurna",
        action: "create",
        missing: ["requirements"],
        price_pending: true,
        system_prompt: "Especialista Software con fuentes",
      },
      {
        program_id: 2,
        name: "Enfermería",
        school: "Salud",
        schedule: "Diurna",
        action: "preserve",
        missing: [],
        price_pending: false,
        system_prompt: "Especialista Enfermería",
      },
    ],
  };
  mocks.api.mockImplementation((path = "") =>
    Promise.resolve(
      path.includes("preview") ? plan : { created: 1, preserved: 1 },
    ),
  );
  const refresh = vi.fn(async () => {});
  render(
    <ProgramSalesSetup catalog={catalog} disabled={false} onSaved={refresh} />,
  );
  fireEvent.click(
    screen.getByText("Especialistas por programa y origen de anuncios"),
  );
  fireEvent.change(screen.getByLabelText("Orientador de Admisiones"), {
    target: { value: "guide" },
  });
  fireEvent.click(
    screen.getByRole("button", {
      name: "Preparar especialistas de todos los programas",
    }),
  );
  await screen.findByText("2 programas · gemini / saved-model");
  const create = screen.getByRole("button", {
    name: "Crear especialistas revisados",
  });
  expect(create).toBeDisabled();
  expect(screen.getByText("Conservar agente existente")).toBeVisible();
  fireEvent.click(screen.getByLabelText(/Revisé la creación de especialistas/));
  fireEvent.click(create);
  await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  expect(mocks.api).toHaveBeenCalledWith(
    "/sales/provision",
    "POST",
    expect.objectContaining({
      guide_id: "guide",
      preview_digest: plan.digest,
      confirmed: true,
    }),
  );
});

test("private graph loads only when opened and never carries the previous conversation into the next", async () => {
  const data = {
    revision: 1,
    facts: [
      {
        field: "schedule",
        value: "Prefiero de noche",
        source_message_id: "source",
        sequence: 7,
      },
    ],
    qualification: {
      score: 60,
      temperature: "warm",
      reasons: ["Jornada declarada"],
    },
    assessment_authority: "manual_preserved",
    graph: {
      nodes: [
        { id: "conversation", label: "Hilo", kind: "conversation" },
        { id: "fact:schedule", label: "Jornada", kind: "fact" },
      ],
      edges: [],
    },
    recent_history: [],
    memory_limit: "Memoria acotada",
  };
  mocks.api.mockResolvedValue(data);
  const view = render(
    <ConversationSalesMemory conversation="one" refresh={1} />,
  );
  expect(mocks.api).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Memoria y contexto del agente"));
  await screen.findByText("Prefiero de noche");
  expect(screen.getByRole("img", { name: /Grafo de hechos/ })).toBeVisible();
  fireEvent.click(screen.getByText("Por qué tiene esta calificación"));
  expect(screen.getByText(/La calificación manual se conserva/)).toBeVisible();
  view.rerender(<ConversationSalesMemory conversation="two" refresh={1} />);
  expect(screen.queryByText("Prefiero de noche")).toBeNull();
});

test("ad binding uses local PUT and the selected program without publishing to Meta", async () => {
  const catalog = {
    agents: [],
    programs: {
      items: [{ program_id: 5, name: "Software", schedule: "Diurna" }],
    },
  } as unknown as Catalog;
  mocks.api.mockResolvedValue({ revision: 2, items: [] });
  render(
    <ProgramSalesSetup
      catalog={catalog}
      disabled={false}
      onSaved={async () => {}}
    />,
  );
  fireEvent.click(
    screen.getByText("Especialistas por programa y origen de anuncios"),
  );
  fireEvent.click(
    screen.getByText("Vincular anuncios de WhatsApp con programas"),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Consultar vinculaciones" }),
  );
  await screen.findByLabelText("ID del anuncio en Meta");
  fireEvent.change(screen.getByLabelText("ID del anuncio en Meta"), {
    target: { value: "12345" },
  });
  fireEvent.change(screen.getByLabelText("Programa y jornada del anuncio"), {
    target: { value: "5" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar vínculo del anuncio" }),
  );
  await waitFor(() =>
    expect(mocks.api).toHaveBeenCalledWith(
      "/sales/ad-links",
      "PUT",
      expect.objectContaining({
        revision: 2,
        items: [{ ad_id: "12345", program_id: 5 }],
      }),
    ),
  );
});
