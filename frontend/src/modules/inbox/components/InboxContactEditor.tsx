import { useEffect, useState } from "react";
import type { Client } from "../../../shared/demo";
import type { CrmConfig } from "../../../shared/crm";
import { allTags, validateCrmClient } from "../../../shared/crm";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import { fetchCatalog } from "../../catalog/api/catalog";
import type { Program } from "../../catalog/model";
import { ClientFields } from "../../clients/components/ClientFields";
import { Badge, Button, Notice } from "../../../shared/ui";
import { useRuntime, usePermission } from "../../../shared/runtimeCapabilities";

export function InboxContactEditor({
  saved,
  config,
  busy,
  onSave,
  onOpenContact,
}: {
  saved: Client;
  config: CrmConfig;
  busy: boolean;
  onSave: (client: Client) => Promise<void>;
  onOpenContact?: (id: string) => void;
}) {
  const { features } = useRuntime().capabilities;
  const canWrite = usePermission("crm.write");
  const [drafts, setDrafts] = useWorkspaceField("clients", "drafts");
  const client = drafts[saved.id] ?? saved;
  const [programs, setPrograms] = useState<Program[]>([]);
  const [catalogError, setCatalogError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (!features.academic) return;
    const controller = new AbortController();
    void (async () => {
      try {
        const values: Program[] = [];
        for (let offset = 0; offset <= 10000; offset += 25) {
          const page = await fetchCatalog(
            "programs",
            "",
            offset,
            controller.signal,
          );
          values.push(...(page.items as Program[]));
          if (!page.page.hasMore) break;
        }
        if (!controller.signal.aborted) setPrograms(values);
      } catch {
        if (!controller.signal.aborted)
          setCatalogError(
            "El catálogo de programas no está disponible. Se conserva el programa guardado.",
          );
      }
    })();
    return () => controller.abort();
  }, [features.academic]);
  function setDraft(value: Client) {
    setDrafts((previous) => ({ ...previous, [saved.id]: value }));
    setFeedback("");
  }
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    const problems = validateCrmClient(client, config, saved);
    setFieldErrors(problems);
    setError(Object.values(problems)[0] ?? "");
    if (Object.keys(problems).length) return;
    const submitted = {
      ...client,
      name: client.name.trim(),
      phone: client.phone.trim(),
    };
    setDraft(submitted);
    try {
      await onSave(submitted);
      setDrafts((previous) => {
        if (JSON.stringify(previous[saved.id]) !== JSON.stringify(submitted))
          return previous;
        const next = { ...previous };
        delete next[saved.id];
        return next;
      });
      setFeedback("Ficha guardada correctamente.");
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "No se pudo guardar. El borrador se conserva.",
      );
    }
  }
  return (
    <form
      onSubmit={save}
      noValidate
      className="inbox-contact-editor"
      aria-label="Ficha CRM compartida"
    >
      {features.advancedCrm && <h3>Editar ficha CRM</h3>}
      <Badge>
        {drafts[saved.id] ? "Cambios sin guardar" : "Ficha guardada"}
      </Badge>
      <p className="scope-text">Campos compartidos con Clientes.</p>
      {error && <Notice error>{error}</Notice>}
      {feedback && <Notice>{feedback}</Notice>}
      <fieldset className="client-editor-fields" disabled={busy || !canWrite}>
        <ClientFields
          client={client}
          setDraft={setDraft}
          config={config}
          programs={programs}
          catalogError={catalogError}
          tags={allTags(config, [saved])}
          stages={[
            ...new Set([
              ...config.stages
                .filter((item) => item.active !== false)
                .map((item) => item.label),
              saved.stage,
            ]),
          ]}
          fieldErrors={fieldErrors}
          setFeedback={setFeedback}
          onOpenContact={onOpenContact}
        />
        <div className="actions">
          <Button type="submit">
            {busy ? "Guardando ficha…" : "Guardar ficha"}
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setDrafts((previous) => {
                const next = { ...previous };
                delete next[saved.id];
                return next;
              });
              setFieldErrors({});
              setError("");
              setFeedback("");
            }}
          >
            Descartar cambios
          </Button>
        </div>
      </fieldset>
    </form>
  );
}
