import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { Comments } from "../institution/Comments";
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
const first = {
  id: "first",
  integration_id: "account",
  external_id: "meta-first",
  channel: "facebook",
  account: "CBN",
  author: "Juan Pablo",
  body: "¿Cuánto cuesta?",
  received_at: "2026-11-18T12:00:00Z",
  row_version: "0000000000000001",
  state: "new",
  control_mode: "human",
  capabilities: { public_comment_reply: true, comment_like: true },
  replies: [
    {
      id: "reply-first",
      author: "CBN",
      body: "Revisamos el valor para tu jornada.",
      received_at: "2026-11-18T12:01:00Z",
      state: "published",
    },
  ],
};
const second = {
  ...first,
  id: "second",
  external_id: "meta-second",
  body: "¿Cuánto dura?",
  row_version: "0000000000000002",
  received_at: "2026-11-18T12:02:00Z",
  replies: [
    {
      id: "reply-second",
      author: "CBN",
      body: "Te confirmamos la duración del programa.",
      received_at: "2026-11-18T12:03:00Z",
      state: "published",
    },
  ],
};
const group = {
  ...second,
  thread: {
    id: "person-post",
    post_id: "post-123",
    comments: 2,
    replies: 2,
    unread: 2,
    focus_id: "second",
    unlinked_reply: false,
  },
};
const ok = (value: unknown) =>
  new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
function setup(readOnly = false, initialComment = "") {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (path, init) => {
      if (init?.method === "POST") return ok({ saved: true });
      if (String(path).includes("/thread?"))
        return ok({
          items: [first, second],
          total: 2,
          has_more: false,
          focus_id: initialComment ? "first" : "second",
        });
      if (String(path).endsWith("/preview"))
        return ok({ caption: "La publicación de programas", media: [] });
      return ok({
        items: [
          {
            ...group,
            thread: { ...group.thread, focus_id: initialComment || "second" },
          },
        ],
        view: "threads",
        total: 1,
        has_more: false,
      });
    });
  render(
    <SessionBoundary
      initial={{
        ...session,
        actions: readOnly ? ["inbox.read"] : session.actions,
      }}
      expire={() => {}}
    >
      <Comments initialComment={initialComment} />
    </SessionBoundary>,
  );
  return fetcher;
}
beforeEach(() => {
  vi.restoreAllMocks();
});

