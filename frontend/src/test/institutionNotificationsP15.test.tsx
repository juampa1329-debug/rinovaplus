import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { EmailWorkspace } from "../institution/EmailWorkspace";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
import { InstitutionApp } from "../institution/InstitutionApp";

const session: Session = {
  session_id: "s",
  csrf_token: "p15-csrf",
  actions: ["users.manage"],
  user: {
    id: "u",
    email: "qa@example.invalid",
    full_name: "QA",
    active: true,
    role: "owner",
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const value = {
  available: true,
  configured: false,
  enabled: false,
  documents: [],
  events: { "users.create": ["Nuevo usuario", "users.manage"] },
  users: [],
  history: [],
  assets: [],
  variables: ["nombre", "evento"],
};
function mount() {
  return render(
    <SessionBoundary initial={session} expire={() => {}}>
      <EmailWorkspace />
    </SessionBoundary>,
  );
}
afterEach(() => vi.restoreAllMocks());

it("keeps mail paused and does not expose SMTP credentials", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(value)),
  );
  mount();
  expect(await screen.findByText("Oracle pendiente")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Enviar correo de prueba" }),
  ).toBeDisabled();
  expect(screen.queryByLabelText(/Contraseña SMTP/)).not.toBeInTheDocument();
  expect(screen.getByLabelText("Habilitar salida de correo")).not.toBeChecked();
});

it("requires the saved CRM switch even when the runtime transport is enabled", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        ...value,
        configured: true,
        enabled: true,
        documents: [
          {
            kind: "transport",
            id: "main",
            revision: 1,
            body: {
              enabled: false,
              name: "CBN",
              sender: "sender@example.invalid",
              daily_limit: 100,
            },
          },
        ],
      }),
    ),
  );
  mount();
  expect(await screen.findByText("Salida pausada")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Enviar correo de prueba" }),
  ).toBeDisabled();
});

it("does not flash a login form while an existing session is being checked", async () => {
  let release!: (response: Response) => void;
  window.location.hash = "";
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (url) =>
      String(url).endsWith("auth/status")
        ? new Response(JSON.stringify({ initialized: true }))
        : new Promise<Response>((resolve) => {
            release = resolve;
          }),
    );
  render(<InstitutionApp />);
  await waitFor(() =>
    expect(fetcher).toHaveBeenCalledWith(
      "/api/institution/auth/me",
      expect.anything(),
    ),
  );
  expect(
    screen.queryByRole("button", { name: "Iniciar sesión" }),
  ).not.toBeInTheDocument();
  release(
    new Response(JSON.stringify({ detail: "session_required" }), {
      status: 401,
    }),
  );
  expect(
    await screen.findByRole("button", { name: "Iniciar sesión" }),
  ).toBeVisible();
});

it("shows the explicit installation requirement without inventing configured transport", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ ...value, available: false })),
  );
  mount();
  expect(
    await screen.findByText(/base de notificaciones necesita/),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Guardar configuración" }),
  ).not.toBeInTheDocument();
});

it("validates server-side and renders preview in an isolated iframe", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(
      async (_url, init) =>
        new Response(
          JSON.stringify(
            init?.method === "POST" ? { html: "<p>Vista segura</p>" } : value,
          ),
        ),
    );
  mount();
  await screen.findByText("Oracle pendiente");
  fireEvent.click(screen.getByRole("button", { name: "Plantillas y marca" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Validar y previsualizar" }),
  );
  const frame = await screen.findByTitle("Vista previa de correo");
  expect(frame).toHaveAttribute("sandbox", "");
  expect(frame).toHaveAttribute("referrerPolicy", "no-referrer");
  expect(frame).toHaveAttribute("srcdoc", "<p>Vista segura</p>");
  await waitFor(() =>
    expect(fetcher).toHaveBeenCalledWith(
      "/api/institution/notifications/preview",
      expect.objectContaining({
        headers: expect.objectContaining({ "X-CSRF-Token": "p15-csrf" }),
      }),
    ),
  );
});

it("never equates SMTP acceptance or uncertain delivery with inbox delivery", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        ...value,
        history: [
          {
            id: "one",
            event: "mail.test",
            recipient: "qa@example.invalid",
            state: "uncertain",
            attempts: 1,
            error: "smtp_result_unknown",
            created_at: "2026-11-18T20:00:00Z",
          },
        ],
      }),
    ),
  );
  mount();
  await screen.findByText("Oracle pendiente");
  fireEvent.click(screen.getByRole("button", { name: "Historial" }));
  expect(screen.getByText("Resultado por confirmar")).toBeVisible();
  expect(screen.getByText(/Consulta sus registros antes/)).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Cancelar envío" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Reintentar/ }),
  ).not.toBeInTheDocument();
});
