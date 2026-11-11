import { useEffect, useRef, useState } from "react";
import {
  contactMergeApi,
  type ContactGroup,
  type MergePreview,
} from "../api/contactMergeApi";
import { clientsApi, ClientsError } from "../../clients/api/clientsApi";
import type { Client } from "../../../shared/demo";
import { useWorkspaceField } from "../../../shared/workspaceSession";
import { Button, Notice } from "../../../shared/ui";
import {
  institutionalIdentityApi,
  type IdentityCatalog,
} from "../api/institutionalIdentity";

const labels: Record<string, string> = {
  name: "Nombre visible",
  phone: "Teléfono de la ficha",
  city: "Ciudad",
  schedule: "Jornada",
  stage: "Etapa",
  tags: "Etiquetas",
  notes: "Notas",
  type: "Tipo de contacto",
  interests: "Intereses",
  program: "Programa de interés",
  "profile.givenNames": "Nombres informados",
  "profile.firstSurname": "Primer apellido",
  "profile.secondSurname": "Segundo apellido",
  "profile.email": "Correo",
  "profile.aspirationPeriodId": "Período aspirado",
  "profile.document": "Tipo y documento",
};
function display(value: unknown): string {
  if (value === null || value === undefined || value === "")
    return "Sin informar";
  if (typeof value === "object")
    return (
      Object.values(value)
        .filter((v) => v !== null && v !== "")
        .join(" · ") || "Sin informar"
    );
  return String(value);
}

