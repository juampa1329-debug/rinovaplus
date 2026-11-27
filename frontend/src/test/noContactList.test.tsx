import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NoContactList } from "../institution/NoContactList";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";

afterEach(() => vi.restoreAllMocks());
it("searches the persisted opt-out list and paginates without writes or consent actions", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({
    items: [{ id: "1", name: "Persona de ejemplo", phone: "", stage: "Seguimiento" }], has_more: true,
  }), { status: 200, headers: { "Content-Type": "application/json" } }));
  const session = { session_id: "s", csrf_token: "test", actions: ["crm.read"], user: { id: "u" } } as Session;
  render(<SessionBoundary initial={session} expire={() => {}}><NoContactList /></SessionBoundary>);
  expect(await screen.findByText("Persona de ejemplo")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Siguiente" }));
  await waitFor(() => expect(fetcher.mock.calls.some(([u]) => String(u).includes("offset=25"))).toBe(true));
  fireEvent.change(screen.getByLabelText("Buscar en No contactar"), { target: { value: "Andrea" } });
  await waitFor(() => expect(fetcher.mock.calls.some(([u]) => String(u).includes("q=Andrea&offset=0"))).toBe(true));
  expect(fetcher.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});
