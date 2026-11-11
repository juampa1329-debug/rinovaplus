import { createContext, useContext, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import type { InboxMedia } from "../modules/inbox/api/mediaApi";
import {
  inboxContextOpenKey,
  readBooleanPreference,
  writeBooleanPreference,
} from "./viewPreferences";

export type MessageDraft = {
  body: string;
  binding?: string;
  delivery?: "local" | "external";
  identityId?: string;
  media?: InboxMedia;
};
type InboxView = {
  mode: string;
  openedThreadRequest: number;
  query: string;
  channel: string;
  filter: string;
  stateFilter: string;
  stage: string;
  showContext: boolean;
  selectedComment: string;
  assignee: string;
  humanId: string;
  aiId: string;
  sla: string;
  assignment: string;
  offset: number;
};
type Session = {
  assignees: Record<string, string>;
  messages: Record<string, MessageDraft>;
  comments: Record<string, string>;
  tasks: Record<string, { title: string; due: string }>;
  view: InboxView;
};
const emptySession = (): Session => ({
  assignees: {},
  messages: {},
  comments: {},
  tasks: {},
  view: {
    mode: "Mensajes",
    openedThreadRequest: 0,
    query: "",
    channel: "Todos",
    filter: "Todos",
    stateFilter: "Todos",
    stage: "",
    showContext: readBooleanPreference(inboxContextOpenKey, true),
    selectedComment: "",
    assignee: "",
    humanId: "",
    aiId: "",
    sla: "",
    assignment: "",
    offset: 0,
  },
});
const InboxSession = createContext<{
  session: Session;
  setSession: Dispatch<SetStateAction<Session>>;
  intents: Map<
    string,
    { operationId: string; messageId: string; expectedRevision?: string }
  >;
} | null>(null);

// Drafts remain in memory; only the visual context-panel preference is persisted.
export function InboxSessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState(emptySession);
  const [intents] = useState(
    () =>
      new Map<
        string,
        { operationId: string; messageId: string; expectedRevision?: string }
      >(),
  );
  return (
    <InboxSession value={{ session, setSession, intents }}>
      {children}
    </InboxSession>
  );
}

export function useInboxIntents() {
  const owner = useContext(InboxSession);
  if (!owner) throw new Error("Inbox intents require their session owner");
  return owner.intents;
}

export function useInboxDrafts<K extends keyof Session>(key: K) {
  const owner = useContext(InboxSession);
  if (!owner) throw new Error("Inbox drafts require their session owner");
  const { session, setSession } = owner;
  const setDrafts: Dispatch<SetStateAction<Session[K]>> = (update) =>
    setSession((previous) => ({
      ...previous,
      [key]: typeof update === "function" ? update(previous[key]) : update,
    }));
  return [session[key], setDrafts] as const;
}

export function useInboxView<K extends keyof InboxView>(key: K) {
  const [view, update] = useInboxDrafts("view");
  const setValue = (value: InboxView[K]) => {
    update((previous) => ({ ...previous, [key]: value }));
    if (key === "showContext" && typeof value === "boolean") {
      writeBooleanPreference(inboxContextOpenKey, value);
    }
  };
  return [view[key], setValue] as const;
}
