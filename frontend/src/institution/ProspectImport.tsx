import { useEffect, useRef, useState } from "react";
import { Button, Notice } from "../shared/ui";
import { useInstitution } from "./api";
import { useDraftGuard } from "./drafts";

type Entry = {
  ref: string;
  name: string;
  review: string[];
  [key: string]: unknown;
};
type Bundle = { version: string; batch_id: string; entries: Entry[] };
type Result = {
  ref: string;
  state: "ready" | "review" | "imported";
  reason: string;
  contact_id?: string | null;
};
type Batch = { operation_id: string; batch_id: string; entries: Entry[] };

export function ProspectImport({ changed }: { changed: () => void }) {
  const { call, session } = useInstitution();
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(0);
  const [confirmed, setConfirmed] = useState(false);
  const alive = useRef(true);
  const pending = useRef<Batch | null>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  useDraftGuard(busy);
  const allowed =
    session.actions.includes("crm.write") &&
    session.actions.includes("settings.crm.write");
  if (!allowed) return null;

  const load = async (file: File | undefined) => {
    if (!file) return;
    setError("");
    try {
      if (file.size > 5_000_000) throw Error("El archivo supera 5 MB.");
      const value = JSON.parse(await file.text()) as Bundle;
      if (
        value.version !== "rinovaplus-prospects-v1" ||
        typeof value.batch_id !== "string" ||
        !Array.isArray(value.entries) ||
        !value.entries.length ||
        value.entries.length > 5000 ||
        value.entries.some(
          (e) =>
            !e ||
            typeof e.ref !== "string" ||
            typeof e.name !== "string" ||
            !Array.isArray(e.review),
        ) ||
        new Set(value.entries.map((e) => e.ref)).size !== value.entries.length
      )
        throw Error("Usa el lote de preinscritos previamente clasificado.");
      setBundle(value);
      setResults([]);
      setProgress(0);
      setConfirmed(false);
      pending.current = null;
      setNotice("");
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "No se pudo leer el lote.",
      );
    }
  };

  const run = async (commit: boolean) => {
    if (!bundle || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    setProgress(0);
    const found: Result[] = [];
    try {
      if (commit) {
        await call("workspace/prospect-import/fields", "POST", {
          operation_id: crypto.randomUUID(),
        });
      }
      const entries = commit
        ? bundle.entries.filter((e) =>
            results.some((r) => r.ref === e.ref && r.state === "ready"),
          )
        : bundle.entries;
      for (let offset = 0; offset < entries.length; offset += 10) {
        // Share the existing request budget with Inbox and normal user actions.
        // Stop on 429 rather than automatically replaying an uncertain mutation.
        if (offset > 0) await new Promise((resolve) => setTimeout(resolve, 1200));
        if (!alive.current) return;
        const slice = entries.slice(offset, offset + 10);
        // Preserve the exact attempt after an uncertain HTTP response.
        if (
          !pending.current ||
          JSON.stringify(pending.current.entries) !== JSON.stringify(slice)
        )
          pending.current = {
            operation_id: crypto.randomUUID(),
            batch_id: bundle.batch_id,
            entries: slice,
          };
        const response = await call<{ items: Result[] }>(
          `workspace/prospect-import/${commit ? "commit" : "preview"}`,
          "POST",
          pending.current,
        );
        pending.current = null;
        found.push(...response.items);
        if (!alive.current) return;
        if (commit)
          setResults((current) =>
            current.map((r) => found.find((f) => f.ref === r.ref) ?? r),
          );
        else setResults([...found]);
        setProgress(offset + slice.length);
      }
      if (alive.current) {
        setNotice(
          commit
            ? "Importación terminada. Casos dudosos conservados para revisión. Cero mensajes enviados."
            : "Contraste terminado. Revisa los resultados antes de importar.",
        );
        if (commit) changed();
      }
    } catch (failure) {
      if (alive.current)
        setError(
          failure instanceof Error
            ? failure.message
            : "La operación se detuvo. Los lotes confirmados se conservan.",
        );
    } finally {
      if (alive.current) setBusy(false);
    }
  };
  const ready = results.filter((r) => r.state === "ready").length;
  const held = results.filter((r) => r.state === "review").length;
  const imported = results.filter((r) => r.state === "imported").length;
  return (
    <details className="panel" style={{ marginBlock: "1rem", padding: "1rem" }}>
      <summary>Importar preinscritos al CRM</summary>
      <p>
        Contrasta el lote con los contactos existentes. Los datos compartidos,
        las etapas contradictorias y las coincidencias dudosas quedan para
        revisión. La importación conserva sus fuentes y no concede
        consentimiento comercial.
      </p>
      <label htmlFor="prospect-import-file">
        Lote JSON de preinscritos revisado
      </label>
      <input
        id="prospect-import-file"
        type="file"
        accept=".json,application/json"
        disabled={busy}
        onChange={(e) => void load(e.target.files?.[0])}
      />
      {bundle && <p>{bundle.entries.length} contactos en el lote.</p>}
      <div className="institution-actions">
        <Button disabled={!bundle || busy} onClick={() => void run(false)}>
          Contrastar con CRM
        </Button>
        <Button
          disabled={!results.length || busy}
          variant="quiet"
          onClick={() => {
            const blob = new Blob(
              [
                JSON.stringify(
                  { batch_id: bundle?.batch_id, results },
                  null,
                  2,
                ),
              ],
              { type: "application/json" },
            );
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "revision-importacion-preinscritos.json";
            a.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
          }}
        >
          Descargar revisión y recibos
        </Button>
      </div>
      {results.length > 0 && (
        <>
          <p role="status">
            Listos: {ready} · Para revisión: {held} · Importados: {imported}
          </p>
          <label>
            <input
              type="checkbox"
              checked={confirmed}
              disabled={busy}
              onChange={(e) => setConfirmed(e.target.checked)}
            />{" "}
            Crear sólo contactos nuevos con datos claros y los campos que
            falten. Sin mensajes.
          </label>
          <Button
            disabled={!confirmed || !ready || busy}
            onClick={() => void run(true)}
          >
            Importar contactos revisados
          </Button>
        </>
      )}
      {busy && (
        <p role="status">
          Procesados en esta operación: {progress}. Se trabaja en lotes de hasta
          diez contactos.
        </p>
      )}
      {error && (
        <Notice>
          {error} Puedes volver a contrastar o continuar; no se sobrescriben
          contactos existentes.
        </Notice>
      )}
      {notice && <Notice>{notice}</Notice>}
      {results.length > 0 && (
        <div className="broadcast-table">
          <table>
            <thead>
              <tr>
                <th>Contacto</th>
                <th>Resultado</th>
                <th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {results.slice(0, 100).map((r) => (
                <tr key={r.ref}>
                  <td>
                    {bundle?.entries.find((e) => e.ref === r.ref)?.name}
                    <small>{r.ref}</small>
                  </td>
                  <td>
                    {
                      {
                        ready: "Listo",
                        review: "Para revisión",
                        imported: "Importado",
                      }[r.state]
                    }
                  </td>
                  <td>{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p>
            Primeros 100 resultados. La descarga conserva el listado completo.
          </p>
        </div>
      )}
    </details>
  );
}
