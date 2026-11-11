import { useState } from "react";
import type { Assessment, InboxDetail } from "../api/inboxApi";
import { operationDate, slaLabels } from "../api/inboxOperations";
import { Badge, Button, Field, Notice, SelectField } from "../../../shared/ui";

export function InboxAssessment({
  detail,
  busy,
  onSave,
}: {
  detail: InboxDetail;
  busy: boolean;
  onSave: (assessment: Assessment) => Promise<unknown>;
}) {
  const saved = detail.miniCrm;
  const assignment = saved.assignment;
  const [draft, setDraft] = useState<{
    score: string;
    temperature: string;
  } | null>(null);
  const [feedback, setFeedback] = useState("");
  const [saving, setSaving] = useState(false);
  const score =
    draft?.score ?? (saved.leadScore == null ? "" : String(saved.leadScore));
  const temperature = draft?.temperature ?? saved.temperature ?? "";
  async function save() {
    if (saving || busy) return;
    const parsed = score === "" ? null : Number(score);
    if (
      parsed !== null &&
      (!Number.isInteger(parsed) || parsed < 0 || parsed > 100)
    ) {
      setFeedback(
        "El puntaje debe ser un entero entre 0 y 100, o quedar sin evaluar.",
      );
      return;
    }
    setSaving(true);
    try {
      await onSave({
        leadScore: parsed,
        temperature: (temperature || null) as Assessment["temperature"],
      });
      setDraft(null);
      setFeedback("Evaluación manual confirmada.");
    } catch (error) {
      setFeedback(
        error instanceof Error
          ? error.message
          : "No se guardó la evaluación. El borrador se conserva.",
      );
    } finally {
      setSaving(false);
    }
  }
  if (!assignment) return null;
  return (
    <section aria-label="Datos operativos del aspirante">
      <h3>Datos operativos</h3>
      <p className="scope-text">
        Prioridad, responsables y control se comparten entre todos los canales
        de esta conversación. La evaluación es manual y no equivale al índice de
        señales de IA.
      </p>
      <dl className="detail-list">
        <dt>Control del bot</dt>
        <dd>
          {saved.takeover
            ? "Pausado por control humano"
            : "Reservado para IA · sin respuestas automáticas"}
        </dd>
        <dt>Responsable humano</dt>
        <dd>{assignment.humanName || "Sin asignar"}</dd>
        <dt>SLA</dt>
        <dd>
          <Badge>{slaLabels[assignment.slaStatus] ?? "Sin configurar"}</Badge>
        </dd>
        <dt>Primera respuesta pendiente</dt>
        <dd>
          {assignment.firstResponseDueAt
            ? operationDate(assignment.firstResponseDueAt)
            : "Sin fecha pendiente"}
        </dd>
        <dt>Próxima respuesta pendiente</dt>
        <dd>
          {assignment.dueAt
            ? operationDate(assignment.dueAt)
            : "Sin fecha pendiente"}
        </dd>
        <dt>Lectura confirmada</dt>
        <dd>Hasta secuencia {saved.readSequence}</dd>
      </dl>
      {!!saved.inFlightOrUncertain && (
        <Notice>
          Hay {saved.inFlightOrUncertain} envío(s) iniciados o de resultado
          incierto. Tomar control bloquea nuevas respuestas del bot; una
          solicitud ya iniciada no se puede retirar.
        </Notice>
      )}
      <fieldset className="client-editor-fields" disabled={busy || saving}>
        <Field
          id="inbox-lead-score"
          label="Puntaje del aspirante (0–100)"
          type="number"
          min={0}
          max={100}
          step={1}
          value={score}
          placeholder="Sin evaluar"
          onChange={(event) =>
            setDraft({ score: event.target.value, temperature })
          }
        />
        <SelectField
          id="inbox-lead-temperature"
          label="Temperatura del aspirante"
          value={temperature}
          options={[
            { value: "", label: "Sin evaluar" },
            { value: "cold", label: "Frío" },
            { value: "warm", label: "Tibio" },
            { value: "hot", label: "Caliente" },
          ]}
          onChange={(event) =>
            setDraft({ score, temperature: event.target.value })
          }
        />
        <Button disabled={!draft} onClick={() => void save()}>
          {saving ? "Guardando evaluación…" : "Guardar evaluación manual"}
        </Button>
        {!!draft && (
          <Button
            variant="quiet"
            onClick={() => {
              setDraft(null);
              setFeedback("");
            }}
          >
            Descartar evaluación
          </Button>
        )}
      </fieldset>
      {feedback && <Notice>{feedback}</Notice>}
    </section>
  );
}
