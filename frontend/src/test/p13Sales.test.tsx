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

const mocks = vi.hoisted(() => ({
  api: vi.fn(),
  call: vi.fn(),
  actions: ["inbox.read"],
}));
vi.mock("../institution/api", async (original) => ({
  ...(await original<typeof import("../institution/api")>()),
  useInstitution: () => ({
    call: mocks.call,
    session: { actions: mocks.actions },
  }),
}));
vi.mock("../modules/agents/api", async (original) => ({
  ...(await original<typeof import("../modules/agents/api")>()),
  api: mocks.api,
}));
afterEach(cleanup);
beforeEach(() => {
  mocks.api.mockReset();
  mocks.call.mockReset();
  mocks.actions = ["inbox.read"];
});

test("central skills are always available while memory writes remain independently controlled", async () => {
  mocks.api.mockResolvedValue({
    items: [
      {
        id: "recall",
        name: "Recuperar contexto",
        category: "Memoria",
        procedure: "Sólo hechos",
        guide: {
          path: "app/modules/agents/skills/recall/SKILL.md",
          version: "cbn-skill-library-v1",
          sha256: "a".repeat(64),
          content:
            "## Procedimiento\nConsulta la memoria de este hilo antes de preguntar otra vez.",
        },
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
  expect(screen.getByText(/2 skills disponibles/)).toBeInTheDocument();
  fireEvent.click(screen.getByText("Consultar guía de Recuperar contexto"));
  expect(
    screen.getByText(/Consulta la memoria de este hilo antes/),
  ).toBeVisible();
  expect(
    screen.getByText(/app\/modules\/agents\/skills\/recall\/SKILL.md/),
  ).toBeVisible();
  expect(
    screen.getByRole("checkbox", { name: /Recuperar contexto/ }),
  ).toBeChecked();
  expect(
    screen.getByRole("checkbox", { name: /Recuperar contexto/ }),
  ).toBeDisabled();
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
  await screen.findByText(/1 skills disponibles/);
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
    contact_projection: [
      { field: "name", state: "updated", source_message_id: "source" },
      { field: "city", state: "manual_preserved", source_message_id: "source" },
    ],
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
  expect(
    screen.getByText(/Nombre declarado: guardado desde el mensaje/),
  ).toBeVisible();
  expect(
    screen.getByText(/Ciudad declarada: dato manual conservado/),
  ).toBeVisible();
  expect(screen.getByRole("img", { name: /Grafo de hechos/ })).toBeVisible();
  fireEvent.click(screen.getByText("Por qué tiene esta calificación"));
  expect(screen.getByText(/La calificación manual se conserva/)).toBeVisible();
  view.rerender(<ConversationSalesMemory conversation="two" refresh={1} />);
  expect(screen.queryByText("Prefiero de noche")).toBeNull();
});

test("reviewed reset uses the identity-aware institutional route and bound revision", async () => {
  mocks.actions = ["inbox.read", "inbox.write"];
  mocks.call.mockResolvedValue({ saved: true });
  mocks.api.mockResolvedValue({
    revision: 3,
    facts: [],
    qualification: null,
    graph: { nodes: [], edges: [] },
    recent_history: [],
    memory_limit: "Acotada",
    reset_target_sequence: 9,
    can_restore_context: true,
  });
  const changed = vi.fn();
  render(
    <ConversationSalesMemory
      conversation="owner-test"
      refresh={1}
      onChanged={changed}
    />,
  );
  fireEvent.click(screen.getByText("Memoria y contexto del agente"));
  fireEvent.click(
    await screen.findByRole("button", { name: "Empezar desde cero con IA" }),
  );
  expect(mocks.call).not.toHaveBeenCalled();
  expect(
    screen.getByText(
      /El historial, la ficha CRM, los recibos y el consumo de voz se conservan/,
    ),
  ).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: /^Cancelar$/ }));
  expect(mocks.call).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Empezar desde cero con IA" }),
  );
  fireEvent.click(screen.getByRole("button", { name: /^Reiniciar contexto$/ }));
  await waitFor(() =>
    expect(mocks.call).toHaveBeenCalledWith(
      "conversation-memory/owner-test/reset",
      "POST",
      expect.objectContaining({
        revision: 3,
        sequence: 9,
        confirmed: true,
        action: "reset",
      }),
    ),
  );
  await screen.findByText(/Contexto reiniciado/);
  expect(changed).toHaveBeenCalledOnce();
});

test("live revision refreshes an open memory without adding a polling timer", async () => {
  const data = {
    revision: 1,
    facts: [],
    qualification: null,
    graph: { nodes: [], edges: [] },
    recent_history: [],
    memory_limit: "Acotada",
  };
  mocks.api.mockResolvedValue(data);
  const view = render(
    <ConversationSalesMemory conversation="live-memory" refresh="one" />,
  );
  fireEvent.click(screen.getByText("Memoria y contexto del agente"));
  await screen.findByText(/Aún no hay datos comerciales extraídos/);
  mocks.api.mockResolvedValue({
    ...data,
    revision: 2,
    facts: [
      {
        field: "goal",
        value: "Quiero emprender",
        sequence: 2,
        source_message_id: "incoming-two",
        origin: "automatic_audio_transcription",
      },
    ],
  });
  view.rerender(
    <ConversationSalesMemory conversation="live-memory" refresh="two" />,
  );
  await screen.findByText("Quiero emprender");
  expect(mocks.api).toHaveBeenCalledTimes(2);
  expect(screen.getByText(/Transcripción automática/)).toBeVisible();
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
