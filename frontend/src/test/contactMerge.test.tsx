import { renderHook } from "@testing-library/react";
import { useInbox } from "../modules/inbox/hooks/useInbox";
import { inboxApi, type InboxDetail } from "../modules/inbox/api/inboxApi";
import { InboxSessionProvider, useInboxDrafts } from "../shared/inboxSession";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ContactMerge } from "../modules/contacts/components/ContactMerge";
import {
  contactMergeApi,
  type ContactGroup,
  type MergePreview,
} from "../modules/contacts/api/contactMergeApi";
import { clientsApi, ClientsError } from "../modules/clients/api/clientsApi";
import { seedClients } from "./legacyData";
import { inboxDetailState } from "./localClientsMock";
import {
  WorkspaceSessionProvider,
  useWorkspaceField,
} from "../shared/workspaceSession";
import { institutionalIdentityApi } from "../modules/contacts/api/institutionalIdentity";

const [target, source] = seedClients();
function group(id = target.id): ContactGroup {
  const client = id === target.id ? target : source;
  return {
    primaryContactId: id,
    primaryContact: client,
    primaryConversationId: "synthetic-thread",
    memberContactIds: [id],
    links: [],
    members: [
      {
        contactId: id,
        conversationId: "synthetic-thread",
        name: client.name,
        phone: client.phone,
        channel: "Local",
      },
    ],
  };
}
function preview(fingerprint = "a".repeat(64)): MergePreview {
  return {
    sourceContactId: source.id,
    targetContactId: target.id,
    fingerprint,
    blockedReason: null,
    validationError: null,
    laterConfirmations: false,
    members: group().members,
    source: group(source.id).members[0],
    fields: [
      {
        key: "city",
        current: "Current city",
        alternative: "Source city",
        selected: "target",
      },
    ],
  };
}
function view(id = target.id, draft = false) {
  function Draft() {
    const [, set] = useWorkspaceField("clients", "drafts");
    return (
      <button onClick={() => set({ [source.id]: source })}>
        Create RAM draft
      </button>
    );
  }
  return (
    <WorkspaceSessionProvider>
      {draft && <Draft />}
      <ContactMerge contactId={id} />
    </WorkspaceSessionProvider>
  );
}
beforeEach(() => {
  vi.mocked(contactMergeApi.group).mockImplementation(async (id) => group(id));
  vi.spyOn(contactMergeApi, "preview").mockResolvedValue(preview());
  vi.spyOn(contactMergeApi, "commit").mockResolvedValue({
    mergeId: "synthetic",
    revision: "2",
    replayed: false,
  });
  vi.mocked(clientsApi.list).mockResolvedValue({
    clients: [source],
    threads: [],
    revision: "1",
  });
});
async function inspect() {
  await screen.findByRole("button", { name: "Revisar posible unificación" });
  fireEvent.click(
    screen.getByRole("button", { name: "Revisar posible unificación" }),
  );
  fireEvent.change(screen.getByLabelText(/Buscar ficha de origen/), {
    target: { value: "Synthetic" },
  });
  await screen.findByRole("option", { name: source.name });
  fireEvent.change(screen.getByLabelText("Ficha de origen"), {
    target: { value: source.id },
  });
  fireEvent.click(
    screen.getByRole("button", {
      name: "Comparar impacto sin modificar datos",
    }),
  );
  await screen.findByLabelText("Ciudad");
}

it("opens readonly preflight without same-person confirmation and requires reviewed fingerprint to commit", async () => {
  render(view());
  await inspect();
  expect(contactMergeApi.preview).toHaveBeenCalledWith(
    expect.not.objectContaining({ confirmedSamePerson: expect.anything() }),
    false,
    expect.any(AbortSignal),
  );
  const commit = screen.getByRole("button", {
    name: "Confirmar unificación CRM",
  });
  expect(commit).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  expect(commit).toBeEnabled();
  fireEvent.change(screen.getByLabelText("Ciudad"), {
    target: { value: "source" },
  });
  expect(commit).toBeDisabled();
  expect(screen.getByRole("checkbox")).not.toBeChecked();
  vi.mocked(contactMergeApi.preview).mockResolvedValue(preview("b".repeat(64)));
  fireEvent.click(
    screen.getByRole("button", {
      name: "Comparar impacto sin modificar datos",
    }),
  );
  await waitFor(() => expect(contactMergeApi.preview).toHaveBeenCalledTimes(2));
  expect(commit).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(commit);
  await waitFor(() =>
    expect(contactMergeApi.commit).toHaveBeenCalledWith(
      expect.objectContaining({
        confirmedSamePerson: true,
        expectedFingerprint: "b".repeat(64),
        choices: { city: "source" },
      }),
      false,
    ),
  );
});

