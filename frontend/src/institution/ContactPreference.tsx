import { Badge, Notice } from "../shared/ui";
import { useResource } from "./Settings";

export function ContactPreference({ id }: { id: string }) {
  const data = useResource<{ no_contact: boolean }>(`workspace/contact-preference/${encodeURIComponent(id)}`);
  if (data.error) return <Notice error>No se pudo consultar la preferencia de contacto.</Notice>;
  if (!data.value) return <p>Consultando preferencia de contacto…</p>;
  return data.value.no_contact ? <Notice><Badge>No contactar</Badge> Esta persona pidió no recibir mensajes. Se excluye de campañas y seguimientos. Una nueva autorización debe quedar registrada antes de retomarlos.</Notice> : <p className="scope-text">Sin solicitud de no contacto registrada. Cada campaña verifica por separado el consentimiento y el modo IA.</p>;
}
