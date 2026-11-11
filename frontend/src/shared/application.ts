import {
  emptyApplication,
  validateApplication,
  type ApplicationDraft,
} from "./demo";

export const applicationScenarios = [
  { value: "valid", label: "Disponible · Demo" },
  { value: "expired", label: "Vencido · Demo" },
  { value: "used", label: "Ya utilizado · Demo" },
  { value: "invalid", label: "No válido · Demo" },
] as const;
export type ApplicationScenario =
  (typeof applicationScenarios)[number]["value"];
export type ApplicationErrors = Partial<Record<keyof ApplicationDraft, string>>;
export type ApplicationState = {
  scenario: ApplicationScenario;
  step: "capture" | "review" | "confirmed";
  draft: ApplicationDraft;
  errors: ApplicationErrors;
};
export type ApplicationAction =
  | { type: "change"; draft: ApplicationDraft }
  | { type: "validate" }
  | { type: "confirm" }
  | { type: "edit" }
  | { type: "reset"; scenario?: ApplicationScenario };

export function initialApplication(
  scenario: ApplicationScenario = "valid",
): ApplicationState {
  return { scenario, step: "capture", draft: emptyApplication(), errors: {} };
}

export function applicationReducer(
  state: ApplicationState,
  action: ApplicationAction,
): ApplicationState {
  if (action.type === "reset")
    return initialApplication(action.scenario ?? state.scenario);
  if (state.scenario !== "valid" || state.step === "confirmed") return state;
  if (action.type === "change")
    return { ...state, draft: action.draft, errors: {}, step: "capture" };
  if (action.type === "edit") return { ...state, step: "capture", errors: {} };
  if (action.type === "confirm" && state.step !== "review") return state;
  const errors = validateApplication(state.draft);
  if (Object.keys(errors).length) return { ...state, errors, step: "capture" };
  return {
    ...state,
    draft: {
      ...state.draft,
      name: state.draft.name.trim(),
      email: state.draft.email.trim(),
    },
    errors: {},
    step: action.type === "confirm" ? "confirmed" : "review",
  };
}
