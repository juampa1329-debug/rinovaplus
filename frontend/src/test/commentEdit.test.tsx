import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CommentEdit } from "../institution/CommentEdit";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";

const session: Session = {
  session_id: "test",
  csrf_token: "csrf",
  actions: ["inbox.read", "inbox.write"],
  user: {
    id: "qa",
    email: "qa@example.invalid",
    full_name: "QA",
    active: true,
    role: "owner",
    revision: 1,
    profile: {},
    mfa_state: "disabled",
  },
};
function setup(status = "confirmed", writable = true, supported = true) {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(
      async (path) =>
        new Response(
          JSON.stringify(
            String(path).includes("edit-status")
              ? { pending: null }
              : { status },
          ),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    );
  const done = vi.fn().mockResolvedValue(undefined);
  render(
    <SessionBoundary
      initial={{
        ...session,
        actions: writable ? session.actions : ["inbox.read"],
      }}
      expire={() => {}}
    >
      <CommentEdit
        identity="reply-1"
        body="Respuesta anterior"
        edit={{ supported, source: "crm", revision: "abc", history: [] }}
        done={done}
      />
    </SessionBoundary>,
  );
  return { fetcher, done };
}
beforeEach(() => {
  vi.restoreAllMocks();
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
});

it("reviews the exact replacement and edits the same reply, without sending a new comment", async () => {
  const { fetcher, done } = setup();
  fireEvent.click(screen.getByRole("button", { name: "Editar comentario" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Editar respuesta publicada")).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText("Editar respuesta publicada"), {
    target: { value: "Respuesta corregida 😊" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Revisar cambio" }));
  expect(
    screen.getByRole("alertdialog", {
      name: "Actualizar comentario en Facebook",
    }),
  ).toHaveTextContent("Respuesta corregida 😊");
  expect(
    fetcher.mock.calls.filter(([, init]) => init?.method === "POST"),
  ).toHaveLength(0);
  fireEvent.click(screen.getByRole("button", { name: "Guardar en Facebook" }));
  await screen.findByRole("dialog", { name: "Comentario actualizado" });
  expect(done).toHaveBeenCalledOnce();
  const [path, init] = fetcher.mock.calls.find(
    ([, value]) => value?.method === "POST",
  )!;
  expect(String(path)).toContain("/comments/reply-1/edit");
  expect(JSON.parse(String(init?.body))).toMatchObject({
    source: "crm",
    revision: "abc",
    body: "Respuesta corregida 😊",
  });
  expect(
    fetcher.mock.calls.filter(([, init]) => init?.method === "POST"),
  ).toHaveLength(1);
});

it("keeps a draft and never retries an uncertain change automatically", async () => {
  const { fetcher, done } = setup("uncertain");
  fireEvent.click(screen.getByRole("button", { name: "Editar comentario" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Editar respuesta publicada")).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText("Editar respuesta publicada"), {
    target: { value: "Nueva versión" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Revisar cambio" }));
  fireEvent.click(screen.getByRole("button", { name: "Guardar en Facebook" }));
  await screen.findByRole("alertdialog", {
    name: "El cambio necesita revisión",
  });
  expect(screen.getByLabelText("Editar respuesta publicada")).toHaveValue(
    "Nueva versión",
  );
  await waitFor(() =>
    expect(
      fetcher.mock.calls.filter(([, init]) => init?.method === "POST"),
    ).toHaveLength(1),
  );
  expect(done).not.toHaveBeenCalled();
});

it("does not expose editing for readers or an unsupported provider", () => {
  setup("confirmed", false);
  expect(
    screen.queryByRole("button", { name: "Editar comentario" }),
  ).toBeNull();
});

it("does not expose editing when the provider capability is absent", () => {
  setup("confirmed", true, false);
  expect(
    screen.queryByRole("button", { name: "Editar comentario" }),
  ).toBeNull();
});

it("finds a pending edit after reopening and reconciles it without resending the edit", async () => {
  const { fetcher } = setup();
  fetcher.mockImplementation(
    async (path) =>
      new Response(
        JSON.stringify(
          String(path).includes("edit-status")
            ? { pending: { operation_id: "prior-operation" } }
            : { status: "confirmed" },
        ),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Editar comentario" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Comprobar texto en Facebook" }),
  );
  await screen.findByRole("dialog", { name: "Texto de Facebook comprobado" });
  const posts = fetcher.mock.calls.filter(
    ([, init]) => init?.method === "POST",
  );
  expect(posts).toHaveLength(1);
  expect(String(posts[0][0])).toContain("/edit/reconcile");
  expect(JSON.parse(String(posts[0][1]?.body))).toEqual({
    source: "crm",
    operation_id: "prior-operation",
  });
});
