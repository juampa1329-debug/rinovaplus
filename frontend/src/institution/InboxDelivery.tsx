import { useContext } from "react";
import { Icon } from "../shared/Icon";
import {
  ErrorFeedbackContext,
  type ErrorGuidance,
  type OperationFailure,
} from "./ErrorFeedback";

const details: Record<string, [string, string, string]> = {
  whatsapp_billing_issue: [
    "Meta rechazó el envío por facturación",
    "La cuenta de WhatsApp tiene un problema de pago. Puede deberse a saldo insuficiente, un método de pago vencido o una cuenta de facturación sin configurar.",
    "Abre Facturación y pagos en Meta, verifica el saldo y el método asociado a esta cuenta, y vuelve a enviar después de corregirlo.",
  ],
  whatsapp_reply_window_closed: [
    "Venció el plazo para responder por WhatsApp",
    "La ventana de conversación de 24 horas está cerrada. Meta limita las respuestas libres cuando el contacto lleva más de 24 horas sin escribir.",
    "Usa una plantilla aprobada o espera que el contacto vuelva a escribir.",
  ],
  whatsapp_recipient_unreachable: [
    "WhatsApp no pudo entregar el mensaje",
    "Meta indicó que el destinatario no pudo recibir este mensaje.",
    "Comprueba que el número siga activo en WhatsApp y confirma con el contacto por otro canal si es necesario.",
  ],
  whatsapp_rate_limit: [
    "WhatsApp limitó temporalmente el envío",
    "Meta recibió demasiadas solicitudes de esta cuenta en un intervalo corto.",
    "Espera unos minutos, comprueba el estado del mensaje y reintenta si figura como fallido.",
  ],
  whatsapp_media_upload_failed: [
    "WhatsApp rechazó el adjunto",
    "Meta no pudo guardar el archivo para enviarlo.",
    "Prepara otro archivo del mismo tipo y comprueba el formato y el tamaño antes de enviarlo.",
  ],
  media_sticker_invalid: [
    "El sticker necesita otro formato",
    "RinovaPlus admite stickers estáticos WebP de 512 × 512 píxeles.",
    "Exporta el archivo como WebP estático de hasta 100 KB y adjúntalo de nuevo.",
  ],
  media_sticker_limit: [
    "El sticker supera el tamaño permitido",
    "Los stickers WebP estáticos pueden pesar hasta 100 KB.",
    "Reduce la calidad o el peso del WebP, conserva 512 × 512 píxeles y vuelve a adjuntarlo.",
  ],
  campaign_video_limit: [
    "El video supera los límites del Inbox",
    "El video puede durar hasta 120 segundos y medir hasta 1920 × 1080 píxeles.",
    "Recorta o reduce la resolución del video y vuelve a adjuntarlo.",
  ],
  media_size_limit: [
    "El adjunto supera el límite",
    "El archivo original o el archivo preparado por RinovaPlus supera los 5 MB.",
    "Comprime o recorta el archivo, verifica que pese hasta 5 MB y vuelve a adjuntarlo.",
  ],
  inbox_recording_failed: [
    "No se pudo preparar la grabación",
    "",
    "Comprueba el micrófono y su permiso en el navegador. También puedes adjuntar un archivo de audio desde el clip.",
  ],
  inbox_file_size: [
    "El tamaño del archivo no es válido",
    "",
    "Elige otro archivo o reduce su tamaño.",
  ],
  delivery_uncertain: [
    "El envío sigue sin confirmar",
    "RinovaPlus no tiene confirmación de que el canal haya aceptado el mensaje.",
    "Revisa la actividad del canal antes de repetir el envío para evitar que el contacto lo reciba dos veces.",
  ],
  outbound_paused: [
    "El envío del canal está pausado",
    "RinovaPlus detuvo los envíos de esta cuenta.",
    "En Ajustes → Webhooks, revisa Permitir salida de cuentas verificadas.",
  ],
  outbound_setup_required: [
    "El mensaje espera la habilitación de los envíos",
    "La salida de cuentas verificadas está pausada y el cupo diario de mensajes está en cero. RinovaPlus conserva el mensaje en cola.",
    "Revisa Mensajes al día en Ajustes → Límites técnicos y Permitir salida de cuentas verificadas en Ajustes → Webhooks.",
  ],
  outbound_budget_disabled: [
    "El límite diario de mensajes está en cero",
    "La institución tiene deshabilitado el envío por el límite diario.",
    "Consulta a un administrador para revisar Mensajes al día en Ajustes → Límites técnicos.",
  ],
  outbound_budget_exhausted: [
    "Se agotó el límite diario de mensajes",
    "La institución alcanzó su tope interno de envíos.",
    "Espera al próximo período o consulta a un administrador para ajustar el límite.",
  ],
  account_paused_or_unverified: [
    "La cuenta del canal requiere revisión",
    "La cuenta de esta conversación está pausada o el proveedor todavía no la ha verificado.",
    "Abre Ajustes → Canales y revisa el estado de la cuenta antes de repetir el envío.",
  ],
  meta_access_token_expired: [
    "Caducó el acceso a Meta",
    "La credencial de la cuenta venció.",
    "Actualiza el Access Token en Ajustes → Canales y verifica la cuenta.",
  ],
  channel_media_not_supported: [
    "El canal no admite este adjunto",
    "El formato solicitado no está disponible para esta conexión.",
    "Elige un tipo de archivo compatible o envía un mensaje de texto.",
  ],
};
details.messaging_response_window_closed = details.whatsapp_reply_window_closed;
details.provider_outcome_unknown = details.delivery_uncertain;
details.provider_result_unknown = details.delivery_uncertain;
details.send_lease_expired = details.delivery_uncertain;

