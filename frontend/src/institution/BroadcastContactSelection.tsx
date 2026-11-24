import { useState } from "react";
import { Button } from "../shared/ui";

export function BroadcastContactSelection({
  change,
}: {
  change: (ids: string[]) => void;
}) {
  const [pending, setPending] = useState<string[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function load(file?: File) {
    setPending(null);
    setError("");
    if (!file) return;
    setLoading(true);
    try {
      if (file.size > 1_000_000) throw Error("El archivo supera 1 MB.");
      const data = JSON.parse(await file.text()) as {
        version?: string;
        contact_ids?: unknown;
      };
      if (
        data.version !== "rinovaplus-broadcast-selection-v1" ||
        !Array.isArray(data.contact_ids) ||
        !data.contact_ids.length ||
        data.contact_ids.length > 5000 ||
        data.contact_ids.some(
          (id) =>
            typeof id !== "string" ||
            !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(
              id,
            ),
        ) ||
        new Set(data.contact_ids).size !== data.contact_ids.length
      )
        throw Error(
          "Usa una selección revisada de RinovaPlus con hasta 5.000 contactos únicos.",
        );
      setPending(data.contact_ids);
    } catch (e) {
      setError(
        e instanceof SyntaxError
          ? "No se pudo leer el archivo de selección."
          : (e as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <details className="broadcast-contact-import">
      <summary>Cargar selección revisada de contactos</summary>
      <p>
        Reemplaza las personas elegidas con un listado revisado del CRM. Se
        mantienen los filtros de programa, la autorización y las exclusiones de
        envío.
      </p>
      <label htmlFor="broadcast-contact-selection-file">
        Archivo de selección de contactos
      </label>
      <input
        id="broadcast-contact-selection-file"
        type="file"
        accept=".json,application/json"
        disabled={loading}
        onChange={(e) => void load(e.target.files?.[0])}
      />
      {error && <p role="alert">{error}</p>}
      {pending && (
        <Button
          variant="secondary"
          onClick={() => {
            change(pending);
            setPending(null);
          }}
        >
          Aplicar selección de {pending.length} contactos
        </Button>
      )}
    </details>
  );
}
