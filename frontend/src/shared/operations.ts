export type OperationStatus = "stable" | "degraded" | "paused" | "recovering";
export type OperationAction = "pause" | "review" | "resume";
export type OperationRecord = {
  id: string;
  name: string;
  description: string;
  status: OperationStatus;
  incident: "none" | "open" | "in_review" | "closed";
  revision: number;
  checks: { id: string; label: string; checked: boolean }[];
  history: { at: string; label: string; reason: string }[];
};
export const operationStatusLabels: Record<OperationStatus, string> = {
  stable: "Estable · Demo",
  degraded: "Degradado · Demo",
  paused: "Pausado · Demo",
  recovering: "En revisión de recuperación · Demo",
};
export const operationActionLabels: Record<OperationAction, string> = {
  pause: "Pausar escenario local",
  review: "Revisar recuperación local",
  resume: "Reanudar escenario local",
};
export const incidentLabels: Record<OperationRecord["incident"], string> = {
  none: "Sin incidencia · Fixture",
  open: "Abierta · Fixture",
  in_review: "En revisión · Demo",
  closed: "Cerrada en demo · Sin prueba externa",
};

export function seedOperations(): OperationRecord[] {
  return [];
}

export function operationBinding(record: OperationRecord) {
  return `${record.id}:${record.revision}`;
}

type OperationResult = { record?: OperationRecord; error?: string };

function appendOperation(
  record: OperationRecord,
  label: string,
  reason: string,
  now: Date,
): OperationRecord {
  return {
    ...record,
    revision: record.revision + 1,
    history: [...record.history, { at: now.toISOString(), label, reason }],
  };
}

export function transitionOperation(
  record: OperationRecord,
  action: OperationAction,
  binding: string,
  reason: string,
  now = new Date(),
): OperationResult {
  if (binding !== operationBinding(record))
    return {
      error:
        "El escenario o su revisión cambió. Prepare nuevamente la acción local.",
    };
  const trimmed = reason.trim();
  if (!trimmed || trimmed.length > 300)
    return {
      error:
        "Escriba un motivo ficticio de 1 a 300 caracteres. No incluya datos personales ni secretos.",
    };
  if (!Number.isFinite(now.getTime()))
    return { error: "La fecha local no es válida; no se registró la acción." };
  if (
    action === "pause" &&
    (record.status === "stable" || record.status === "degraded")
  ) {
    return {
      record: appendOperation(
        {
          ...record,
          status: "paused",
          checks: record.checks.map((check) => ({ ...check, checked: false })),
        },
        "Pausa del escenario · Demo",
        trimmed,
        now,
      ),
    };
  }
  if (
    action === "review" &&
    record.status === "paused" &&
    record.checks.length > 0 &&
    record.checks.every((check) => check.checked)
  ) {
    return {
      record: appendOperation(
        {
          ...record,
          status: "recovering",
          incident: record.incident === "open" ? "in_review" : record.incident,
        },
        "Checklist revisado · Demo",
        trimmed,
        now,
      ),
    };
  }
  if (
    action === "resume" &&
    record.status === "recovering" &&
    record.checks.length > 0 &&
    record.checks.every((check) => check.checked)
  ) {
    return {
      record: appendOperation(
        {
          ...record,
          status: "stable",
          incident:
            record.incident === "in_review" ? "closed" : record.incident,
        },
        "Reanudación del escenario · Demo",
        trimmed,
        now,
      ),
    };
  }
  return {
    error:
      "Transición local no disponible. Pause, complete el checklist y revise antes de reanudar.",
  };
}

export function setRecoveryCheck(
  record: OperationRecord,
  checkId: string,
  checked: boolean,
  now = new Date(),
): OperationResult {
  const check = record.checks.find((item) => item.id === checkId);
  if (
    record.status !== "paused" ||
    !check ||
    check.checked === checked ||
    !Number.isFinite(now.getTime())
  )
    return {
      error:
        "El checklist solo puede cambiar durante la pausa del escenario seleccionado.",
    };
  return {
    record: appendOperation(
      {
        ...record,
        checks: record.checks.map((item) =>
          item.id === checkId ? { ...item, checked } : item,
        ),
      },
      checked ? "Paso revisado · Demo" : "Paso desmarcado · Demo",
      check.label,
      now,
    ),
  };
}
