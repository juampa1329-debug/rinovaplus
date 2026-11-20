import type { ErrorGuidance, OperationFailure } from "./ErrorFeedback";

const cases = new Map<string, ErrorGuidance>([
  [
    "gemini_whatsapp_previous_part_not_sent",
    {
      title: "La respuesta por partes se detuvo",
      detail:
        "Una parte anterior falló o quedó sin confirmación. Detuvimos las siguientes para evitar un mensaje incompleto o fuera de orden.",
      nextStep:
        "Revisa qué partes llegaron en el chat y el motivo del envío anterior. Un resultado incierto no se repite automáticamente; puedes continuar en Humano con el contexto conservado.",
    },
  ],
  [
    "gemini_whatsapp_segment_too_long",
    {
      title: "La respuesta necesita revisión",
      detail:
        "Una idea completa supera el tamaño permitido por este canal. No cortamos sus palabras ni enviamos sólo una parte.",
      nextStep:
        "Prepara una explicación más breve o revisa el borrador antes de enviarlo. El texto y la consulta originales se conservan.",
    },
  ],
  [
    "reply_group_waiting_previous",
    {
      title: "Esperando la parte anterior",
      detail:
        "La siguiente parte se enviará cuando Meta confirme la anterior y termine la pausa configurada.",
      nextStep:
        "No hace falta pulsar Enviar otra vez. Si una parte falla o cambias a Humano, se detienen las partes pendientes.",
    },
  ],
  [
    "comment_edit_source_changed",
    {
      title: "El comentario cambió en Facebook",
      detail: "El texto publicado ya no coincide con la versión que abriste.",
      nextStep:
        "Abre la publicación original y actualiza el hilo antes de editar de nuevo.",
    },
  ],
  [
    "comment_edit_review_required",
    {
      title: "Hay una edición por revisar",
      detail:
        "Una edición anterior sigue en proceso o Meta no confirmó su resultado.",
      nextStep:
        "Comprueba el comentario directamente en Facebook. No repetiremos el cambio automáticamente; conserva la referencia de la operación para revisar el resultado.",
    },
  ],
  [
    "comment_edit_own_only",
    {
      title: "Sólo puedes editar respuestas de tu cuenta",
      detail:
        "El comentario debe pertenecer a la Página de Facebook conectada.",
      nextStep:
        "Selecciona una respuesta publicada por CBN. Los comentarios de otras personas se conservan tal como los escribieron.",
    },
  ],
  [
    "comment_edit_unsupported_by_provider",
    {
      title: "Este canal no admite editar comentarios",
      detail:
        "La API de este proveedor no permite cambiar el texto publicado desde RinovaPlus.",
      nextStep:
        "Puedes enviar una aclaración como nueva respuesta o revisar las opciones de la aplicación original.",
    },
  ],
  [
    "comment_edit_published_required",
    {
      title: "La respuesta aún no está publicada",
      detail:
        "Necesitamos la confirmación y el identificador de Meta para editarla.",
      nextStep:
        "Espera a que finalice el envío y actualiza el hilo. Una respuesta fallida o en cola todavía no se puede editar.",
    },
  ],
  [
    "saved_app_secret_incompatible",
    {
      title: "Esta clave no corresponde a la aplicación",
      detail:
        "La clave elegida debe pertenecer al mismo App ID y al mismo tipo de inicio de sesión.",
      nextStep:
        "Actualiza las credenciales y selecciona una clave vigente de esta aplicación.",
    },
  ],
  [
    "oauth_account_mismatch",
    {
      title: "El número o la cuenta no corresponde a este canal",
      detail: "RinovaPlus conserva la cuenta que ya estaba configurada.",
      nextStep:
        "Elige la cuenta que corresponde al canal. Para agregar otra, crea un canal separado.",
    },
  ],
  [
    "oauth_session_expired",
    {
      title: "La autorización venció",
      detail: "Se agotó el tiempo para guardar la selección.",
      nextStep:
        "Vuelve a iniciar sesión con el proveedor y selecciona el número, página o cuenta de nuevo.",
    },
  ],
  [
    "whatsapp_business_account_id_required",
    {
      title: "Falta la cuenta de WhatsApp",
      detail: "RinovaPlus necesita el WABA ID para sincronizar sus números.",
      nextStep:
        "Conecta la cuenta con Meta o guarda el WABA ID desde el Administrador de WhatsApp.",
    },
  ],
  [
    "api_version_required",
    {
      title: "Falta la versión de Graph API",
      detail:
        "RinovaPlus necesita la versión de la API para consultar esta cuenta en Meta.",
      nextStep:
        "Escribe una versión vigente de la app en el campo Graph API, guarda la cuenta y repite la operación.",
    },
  ],
  [
    "credential_required",
    {
      title: "Faltan credenciales para esta cuenta",
      detail: "La operación requiere una clave que todavía no está disponible.",
      nextStep:
        "Revisa en Credenciales que estén guardados el App Secret de la app y el Access Token de la cuenta.",
    },
  ],
  [
    "token_application_mismatch_or_invalid",
    {
      title: "Meta no confirmó el token para esta app",
      detail:
        "La comprobación de Meta no confirmó un Access Token válido para el App ID guardado.",
      nextStep:
        "Comprueba en el depurador de Meta que el token sea válido y que el App ID de Meta coincida con el de la cuenta.",
    },
  ],
  [
    "meta_access_token_invalid",
    {
      title: "Meta rechazó la credencial",
      detail: "Meta no aceptó la credencial usada en esta consulta.",
      nextStep:
        "Confirma que el App Secret pertenezca al App ID guardado y que el Access Token siga siendo válido. Actualiza la credencial que corresponda y vuelve a verificar.",
    },
  ],
  [
    "meta_access_token_expired",
    {
      title: "El token de Meta caducó",
      detail: "Meta indicó que venció el token usado en la consulta.",
      nextStep:
        "Genera un token vigente en Meta, guárdalo en Credenciales y vuelve a verificar la cuenta.",
    },
  ],
  [
    "phone_not_in_waba",
    {
      title: "El número no aparece en la cuenta de WhatsApp",
      detail:
        "Meta no devolvió el ID del número guardado entre los números de la WABA indicada.",
      nextStep:
        "Abre Consultar números de WhatsApp y compara el Phone Number ID y el WABA ID con los de Meta. Corrige el dato que corresponda y guarda la cuenta.",
    },
  ],
  [
    "external_account_required",
    {
      title: "Falta el identificador de la cuenta",
      detail:
        "RinovaPlus necesita el identificador externo para comprobar esta conexión.",
      nextStep:
        "Completa el identificador de la cuenta. Para WhatsApp, revisa los campos WABA ID e ID del número de teléfono en Meta, y guarda la cuenta.",
    },
  ],
  [
    "provider_permission_or_request_rejected",
    {
      title: "El proveedor rechazó la solicitud",
      detail:
        "El proveedor rechazó la solicitud con la configuración guardada.",
      nextStep:
        "Comprueba los identificadores, las credenciales y los permisos de esta cuenta en el panel del proveedor. Después vuelve a verificar.",
    },
  ],
  [
    "provider_outcome_unknown",
    {
      title: "Resultado sin confirmar",
      detail: "RinovaPlus no pudo confirmar el resultado de la operación.",
      nextStep:
        "Revisa Actividad y recuperación y comprueba el estado en el proveedor antes de repetir la operación.",
    },
  ],
  [
    "revision_conflict",
    {
      title: "La cuenta cambió mientras la editabas",
      detail:
        "Hay una versión más reciente de esta cuenta. Tu formulario conserva los cambios.",
      nextStep:
        "Consulta la configuración guardada y compara los cambios antes de volver a guardar.",
    },
  ],
  [
    "public_https_origin_required",
    {
      title: "Falta la URL pública del webhook",
      detail:
        "El proveedor necesita una dirección HTTPS pública para entregar eventos a RinovaPlus.",
      nextStep:
        "Abre Ajustes → Webhooks y revisa la URL pública de la institución antes de reintentar.",
    },
  ],
  [
    "callback_copy_failed",
    {
      title: "No se pudo copiar el callback",
      detail: "El navegador no permitió copiar la URL al portapapeles.",
      nextStep:
        "Selecciona y copia manualmente el valor del campo de callback.",
    },
  ],
  [
    "webhook_token_copy_failed",
    {
      title: "No se pudo copiar el token",
      detail: "El navegador no permitió usar el portapapeles.",
      nextStep:
        "Selecciona el valor en «Token de verificación» y cópialo manualmente.",
    },
  ],
  [
    "webhook_values_already_issued",
    {
      title: "El webhook ya se generó",
      detail: "El token se entrega una sola vez y esta solicitud ya se aplicó.",
      nextStep: "Pulsa «Generar webhook» otra vez si necesitas un token nuevo.",
    },
  ],
]);

