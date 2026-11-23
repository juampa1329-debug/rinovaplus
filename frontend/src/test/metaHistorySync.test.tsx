import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi, afterEach } from "vitest";
import { MetaHistorySync } from "../institution/MetaHistorySync";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";

afterEach(() => vi.restoreAllMocks());

it("imports known outgoing history without calling a send endpoint", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(
      async (_path, init) =>
        new Response(
          JSON.stringify(
            init?.method === "POST"
              ? { imported: 25, skipped: 0, has_more: false, after: "" }
              : {
                  items: [
                    {
                      id: "page",
                      name: "Messenger · CBN",
                      channel: "messenger",
                    },
                  ],
                },
          ),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    );
  const session: Session = {
    session_id: "s",
    csrf_token: "c",
    actions: ["inbox.read", "inbox.write"],
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
  const done = vi.fn();
  render(
    <SessionBoundary initial={session} expire={() => {}}>
      <MetaHistorySync done={done} />
    </SessionBoundary>,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Traer historial de Meta" }),
  );
  await screen.findByRole("option", { name: "Messenger · CBN" });
  fireEvent.change(screen.getByLabelText("Cuenta de Meta"), {
    target: { value: "page" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Sincronizar mensajes salientes" }),
  );
  await screen.findByText(/25 mensajes incorporados/);
  await waitFor(() => expect(done).toHaveBeenCalledTimes(1));
  const posts = fetcher.mock.calls.filter(
    ([, init]) => init?.method === "POST",
  );
  expect(posts).toHaveLength(1);
  expect(String(posts[0][0])).toContain("workspace/inbox/meta-history/page");
  expect(
    fetcher.mock.calls.some(([path]) =>
      /\/messages$|\/recover$/.test(String(path)),
    ),
  ).toBe(false);
});
