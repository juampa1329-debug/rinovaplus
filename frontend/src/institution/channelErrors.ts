import type { ErrorGuidance, OperationFailure } from "./ErrorFeedback";

const cases = new Map<string, ErrorGuidance>([
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
