export const reviewStatusLabels = {
  pending: "Pendiente",
  in_review: "En revisión",
  reviewed: "Revisada · Demo",
  observed: "Observada · Demo",
  rejected: "Rechazada · Demo",
} as const;
export type ReviewStatus = keyof typeof reviewStatusLabels;
export type ReviewAction =
  "start" | "reviewed" | "observed" | "rejected" | "reopen";
export type ReviewEvent = {
  status: ReviewStatus;
  reason: string;
  at: string;
  actor: string;
};
export type ReviewRecord = {
  id: string;
  name: string;
  email: string;
  program: string;
  schedule: string;
  syntheticConfirmed: boolean;
  status: ReviewStatus;
  history: ReviewEvent[];
};

export function seedReviews(): ReviewRecord[] {
  return [];
}

export function filterReviews(
  records: ReviewRecord[],
  query: string,
  status = "all",
  program = "all",
) {
  const text = query.trim().toLocaleLowerCase("es");
  return records.filter(
    (record) =>
      (status === "all" || record.status === status) &&
      (program === "all" || record.program === program) &&
      [record.id, record.name, record.email, record.program]
        .join(" ")
        .toLocaleLowerCase("es")
        .includes(text),
  );
}

export function transitionReview(
  record: ReviewRecord,
  action: ReviewAction,
  reason: string,
  now = new Date(),
): { record?: ReviewRecord; error?: string } {
  const resolved = ["reviewed", "observed", "rejected"].includes(record.status);
  const allowed =
    action === "start"
      ? record.status === "pending"
      : action === "reopen"
        ? resolved
        : record.status === "in_review";
  if (!allowed)
    return {
      error:
        "El estado cambió o la acción no corresponde. Revise el caso antes de continuar.",
    };
  const trimmed = reason.trim();
  if (action !== "start" && (trimmed.length < 5 || trimmed.length > 600)) {
    return {
      error:
        "Escriba un motivo entre 5 y 600 caracteres, sin contar espacios externos.",
    };
  }
  const status: ReviewStatus =
    action === "start" ? "in_review" : action === "reopen" ? "pending" : action;
  return {
    record: {
      ...record,
      status,
      history: [
        ...record.history,
        {
          status,
          reason:
            action === "start"
              ? "Inicio explícito de revisión local."
              : trimmed,
          at: now.toISOString(),
          actor: "Revisor local · Sin identidad autenticada",
        },
      ],
    },
  };
}