it("drops confirmation after conflict and after a new preflight", async () => {
  vi.mocked(contactMergeApi.commit).mockRejectedValue(new ClientsError(409));
  render(view());
  await inspect();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(
    screen.getByRole("button", { name: "Confirmar unificación CRM" }),
  );
  await screen.findByText(/Los datos cambiaron/);
  expect(screen.getByRole("checkbox")).not.toBeChecked();
  vi.mocked(contactMergeApi.preview).mockResolvedValue(preview("c".repeat(64)));
  fireEvent.click(
    screen.getByRole("button", {
      name: "Comparar impacto sin modificar datos",
    }),
  );
  await waitFor(() => expect(contactMergeApi.preview).toHaveBeenCalledTimes(2));
  expect(
    screen.getByRole("button", { name: "Confirmar unificación CRM" }),
  ).toBeDisabled();
});

it("removes stale AJAX options immediately on new search criteria", async () => {
  render(view());
  await inspect();
  let resolve!: (value: Awaited<ReturnType<typeof clientsApi.list>>) => void;
  vi.mocked(clientsApi.list).mockReturnValue(
    new Promise((value) => {
      resolve = value;
    }),
  );
  fireEvent.change(screen.getByLabelText(/Buscar ficha de origen/), {
    target: { value: "Other" },
  });
  expect(
    screen.queryByRole("option", { name: source.name }),
  ).not.toBeInTheDocument();
  await waitFor(() => expect(clientsApi.list).toHaveBeenCalledTimes(2));
  fireEvent.change(screen.getByLabelText(/Buscar ficha de origen/), {
    target: { value: "Newer" },
  });
  await act(async () =>
    resolve({ clients: [source], threads: [], revision: "1" }),
  );
  expect(
    screen.queryByRole("option", { name: source.name }),
  ).not.toBeInTheDocument();
});

it("retries failed group reads without a page reload", async () => {
  vi.mocked(contactMergeApi.group).mockRejectedValueOnce(
    new Error("synthetic failure"),
  );
  render(view());
  fireEvent.click(
    await screen.findByRole("button", {
      name: "Reintentar relación de fichas",
    }),
  );
  expect(
    await screen.findByRole("button", { name: "Revisar posible unificación" }),
  ).toBeEnabled();
});

it("keeps RAM drafts and blocks final unification until saved or discarded", async () => {
  render(view(target.id, true));
  await inspect();
  fireEvent.click(screen.getByRole("button", { name: "Create RAM draft" }));
  fireEvent.click(screen.getByRole("checkbox"));
  expect(
    screen.getByRole("button", { name: "Confirmar unificación CRM" }),
  ).toBeDisabled();
  expect(contactMergeApi.commit).not.toHaveBeenCalled();
  expect(
    screen.getByText(/Guarde o descarte los borradores/),
  ).toBeInTheDocument();
});

