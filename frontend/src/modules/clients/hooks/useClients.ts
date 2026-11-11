import { useCallback, useEffect, useRef, useState } from "react";
import type { Client, Thread } from "../../../shared/demo";
import { workflowOf } from "../../../shared/workflow";
import {
  clientsApi,
  ClientsError,
  type ClientSnapshot,
} from "../api/clientsApi";

export function useClients() {
  const [snapshot, setSnapshot] = useState<ClientSnapshot>({
    clients: [],
    threads: [],
    revision: "",
  });
  const current = useRef(snapshot);
  const sequence = useRef(0);
  const mutation = useRef(false);
  const intents = useRef(
    new Map<string, { operationId: string; entityId: string }>(),
  );
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const accept = useCallback((value: ClientSnapshot) => {
    current.current = value;
    setSnapshot(value);
    setStatus("ready");
    setError("");
  }, []);
  const load = useCallback(
    async (signal?: AbortSignal) => {
      if (mutation.current) return;
      const token = ++sequence.current;
      try {
        const value = await clientsApi.workspace(signal);
        if (token === sequence.current && !signal?.aborted) accept(value);
      } catch (failure) {
        if (token !== sequence.current || signal?.aborted) return;
        setStatus("error");
        setError(
          failure instanceof Error
            ? failure.message
            : "No se pudo cargar la información.",
        );
      }
    },
    [accept],
  );
  useEffect(() => {
    const controller = new AbortController();
    const token = ++sequence.current;
    void clientsApi
      .workspace(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted && token === sequence.current)
          accept(value);
      })
      .catch((failure) => {
        if (controller.signal.aborted || token !== sequence.current) return;
        setStatus("error");
        setError(
          failure instanceof Error
            ? failure.message
            : "No se pudo cargar la información.",
        );
      });
    return () => controller.abort();
  }, [accept]);
  async function confirm(
    key: string,
    execute: (
      operationId: string,
      entityId: string,
      revision: string,
    ) => Promise<ClientSnapshot>,
  ) {
    if (mutation.current || !current.current.revision)
      throw new ClientsError(409);
    const intent = intents.current.get(key) ?? {
      operationId: crypto.randomUUID(),
      entityId: crypto.randomUUID(),
    };
    intents.current.set(key, intent);
    mutation.current = true;
    setBusy(true);
    ++sequence.current;
    try {
      const result = await execute(
        intent.operationId,
        intent.entityId,
        current.current.revision,
      );
      accept(result);
      intents.current.delete(key);
      return result;
    } catch (failure) {
      mutation.current = false;
      if (failure instanceof ClientsError && failure.status === 409)
        await load();
      throw failure;
    } finally {
      mutation.current = false;
      setBusy(false);
    }
  }
  async function save(client: Client, create: boolean) {
    const result = await confirm(
      JSON.stringify(["contact", create, client]),
      (operationId, entityId, revision) => {
        const conversationId = create
          ? entityId
          : current.current.threads.find(
              (thread) => thread.clientId === client.id,
            )?.id;
        if (!conversationId) throw new ClientsError(404);
        return clientsApi.save(
          client,
          revision,
          create,
          operationId,
          conversationId,
        );
      },
    );
    const saved = result.clients.find((item) => item.id === client.id);
    if (!saved) throw new ClientsError(502);
    return saved;
  }
  async function changeThread(thread: Thread) {
    const original = current.current.threads.find(
      (item) => item.id === thread.id,
    );
    if (!original || !thread.id) throw new ClientsError(404);
    const message = thread.messages.find(
      (item) => !original.messages.some((value) => value.id === item.id),
    );
    const workflow = workflowOf(thread);
    const states = {
      Abierta: "open",
      "En espera": "waiting",
      Cerrada: "closed",
    };
    const priorities = {
      Baja: "low",
      Normal: "normal",
      Alta: "high",
      Urgente: "urgent",
    };
    const payload = message
      ? { body: message.body }
      : {
          state: states[workflow.state],
          priority: priorities[workflow.priority],
          assignee:
            workflow.assignee === "Sin asignar" ? "" : workflow.assignee,
          mode: thread.mode,
          unread: thread.unread,
        };
    await confirm(
      JSON.stringify([thread.id, payload]),
      (operationId, entityId, expectedRevision) =>
        message
          ? clientsApi.message(thread.id!, {
              ...payload,
              operationId,
              expectedRevision,
              messageId: entityId,
            })
          : clientsApi.conversation(thread.id!, {
              ...payload,
              operationId,
              expectedRevision,
            }),
    );
  }
  function reload() {
    setStatus("loading");
    return load();
  }
  return { ...snapshot, status, busy, error, reload, save, changeThread };
}
