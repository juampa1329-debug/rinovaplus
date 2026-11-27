import { useEffect, useRef, useState } from "react";
import { Button, Notice } from "../shared/ui";
import { ApiError, useInstitution } from "./api";
import { useDraftGuard } from "./drafts";
import { useResource } from "./Settings";

type Item = {
  contact_id: string;
  name: string;
  stage: string;
  signature: string;
  label: string;
  next_action: string;
  quote: string;
  held: boolean;
  no_contact: boolean;
  suppressed?: boolean;
};
type Review = { items: Item[]; ready: number; review: number };
type Batch = {
  operation_id: string;
  items: { contact_id: string; signature: string }[];
};

export function CommercialFollowupReview({ changed }: { changed: () => void }) {
  const { call, session } = useInstitution();
  const [review, setReview] = useState<Review | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [done, setDone] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const pending = useRef<Batch | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useDraftGuard(busy || uncertain);
  if (!session.actions.includes("crm.write")) return null;
  async function load() {
    setBusy(true);
    setError("");
    try {
      const result = await call<Review>(
        "workspace/commercial-followup/preview",
      );
      if (alive.current) {
        setReview(result);
        setConfirmed(false);
        setDone([]);
      }
    } catch (e) {
      if (alive.current)
        setError(
          e instanceof Error ? e.message : "No se pudo revisar el seguimiento.",
        );
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  async function apply() {
    if (!review || !confirmed || busy) return;
    setBusy(true);
    setError("");
    const completed = new Set(done);
    try {
      const items = review.items.filter(
        (i) => !(i.suppressed ?? i.no_contact) && !completed.has(i.contact_id),
      );
      for (let n = 0; n < items.length; n += 10) {
        if (!alive.current) return;
        if (!pending.current)
          pending.current = {
            operation_id: crypto.randomUUID(),
            items: items
              .slice(n, n + 10)
              .map(({ contact_id, signature }) => ({ contact_id, signature })),
          };
        setUncertain(true);
        const batch = pending.current;
        await call("workspace/commercial-followup/apply", "POST", batch);
        batch.items.forEach((i) => completed.add(i.contact_id));
        pending.current = null;
        setUncertain(false);
        if (alive.current) setDone([...completed]);
      }
      if (alive.current) changed();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        pending.current = null;
        setUncertain(false);
      }
      if (alive.current)
        setError(
          e instanceof Error
            ? e.message
            : "Se detuvo el registro. Conserva esta revisión para continuar.",
        );
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <details className="panel" style={{ marginBlock: "1rem", padding: "1rem" }}>
      <summary>Seguimiento de interés y formularios</summary>
      <p>
        Separa interés confirmado, formulario enviado y formulario que la
        persona dice haber completado, y solicitudes de datos de pago.
        Al avanzar a formulario completado o pago, deja de corresponder el
        recordatorio para diligenciar el formulario. Quedan fuera de la reactivación general.
        Registra una tarea por caso y conserva etapas avanzadas o cambios
        posteriores del asesor.
      </p>
      <p>
        No envía mensajes ni acredita inscripción, pago o matrícula. Un sí
        ambiguo queda para revisión, con protección frente a reactivación
        general.
      </p>
      <Button disabled={busy || uncertain} onClick={() => void load()}>
        Revisar interés y formularios
      </Button>
      {review && (
        <>
          <p role="status">
            Casos claros: {review.ready} · Para revisión: {review.review} ·
            Registrados: {done.length}
          </p>
          <div
            className="table-wrap"
            style={{ maxHeight: "24rem", overflow: "auto" }}
          >
            <table>
              <thead>
                <tr>
                  <th>Persona y etapa</th>
                  <th>Avance</th>
                  <th>Próxima acción</th>
                  <th>Evidencia</th>
                </tr>
              </thead>
              <tbody>
                {review.items.map((i) => (
                  <tr key={i.contact_id}>
                    <td>
                      {i.name}
                      <small>{i.stage}</small>
                    </td>
                    <td>
                      {i.label}
                      {i.suppressed && (
                        <p>
                          Excluido de seguimiento comercial · sin nueva tarea
                        </p>
                      )}
                    </td>
                    <td>{i.next_action}</td>
                    <td>
                      <details>
                        <summary>Ver mensaje de origen</summary>
                        <p>{i.quote}</p>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <label>
            <input
              type="checkbox"
              checked={confirmed}
              disabled={busy}
              onChange={(e) => setConfirmed(e.target.checked)}
            />{" "}
            Registrar estos avances, sus tareas y la exclusión de reactivación
            general.
          </label>
          <Button
            disabled={
              busy ||
              !confirmed ||
              review.items.filter((i) => !(i.suppressed ?? i.no_contact))
                .length <= done.length
            }
            onClick={() => void apply()}
          >
            {done.length || uncertain
              ? "Continuar registro de seguimientos"
              : "Registrar seguimientos revisados"}
          </Button>
        </>
      )}
      {busy && <p role="status">Procesando seguimientos…</p>}
      {error && <Notice error>{error}</Notice>}
    </details>
  );
}

export function CommercialFollowupCard({ id }: { id: string }) {
  const data = useResource<{
    progress: {
      label: string;
      next_action: string;
      receipt_state: string | null;
      observed_at: string;
    } | null;
  }>(`workspace/commercial-followup/${encodeURIComponent(id)}`);
  if (data.error)
    return (
      <Notice error>No se pudo consultar el avance del seguimiento.</Notice>
    );
  if (!data.value?.progress) return null;
  const p = data.value.progress;
  return (
    <aside aria-label="Avance comercial" className="notice">
      <strong>{p.label}</strong>
      <p>{p.next_action}</p>
      <p>
        Excluido de reactivación general. Consulta su tarea en CRM → Tareas. La
        inscripción y el pago se verifican por separado.
      </p>
      {p.receipt_state && (
        <small>
          Formulario:{" "}
          {p.receipt_state === "accepted"
            ? "Aceptado por el canal"
            : p.receipt_state === "read"
              ? "Leído"
              : p.receipt_state === "delivered"
                ? "Entregado"
                : "Enviado"}
        </small>
      )}
    </aside>
  );
}
