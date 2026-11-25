import { useState } from "react";
import { Button } from "../shared/ui";

export function BroadcastContactSelection({
  change,
}: {
  change: (ids: string[], identityIds?: string[]) => void;
}) {
  const [pending, setPending] = useState<{
    contacts: string[];
    identities?: string[];
  } | null>(null);
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
        identity_ids?: unknown;
      };
      const routed = data.version === "rinovaplus-broadcast-routes-v1";
      const validId = (id: unknown) =>
        typeof id === "string" &&
        /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(
          id,
        );
      if (
        (!routed && data.version !== "rinovaplus-broadcast-selection-v1") ||
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
        new Set(data.contact_ids).size !== data.contact_ids.length ||
        (routed &&
          (!Array.isArray(data.identity_ids) ||
            !data.identity_ids.length ||
            data.identity_ids.length > data.contact_ids.length ||
            data.identity_ids.some((id) => !validId(id)) ||
            new Set(data.identity_ids).size !== data.identity_ids.length)) ||
        (!routed && data.identity_ids !== undefined)
      )
        throw Error(
          "Usa una selección revisada de RinovaPlus con hasta 5.000 contactos únicos.",
        );
      setPending({
        contacts: data.contact_ids,
        identities: routed ? (data.identity_ids as string[]) : undefined,
      });
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
            if (pending.identities)
              change(pending.contacts, pending.identities);
            else change(pending.contacts);
            setPending(null);
          }}
        >
          Aplicar selección de {pending.contacts.length} contactos
        </Button>
      )}
      {pending?.identities && (
        <p>
          La selección fija {pending.identities.length} destinos de la cuenta.
          Cada ficha recibe como máximo un mensaje en esta campaña.
        </p>
      )}
    </details>
  );
}
