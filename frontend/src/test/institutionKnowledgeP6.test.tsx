import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import {
  KnowledgeWorkspace,
  PrivateMemory,
} from "../institution/KnowledgeWorkspace";
import { SessionBoundary } from "../institution/api";
import type { Session } from "../institution/api";
const session: Session = {
  session_id: "s",
  csrf_token: "p6-csrf",
  actions: ["sources.manage", "inbox.read", "inbox.write"],
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
const ok = (v: unknown, status = 200) =>
  new Response(
    JSON.stringify({
      programs: [],
      stages: [],
      has_more: false,
      ...(v as object),
    }),
    {
      status,
      headers: { "Content-Type": "application/json" },
    },
  );
const document = {
  kind: "collective",
  title: "Criterio revisado",
  body: "Escuchar al aspirante",
  owner: "Admisiones",
  origin: "Acta",
  valid_until: "2027-12-31",
  confidence: 0,
  visibility: "staff_only",
  program_id: null,
  stage_id: null,
  dna: null,
  source_message_id: null,
  quote: "",
  fact_type: "followup_note",
};
const item = {
  id: "record",
  kind: "collective",
  revision: 2,
  state: "published",
  document,
};
afterEach(() => vi.restoreAllMocks());
function mount(child: React.ReactNode) {
  render(
    <SessionBoundary initial={session} expire={() => {}}>
      {child}
    </SessionBoundary>,
  );
}
it("new source stays a draft and publication needs a reviewed stored version", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    ok({ items: [] }),
  );
  mount(<KnowledgeWorkspace />);
  fireEvent.click(await screen.findByRole("button", { name: "Nueva fuente" }));
  expect(
    screen.getByLabelText("Archivo PDF o TXT (hasta 5 MB)"),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Publicar versión revisada" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Guardar borrador" }),
  ).toBeDisabled();
});
it("collective confidence zero and staff-only visibility roundtrip; stale saves preserve draft", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (_, options) =>
      options?.method === "PUT"
        ? ok({ detail: "revision_conflict" }, 409)
        : ok({ items: [item] }),
    );
  mount(<KnowledgeWorkspace memory />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Criterio revisado/ }),
  );
  expect(screen.getByLabelText("Confianza editorial (0–100)")).toHaveValue(0);
  expect(screen.getByLabelText("Visibilidad")).toHaveValue("staff_only");
  fireEvent.change(screen.getByLabelText("Contenido"), {
    target: { value: "Borrador conservado" },
  });
  fireEvent.change(screen.getByLabelText("Motivo de cambio o revisión"), {
    target: { value: "Corrección" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));
  await screen.findByText(/Hay una versión más reciente/);
  expect(screen.getByLabelText("Contenido")).toHaveValue("Borrador conservado");
  const mutation = fetcher.mock.calls.find((v) => v[1]?.method === "PUT");
  expect(new Headers(mutation?.[1]?.headers).get("X-CSRF-Token")).toBe(
    "p6-csrf",
  );
  expect(JSON.parse(String(mutation?.[1]?.body))).toMatchObject({
    confidence: 0,
    visibility: "staff_only",
    revision: 2,
  });
});
it("review controls require reason and explicit confirmation, without editing the version", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(ok({ items: [item] }));
  mount(<KnowledgeWorkspace memory />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Criterio revisado/ }),
  );
  const publish = screen.getByRole("button", {
    name: "Publicar versión revisada",
  });
  expect(publish).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Motivo de cambio o revisión"), {
    target: { value: "Revisado" },
  });
  expect(publish).toBeDisabled();
  fireEvent.click(
    screen.getByRole("checkbox", { name: /He revisado contenido/ }),
  );
  expect(publish).toBeEnabled();
});
it("DNA uses distinct structured fields and preserves academic authority", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
    ok({ items: [] }),
  );
  mount(<KnowledgeWorkspace memory />);
  await screen.findByRole("button", { name: "Nueva memoria" });
  fireEvent.click(screen.getByRole("button", { name: "ADN institucional" }));
  fireEvent.click(await screen.findByRole("button", { name: "Nuevo ADN" }));
  expect(screen.getByLabelText("Misión")).toBeInTheDocument();
  expect(screen.getByLabelText("Límites institucionales")).toBeInTheDocument();
  expect(
    screen.getByText(/SIIE conserva la autoridad académica/),
  ).toBeInTheDocument();
});
it("readonly Inbox memory cannot write or publish and uses its conversation URL", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    ok({
      items: [
        {
          ...item,
          kind: "private",
          document: {
            ...document,
            kind: "private",
            visibility: "conversation_only",
          },
        },
      ],
    }),
  );
  mount(<PrivateMemory conversation="own-conversation" canWrite={false} />);
  fireEvent.click(
    await screen.findByRole("button", { name: /Criterio revisado/ }),
  );
  expect(
    screen.queryByRole("button", { name: "Nueva memoria" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Guardar borrador" }),
  ).toBeDisabled();
  await waitFor(() =>
    expect(fetcher.mock.calls[0][0]).toBe(
      "/api/institution/conversation-memory/own-conversation",
    ),
  );
});
