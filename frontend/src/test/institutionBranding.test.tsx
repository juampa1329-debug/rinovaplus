import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { InstitutionApp } from "../institution/InstitutionApp";
import { AccessLayout } from "../institution/AccessLayout";
import { bindInstitutionSession } from "../shared/institutionSession";
import { themeStorageKey } from "../shared/theme";

const response = (value: unknown, status = 200) => Response.json(value, { status });
beforeEach(() => {
  bindInstitutionSession("");
  window.history.replaceState(null, "", "/#/access");
  localStorage.removeItem(themeStorageKey);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function signedOut(post: (path: string, body: Record<string, unknown>) => Response) {
  const fetcher = vi.fn(async (url: string, options?: RequestInit) => {
    if (options?.method === "POST") return post(url, JSON.parse(String(options.body)));
    if (url.endsWith("auth/status")) return response({ initialized: true });
    return response({ detail: "session_required" }, 401);
  });
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}

it("keeps password visibility local and resets it between login, recovery and activation", async () => {
  const posts: Array<{ path: string; body: Record<string, unknown> }> = [];
  const fetcher = signedOut((path, body) => { posts.push({ path, body }); return response({ ok: true }); });
  render(<InstitutionApp />);
  const password = await screen.findByLabelText("Contraseña", { exact: true });
  fireEvent.change(password, { target: { value: "fixture-only-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
  expect(password).toHaveAttribute("type", "text");
  expect(posts).toHaveLength(0);
  fireEvent.click(screen.getByRole("button", { name: "Olvidé mi contraseña" }));
  expect(screen.queryByLabelText("Contraseña", { exact: true })).toBeNull();
  fireEvent.change(screen.getByLabelText("Correo"), { target: { value: "fixture@example.invalid" } });
  fireEvent.click(screen.getByRole("button", { name: "Solicitar recuperación" }));
  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0]).toEqual({ path: "/api/institution/auth/recover-email", body: { email: "fixture@example.invalid" } });
  await waitFor(() => expect(screen.getByRole("button", { name: "Solicitar recuperación" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Volver al acceso" }));
  expect(screen.getByLabelText("Contraseña", { exact: true })).toHaveAttribute("type", "password");
  expect(screen.getByLabelText("Contraseña", { exact: true })).toHaveValue("");
  fireEvent.click(screen.getByRole("button", { name: "Tengo un código de activación o recuperación" }));
  const next = screen.getByLabelText("Nueva contraseña");
  expect(next).toHaveAttribute("type", "password");
  expect(next).toHaveAttribute("minlength", "15");
  fireEvent.change(next, { target: { value: "fixture-only-new-password" } });
  fireEvent.change(screen.getByLabelText("Código de activación o recuperación", { exact: true }), { target: { value: "fixture-only-token" } });
  fireEvent.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
  fireEvent.click(screen.getByRole("button", { name: "Guardar contraseña" }));
  await waitFor(() => expect(posts).toHaveLength(2));
  expect(posts[1]).toEqual({ path: "/api/institution/auth/redeem", body: { token: "fixture-only-token", new_password: "fixture-only-new-password" } });
  expect(await screen.findByLabelText("Contraseña", { exact: true })).toHaveAttribute("type", "password");
  expect(fetcher.mock.calls.some(([url]) => url.includes("fixture-only"))).toBe(false);
});

it("preserves the MFA challenge contract and clears the revealed password", async () => {
  const posts: Array<{ path: string; body: Record<string, unknown> }> = [];
  signedOut((path, body) => {
    posts.push({ path, body });
    return path.endsWith("auth/login")
      ? response({ mfa_required: true, challenge_token: "fixture-challenge" })
      : response({ detail: "confirmation_failed" }, 422);
  });
  render(<InstitutionApp />);
  await screen.findByLabelText("Contraseña", { exact: true });
  fireEvent.change(screen.getByLabelText("Correo"), { target: { value: "fixture@example.invalid" } });
  fireEvent.change(screen.getByLabelText("Contraseña", { exact: true }), { target: { value: "fixture-only-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
  fireEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
  await screen.findByRole("heading", { name: "Verifica tu identidad" });
  expect(screen.queryByLabelText("Contraseña", { exact: true })).toBeNull();
  fireEvent.change(screen.getByLabelText("Código del autenticador o de recuperación"), { target: { value: "123456" } });
  fireEvent.click(screen.getByRole("button", { name: "Verificar código" }));
  await waitFor(() => expect(posts).toHaveLength(2));
  expect(posts[1]).toEqual({ path: "/api/institution/auth/verify", body: { challenge_token: "fixture-challenge", code: "123456" } });
  await screen.findByText("No se pudo confirmar tu identidad.");
  fireEvent.click(screen.getByRole("button", { name: "Tengo un código de activación o recuperación" }));
  expect(screen.getByLabelText("Nueva contraseña")).toHaveAttribute("type", "password");
});

it("keeps theme choice accessible and persistent without making a request", () => {
  const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher);
  render(<AccessLayout><h1 id="access-title">Ensayo</h1></AccessLayout>);
  fireEvent.click(screen.getByRole("button", { name: "Oscuro" }));
  expect(screen.getByRole("button", { name: "Oscuro" })).toHaveAttribute("aria-pressed", "true");
  expect(localStorage.getItem(themeStorageKey)).toBe("dark");
  expect(document.documentElement.dataset.theme).toBe("dark");
  fireEvent.click(screen.getByRole("button", { name: "Claro" }));
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(fetcher).not.toHaveBeenCalled();
});

it("pauses animation for manual pause, reduced motion, compact layout and hidden documents", () => {
  const pause = vi.fn(), resume = vi.fn();
  const oldPause = Object.getOwnPropertyDescriptor(SVGSVGElement.prototype, "pauseAnimations");
  const oldResume = Object.getOwnPropertyDescriptor(SVGSVGElement.prototype, "unpauseAnimations");
  Object.defineProperty(SVGSVGElement.prototype, "pauseAnimations", { configurable: true, value: pause });
  Object.defineProperty(SVGSVGElement.prototype, "unpauseAnimations", { configurable: true, value: resume });
  const queries = new Map<string, { matches: boolean; listeners: Set<() => void> }>();
  vi.stubGlobal("matchMedia", (query: string) => {
    const state = queries.get(query) ?? { matches: false, listeners: new Set<() => void>() }; queries.set(query, state);
    return { get matches() { return state.matches; }, addEventListener: (_: string, f: () => void) => state.listeners.add(f), removeEventListener: (_: string, f: () => void) => state.listeners.delete(f) };
  });
  let hidden = false; vi.spyOn(document, "hidden", "get").mockImplementation(() => hidden);
  try {
    const view = render(<AccessLayout><h1 id="access-title">Ensayo</h1></AccessLayout>);
    expect(resume).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Pausar animación" }));
    expect(pause).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Reanudar animación" }));
    expect(resume).toHaveBeenCalledTimes(2);
    for (const query of ["(prefers-reduced-motion: reduce)", "(max-width: 900px)"]) {
      const media = queries.get(query)!;
      act(() => { media.matches = true; media.listeners.forEach(f => f()); });
      expect(pause).toHaveBeenCalledTimes(query.includes("reduced") ? 2 : 3);
      act(() => { media.matches = false; media.listeners.forEach(f => f()); });
    }
    hidden = true; fireEvent(document, new Event("visibilitychange"));
    expect(pause).toHaveBeenCalledTimes(4);
    view.unmount();
    expect([...queries.values()].every(q => q.listeners.size === 0)).toBe(true);
  } finally {
    if (oldPause) Object.defineProperty(SVGSVGElement.prototype, "pauseAnimations", oldPause);
    else Reflect.deleteProperty(SVGSVGElement.prototype, "pauseAnimations");
    if (oldResume) Object.defineProperty(SVGSVGElement.prototype, "unpauseAnimations", oldResume);
    else Reflect.deleteProperty(SVGSVGElement.prototype, "unpauseAnimations");
  }
});
