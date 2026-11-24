import { useRef, useState } from "react";
import { Button, Notice } from "../shared/ui";
import { ApiError, useInstitution } from "./api";
import { useDraftGuard } from "./drafts";

type Bundle = {
  version: string;
  program: "logistica" | "aduanas" | "all";
  contact_ids: string[];
  review_count?: number;
};

export function BroadcastProspectSetup({
  account, changed,
}: { account: string; changed: () => Promise<unknown> }) {
  const { call, session } = useInstitution();
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [evidence, setEvidence] = useState("");
  const [origin, setOrigin] = useState("");
  const [expires, setExpires] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [count, setCount] = useState(0);
  const [enabledCount, setEnabledCount] = useState(0);
  const [reviewCount, setReviewCount] = useState(0);
  const [error, setError] = useState("");
  const [hasPending, setHasPending] = useState(false);
  const pending = useRef<Record<string, unknown> | null>(null);
  const locked = busy || !!count || hasPending;
  useDraftGuard(busy || hasPending);
  if (!session.actions.includes("crm.write") || !session.actions.includes("inbox.write")) return null;
  const load = async (file?: File) => {
    if (!file) return;
    setError("");
    try {
      if (file.size > 1_000_000) throw Error("El lote supera 1 MB.");
      const value = JSON.parse(await file.text()) as Bundle;
      if (value.version !== "rinovaplus-whatsapp-prospects-v1" ||
        !["logistica", "aduanas", "all"].includes(value.program) ||
        !Array.isArray(value.contact_ids) || !value.contact_ids.length ||
        value.contact_ids.length > 5000 ||
        value.contact_ids.some(v => typeof v !== "string" || !/^[a-f0-9-]{36}$/i.test(v)) ||
        new Set(value.contact_ids).size !== value.contact_ids.length)
        throw Error("Usa un lote de preinscritos revisado para este programa.");
      setBundle(value); setCount(0); setDone(false); setConfirmed(false);
      setEnabledCount(0); setReviewCount(0);
      pending.current = null;
      setHasPending(false);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "No se pudo leer el lote.");
    }
  };
  const loadAll = async () => {
    setBusy(true); setError("");
    try {
      const value = await call<Bundle>(`broadcasts/accounts/${account}/prospects`);
      setBundle(value); setCount(0); setDone(false); setConfirmed(false);
      setEnabledCount(0); setReviewCount(value.review_count || 0);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "No se pudo cargar el CRM.");
    } finally { setBusy(false); }
  };
  const run = async () => {
    if (!bundle || busy || !confirmed) return;
    setBusy(true); setError("");
    try {
      for (let offset = count; offset < bundle.contact_ids.length; offset += 10) {
        if (!pending.current) { pending.current = {
          operation_id: crypto.randomUUID(), revision: 0,
          reason: "Vinculación de preinscritos revisados para seguimiento WhatsApp",
          program: bundle.program, contact_ids: bundle.contact_ids.slice(offset, offset + 10),
          state: "granted", confirmed: true, evidence, origin,
          expires_at: new Date(expires).toISOString(),
        };
          setHasPending(true);
        }
        const result = await call<{ items?: unknown[]; held?: unknown[] }>(
          `broadcasts/accounts/${account}/prospects/setup`, "POST", pending.current,
        );
        setEnabledCount(previous => previous + (result.items?.length ?? Math.min(10, bundle.contact_ids.length - offset)));
        setReviewCount(previous => previous + (result.held?.length || 0));
        pending.current = null;
        setHasPending(false);
        setCount(Math.min(offset + 10, bundle.contact_ids.length));
      }
      setDone(true);
      try { await changed(); }
      catch { setError("La habilitación terminó. No se pudo refrescar el listado de consulta; recárgalo sin repetir la habilitación."); }
    } catch (failure) {
      const reasons: Record<string, string> = {
        prospect_phone_identity_conflict: "El número ya está vinculado a otra ficha. Revisa ese destinatario.",
        prospect_existing_channel_review_required: "La ficha ya tiene otro canal. Revisa su vinculación.",
        prospect_existing_history_review_required: "Existe una conversación o intervención humana previa. Se conserva para revisión.",
        prospect_revoked_consent_review_required: "Hay una revocación previa. Se requiere revisión individual.",
        prospect_phone_program_review_required: "Revisa el número y el programa de estos preinscritos.",
      };
      setError(failure instanceof ApiError && reasons[failure.detail] ||
        (failure instanceof Error ? failure.message : "La vinculación se detuvo."));
    } finally { setBusy(false); }
  };
  return <section className="panel" style={{ gridColumn: "1 / -1" }}>
    <details>
      <summary>Habilitar preinscritos revisados en WhatsApp</summary>
      <p>Vincula los teléfonos del lote a esta cuenta y registra su autorización de seguimiento.
        No envía mensajes ni activa campañas. Habilita IA sólo en la ficha de importación vacía,
        sin mensajes ni intervención humana. Los chats con historial o control cambiado quedan para revisión.
        Meta confirmará la entrega cuando se envíe la plantilla.</p>
      <Button disabled={busy || hasPending} onClick={() => void loadAll()}>Cargar todos los preinscritos del CRM</Button>
      <p>Una sola revisión para todos los programas. Las campañas se activan por separado y
        las autorizaciones vigentes se conservan; no se sustituyen revocaciones.</p>
      <label htmlFor="whatsapp-prospect-file">Lote de preinscritos revisado</label>
      <input id="whatsapp-prospect-file" type="file" accept=".json,application/json"
        disabled={busy || hasPending} onChange={e => void load(e.target.files?.[0])} />
      {bundle && <p>{bundle.contact_ids.length} contactos · {bundle.program === "all" ? "Todos los programas" : bundle.program === "logistica" ? "Logística" : "Aduanas"}</p>}
      <label htmlFor="whatsapp-prospect-evidence">Evidencia de autorización del lote</label>
      <textarea id="whatsapp-prospect-evidence" value={evidence} disabled={locked}
        maxLength={1000} onChange={e => setEvidence(e.target.value)} />
      <label htmlFor="whatsapp-prospect-origin">Fuente de la autorización</label>
      <input id="whatsapp-prospect-origin" value={origin} disabled={locked}
        maxLength={200} onChange={e => setOrigin(e.target.value)} />
      <label htmlFor="whatsapp-prospect-expiry">Vigencia para este seguimiento</label>
      <input id="whatsapp-prospect-expiry" type="datetime-local" value={expires}
        disabled={locked} onChange={e => setExpires(e.target.value)} />
      <p>El registro de este lote tiene una vigencia máxima de dos días. Una revocación previa requiere revisión individual.</p>
      <label><input type="checkbox" checked={confirmed} disabled={busy}
        onChange={e => setConfirmed(e.target.checked)} />
        Confirmo el número, el programa y la evidencia de autorización de estos contactos.</label>
      <Button disabled={!bundle || !confirmed || !evidence.trim() || !origin.trim() || !expires || busy || done}
        onClick={() => void run()}>Vincular y registrar autorización, sin enviar</Button>
      {!!count && <p role="status">{count} procesados de {bundle?.contact_ids.length} · {enabledCount} habilitados · {reviewCount} para revisión.</p>}
      {done && <Notice>Lote vinculado. Revisa los destinatarios de la campaña antes de activar.</Notice>}
      {error && <Notice>{error} {!done && "Los lotes anteriores se conservan. Continuar recupera el mismo intento pendiente."}</Notice>}
    </details>
  </section>;
}
