type Row = Record<string, unknown>;
const missing = (value: unknown) =>
  value === null ||
  value === undefined ||
  value === "" ||
  (Array.isArray(value) && !value.length);
const names: Record<string, string> = {
  name: "Nombre",
  school: "Escuela",
  schedule: "Jornada",
  duration: "Duración",
  modality: "Modalidad",
  aliases: "Alias",
  price_cop: "Tarifa",
  price_concept: "Concepto de tarifa",
  price_valid_from: "Vigencia inicial",
  price_valid_until: "Vigencia final",
  full_cost_cash_cop: "Costo total de contado",
  syllabus: "Materias",
  requirements: "Requisitos",
  cost_inclusions: "Incluye",
  cost_exclusions: "No incluye",
  financial_plans: "Planes financieros",
  initial_payment_cop: "Abono inicial",
  initial_payment_due_date: "Fecha del abono",
  total_cost_cop: "Total financiado",
  valid_from: "Vigencia inicial",
  valid_until: "Vigencia final",
  installments: "Cuotas",
  due_date: "Fecha",
  amount_cop: "Importe",
  conditions: "Condiciones",
};
export function sourceGaps(local: Row, remote: Row, kind: "program" | "offer") {
  const gaps: string[] = [];
  const compare = (current: Row, source: Row, keys: string[], prefix = "") => {
    keys.forEach((key) => {
      if (!missing(current[key]) && missing(source[key]))
        gaps.push(prefix + (names[key] ?? key));
    });
  };
  compare(local, remote, ["name", "school", "schedule"]);
  const current = (local.commercial ?? {}) as Row;
  const source = (remote.commercial ?? {}) as Row;
  compare(
    current,
    source,
    kind === "program"
      ? ["duration", "modality", "aliases"]
      : [
          "duration",
          "modality",
          "syllabus",
          "requirements",
          "price_cop",
          "price_concept",
          "price_valid_from",
          "price_valid_until",
          "full_cost_cash_cop",
          "cost_inclusions",
          "cost_exclusions",
          "financial_plans",
        ],
  );
  if (kind === "offer") {
    const plans = (source.financial_plans ?? []) as Row[];
    ((current.financial_plans ?? []) as Row[]).forEach((plan) => {
      const original = plans.find(
        (row) => row.external_id === plan.external_id,
      );
      const prefix = `Plan ${String(plan.name || plan.external_id)} · `;
      if (!original) {
        if (!gaps.includes("Planes financieros"))
          gaps.push(prefix + "no recibido en esta copia");
        return;
      }
      compare(
        plan,
        original,
        [
          "initial_payment_cop",
          "initial_payment_due_date",
          "total_cost_cop",
          "valid_from",
          "valid_until",
          "conditions",
          "installments",
        ],
        prefix,
      );
      ((plan.installments ?? []) as Row[]).forEach((part) => {
        const baseline =
          ((original.installments ?? []) as Row[]).find(
            (row) => row.number === part.number,
          ) ?? {};
        compare(
          part,
          baseline,
          ["amount_cop", "due_date"],
          `${prefix}Cuota ${part.number} · `,
        );
      });
    });
  }
  return gaps;
}
