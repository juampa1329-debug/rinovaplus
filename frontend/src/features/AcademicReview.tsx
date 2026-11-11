import { useRef, useState } from "react";
import { programs } from "../shared/demo";
import {
  filterReviews,
  reviewStatusLabels,
  transitionReview,
  type ReviewAction,
  type ReviewRecord,
} from "../shared/review";
import {
  Badge,
  Button,
  EmptyState,
  Field,
  Notice,
  SelectField,
} from "../shared/ui";

export function AcademicReview({
  records,
  onChange,
}: {
  records: ReviewRecord[];
  onChange: (record: ReviewRecord) => void;
}) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [program, setProgram] = useState("all");
  const [selected, setSelected] = useState(records[0]?.id ?? "");
  const [contextRevision, setContextRevision] = useState(0);
  const visible = filterReviews(records, query, status, program);
  const record = visible.find((item) => item.id === selected);
  function invalidate() {
    setContextRevision((value) => value + 1);
  }
  return (
    <>
      <Notice>
        Revisión humana LOCAL con fixtures independientes. El formulario no
        alimenta esta cola. No hay solicitudes recibidas, decisiones académicas
        reales ni registro SIIE.
      </Notice>
      <div className="clients-grid review-grid">
        <section
          className="panel client-list"
          aria-labelledby="review-queue-title"
        >
          <div className="panel-heading">
            <h2 id="review-queue-title">
              Cola de revisión{" "}
              <span className="count">
                {visible.length}/{records.length}
              </span>
            </h2>
            <Badge>Solo demo</Badge>
          </div>
          <div className="filter-stack">
            <Field
              id="review-search"
              label="Buscar casos ficticios"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                invalidate();
              }}
            />
            <SelectField
              id="review-status"
              label="Filtrar estado de revisión"
              value={status}
              options={[
                { value: "all", label: "Todos los estados" },
                ...Object.entries(reviewStatusLabels).map(([value, label]) => ({
                  value,
                  label,
                })),
              ]}
              onChange={(event) => {
                setStatus(event.target.value);
                invalidate();
              }}
            />
            <SelectField
              id="review-program"
              label="Filtrar programa demo"
              value={program}
              options={[
                { value: "all", label: "Todos los programas" },
                ...programs,
              ]}
              onChange={(event) => {
                setProgram(event.target.value);
                invalidate();
              }}
            />
            <Button
              variant="quiet"
              onClick={() => {
                setQuery("");
                setStatus("all");
                setProgram("all");
                invalidate();
              }}
            >
              Restablecer filtros de revisión
            </Button>
          </div>
          <ul className="record-list">
            {visible.map((item) => (
              <li key={item.id}>
                <button
                  className={`record${selected === item.id ? " selected" : ""}`}
                  aria-pressed={selected === item.id}
                  onClick={() => {
                    setSelected(item.id);
                    invalidate();
                  }}
                >
                  <span className="record-copy">
                    <strong>{item.name}</strong>
                    <small>
                      {item.id} · {item.program}
                    </small>
                    <span>{reviewStatusLabels[item.status]}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {!visible.length && (
            <EmptyState title="Sin casos coincidentes">
              Cambie o restablezca los filtros. No se consulta ninguna fuente
              externa.
            </EmptyState>
          )}
        </section>
        {record ? (
          <ReviewDetail
            key={`${record.id}-${record.history.length}-${contextRevision}`}
            record={record}
            onChange={onChange}
          />
        ) : (
          <section className="panel client-detail">
            <EmptyState title="Seleccione un caso visible">
              Los filtros se conservan. El detalle y cualquier confirmación
              anterior quedan ocultos hasta seleccionar un caso de la lista.
            </EmptyState>
          </section>
        )}
      </div>
    </>
  );
}

function ReviewDetail({
  record,
  onChange,
}: {
  record: ReviewRecord;
  onChange: (record: ReviewRecord) => void;
}) {
  const [action, setAction] = useState<ReviewAction>("reviewed");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState<ReviewAction | null>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const terminal = ["reviewed", "observed", "rejected"].includes(record.status);
  function prepare(event: React.FormEvent) {
    event.preventDefault();
    const nextAction = terminal ? "reopen" : action;
    const result = transitionReview(record, nextAction, reason);
    setError(result.error ?? "");
    if (result.error) {
      reasonRef.current?.focus();
      return;
    }
    setPending(nextAction);
  }
  function confirm() {
    if (!pending) return;
    const result = transitionReview(record, pending, reason);
    if (result.error) {
      setError(result.error);
      setPending(null);
      return;
    }
    setPending(null);
    onChange(result.record!);
  }
  return (
    <section
      className="panel client-detail review-detail"
      aria-labelledby="review-detail-title"
    >
      <div className="panel-heading">
        <h2 id="review-detail-title">{record.name}</h2>
        <Badge>{reviewStatusLabels[record.status]}</Badge>
      </div>
      <p className="scope-text">
        {record.id} · Datos sintéticos. Campos provisionales, no requisitos
        académicos aceptados.
      </p>
      <dl className="planned-sections">
        <div>
          <dt>Nombre ficticio</dt>
          <dd>{record.name}</dd>
        </div>
        <div>
          <dt>Correo de ejemplo</dt>
          <dd>{record.email || "Sin dato · Fixture incompleto"}</dd>
        </div>
        <div>
          <dt>Programa demo</dt>
          <dd>{record.program}</dd>
        </div>
        <div>
          <dt>Jornada demo</dt>
          <dd>{record.schedule}</dd>
        </div>
        <div>
          <dt>Confirmación de datos ficticios</dt>
          <dd>
            {record.syntheticConfirmed
              ? "Sí · No es consentimiento legal"
              : "No confirmada"}
          </dd>
        </div>
      </dl>
      <Notice>
        Revisada significa revisión humana completada solo en esta demo: no
        aprobación, elegibilidad, matrícula o pago. Observar o rechazar no
        notifica al aspirante.
      </Notice>
      {record.status === "pending" && (
        <Button
          onClick={() =>
            onChange(transitionReview(record, "start", "").record!)
          }
        >
          Iniciar revisión local
        </Button>
      )}
      {record.status !== "pending" && !pending && (
        <form onSubmit={prepare} noValidate className="review-action-form">
          <h3>
            {terminal
              ? "Reabrir sin borrar el historial"
              : "Registrar resultado humano local"}
          </h3>
          {!terminal && (
            <SelectField
              id="review-action"
              label="Resultado de revisión local"
              value={action}
              options={[
                { value: "reviewed", label: "Marcar revisada · No aprobar" },
                { value: "observed", label: "Observar · Demo" },
                { value: "rejected", label: "Rechazar · Demo" },
              ]}
              onChange={(event) => {
                setAction(event.target.value as ReviewAction);
                setError("");
              }}
            />
          )}
          <div className="field">
            <label htmlFor="review-reason">Motivo de la acción local</label>
            <textarea
              ref={reasonRef}
              id="review-reason"
              rows={3}
              maxLength={600}
              value={reason}
              aria-invalid={!!error}
              aria-describedby={
                error ? "review-reason-error" : "review-reason-hint"
              }
              onChange={(event) => {
                setReason(event.target.value);
                setError("");
              }}
            />
            <small id="review-reason-hint">
              Obligatorio: 5–600 caracteres. Solo texto ficticio, sin datos
              personales.
            </small>
            {error && (
              <small
                className="field-error"
                id="review-reason-error"
                role="alert"
              >
                {error}
              </small>
            )}
          </div>
          <Button type="submit">
            {terminal ? "Revisar reapertura local" : "Revisar acción local"}
          </Button>
        </form>
      )}
      {pending && (
        <section
          className="reset-confirmation"
          aria-label="Confirmar acción de revisión local"
        >
          <h3>
            {pending === "reopen"
              ? "Reabrir como pendiente"
              : reviewStatusLabels[pending === "start" ? "in_review" : pending]}
          </h3>
          <p>
            {record.name} · {record.id}. Estado actual:{" "}
            {reviewStatusLabels[record.status]}.
          </p>
          <p className="review-reason-preview">{reason.trim()}</p>
          <p>
            Solo cambiará el estado temporal de este caso. El historial previo
            se conserva; no hay aprobación ni acción externa.
          </p>
          <div className="actions">
            <Button onClick={confirm}>Confirmar acción local</Button>
            <Button variant="secondary" onClick={() => setPending(null)}>
              Volver a editar motivo
            </Button>
          </div>
        </section>
      )}
      <section
        className="operational-context"
        aria-labelledby="review-history-title"
      >
        <h3 id="review-history-title">Historial temporal del caso</h3>
        <p className="scope-text">
          No es auditoría durable. Las entradas del fixture no tienen fecha
          real.
        </p>
        <ol className="workflow-list">
          {record.history.map((event, index) => (
            <li key={index}>
              <strong>{reviewStatusLabels[event.status]}</strong>
              <p className="review-reason-preview">{event.reason}</p>
              <small>
                {event.actor} ·{" "}
                {event.at
                  ? new Date(event.at).toLocaleString("es-CO")
                  : "Sin fecha · Fixture"}
              </small>
            </li>
          ))}
        </ol>
      </section>
      <div className="operational-context">
        <h3>Registro académico bloqueado</h3>
        <p>
          Fase 1, contrato core P-011 y autorización específica pendientes.
          Ningún resultado local habilita escritura SIIE.
        </p>
        <Button disabled variant="secondary">
          Registro SIIE no autorizado
        </Button>
      </div>
    </section>
  );
}