it("sends a private reply for the chosen comment and keeps public sends distinct", async () => {
  const fetcher = setup();
  fireEvent.click(
    await screen.findByRole("button", { name: /Juan Pablo.*CBN · Nuevo/ }),
  );
  fireEvent.click(
    await screen.findByRole("button", {
      name: "Responder al comentario: ¿Cuánto cuesta?",
    }),
  );
  fireEvent.change(screen.getByLabelText("Respuesta pública"), {
    target: { value: "Te comparto la financiación que solicitaste." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Enviar por privado" }));
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(
        ([path, init]) =>
          String(path).endsWith("comments/first") && init?.method === "POST",
      ),
    ).toBe(true),
  );
  const call = fetcher.mock.calls.find(
    ([path, init]) =>
      String(path).endsWith("comments/first") && init?.method === "POST",
  )!;
  expect(JSON.parse(String(call[1]?.body))).toMatchObject({
    action: "private_reply",
    row_version: first.row_version,
    body: "Te comparto la financiación que solicitaste.",
  });
});

it("does not allow private messages with more than 900 characters", async () => {
  setup();
  fireEvent.click(
    await screen.findByRole("button", { name: /Juan Pablo.*CBN · Nuevo/ }),
  );
  await screen.findByRole("button", { name: "Enviar por privado" });
  fireEvent.change(screen.getByLabelText("Respuesta pública"), {
    target: { value: "x".repeat(901) },
  });
  expect(
    screen.getByRole("button", { name: "Enviar por privado" }),
  ).toBeDisabled();
});

it("groups a person and post and keeps each CBN answer below its exact comment", async () => {
  setup();
  fireEvent.click(
    await screen.findByRole("button", { name: /Juan Pablo.*CBN · Nuevo/ }),
  );
  expect(
    await screen.findByRole("heading", {
      name: "Juan Pablo en esta publicación",
    }),
  ).toBeVisible();
  const entries = screen.getAllByRole("article", {
    name: "Comentario de Juan Pablo",
  });
  expect(within(entries[0]).getByText("¿Cuánto cuesta?")).toBeVisible();
  expect(
    within(entries[0]).getByText("Revisamos el valor para tu jornada."),
  ).toBeVisible();
  expect(
    within(entries[0]).queryByText("Te confirmamos la duración del programa."),
  ).toBeNull();
  expect(
    within(entries[1]).getByText("Te confirmamos la duración del programa."),
  ).toBeVisible();
  expect(screen.getAllByText("Cuenta conectada")).toHaveLength(2);
  expect(
    screen.getByText(/^1 hilo · por persona y publicación$/),
  ).toBeVisible();
});

it("responds to the chosen original using its own version and preserves the draft on refresh", async () => {
  const fetcher = setup();
  fireEvent.click(
    await screen.findByRole("button", { name: /Juan Pablo.*CBN · Nuevo/ }),
  );
  fireEvent.click(
    await screen.findByRole("button", {
      name: "Responder al comentario: ¿Cuánto cuesta?",
    }),
  );
  expect(screen.getByLabelText("Respuesta pública")).toHaveFocus();
  fireEvent.change(screen.getByLabelText("Respuesta pública"), {
    target: { value: "Respuesta individual" },
  });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  fireEvent.click(
    screen.getByRole("button", {
      name: "Responder al comentario: ¿Cuánto cuesta?",
    }),
  );
  expect(confirm).not.toHaveBeenCalled();
  expect(screen.getByLabelText("Respuesta pública")).toHaveValue(
    "Respuesta individual",
  );
  fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Respuesta pública")).toHaveValue(
      "Respuesta individual",
    ),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Enviar respuesta pública" }),
  );
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(
        ([path, init]) =>
          String(path).endsWith("/comments/first") && init?.method === "POST",
      ),
    ).toBe(true),
  );
  const sent = fetcher.mock.calls.find(
    ([path, init]) =>
      String(path).endsWith("/comments/first") && init?.method === "POST",
  );
  expect(JSON.parse(String(sent?.[1]?.body))).toMatchObject({
    action: "reply",
    body: "Respuesta individual",
    row_version: first.row_version,
  });
});

it("a notification for a CBN echo opens the user's group and original target", async () => {
  const fetcher = setup(false, "cbn-echo");
  expect(
    await screen.findByRole("heading", {
      name: "Juan Pablo en esta publicación",
    }),
  ).toBeVisible();
  expect(screen.getByLabelText("Respuesta pública")).toHaveValue("");
  expect(screen.getByText(/Respondiendo a/)).toHaveTextContent(
    "¿Cuánto cuesta?",
  );
  expect(
    fetcher.mock.calls.some(([path]) =>
      String(path).includes("comment_id=cbn-echo"),
    ),
  ).toBe(true);
  expect(
    fetcher.mock.calls.some(([path]) =>
      String(path).includes("comments/cbn-echo/thread"),
    ),
  ).toBe(true);
});

it("read-only roles see the full thread but cannot respond to an individual comment", async () => {
  setup(true);
  fireEvent.click(
    await screen.findByRole("button", { name: /Juan Pablo.*CBN · Nuevo/ }),
  );
  expect(
    await screen.findByRole("button", {
      name: "Responder al comentario: ¿Cuánto cuesta?",
    }),
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Enviar respuesta pública" }),
  ).toBeDisabled();
});

it("keeps an unlinked account reply without guessing the author and allows returning to the list", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    if (String(path).includes("/thread?"))
      return ok({
        items: [],
        total: 0,
        has_more: false,
        unlinked_reply: true,
        focus_id: "orphan",
      });
    return ok({
      items: [
        {
          ...group,
          id: "orphan",
          author: "CBN",
          body: "Respuesta sin padre recibido",
          is_self: true,
          thread: { ...group.thread, focus_id: "orphan", unlinked_reply: true },
        },
      ],
      total: 1,
      has_more: false,
      view: "threads",
    });
  });
  render(
    <SessionBoundary initial={session} expire={() => {}}>
      <Comments />
    </SessionBoundary>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /CBN.*contexto no recibido/ }),
  );
  expect(
    await screen.findByText(/El comentario original aún no llegó desde Meta/),
  ).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Enviar respuesta pública" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Volver a comentarios" }));
  expect(
    screen.getByRole("heading", { name: "Selecciona un comentario" }),
  ).toBeVisible();
});