export function ContactMerge({
  contactId,
  refresh,
  onConfirmed,
  onOpenContact,
}: {
  contactId: string;
  refresh?: string | number;
  onConfirmed?: () => void;
  onOpenContact?: (id: string) => void;
}) {
  const [drafts] = useWorkspaceField("clients", "drafts");
  const [groupResult, setGroupResult] = useState<{
    key: string;
    value: ContactGroup;
  } | null>(null);
  const [failedGroupKey, setFailedGroupKey] = useState("");
  const [catalog, setCatalog] = useState<IdentityCatalog | null>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Client[]>([]);
  const [source, setSource] = useState("");
  const [undoId, setUndoId] = useState("");
  const [choices, setChoices] = useState<Record<string, string>>({});
  const [storedPreview, setPreview] = useState<MergePreview | null>(null);
  const [previewScope, setPreviewScope] = useState("");
  const [previewKey, setPreviewKey] = useState("");
  const [confirmed, setConfirmed] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [generation, setGeneration] = useState(0);
  const groupKey = JSON.stringify([contactId, refresh, generation]);
  const group = groupResult?.key === groupKey ? groupResult.value : null;
  const groupError = failedGroupKey === groupKey;
  const preview = previewScope === groupKey ? storedPreview : null;
  const intent = useRef<{ key: string; operationId: string } | null>(null);
  const previewController = useRef<AbortController | null>(null);
  const undo = Boolean(undoId);
  useEffect(() => {
    const controller = new AbortController();
    void contactMergeApi
      .group(contactId, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted)
          setGroupResult({ key: groupKey, value });
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setFailedGroupKey(groupKey);
          setError("No se pudo consultar la relación de fichas.");
        }
      });
    return () => {
      controller.abort();
      previewController.current?.abort();
    };
  }, [contactId, groupKey]);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void institutionalIdentityApi
      .catalog(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setCatalog(value);
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError(
            "El catálogo institucional no está disponible. No confirme valores de identidad sin revisar sus etiquetas.",
          );
      });
    return () => controller.abort();
  }, [open]);
  useEffect(() => {
    if (!open || undo || query.trim().length < 3) {
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void clientsApi
        .list(query, "Todas", "Todas", controller.signal)
        .then((value) => {
          if (!controller.signal.aborted)
            setResults(
              value.clients.filter(
                (c) => !group?.memberContactIds.includes(c.id),
              ),
            );
        })
        .catch(() => {
          if (!controller.signal.aborted)
            setError("No se pudo buscar la ficha de origen.");
        });
    }, 250);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, group, open, undo]);
  const request = undo
    ? { mergeId: undoId, choices }
    : {
        sourceContactId: source,
        targetContactId: group?.primaryContactId,
        choices,
      };
  const requestKey = JSON.stringify([groupKey, request]);
  const previewCurrent = previewKey === requestKey;
  useEffect(() => () => previewController.current?.abort(), [requestKey]);
  function fieldDisplay(key: string, value: unknown) {
    if (key === "profile.aspirationPeriodId" && value != null)
      return (
        catalog?.periods.items.find((period) => period.id === value)?.label ??
        "Período no disponible en catálogo"
      );
    if (
      key === "profile.document" &&
      value &&
      typeof value === "object" &&
      "documentTypeId" in value
    ) {
      const pair = value as { documentTypeId: number | null; document: string };
      if (pair.documentTypeId == null) return "Sin informar";
      const documentType = catalog?.documentTypes.find(
        (item) => item.id === pair.documentTypeId,
      );
      return `${documentType ? `${documentType.code} · ${documentType.label}` : "Tipo no disponible en catálogo"} · ${pair.document}`;
    }
    if (
      key === "program" &&
      value &&
      typeof value === "object" &&
      "program" in value
    )
      return display(value.program);
    return display(value);
  }
  const blockedDraft = Boolean(
    group && [...group.memberContactIds, source].some((id) => drafts[id]),
  );
  async function inspect() {
    setBusy(true);
    setError("");
    setConfirmed("");
    previewController.current?.abort();
    const controller = new AbortController();
    previewController.current = controller;
    try {
      const value = await contactMergeApi.preview(
        request,
        undo,
        controller.signal,
      );
      if (!controller.signal.aborted) {
        setPreview(value);
        setPreviewScope(groupKey);
        setPreviewKey(requestKey);
      }
    } catch (failure) {
      if (!controller.signal.aborted) {
        setPreview(null);
        setError(
          failure instanceof Error
            ? failure.message
            : "No se pudo revisar la operación.",
        );
      }
    } finally {
      if (previewController.current === controller) setBusy(false);
    }
  }
  async function commit() {
    if (
      !preview ||
      !previewCurrent ||
      confirmed !== preview.fingerprint ||
      blockedDraft ||
      busy
    )
      return;
    const body = {
      ...request,
      expectedFingerprint: preview.fingerprint,
      ...(undo ? { confirmedUndo: true } : { confirmedSamePerson: true }),
    };
    const key = JSON.stringify(body);
    if (intent.current?.key !== key)
      intent.current = { key, operationId: crypto.randomUUID() };
    setBusy(true);
    setError("");
    try {
      await contactMergeApi.commit(
        { ...body, operationId: intent.current.operationId },
        undo,
      );
      intent.current = null;
      setOpen(false);
      setPreview(null);
      setConfirmed("");
      setChoices({});
      setSource("");
      setUndoId("");
      setGeneration((v) => v + 1);
      onConfirmed?.();
    } catch (failure) {
      setConfirmed("");
      if (
        failure instanceof ClientsError &&
        [409, 422].includes(failure.status)
      )
        setPreviewKey("");
      setError(
        failure instanceof Error
          ? failure.message
          : "No se pudo confirmar la operación.",
      );
    } finally {
      setBusy(false);
    }
  }
  function reset() {
    setPreview(null);
    setChoices({});
    setConfirmed("");
    setError("");
  }
  return (
    <section
      className="mini-crm contact-merge"
      aria-label="Unificación reversible de fichas"
    >
      <h3>Ficha principal y conversaciones</h3>
      {error && <Notice>{error}</Notice>}
      {group ? (
        <>
          <p>
            {group.memberContactIds.length > 1
              ? `${group.memberContactIds.length} fichas conservadas · principal: ${group.primaryContact.name || "Sin nombre"}`
              : "Esta ficha conserva su identidad y conversación originales."}
          </p>
          {group.members.map((member) => (
            <div key={member.contactId} className="scope-note">
              <strong>
                {member.name || "Sin nombre"}
                {member.contactId === group.primaryContactId
                  ? " · Principal"
                  : " · Origen"}
              </strong>
              <p>
                {member.phone || "Sin teléfono"} · {member.channel}
              </p>
              {onOpenContact && (
                <Button
                  variant="quiet"
                  onClick={() => onOpenContact(member.contactId)}
                >
                  Abrir conversación de origen
                </Button>
              )}
            </div>
          ))}
          <Button
            variant="quiet"
            onClick={() => {
              setOpen(!open);
              reset();
              setUndoId("");
            }}
          >
            Revisar posible unificación
          </Button>
          {group.links.map((link) => (
            <Button
              key={link.mergeId}
              variant="quiet"
              onClick={() => {
                reset();
                setUndoId(link.mergeId);
                setOpen(true);
              }}
            >
              Revisar reversión de relación
            </Button>
          ))}
        </>
      ) : groupError ? (
        <Button
          variant="secondary"
          onClick={() => {
            setError("");
            setGeneration((value) => value + 1);
          }}
        >
          Reintentar relación de fichas
        </Button>
      ) : (
        <p>Cargando relación de fichas…</p>
      )}
      {open && group && (
        <div>
          <p>
            La comparación es de solo lectura. Unificar conserva los mensajes,
            el teléfono, el canal, los responsables, las tareas, el SLA y la
            memoria de cada conversación. No combina estudiantes ni confirma
            identidad académica.
          </p>
          {!undo && (
            <>
              <label className="field merge-field">
                Buscar ficha de origen (mínimo 3 caracteres)
                <input
                  disabled={busy}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setResults([]);
                    setSource("");
                    reset();
                  }}
                />
              </label>
              <label className="field merge-field">
                Ficha de origen
                <select
                  disabled={busy}
                  value={source}
                  onChange={(e) => {
                    setSource(e.target.value);
                    reset();
                  }}
                >
                  <option value="">Seleccione una ficha real</option>
                  {results.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name || c.phone || "Sin nombre"}
                    </option>
                  ))}
                </select>
              </label>
            </>
          )}
          <Button
            variant="secondary"
            disabled={busy || (!undo && !source)}
            onClick={() => void inspect()}
          >
            Comparar impacto sin modificar datos
          </Button>
          {preview && (
            <>
              {preview.laterConfirmations && (
                <Notice>
                  Hay confirmaciones posteriores. Se conservarán los valores
                  actuales salvo selección explícita.
                </Notice>
              )}
              {preview.blockedReason && (
                <Notice>
                  Hay un análisis reservado. Espere a que termine y actualice la
                  comparación.
                </Notice>
              )}
              {preview.validationError && (
                <Notice>
                  Los valores elegidos no cumplen el catálogo o la validación
                  actuales. Elija conservar valores válidos y actualice la
                  comparación.
                </Notice>
              )}
              {!previewCurrent && (
                <Notice>
                  Actualice la comparación para revisar los valores elegidos
                  antes de confirmar.
                </Notice>
              )}
              <p>
                Principal: {preview.members[0]?.name || "Sin nombre"}. Origen:{" "}
                {preview.source.name || "Sin nombre"}.
              </p>
              <fieldset disabled={busy}>
                <legend>Elegir los valores de la ficha principal</legend>
                {preview.fields.map((field) => (
                  <label className="field merge-field" key={field.key}>
                    {labels[field.key] ||
                      `Campo personalizado: ${field.key.slice(7)}`}
                    <select
                      value={choices[field.key] ?? field.selected}
                      onChange={(e) => {
                        setChoices((previous) => ({
                          ...previous,
                          [field.key]: e.target.value,
                        }));
                        setConfirmed("");
                      }}
                    >
                      <option value={undo ? "current" : "target"}>
                        {undo ? "Conservar actual" : "Principal"}:{" "}
                        {fieldDisplay(field.key, field.current)}
                      </option>
                      <option value={undo ? "before" : "source"}>
                        {undo ? "Restaurar anterior" : "Origen"}:{" "}
                        {fieldDisplay(field.key, field.alternative)}
                      </option>
                    </select>
                  </label>
                ))}
              </fieldset>
              {blockedDraft && (
                <Notice>
                  Guarde o descarte los borradores de las fichas participantes
                  antes de confirmar. La conversación y sus borradores se
                  conservan.
                </Notice>
              )}
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  disabled={busy || !previewCurrent}
                  checked={Boolean(
                    previewCurrent && confirmed === preview.fingerprint,
                  )}
                  onChange={(e) =>
                    setConfirmed(
                      e.target.checked && previewCurrent
                        ? preview.fingerprint
                        : "",
                    )
                  }
                />
                {undo
                  ? "Confirmo la reversión y los valores elegidos para la ficha principal."
                  : "Verifiqué que ambas fichas corresponden a la misma persona y confirmo los valores elegidos."}
              </label>
              <Button
                disabled={
                  busy ||
                  !previewCurrent ||
                  confirmed !== preview.fingerprint ||
                  blockedDraft ||
                  Boolean(preview.blockedReason) ||
                  Boolean(preview.validationError)
                }
                onClick={() => void commit()}
              >
                {undo ? "Confirmar reversión" : "Confirmar unificación CRM"}
              </Button>
            </>
          )}
          <Button
            variant="quiet"
            disabled={busy}
            onClick={() => {
              setOpen(false);
              reset();
            }}
          >
            Cerrar revisión
          </Button>
        </div>
      )}
    </section>
  );
}
