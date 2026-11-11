import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SessionBoundary, send } from "../institution/api";
import type { Contract, Session } from "../institution/api";
import { SettingPage } from "../institution/Settings";
import { InstitutionApp } from "../institution/InstitutionApp";
import { TypedFields } from "../institution/Fields";
import { allowNavigation, useDraftGuard } from "../institution/drafts";
import {
  bindInstitutionSession,
  institutionHeaders,
} from "../shared/institutionSession";

const session: Session = {
  session_id: "own-session",
  csrf_token: "csrf-only-memory",
  actions: ["settings.institution.read", "settings.institution.write"],
  user: {
    id: "person",
    email: "person@cbn.local",
    full_name: "Persona CBN",
    active: true,
    role: "viewer",
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
const contract = {
  fields: {
    institution: [
      {
        path: "name",
        label: "Nombre de la institución",
        type: "string",
        group: "Institución",
        options: [],
        nullable: false,
        read_only: false,
        multiline: false,
      },
    ],
  },
  actions: [],
  modules: [],
  provider_categories: {},
} as Contract;
const ok = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
beforeEach(() => {
  bindInstitutionSession("");
  window.location.hash = "";
});
describe("Institutional entry boundary", () => {
  it("accepts decimal AI values in the native HTML form", () => {
    render(
      <TypedFields
        prefix="ai"
        specs={[
          {
            path: "temperature",
            label: "Temperatura",
            type: "number",
            group: "IA",
            options: [],
            nullable: false,
            read_only: false,
            multiline: false,
            minimum: 0,
            maximum: 2,
          },
        ]}
        value={{ temperature: 0.35 }}
        onChange={() => {}}
      />,
    );
    expect(screen.getByLabelText("Temperatura")).toBeValid();
  });
  it("asks before discarding a dirty form and clears the guard on unmount", () => {
    function Dirty() {
      useDraftGuard(true);
      return null;
    }
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const view = render(<Dirty />);
    expect(allowNavigation()).toBe(false);
    expect(confirm).toHaveBeenCalledOnce();
    view.unmount();
    expect(allowNavigation()).toBe(true);
  });
  it("uses explicit login and no owner-preview fallback", async () => {
    const fetch = vi
      .fn()
      .mockImplementation((url: string) =>
        Promise.resolve(
          url.endsWith("auth/status")
            ? ok({ initialized: true })
            : ok({ detail: "session_required" }, 401),
        ),
      );
    vi.stubGlobal("fetch", fetch);
    render(<InstitutionApp />);
    expect(
      await screen.findByRole("button", { name: "Iniciar sesión" }),
    ).toBeEnabled();
    expect(
      fetch.mock.calls.every(([url]) =>
        String(url).startsWith("/api/institution/"),
      ),
    ).toBe(true);
    expect(
      screen.queryByText(/ensayo|planes|woocommerce/i),
    ).not.toBeInTheDocument();
  });
  it("never echoes secrets in a failed API response", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          ok(
            { detail: "invalid_request", password: "private-do-not-display" },
            422,
          ),
        ),
    );
    await expect(
      send("auth/login", "POST", { password: "private-do-not-display" }),
    ).rejects.not.toThrow("private-do-not-display");
  });
  it("retains a draft and the same operation ID after SQL conflict", async () => {
    const bodies: Record<string, unknown>[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((_url: string, options: RequestInit) => {
        if (options.method === "PUT") {
          bodies.push(JSON.parse(String(options.body)));
          return Promise.resolve(ok({ detail: "revision_conflict" }, 409));
        }
        return Promise.resolve(
          ok({
            revision: 1,
            document: { name: "CBN" },
            updated_at: "2026-10-26T00:00:00Z",
          }),
        );
      }),
    );
    render(
      <SessionBoundary initial={session} expire={() => {}}>
        <SettingPage section="institution" contract={contract} />
      </SessionBoundary>,
    );
    const name = await screen.findByLabelText("Nombre de la institución");
    fireEvent.change(name, { target: { value: "Borrador institucional" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await screen.findByRole("alert");
    expect(name).toHaveValue("Borrador institucional");
    fireEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[0]).toEqual(bodies[1]);
    expect(localStorage.getItem("csrf_token")).toBeNull();
  });
  it("keeps read-only forms visible and disables mutations", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        ok({
          revision: 1,
          document: { name: "CBN" },
          updated_at: "2026-10-26T00:00:00Z",
        }),
      ),
    );
    render(
      <SessionBoundary
        initial={{ ...session, actions: ["settings.institution.read"] }}
        expire={() => {}}
      >
        <SettingPage section="institution" contract={contract} />
      </SessionBoundary>,
    );
    expect(
      await screen.findByLabelText("Nombre de la institución"),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Guardar cambios" }),
    ).toBeDisabled();
  });
  it("clears the in-memory CSRF binding when a session expires", async () => {
    const expired = vi.fn();
    bindInstitutionSession("private-csrf", expired);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(ok({ detail: "session_required" }, 401)),
    );
    await act(async () => {
      await expect(send("auth/me")).rejects.toThrow();
    });
    expect(expired).toHaveBeenCalledOnce();
    expect(institutionHeaders()).toEqual({});
  });
});