export function explainInboxError({
  code,
  message,
  status,
}: OperationFailure): ErrorGuidance {
  const guide =
    code && Object.hasOwn(details, code) ? details[code] : undefined;
  const [title, detail, nextStep] = guide ?? [
    "No se pudo completar la operación",
    message || "El canal no devolvió una causa específica para este resultado.",
    status === 403
      ? "Pide a un administrador que confirme los permisos de tu cuenta."
      : status === 409 || status === 503
        ? "Consulta el estado actual antes de repetir la operación. El borrador permanece en el hilo."
        : "Revisa la conexión y la actividad de la cuenta en Ajustes → Canales.",
  ];
  return { title, detail: detail || message, nextStep };
}

const statuses: Record<string, [string, string?]> = {
  queued: ["En cola"],
  sending: ["Enviando"],
  accepted: ["Aceptado por el canal"],
  sent: ["Enviado", "check"],
  delivered: ["Entregado", "doubleCheck"],
  read: ["Leído", "doubleCheck"],
  cancelled: ["Cancelado"],
};

export function MessageDelivery({
  state,
  reason,
}: {
  state: string;
  reason?: string;
}) {
  const report = useContext(ErrorFeedbackContext);
  const blocked = state === "queued" && !!reason;
  if (blocked || state === "failed" || state === "uncertain") {
    return (
      <button
        type="button"
        className="inbox-delivery-alert"
        onClick={(event) =>
          report?.(
            {
              code: state === "uncertain" ? "delivery_uncertain" : reason,
              message:
                state === "failed"
                  ? "El canal marcó el mensaje como fallido."
                  : "",
            },
            event.currentTarget,
          )
        }
      >
        <Icon name="warning" />
        {blocked
          ? "En cola · ver motivo"
          : state === "failed"
            ? "No enviado"
            : "Sin confirmar"}
      </button>
    );
  }
  const [text, icon] = Object.hasOwn(statuses, state)
    ? statuses[state]
    : ["Pendiente de confirmar"];
  return (
    <small className="inbox-delivery" data-state={state}>
      {icon && <Icon name={icon} />}
      {text}
    </small>
  );
}
