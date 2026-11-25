import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { SiieRegistration } from "./SiieRegistration";

const mock = vi.hoisted(() => ({
  call: vi.fn(),
  mode: "empty",
  actions: ["crm.read", "crm.write", "settings.webhooks.write"],
}));
vi.mock("./api", async (original) => ({
  ...(await original<typeof import("./api")>()),
  useInstitution: () => ({
    call: mock.call,
    session: { actions: mock.actions },
  }),
}));

const sections = [
  "estudiante",
  "acudiente",
  "inscripcion",
  "estudiosSecundarios",
  "referencia",
  "socioeconomica",
  "padres",
  "otrosEstudios",
  "informacionLaboral",
  "familiaCbn",
  "grupoEspecial",
];
const name = {
  name: "Nombres",
  label: "Nombres del estudiante",
  kind: "text",
  required: true,
  max_length: 40,
  options: [],
  catalog: null,
};
const draft = {
  id: "a1111111-1111-4111-8111-111111111111",
  revision: 1,
  kind: "registration",
  state: "draft",
  form: { estudiante: { Nombres: "ENSAYO" } },
  context: {
    program_name: "PRE-ICFES",
    schedule: "Sábados",
    selection: { program_id: "3", offer_ref: "21-n1" },
  },
};
const status = {
  revision: 0,
  api_configured: true,
  webhook_secret_configured: false,
  webhook_enabled: false,
  writes_enabled: true,
  stage_key: "",
  webhook_path: "/hooks/siie/v1",
  stages: [{ key: "nuevo", label: "Nuevo" }],
  schema: sections.map((s, i) => ({
    name: s,
    label: `Sección ${i + 1}`,
    fields:
      i === 0
        ? [
            name,
            {
              ...name,
              name: "Id_Genero",
              label: "Género",
              catalog: "generos",
              kind: "integer",
            },
          ]
        : [],
  })),
  applicant_fields: [],
};
beforeEach(() => {
  mock.mode = "empty";
  mock.actions = ["crm.read", "crm.write", "settings.webhooks.write"];
  mock.call.mockReset();
  mock.call.mockImplementation(async (path: string) => {
    if (path.endsWith("/status")) return status;
    if (path.endsWith("/records/sd"))
      return {
        items:
          mock.mode === "draft"
            ? [
                {
                  ...draft,
                  program_name: draft.context.program_name,
                  updated_at: "2026-11-25",
                },
              ]
            : [],
      };
    if (path.endsWith("/records/se"))
      return {
        items:
          mock.mode === "event"
            ? [
                {
                  id: "event-one",
                  event_type: "registration.created",
                  projection: "review_required",
                },
              ]
            : [],
      };
    if (path.includes("/records/sd/")) return draft;
    if (path.includes("/catalogs?"))
      return { items: {}, missing: ["generos", "municipios"] };
    if (path.includes("/records/se/"))
      return {
        event: {
          event_type: "registration.created",
          persona: { nombres: "ENSAYO", primerApellido: "PRUEBA" },
          programa: "PRE-ICFES",
        },
        candidates: [
          {
            id: "contact-one",
            name: "CONTACTO REVISADO",
            phone: "+573000000000",
          },
        ],
      };
    if (path.includes("/events/")) return { linked: true };
    throw Error(`Unexpected synthetic route ${path}`);
  });
});

it("does not open private registration dossiers for a read-only CRM viewer", async () => {
  mock.mode = "draft";
  mock.actions = ["crm.read"];
  render(<SiieRegistration />);
  expect(
    await screen.findByRole("button", { name: /PRE-ICFES/ }),
  ).toBeDisabled();
  expect(
    mock.call.mock.calls.some((c) => String(c[0]).includes("/records/sd/")),
  ).toBe(false);
});

it("shows the webhook setup without silently enabling reception or creating students", async () => {
  render(<SiieRegistration />);
  expect(
    await screen.findByText("Recepción pendiente de habilitar"),
  ).toBeInTheDocument();
  expect(screen.getByText(/Falta SIIE_WEBHOOK_SECRET/)).toBeInTheDocument();
  expect(
    screen.getByLabelText("Recibir eventos firmados de SIIE"),
  ).toBeDisabled();
  expect(mock.call.mock.calls.every((c) => !c[1] || c[1] === "GET")).toBe(true);
  expect(screen.getByText(/\/hooks\/siie\/v1/)).toBeInTheDocument();
});

it("keeps a draft editable while missing real catalogs block final registration", async () => {
  mock.mode = "draft";
  render(<SiieRegistration />);
  fireEvent.click(await screen.findByRole("button", { name: /PRE-ICFES/ }));
  expect(await screen.findByLabelText("Nombres del estudiante *")).toHaveValue(
    "ENSAYO",
  );
  expect(screen.getByLabelText("Género *")).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Revisar envío a SIIE" }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Nombres del estudiante *"), {
    target: { value: "NOMBRE REVISADO" },
  });
  expect(
    screen.getByRole("button", { name: "Guardar borrador" }),
  ).toBeEnabled();
  expect(mock.call.mock.calls.some((c) => c[1] === "POST")).toBe(false);
  expect(screen.getByText("11. Sección 11")).toBeInTheDocument();
});

it("requires explicit identity review before linking an existing CRM contact", async () => {
  mock.mode = "event";
  render(<SiieRegistration />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Inscripción nueva/ }),
  );
  const button = await screen.findByRole("button", {
    name: "Confirmar vínculo con el contacto",
  });
  expect(button).toBeDisabled();
  fireEvent.change(
    screen.getByLabelText("Contacto existente que corresponde a esta persona"),
    { target: { value: "contact-one" } },
  );
  expect(button).toBeDisabled();
  fireEvent.click(
    screen.getByLabelText(
      "Verifiqué que la inscripción y el contacto pertenecen a la misma persona",
    ),
  );
  fireEvent.click(button);
  await waitFor(() =>
    expect(mock.call).toHaveBeenCalledWith(
      "siie-registration/events/event-one/link",
      "POST",
      { contact_id: "contact-one", reviewed: true },
    ),
  );
});
