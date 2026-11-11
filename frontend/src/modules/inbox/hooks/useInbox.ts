import { useCallback, useEffect, useRef, useState } from "react";
import { inboxApi, type InboxDetail, type MessagePage } from "../api/inboxApi";
import { ClientsError } from "../../clients/api/clientsApi";
import { useInboxIntents } from "../../../shared/inboxSession";
import { workflowOf } from "../../../shared/workflow";
import type { Client, Thread } from "../../../shared/demo";
import type { Assessment, DeliveryIntent } from "../api/inboxApi";
import { useRuntime } from "../../../shared/runtimeCapabilities";

export function useInbox(contactId: string, onConfirmed: () => void) {
  const { features } = useRuntime().capabilities;
  const intents = useInboxIntents();
  const [value, setValue] = useState<{
    key: string;
    detail: InboxDetail;
    page: MessagePage;
  } | null>(null);
  const [failure, setFailure] = useState<{
    key: string;
    message: string;
  } | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [busy, setBusy] = useState(false);
  const [olderBusy, setOlderBusy] = useState(false);
  const lock = useRef(false);
  const sequence = useRef(0);
  const mounted = useRef(false);
  const key = JSON.stringify([contactId, refresh]);
  const current = useRef(value);
  const olderController = useRef<AbortController | null>(null);
  const reload = useCallback(() => setRefresh((n) => n + 1), []);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      olderController.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!contactId) return;
    const controller = new AbortController();
    const token = ++sequence.current;
    olderController.current?.abort();
    void inboxApi
      .detail(contactId, controller.signal)
      .then(async (detail) => {
        const page = await inboxApi.messages(
          detail.thread.id,
          null,
          controller.signal,
        );
        if (controller.signal.aborted || token !== sequence.current) return;
        const next = { key, detail, page };
        current.current = next;
        setValue(next);
        setFailure(null);
        setOlderBusy(false);
      })
      .catch(() => {
        if (!controller.signal.aborted && token === sequence.current) {
          setFailure({
            key,
            message:
              "No se pudo cargar esta conversación. Reintente; su borrador se conserva.",
          });
          setOlderBusy(false);
        }
      });
    return () => controller.abort();
  }, [contactId, key]);
  const ready = value?.key === key;
  async function older() {
    if (!ready || olderBusy || !value.page.hasMore || lock.current) return;
    const previous = value;
    const controller = new AbortController();
    olderController.current = controller;
    const token = sequence.current;
    setOlderBusy(true);
    try {
      const page = await inboxApi.messages(
        previous.detail.thread.id,
        previous.page.before,
        controller.signal,
      );
      if (
        !mounted.current ||
        controller.signal.aborted ||
        token !== sequence.current
      )
        return;
      const next = {
        ...previous,
        page: { ...page, items: [...page.items, ...previous.page.items] },
      };
      current.current = next;
      setValue(next);
      setFailure(null);
    } catch {
      if (!controller.signal.aborted && token === sequence.current)
        setFailure({
          key,
          message: "No se pudieron cargar mensajes anteriores. Reintente.",
        });
    } finally {
      if (mounted.current && token === sequence.current) setOlderBusy(false);
    }
  }
  async function change(
    thread: Thread,
    route?: DeliveryIntent,
    assessment?: Assessment,
  ) {
    const original = current.current;
    if (
      lock.current ||
      !ready ||
      !original ||
      original.key !== key ||
      thread.id !== original.detail.thread.id
    )
      throw new ClientsError(409);
    const message = thread.messages.find(
      (item) => !original.page.items.some((old) => old.id === item.id),
    );
    const workflow = workflowOf(thread);
    const payload = message
      ? { body: message.body, ...(route ?? { delivery: "local" }) }
      : {
          state: { Abierta: "open", "En espera": "waiting", Cerrada: "closed" }[
            workflow.state
          ],
          priority: {
            Baja: "low",
            Normal: "normal",
            Alta: "high",
            Urgente: "urgent",
          }[workflow.priority],
          assignee:
            workflow.assignee === "Sin asignar" ? "" : workflow.assignee,
          mode: thread.mode,
          unread: thread.unread,
          ...(!thread.unread && features.readSequence
            ? {
                readThroughSequence: original.page.items.reduce(
                  (maximum, item) =>
                    BigInt(item.sequence) > BigInt(maximum)
                      ? item.sequence
                      : maximum,
                  "0",
                ),
              }
            : {}),
          ...(assessment ? { ...assessment, assessmentChanged: true } : {}),
        };
    return mutate(
      thread.id!,
      message ? "message" : "operation",
      payload,
      original.detail.revision,
    );
  }
  async function saveContact(client: Client) {
    const original = current.current;
    if (
      lock.current ||
      !ready ||
      !original ||
      original.key !== key ||
      client.id !==
        (original.detail.contactGroup?.primaryContactId ??
          original.detail.client.id)
    )
      throw new ClientsError(409);
    return mutate(
      client.id,
      "contact",
      {
        client,
        conversationId:
          original.detail.contactGroup?.primaryConversationId ??
          original.detail.thread.id,
      },
      original.detail.revision,
    );
  }
  async function mutate(
    id: string,
    action: string,
    payload: object,
    revision: string,
  ) {
    const intentKey = JSON.stringify([id, action, payload]);
    const intent = intents.get(intentKey) ?? {
      operationId: crypto.randomUUID(),
      messageId: crypto.randomUUID(),
    };
    intents.set(intentKey, intent);
    lock.current = true;
    setBusy(true);
    olderController.current?.abort();
    try {
      const body = {
        ...payload,
        operationId: intent.operationId,
        expectedRevision: revision,
      };
      if (action === "contact") await inboxApi.saveContact(id, body);
      else if (action === "message")
        await inboxApi.send(id, { ...body, messageId: intent.messageId });
      else await inboxApi.change(id, body);
      intents.delete(intentKey);
      // A confirmed write stays confirmed even if a later read of another module fails.
      if (mounted.current) reload();
      onConfirmed();
    } catch (error) {
      if (
        error instanceof ClientsError &&
        error.status === 409 &&
        mounted.current
      )
        reload();
      throw error;
    } finally {
      lock.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  return {
    detail: value?.detail.client.id === contactId ? value.detail : null,
    page: value?.detail.client.id === contactId ? value.page : null,
    busy: busy || !ready,
    olderBusy,
    error: failure?.key === key ? failure.message : "",
    loading: !!contactId && !ready && failure?.key !== key,
    change,
    send: (body: string, route: DeliveryIntent) => {
      const original = current.current;
      if (lock.current || !ready || !original || original.key !== key)
        throw new ClientsError(409);
      return mutate(
        original.detail.thread.id,
        "message",
        { body, ...route },
        original.detail.revision,
      );
    },
    assess: (assessment: Assessment) => {
      if (!current.current) throw new ClientsError(409);
      return change(current.current.detail.thread, undefined, assessment);
    },
    saveContact,
    older,
    reload,
    refresh,
  };
}
