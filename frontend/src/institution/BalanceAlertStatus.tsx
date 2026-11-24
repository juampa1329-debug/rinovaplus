import { useState } from "react";
import { Button, Notice } from "../shared/ui";
import { useInstitution, useTask } from "./api";

const labels: Record<string, string> = {
  management_key_required: "Falta la clave de administración de OpenRouter. Guárdala en APIs y modelos para consultar el saldo total; la clave normal de IA no muestra ese saldo.",
  management_key_rejected: "OpenRouter rechazó la clave de administración. Revisa esa credencial en APIs y modelos.",
  unavailable: "No se pudo consultar el saldo. La IA continúa funcionando; se consultará de nuevo en el intervalo configurado.",
  checking: "Consulta de saldo en curso.",
  available: "Saldo consultado; no está por debajo del umbral.",
  low_notified: "Saldo bajo: alerta preparada para los administradores. Revisa su entrega en Correos y notificaciones.",
  mail_disabled: "Saldo bajo, pero el envío de correos está deshabilitado. Habilítalo en Correos y notificaciones.",
  no_admin_recipient: "No hay un administrador activo como destinatario.",
  mail_unavailable: "El servicio de correo no está disponible en este entorno.",
};
export function BalanceAlertStatus() {
  const { call } = useInstitution(), task = useTask();
  const [value, setValue] = useState<{status: string | null; checked_at: string | null; remaining_usd: number | null} | null>(null);
  return <section className="panel">
    <h3>Alerta de saldo de OpenRouter</h3>
    <p>Umbral inicial: USD 5 de saldo restante. Puedes modificarlo y activar el aviso en los campos de esta página.</p>
    <Button variant="secondary" disabled={task.busy} onClick={() => void task.run(async () => setValue(await call("provider-balance/openrouter/alert")), "Estado del monitor consultado.")}>Consultar estado del aviso</Button>
    {task.notices}
    {value && <Notice>{labels[value.status ?? ""] ?? "El monitor aún no ha realizado una consulta. Guarda la configuración y espera el intervalo establecido."}{value.checked_at && ` Última consulta: ${new Date(value.checked_at).toLocaleString()}.`}{value.remaining_usd != null && ` Último saldo conocido: USD ${value.remaining_usd.toFixed(2)}.`}</Notice>}
  </section>;
}
