import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  BroadcastWorkspace,
  variableKeys,
} from "../institution/BroadcastWorkspace";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
const session: Session = {
  session_id: "s",
  csrf_token: "p7-csrf",
  actions: ["campaigns.manage", "crm.read", "inbox.write"],
  user: {
    id: "u",
    email: "u@cbn.local",
    full_name: "Admisiones",
    role: "owner",
    active: true,
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const template = {
  id: "t",
  version: 2,
  integration_id: "a",
  name: "admisiones",
  language: "es",
  category: "MARKETING",
  status: "APPROVED",
  origin: "provider",
  paused: false,
  components: [
    { type: "BODY", text: "Hola {{1}}" },
    { type: "HEADER", format: "TEXT", text: "CBN {{1}}" },
    {
      type: "BUTTONS",
      buttons: [{ type: "URL", text: "Ver", url: "https://cbn.example/{{1}}" }],
    },
  ],
};
const campaign = {
  id: "c",
  name: "Admisiones CBN",
  state: "draft",
  revision: 1,
  epoch: 1,
  document: {
    name: "Admisiones CBN",
    integration_id: "a",
    template_id: "t",
    template_version: 2,
    filters: {
      contact_ids: [],
      program_ids: [],
      stages: [],
      cities: [],
      tags: [],
    },
    variables: {
      "body.1": { source: "customer_name" },
      "header.1": { source: "literal", value: "Sede" },
      "button.0.1": { source: "literal", value: "info" },
    },
    header_media_url: "",
    scheduled_local: null,
    timezone: "America/Bogota",
  },
};
const options = {
  accounts: [
    { id: "a", name: "Admisiones WhatsApp", verified_status: "verified" },
  ],
  templates: [template],
  programs: [{ program_id: 7, name: "Programa declarado" }],
  stages: ["Interesado"],
  outbound_enabled: false,
};
const ok = (value: unknown, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
function setup(
  extra?: (path: string, init?: RequestInit) => Response | undefined,
) {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (url, init) => {
      const path = String(url),
        custom = extra?.(path, init);
      if (custom) return custom;
      if (path.endsWith("options")) return ok(options);
      if (path.endsWith("/broadcasts")) return ok({ items: [campaign] });
      if (path.includes("report?"))
        return ok({
          total: 2,
          offset: 0,
          counts: { accepted: 1, uncertain: 1 },
          items: [
            {
              id: "r1",
              name: "Ana",
              phone: "573100000000",
              status: "accepted",
              provider_message_id: "wamid.1",
              attempts: 1,
            },
            {
              id: "r2",
              name: "Beto",
              phone: "573100000001",
              status: "uncertain",
              provider_message_id: null,
              attempts: 1,
            },
          ],
          has_more: false,
        });
      if (path.endsWith("identities"))
        return ok({
          items: [
            {
              id: "identity",
              name: "Ana",
              phone: "573100000000",
              consent: null,
            },
          ],
        });
      if (path.endsWith("cadence"))
        return ok({
          revision: 0,
          enabled: false,
          daily_limit: 100,
          interval_seconds: 30,
          reserved: 0,
        });
      return ok({});
    });
  render(
    <SessionBoundary initial={session} expire={() => {}}>
      <BroadcastWorkspace />
    </SessionBoundary>,
  );
  return fetcher;
}
afterEach(() => vi.restoreAllMocks());
it("creates a template inside a campaign without submitting or losing the campaign draft", async () => {
  const f = setup();
  fireEvent.click(
    await screen.findByRole("button", { name: "Admisiones CBN · Borrador" }),
  );
  fireEvent.change(screen.getByLabelText("Nombre de campaña"), {
    target: { value: "Campaña conservada" },
  });
  fireEvent.click(
    screen.getByRole("button", {
      name: "Crear o gestionar plantillas de esta campaña",
    }),
  );
  fireEvent.change(screen.getByLabelText("Nombre de plantilla"), {
    target: { value: "nueva_plantilla" },
  });
  fireEvent.change(screen.getByLabelText("Cuerpo del mensaje"), {
    target: { value: "Hola, prueba de nueva plantilla." },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar borrador de plantilla" }),
  );
  await waitFor(() =>
    expect(
      f.mock.calls.some(
        ([path, init]) =>
          String(path).includes("/templates/") && init?.method === "PUT",
      ),
    ).toBe(true),
  );
  expect(screen.getByLabelText("Nombre de campaña")).toHaveValue(
    "Campaña conservada",
  );
  expect(
    f.mock.calls.filter(([, init]) => init?.method === "PUT"),
  ).toHaveLength(1);
});
it("an empty specific-person audience cannot become a send to everyone", async () => {
  setup((path) =>
    path.includes("audience=true")
      ? ok({
          items: [
            {
              contact_id: "contact-one",
              name: "Persona autorizada",
              phone: "573000000000",
            },
          ],
          has_more: false,
        })
      : undefined,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Admisiones CBN · Borrador" }),
  );
  fireEvent.click(
    screen.getByRole("checkbox", { name: "Elegir personas específicas" }),
  );
  expect(
    screen.getByRole("button", { name: "Guardar campaña" }),
  ).toBeDisabled();
  fireEvent.click(
    await screen.findByRole("checkbox", {
      name: "Seleccionar a Persona autorizada, 573000000000",
    }),
  );
  expect(
    screen.getByRole("button", { name: "Guardar campaña" }),
  ).not.toBeDisabled();
});
it("loads campaign analytics only when the charts are requested", async () => {
  const f = setup((path) =>
    path.includes("analytics=true")
      ? ok({
          counts: {},
          total: 0,
          items: [],
          offset: 0,
          has_more: false,
          analytics: {
            totals: { total: 0, delivered: 0, read: 0, replied: 0, failed: 0 },
            dimensions: { gender: [] },
          },
        })
      : undefined,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Admisiones CBN · Borrador" }),
  );
  expect(
    f.mock.calls.some(([path]) => String(path).includes("analytics=true")),
  ).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Gráficos y detalles" }));
  expect(
    await screen.findByRole("region", { name: "Gráficos de la campaña" }),
  ).toBeInTheDocument();
  expect(
    f.mock.calls.some(([path]) => String(path).includes("analytics=true")),
  ).toBe(true);
});
it("composes CRM variables with synthetic examples and previews them without sending", async () => {
  const f = setup();
  fireEvent.click(
    await screen.findByRole("button", { name: "Plantillas WhatsApp" }),
  );
  fireEvent.change(screen.getByLabelText("Cuenta WhatsApp"), {
    target: { value: "a" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Crear plantilla" }));
  fireEvent.change(screen.getByLabelText("Nombre de plantilla"), {
    target: { value: "informacion_cbn" },
  });
  const text = screen.getByLabelText(
    "Cuerpo del mensaje",
  ) as HTMLTextAreaElement;
  fireEvent.change(text, {
    target: { value: "Hola , conoce nuestros programas." },
  });
  text.setSelectionRange(5, 5);
  fireEvent.select(text);
  fireEvent.click(screen.getByRole("button", { name: "Insertar en cuerpo" }));
  expect(text).toHaveValue(
    "Hola {{customer_name}}, conoce nuestros programas.",
  );
  expect(screen.getByLabelText("Vista previa de WhatsApp")).toHaveTextContent(
    "Hola Laura Gómez, conoce nuestros programas.",
  );
  fireEvent.change(
    screen.getByLabelText("Ejemplo: Nombre completo (cuerpo 1)"),
    { target: { value: "Persona de ejemplo" } },
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Guardar borrador de plantilla" }),
  );
  await waitFor(() =>
    expect(f.mock.calls.some(([, i]) => i?.method === "PUT")).toBe(true),
  );
  const body = JSON.parse(
    String(f.mock.calls.find(([, i]) => i?.method === "PUT")?.[1]?.body),
  );
  expect(body.examples).toEqual({ "body.1": "Persona de ejemplo" });
  expect(body.body_text).toContain("{{customer_name}}");
  expect(
    f.mock.calls.some(
      ([u]) => String(u).endsWith("/submit") || String(u).endsWith("/activate"),
    ),
  ).toBe(false);
});
it("explains actual Meta quality without displaying NONE as a rejection", async () => {
  setup((path) =>
    path.endsWith("options")
      ? ok({
          ...options,
          templates: [
            {
              ...template,
              metadata: {
                quality_score: "{'score': 'UNKNOWN', 'date': 123}",
                rejection_reason: "NONE",
              },
            },
          ],
        })
      : undefined,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Plantillas WhatsApp" }),
  );
  fireEvent.change(screen.getByLabelText("Cuenta WhatsApp"), {
    target: { value: "a" },
  });
  expect(screen.getByText("Aprobada por Meta")).toBeInTheDocument();
  expect(screen.getByText(/Todavía sin calificar/)).toBeInTheDocument();
  expect(screen.queryByText(/Motivo de rechazo/)).not.toBeInTheDocument();
});
it("reuses the approved template CRM mapping and preserves custom field keys in campaigns", async () => {
  const f = setup((path) =>
    path.endsWith("options")
      ? ok({
          ...options,
          variables: [
            {
              token: "crm.sede",
              source: "custom_field",
              field_key: "sede",
              label: "Sede",
              example: "Principal",
            },
          ],
          templates: [
            {
              ...template,
              metadata: {
                variable_bindings: {
                  "body.1": { source: "custom_field", field_key: "sede" },
                },
              },
            },
          ],
        })
      : undefined,
  );
  fireEvent.click(await screen.findByRole("button", { name: "Nueva campaña" }));
  fireEvent.change(screen.getByLabelText("Nombre de campaña"), {
    target: { value: "Piloto" },
  });
  fireEvent.change(screen.getByLabelText("Cuenta de envío"), {
    target: { value: "a" },
  });
  fireEvent.change(screen.getByLabelText("Plantilla e idioma"), {
    target: { value: "t" },
  });
  expect(screen.getByLabelText("Variable body.1")).toHaveValue("crm.sede");
  fireEvent.change(screen.getByLabelText("Texto de header.1"), {
    target: { value: "Sede de ejemplo" },
  });
  fireEvent.change(screen.getByLabelText("Texto de button.0.1"), {
    target: { value: "programas" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar campaña" }));
  await waitFor(() =>
    expect(f.mock.calls.some(([, i]) => i?.method === "PUT")).toBe(true),
  );
  const body = JSON.parse(
    String(f.mock.calls.find(([, i]) => i?.method === "PUT")?.[1]?.body),
  );
  expect(body.variables["body.1"]).toEqual({
    source: "custom_field",
    field_key: "sede",
  });
});
it("extracts body, header and dynamic URL bindings without alias collisions", () => {
  expect(variableKeys(template)).toEqual(["body.1", "header.1", "button.0.1"]);
});
it("loads the integrated campaign list and keeps sending review separate from saving", async () => {
  setup();
  fireEvent.click(
    await screen.findByRole("button", { name: "Admisiones CBN · Borrador" }),
  );
  expect(screen.getByRole("button", { name: "Guardar campaña" })).toBeEnabled();
  expect(
    screen.getByRole("button", { name: "Activar o reanudar envío" }),
  ).toBeDisabled();
  expect(
    screen.getByText(/Los envíos están deshabilitados/),
  ).toBeInTheDocument();
  expect(await screen.findByLabelText("Reintentar Ana")).toBeDisabled();
  expect(screen.getByLabelText("Reintentar Beto")).toBeDisabled();
});
it("uses declared program IDs and preserves the form after a CAS conflict", async () => {
  const f = setup((_p, init) =>
    init?.method === "PUT"
      ? ok({ detail: "revision_conflict" }, 409)
      : undefined,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Admisiones CBN · Borrador" }),
  );
  fireEvent.change(screen.getByLabelText("Nombre de campaña"), {
    target: { value: "Nombre conservado" },
  });
  fireEvent.click(screen.getByRole("checkbox", { name: "Programa declarado" }));
  fireEvent.click(screen.getByRole("button", { name: "Guardar campaña" }));
  expect(
    await screen.findByText(/Hay una versión más reciente/),
  ).toBeInTheDocument();
  expect(screen.getByLabelText("Nombre de campaña")).toHaveValue(
    "Nombre conservado",
  );
  const request = f.mock.calls.find(([, i]) => i?.method === "PUT")!;
  const body = JSON.parse(String(request[1]?.body));
  expect(body.filters.program_ids).toEqual([7]);
  expect(body.revision).toBe(1);
  expect(body.operation_id).toBeTruthy();
});
it("preparation is an explicit no-send command and does not activate a campaign", async () => {
  const f = setup();
  fireEvent.click(
    await screen.findByRole("button", { name: "Admisiones CBN · Borrador" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Preparar sin enviar" }));
  await waitFor(() =>
    expect(
      f.mock.calls.some(
        ([u, i]) => String(u).endsWith("/prepare") && i?.method === "POST",
      ),
    ).toBe(true),
  );
  expect(f.mock.calls.some(([u]) => String(u).endsWith("/activate"))).toBe(
    false,
  );
});
it("shows exclusions and actual matched counts without inventing recipients", async () => {
  setup((p) =>
    p.endsWith("preview")
      ? ok({
          counts: { matched: 3, eligible: 1, excluded: 2 },
          exclusions: { human_control: 1, marketing_consent_required: 1 },
          items: [
            {
              identity_id: "x",
              name: "Sin permiso",
              eligible: false,
              reasons: ["marketing_consent_required"],
              text: "",
            },
          ],
        })
      : undefined,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Admisiones CBN · Borrador" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Vista previa de destinatarios" }),
  );
  expect(
    await screen.findByText("1 elegibles de 3 · 2 excluidos"),
  ).toBeInTheDocument();
  expect(screen.getByText("Atención humana: 1")).toBeInTheDocument();
});
it("template editor has Scentra components and no local provider approval control", async () => {
  setup();
  fireEvent.click(
    await screen.findByRole("button", { name: "Plantillas WhatsApp" }),
  );
  fireEvent.change(screen.getByLabelText("Cuenta WhatsApp"), {
    target: { value: "a" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Crear plantilla" }));
  expect(screen.getByLabelText("Categoría")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Tipo de cabecera"), {
    target: { value: "IMAGE" },
  });
  expect(
    screen.getByLabelText("Identificador de archivo de ejemplo de Meta"),
  ).toBeRequired();
  fireEvent.click(screen.getByRole("button", { name: "Agregar botón" }));
  expect(screen.getByLabelText("Tipo de botón 1")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /aprobar/i }),
  ).not.toBeInTheDocument();
});
it("consent requires independent evidence and explicit human confirmation", async () => {
  setup();
  fireEvent.click(
    await screen.findByRole("button", { name: "Consentimiento y cadencia" }),
  );
  fireEvent.change(screen.getByLabelText("Cuenta WhatsApp"), {
    target: { value: "a" },
  });
  expect(
    await screen.findByRole("button", { name: "Registrar autorización" }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Revocar consentimiento" }),
  ).toBeDisabled();
  expect(screen.getByLabelText("Máximo en 24 horas")).toHaveValue(100);
});
