import type { AnalysisPolicyDraft } from "../modules/conversation-analysis/api/analysis";
import type {
  TaskDraft,
  AssignmentDraft,
  AgentDraft,
} from "../modules/inbox/api/inboxOperations";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import type { Client } from "./demo";
import type { CustomField } from "./crm";
import type { IdentitySearch } from "../modules/contacts/api/institutionalIdentity";
import type { ActivityFilters } from "../modules/contacts/api/contactActivity";
import type {
  Followup,
  FollowupInput,
} from "../modules/admissions/api/admissionsApi";

export type AdmissionDraft = {
  body: string;
  state: string;
  due: string;
  editing: Followup | null;
  attempt: { key: string; id: string; input: FollowupInput } | null;
};
import type {
  AiConfig,
  AiModel,
  AiProvider,
  AiSnapshot,
  AiTestResult,
  VoiceCatalog,
} from "./aiSettings";

type WorkspaceSession = {
  institutional: {
    cache: Map<string, unknown>;
    contacts: Map<string, Client>;
    messages: Map<string, string>;
  };
  analysis: {
    strategyFeedback: Record<
      string,
      {
        planId: string;
        usefulness: string;
        outcome: string;
        correction: string;
      }
    >;
    policy: AnalysisPolicyDraft | null;
    feedback: Record<string, { text: string; revision: string }>;
  };
  inboxOperations: {
    tasks: Record<string, TaskDraft>;
    assignments: Record<string, AssignmentDraft>;
    agent: AgentDraft | null;
    policy: { enabled: boolean; threshold: string; revision: string } | null;
  };
  admissions: { drafts: Record<string, AdmissionDraft> };
  clients: {
    selected: string;
    openedRequest: number;
    drafts: Record<string, Client>;
    query: string;
    stage: string;
    tag: string;
    city: string;
    contactType: string;
    program: string;
    identitySearches: Record<string, IdentitySearch>;
    activityFilters: Record<string, ActivityFilters>;
  };
  crm: {
    stageKey: string;
    stageLabel: string;
    probability: string;
    probabilityDrafts: Record<string, string>;
    tag: string;
    fieldKey: string;
    fieldLabel: string;
    fieldType: CustomField["type"];
    options: string;
    required: boolean;
  };
  settingsSection:
    | "IA"
    | "Canales"
    | "Base de datos"
    | "APIs"
    | "Diagnóstico"
    | "Usuarios"
    | "Perfil"
    | "Seguridad";
  responses: Record<
    string,
    { binding: string; body: string; reviewed: boolean; used: boolean }
  >;
  ai: {
    snapshot: AiSnapshot | null;
    draft: AiConfig | null;
    catalogs: Partial<Record<AiProvider, AiModel[]>>;
    voiceCatalogs: Record<string, VoiceCatalog>;
    busy: string;
    error: string;
    feedback: string;
    reloadPending: boolean;
    prompt: string;
    history: { role: "user" | "assistant"; content: string }[];
    result: AiTestResult | null;
  };
};
function initialWorkspaceSession(): WorkspaceSession {
  return {
    institutional: {
      cache: new Map(),
      contacts: new Map(),
      messages: new Map(),
    },
    analysis: { policy: null, feedback: {}, strategyFeedback: {} },
    inboxOperations: { tasks: {}, assignments: {}, agent: null, policy: null },
    admissions: { drafts: {} },
    clients: {
      selected: "",
      openedRequest: 0,
      drafts: {},
      query: "",
      stage: "Todas",
      tag: "Todas",
      city: "",
      contactType: "",
      program: "",
      identitySearches: {},
      activityFilters: {},
    },
    crm: {
      stageKey: "",
      stageLabel: "",
      probability: "",
      probabilityDrafts: {},
      tag: "",
      fieldKey: "",
      fieldLabel: "",
      fieldType: "Text",
      options: "",
      required: false,
    },
    settingsSection: "IA",
    responses: {},
    ai: {
      snapshot: null,
      draft: null,
      catalogs: {},
      voiceCatalogs: {},
      busy: "",
      error: "",
      feedback: "",
      reloadPending: false,
      prompt: "",
      history: [],
      result: null,
    },
  };
}
const WorkspaceContext = createContext<{
  session: WorkspaceSession;
  setSession: Dispatch<SetStateAction<WorkspaceSession>>;
} | null>(null);

// Drafts are kept in this tab until explicit confirmation or cancellation.
export function WorkspaceSessionProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [session, setSession] = useState(initialWorkspaceSession);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      const data = session.institutional;
      const pending =
        data.contacts.size > 0 ||
        [...data.messages.values()].some((value) => !!value.trim()) ||
        [...data.cache.keys()].some(
          (key) =>
            key.startsWith("command:") ||
            key.startsWith("note:") ||
            key.startsWith("sla:") ||
            key.split(":").length > 2,
        );
      if (pending) event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [session.institutional]);
  const dirtyAi =
    !!session.ai.snapshot &&
    JSON.stringify(session.ai.snapshot.settings) !==
      JSON.stringify(session.ai.draft);
  const dirtyAdmissions = Object.values(session.admissions.drafts).some(
    (draft) => draft.body.trim().length > 0,
  );
  useEffect(() => {
    if (!dirtyAi && !dirtyAdmissions) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirtyAi, dirtyAdmissions]);
  return (
    <WorkspaceContext value={{ session, setSession }}>
      {children}
    </WorkspaceContext>
  );
}
export function useWorkspaceState<K extends keyof WorkspaceSession>(key: K) {
  const owner = useContext(WorkspaceContext);
  if (!owner) throw new Error("Workspace state requires its session owner");
  const { session, setSession } = owner;
  const update: Dispatch<SetStateAction<WorkspaceSession[K]>> = useCallback(
    (value) =>
      setSession((previous) => ({
        ...previous,
        [key]: typeof value === "function" ? value(previous[key]) : value,
      })),
    [key, setSession],
  );
  return [session[key], update] as const;
}

export function useWorkspaceField<
  S extends "clients" | "crm" | "ai" | "inboxOperations" | "analysis",
  K extends keyof WorkspaceSession[S],
>(section: S, key: K) {
  const [data, update] = useWorkspaceState(section);
  const setValue: Dispatch<SetStateAction<WorkspaceSession[S][K]>> =
    useCallback(
      (value) =>
        update((previous) => ({
          ...previous,
          [key]:
            typeof value === "function"
              ? (
                  value as (
                    previous: WorkspaceSession[S][K],
                  ) => WorkspaceSession[S][K]
                )(previous[key])
              : value,
        })),
      [key, update],
    );
  return [data[key], setValue] as const;
}