export function explainChannelError(failure: OperationFailure): ErrorGuidance {
  if (failure.code?.startsWith("voice_mix_"))
    return {
      title: "No se pudo preparar la mezcla",
      detail: failure.message,
      nextStep:
        "Para una vista previa, vuelve a abrir la misma muestra reciente; sus volúmenes se ajustan sin generar otra voz. Si continúa, pide revisar el mezclador del backend y consulta la actividad antes de repetir una generación.",
    };
  if (
    failure.code?.startsWith("voice_") ||
    failure.code === "provider_timeout_or_network"
  )
    return {
      title: "No se pudo generar el audio",
      detail: failure.message,
      nextStep:
        "Revisa Ajustes → Voces y audios y la clave de ElevenLabs en APIs y modelos. Consulta la actividad antes de generar otra muestra; un resultado incierto no se reintenta automáticamente.",
    };
  if (failure.code?.startsWith("email_"))
    return {
      title: "No se pudo completar la operación de correo",
      detail: failure.message,
      nextStep:
        "Abre Ajustes → Correos y notificaciones. Revisa el aviso, la plantilla, los destinatarios y la configuración de Oracle en Coolify antes de repetir el envío.",
    };
  if (failure.code?.startsWith("ads_meta_"))
    return {
      title: "No se pudo completar la operación de Publicidad",
      detail: failure.message,
      nextStep:
        "En Publicidad revisa la cuenta, el período y su conexión con Meta. Tus borradores y consultas anteriores se conservan.",
    };
  const known = failure.code && cases.get(failure.code);
  if (failure.status === 503) {
    return {
      title: "Canales no está disponible en este momento",
      detail: "RinovaPlus no pudo confirmar el resultado de la solicitud.",
      nextStep:
        "Revisa si el cambio quedó guardado antes de repetirlo. Si el problema continúa, consulta al administrador de RinovaPlus.",
    };
  }
  return (
    known || {
      title: "No se pudo completar la operación en Canales",
      detail: failure.message,
      nextStep:
        failure.status === 403
          ? "Verifica si tu rol tiene permiso para esta acción o consulta al administrador de RinovaPlus."
          : "Revisa los datos de la cuenta y el estado en Actividad y recuperación. Si el problema continúa, comparte con el administrador el nombre de la acción y el aviso.",
    }
  );
}
