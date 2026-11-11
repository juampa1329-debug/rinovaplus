import { useState } from "react";
import {
  incidentLabels,
  operationActionLabels,
  operationBinding,
  operationStatusLabels,
  setRecoveryCheck,
  transitionOperation,
  type OperationAction,
  type OperationRecord,
} from "../shared/operations";
import { Badge, Button, Notice, SelectField, TextArea } from "../shared/ui";

export function OperationDiagnostics({
  records,
  onChange,
}: {
  records: OperationRecord[];
  onChange: (record: OperationRecord) => void;
}) {
  const [selected, setSelected] = useState(records[0].id);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [pending, setPending] = useState<{
    action: OperationAction;
    binding: string;
    reason: string;
  } | null>(null);
  const record = records.find((item) => item.id === selected)!;
  const allChecked = record.checks.every((check) => check.checked);
  const binding = operationBinding(record);
  const validPending =
    pending?.binding === binding && pending.reason === reason;

  function prepare(action: OperationAction) {
    const result = transitionOperation(record, action, binding, reason);
    setError(result.error ?? "");
    setFeedback("");
    setPending(result.error ? null : { action, binding, reason });
  }
  function confirm() {
    if (!pending) return;
    const result = transitionOperation(
      record,
      pending.action,
      pending.binding,
      pending.reason,
    );
    setPending(null);
    setError(result.error ?? "");
    if (result.record) {
      onChange(result.record);
      setReason("");
      setFeedback(
        "Acción registrada solo en el escenario local. No modificó servicios, mensajes ni control humano.",
      );
    }
  }
  return (
    <section aria-labelledby="operation-local-title">
      <div className="panel-heading">
        <h3 id="operation-local-title">Ensayo de operación local</h3>
        <Badge>Fase 6 · Solo fixtures</Badge>
      </div>
      <Notice>
        Todos los estados e incidencias siguientes son sintéticos. La pausa solo
        afecta el escenario seleccionado; Inbox y el control humano no cambian.
        No procesa colas, reenvía mensajes ni consulta proveedores.
      </Notice>
      <SelectField
        id="operation-scenario"
        label="Escenario sintético de operación"
        options={records.map((item) => ({ value: item.id, label: item.name }))}
        value={selected}
        onChange={(event) => {
          setSelected(event.target.value);
          setPending(null);
          setReason("");
          setError("");
          setFeedback("");
        }}
      />
      <p>{record.description}</p>
      <dl className="detail-list">
        <dt>Estado del escenario seleccionado</dt>
        <dd>{operationStatusLabels[record.status]}</dd>
        <dt>Incidencia del escenario</dt>
        <dd>{incidentLabels[record.incident]}</dd>
        <dt>Incidencias sintéticas abiertas</dt>
        <dd>
          {
            records.filter(
              (item) =>
                item.incident === "open" || item.incident === "in_review",
            ).length
          }
        </dd>
        <dt>Escenarios pausados · Demo</dt>
        <dd>{records.filter((item) => item.status === "paused").length}</dd>
        <dt>Eventos operativos de esta pestaña · Demo</dt>
        <dd>
          {records.reduce((count, item) => count + item.history.length, 0)}
        </dd>
      </dl>
      {(record.status === "paused" || record.status === "recovering") && (
        <fieldset className="field">
          <legend>Checklist de recuperación · Solo revisión local</legend>
          <p>
            No acredita restauración ni disponibilidad. Desmarcar un paso
            invalida la acción preparada.
          </p>
          {record.checks.map((check) => (
            <div className="field" key={check.id}>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={check.checked}
                  disabled={record.status !== "paused"}
                  onChange={(event) => {
                    const result = setRecoveryCheck(
                      record,
                      check.id,
                      event.target.checked,
                    );
                    setPending(null);
                    setError(result.error ?? "");
                    setFeedback("");
                    if (result.record) onChange(result.record);
                  }}
                />
                {check.label}
              </label>
            </div>
          ))}
        </fieldset>
      )}
      <TextArea
        id="operation-reason"
        label="Motivo ficticio de operación"
        value={reason}
        maxLength={300}
        aria-invalid={!!error}
        aria-describedby={error ? "operation-error" : "operation-reason-hint"}
        onChange={(event) => {
          setReason(event.target.value);
          setPending(null);
          setError("");
          setFeedback("");
        }}
      />
      <p id="operation-reason-hint" className="scope-text">
        Solo texto ficticio, sin datos personales ni secretos. El límite es de
        la demo, no una política operativa aprobada.
      </p>
      {error && (
        <div id="operation-error">
          <Notice error>{error}</Notice>
        </div>
      )}
      {feedback && <Notice>{feedback}</Notice>}
      <div className="actions">
        <Button
          disabled={record.status !== "stable" && record.status !== "degraded"}
          onClick={() => prepare("pause")}
        >
          Pausar escenario local
        </Button>
        <Button
          variant="secondary"
          disabled={record.status !== "paused" || !allChecked}
          onClick={() => prepare("review")}
        >
          Revisar recuperación local
        </Button>
        <Button
          variant="secondary"
          disabled={record.status !== "recovering"}
          onClick={() => prepare("resume")}
        >
          Reanudar escenario local
        </Button>
      </div>
      {pending && validPending && (
        <section
          className="reset-confirmation"
          aria-label="Confirmación operativa local"
        >
          <h4>Confirmar: {operationActionLabels[pending.action]}</h4>
          <p>
            {record.name} · Revisión local {record.revision}. Solo este registro
            sintético.
          </p>
          <p className="review-reason-preview">Motivo: {pending.reason}</p>
          <p>
            No pausa/reanuda el CRM real ni restaura servicios. Los controles
            humanos se conservan.
          </p>
          <div className="actions">
            <Button onClick={confirm}>Confirmar acción del escenario</Button>
            <Button
              variant="secondary"
              onClick={() => {
                setPending(null);
                setError("");
              }}
            >
              Cancelar acción del escenario
            </Button>
          </div>
        </section>
      )}
      <details className="workflow-details">
        <summary>Historial operativo local ({record.history.length})</summary>
        <p>
          Solo el escenario seleccionado, en orden de acción. Hora del navegador
          presentada en America/Bogota; no auditoría durable.
        </p>
        {!record.history.length && (
          <p>Sin acciones operativas en este escenario.</p>
        )}
        <ol className="workflow-list">
          {record.history.map((event, index) => (
            <li key={index}>
              <strong>{event.label}</strong>
              <p className="review-reason-preview">{event.reason}</p>
              <time dateTime={event.at}>
                {new Date(event.at).toLocaleString("es-CO", {
                  timeZone: "America/Bogota",
                })}
              </time>
            </li>
          ))}
        </ol>
      </details>
      <details className="workflow-details">
        <summary>Runbook local y puertas de operación</summary>
        <ol className="workflow-list">
          <li>
            Pausar el escenario sintético, conservar su historial y revisar el
            motivo sin tocar Inbox o core.
          </li>
          <li>
            Revisar aislamiento, control humano y el plan específico del
            incidente. No reintentar un envío incierto sin reconciliación
            conectada probada.
          </li>
          <li>
            Revisar el checklist y confirmar la reanudación local por separado.
            Un estado estable en demo no prueba recuperación.
          </li>
        </ol>
        <p>
          Roles y contactos de soporte: sin configurar. SLAs, budgets y RPO/RTO:
          sin configurar; P-012 sigue abierto.
        </p>
        <p>
          Piloto conectado: fase 1, aceptación conectada y autorización
          específica obligatorias. Rotación/revocación upstream,
          backup/restauración/reconciliación, carga y rollback requieren sus
          propios contratos y pruebas en ambiente autorizado.
        </p>
        <div className="actions">
          <Button disabled>Procesar colas reales · Bloqueado</Button>
          <Button variant="secondary" disabled>
            Revocar / rotar secretos reales · Bloqueado
          </Button>
          <Button variant="secondary" disabled>
            Exportación / baja real · Bloqueado
          </Button>
        </div>
      </details>
    </section>
  );
}