it("uses real catalog labels for period and document comparison", async () => {
  vi.mocked(institutionalIdentityApi.catalog).mockResolvedValue({
    documentTypes: [{ id: 2, code: "DOC", label: "Synthetic document type" }],
    periods: {
      items: [{ id: 128, label: "2026-B", active: true }],
      activePeriodId: 128,
      selectionRequired: false,
    },
  });
  vi.mocked(contactMergeApi.preview).mockResolvedValue({
    ...preview(),
    fields: [
      {
        key: "profile.aspirationPeriodId",
        current: null,
        alternative: 128,
        selected: "target",
      },
      {
        key: "profile.document",
        current: { documentTypeId: null, document: "" },
        alternative: { documentTypeId: 2, document: "00.X" },
        selected: "target",
      },
    ],
  });
  render(view());
  await screen.findByRole("button", { name: "Revisar posible unificación" });
  fireEvent.click(
    screen.getByRole("button", { name: "Revisar posible unificación" }),
  );
  fireEvent.change(screen.getByLabelText(/Buscar ficha de origen/), {
    target: { value: "Synthetic" },
  });
  await screen.findByRole("option", { name: source.name });
  fireEvent.change(screen.getByLabelText("Ficha de origen"), {
    target: { value: source.id },
  });
  fireEvent.click(
    screen.getByRole("button", {
      name: "Comparar impacto sin modificar datos",
    }),
  );
  expect(
    await screen.findByRole("option", { name: "Origen: 2026-B" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("option", {
      name: "Origen: DOC · Synthetic document type · 00.X",
    }),
  ).toBeInTheDocument();
});

it("ignores a late preflight from the previous contact", async () => {
  let resolve!: (value: MergePreview) => void;
  vi.mocked(contactMergeApi.preview).mockReturnValue(
    new Promise((value) => {
      resolve = value;
    }),
  );
  const rendered = render(view());
  fireEvent.click(
    await screen.findByRole("button", { name: "Revisar posible unificación" }),
  );
  fireEvent.change(screen.getByLabelText(/Buscar ficha de origen/), {
    target: { value: "Synthetic" },
  });
  await screen.findByRole("option", { name: source.name });
  fireEvent.change(screen.getByLabelText("Ficha de origen"), {
    target: { value: source.id },
  });
  fireEvent.click(
    screen.getByRole("button", {
      name: "Comparar impacto sin modificar datos",
    }),
  );
  rendered.rerender(view(source.id));
  await act(async () => resolve(preview()));
  expect(screen.queryByLabelText("Ciudad")).not.toBeInTheDocument();
  expect(contactMergeApi.commit).not.toHaveBeenCalled();
});

it("edits the explicit principal pair while messaging and control remain on the source thread", async () => {
  const sourceThread = "synthetic-source-thread",
    targetThread = "synthetic-target-thread";
  const detail: InboxDetail = {
    ...inboxDetailState(
      {
        clientId: source.id,
        channel: "Local",
        mode: "human",
        unread: false,
        messages: [],
      },
      "3",
    ),
    client: source,
    revision: "3",
    thread: {
      id: sourceThread,
      clientId: source.id,
      channel: "Local",
      mode: "human",
      unread: false,
      messages: [],
      name: source.name,
      phone: source.phone,
      preview: null,
      createdAt: "2026-10-16T00:00:00Z",
      updatedAt: "2026-10-16T00:00:00Z",
      lastMessageAt: null,
    },
    contactGroup: {
      ...group(),
      primaryConversationId: targetThread,
      memberContactIds: [target.id, source.id],
      links: [
        {
          mergeId: "synthetic-merge",
          sourceContactId: source.id,
          targetContactId: target.id,
        },
      ],
      members: [...group().members, group(source.id).members[0]],
    },
  };
  vi.mocked(inboxApi.detail).mockResolvedValue(detail);
  vi.mocked(inboxApi.messages).mockResolvedValue({
    items: [],
    before: null,
    hasMore: false,
    limit: 50,
  });
  vi.mocked(inboxApi.saveContact).mockResolvedValue({ revision: "4" });
  vi.mocked(inboxApi.send).mockResolvedValue({ revision: "5" });
  vi.mocked(inboxApi.change).mockResolvedValue({ revision: "6" });
  const hook = renderHook(
    () => ({
      store: useInbox(source.id, () => {}),
      messages: useInboxDrafts("messages"),
    }),
    { wrapper: InboxSessionProvider },
  );
  await waitFor(() => expect(hook.result.current.store.loading).toBe(false));
  expect(hook.result.current.store.detail?.client.phone).toBe(source.phone);
  await act(() =>
    hook.result.current.messages[1]({
      [sourceThread]: { body: "RAM message stays on source" },
    }),
  );
  await act(async () =>
    hook.result.current.store.saveContact({
      ...target,
      city: "Synthetic principal edit",
    }),
  );
  expect(inboxApi.saveContact).toHaveBeenCalledWith(
    target.id,
    expect.objectContaining({
      conversationId: targetThread,
      client: expect.objectContaining({ id: target.id }),
    }),
  );
  await waitFor(() => expect(hook.result.current.store.loading).toBe(false));
  await act(async () =>
    hook.result.current.store.change({
      ...detail.thread,
      messages: [
        {
          id: "synthetic-message",
          body: "Synthetic new message",
          direction: "outgoing",
        },
      ],
    }),
  );
  expect(inboxApi.send).toHaveBeenCalledWith(
    sourceThread,
    expect.objectContaining({ body: "Synthetic new message" }),
  );
  await waitFor(() => expect(hook.result.current.store.loading).toBe(false));
  await act(async () => hook.result.current.store.change(detail.thread));
  expect(inboxApi.change).toHaveBeenCalledWith(sourceThread, expect.anything());
  await waitFor(() => expect(hook.result.current.store.loading).toBe(false));
  vi.mocked(inboxApi.detail).mockResolvedValue({
    ...detail,
    contactGroup: group(source.id),
  });
  await act(() => hook.result.current.store.reload());
  await waitFor(() =>
    expect(
      hook.result.current.store.detail?.contactGroup?.memberContactIds,
    ).toEqual([source.id]),
  );
  expect(hook.result.current.messages[0][sourceThread].body).toBe(
    "RAM message stays on source",
  );
});
