import { useEffect, useRef, useState } from "react";
import { Button, Notice } from "../shared/ui";
import { useInstitution } from "./api";
import { useDraftGuard } from "./drafts";

type Item = { contact_id: string; signature: string };
type Review = {
  groups: {
    source: string;
    programs: string[];
    count: number;
    review: number;
    reason: string;
  }[];
  items: Item[];
  ready: number;
  review: number;
};
type Batch = { operation_id: string; items: Item[] };

export function MasterclassInterests({ changed }: { changed: () => void }) {
  const { call, session } = useInstitution();
  const [review, setReview] = useState<Review | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState<string[]>([]);
  const pending = useRef<Batch | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useDraftGuard(busy);
  if (!session.actions.includes("crm.write")) return null;

  async function load() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await call<Review>(
        "workspace/masterclass-interests/preview",
      );
      if (alive.current) {
        setReview(result);
        setUpdated([]);
        setConfirmed(false);
        pending.current = null;
      }
    } catch (failure) {
      if (alive.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "No se pudo revisar los intereses.",
        );
    } finally {
      if (alive.current) setBusy(false);
    }
  }

  async function run() {
    if (!review || !confirmed || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    const done = new Set(updated);
    try {
      const remaining = review.items.filter((i) => !done.has(i.contact_id));
      for (let offset = 0; offset < remaining.length; offset += 10) {
        if (offset > 0)
          await new Promise((resolve) => setTimeout(resolve, 1200));
        if (!alive.current) return;
        const items = remaining.slice(offset, offset + 10);
        if (
          !pending.current ||
          JSON.stringify(pending.current.items) !== JSON.stringify(items)
        )
          pending.current = { operation_id: crypto.randomUUID(), items };
        const result = await call<{
          items: { contact_id: string; state: string }[];
        }>("workspace/masterclass-interests/apply", "POST", pending.current);
        pending.current = null;
        result.items
          .filter((i) => i.state === "updated")
          .forEach((i) => done.add(i.contact_id));
        if (alive.current) setUpdated([...done]);
      }
      if (alive.current) {
        setNotice(
          "Intereses actualizados. El antecedente de masterclass quedó guardado en cada ficha.",
        );
        changed();
      }
    } catch (failure) {
      if (alive.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "La actualización se detuvo. Los lotes confirmados se conservan.",
        );
    } finally {
      if (alive.current) setBusy(false);
    }
  }

  return (
    <details className="panel" style={{ marginBlock: "1rem", padding: "1rem" }}>
      <summary>Relacionar masterclasses con programas</summary>
      <p>
        Actualiza el interés comercial con los programas relacionados. La IA
        ofrecerá las opciones de la escuela y preguntará cuál interesa,
        conservando la masterclass original como antecedente.
      </p>
      <Button disabled={busy} onClick={() => void load()}>
        Revisar intereses de masterclass
      </Button>
      {review && (
        <>
          <p role="status">
            Listos: {review.ready} · Para revisión: {review.review} ·
            Actualizados: {updated.length}
          </p>
          <div
            className="table-wrap"
            style={{
              maxHeight: "22rem",
              overflow: "auto",
              marginBlock: "1rem",
            }}
          >
            <table>
              <thead>
                <tr>
                  <th>Interés original</th>
                  <th>Opciones relacionadas</th>
                  <th>Contactos</th>
                </tr>
              </thead>
              <tbody>
                {review.groups.map((g) => (
                  <tr key={g.source}>
                    <td>{g.source}</td>
                    <td>
                      {g.programs.join(" · ") || "Pendiente de relación"}
                      {g.reason && <p>{g.reason}</p>}
                    </td>
                    <td>{g.count}</td>
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
            Ofrecer estos programas relacionados, dejando la elección al
            contacto.
          </label>
          <div className="institution-actions">
            <Button
              disabled={busy || !confirmed || updated.length >= review.ready}
              onClick={() => void run()}
            >
              {updated.length
                ? "Continuar actualización de intereses"
                : "Actualizar intereses revisados"}
            </Button>
          </div>
        </>
      )}
      {busy && <Notice>Procesando intereses…</Notice>}
      {notice && <p role="status">{notice}</p>}
      {error && <Notice error>{error}</Notice>}
    </details>
  );
}
