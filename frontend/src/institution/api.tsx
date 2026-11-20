import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  bindInstitutionSession,
  institutionUnauthorized,
} from "../shared/institutionSession";
import { Button, Field, Notice } from "../shared/ui";
import { ErrorFeedbackContext } from "./ErrorFeedback";
import type { OperationFailure } from "./ErrorFeedback";
import { coordinatedRead, readRetrySeconds, observeReadLimit } from "./readCoordinator";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  active: boolean;
  revision: number;
  profile: Record<string, string>;
  mfa_state: string;
  activation_pending?: boolean;
};
export type Session = {
  user: User;
  session_id: string;
  actions: string[];
  csrf_token: string;
  mfa_enabled?: boolean;
};
export type FieldSpec = {
  path: string;
  label: string;
  type: string;
  group: string;
  options: (string | number | boolean)[];
  nullable: boolean;
  minimum?: number;
  maximum?: number;
  max_length?: number;
  read_only: boolean;
  multiline: boolean;
};
export type Contract = {
  channel_operations?: boolean;
  agent_operations?: boolean;
  fields: Record<string, FieldSpec[]>;
  provider_categories: Record<string, string[]>;
  actions: { id: string; label: string; group: string }[];
  modules: { id: string; label: string }[];
};
export type Document = Record<string, unknown>;
export type Setting = {
  document: Document;
  revision: number;
  updated_at: string;
};
const messages: Record<string, string> = {
  language_rehearsal_free_backup_required: "Este ensayo sólo admite respaldos gratuitos de OpenRouter, con topes de tarifa en cero. Revisa y guarda la política antes de probar.",
  language_rehearsal_ai_disabled: "Habilita la IA antes de probar su respaldo. No se consultó ningún proveedor.",
  language_rehearsal_not_found: "No se encontró ese ensayo para tu usuario. Conserva el identificador y revisa la sesión; no generes otra respuesta para recuperar la anterior.",
  language_rehearsal_claim_changed: "El ensayo cambió o venció. Consulta su resultado antes de preparar otra prueba.",
  language_backup_required: "Añade al menos un modelo de respaldo del catálogo antes de habilitar esta función.",
  language_backup_duplicate: "Hay un modelo de respaldo repetido. Elige alternativas diferentes.",
  language_backup_interactive_model_required: "Elige un modelo de conversación del catálogo; las variantes batch no sirven para atención en tiempo real.",
  language_backup_configuration_changed: "La política o una clave de respaldo cambió. Actualiza la configuración antes de continuar.",
  voice_mix_busy: "El mezclador está ocupado. Espera unos segundos y vuelve a escuchar la misma muestra; no se generará otra voz.",
  voice_mix_failed: "No se pudo mezclar el ambiente con la voz. El administrador debe revisar FFmpeg y las pistas de ambiente.",
  voice_mix_unavailable: "El mezclador de audio no está disponible en el backend. Pide al administrador revisar FFmpeg.",
  voice_mix_source_unavailable: "La voz original de esta muestra ya no está disponible para mezclar. Elige una muestra reciente generada desde tu sesión.",
  voice_mix_invalid: "Uno de los volúmenes está fuera del rango permitido. Revisa los controles y prueba de nuevo.",
  voice_greeting_model_required: "Las entonaciones del saludo requieren un modelo Eleven v4 o v3. Selecciona uno del catálogo y guarda el perfil antes de comparar.",
  voice_preview_result_review: "Una muestra quedó en curso o con resultado incierto. La comparación se detuvo para evitar más consumo. Revisa su actividad antes de iniciar otro intento.",
  voice_pilot_conversation_required: "Marca al menos una conversación de WhatsApp en el modo piloto antes de activar la voz. Sólo esos hilos usarán ElevenLabs.",
  voice_default_profile_missing: "Crea un perfil de voz activo y selecciónalo como predeterminado antes de activar la generación.",
  voice_duplicate_assignment: "Un agente o una escuela está asignado a más de un perfil activo. Deja una única voz para cada asignación.",
  voice_duplicate_profile: "Hay dos perfiles con el mismo identificador. Actualiza la configuración guardada y crea un perfil nuevo desde Añadir perfil.",
  voice_invalid_threshold: "El máximo de caracteres por audio debe ser igual o mayor que el umbral de explicación larga. Ajusta ambos valores y guarda.",
  voice_language_unsupported: "El modelo no admite fijar ese idioma o ya no lo incluye en su catálogo. Elige Automático o un idioma disponible para el modelo seleccionado.",
  voice_duration_estimated_exceeded: "El texto de la muestra duraría más que el máximo configurado. No se generó audio. Reduce el texto, aumenta la duración máxima o usa 0 para desactivar ese límite.",
  voice_duration_actual_exceeded: "El audio generado excedió la duración máxima. Se descartó sin cortarlo. La generación pudo consumir caracteres; revisa la actividad y reduce el texto antes de otra prueba.",
  voice_key_required: "Guarda primero la clave de ElevenLabs en Ajustes → APIs y modelos → Credenciales.",
  voice_profile_unavailable: "El perfil de voz no está disponible o está desactivado. Elige un perfil activo y guarda la configuración.",
  voice_text_too_large: "El texto supera el máximo de caracteres por audio. Reduce la muestra o ajusta ese límite; las respuestas automáticas continúan completas por texto.",
  voice_check_context_immutable: "Para comprobar un chat real se usa su agente y programa guardados. Elige Simulación de asignación si quieres comparar otras opciones.",
  voice_check_program_mismatch: "El agente elegido pertenece a otro programa. Selecciona su programa o deja que la comprobación use el programa del agente.",
  voice_conversation_limit: "Este hilo ya alcanzó su máximo de audios. Las siguientes respuestas continúan por texto.",
  voice_daily_limit: "Se alcanzó el tope de caracteres de las últimas 24 horas. Espera o ajusta el límite de voz; las conversaciones continúan por texto.",
  voice_preview_limit: "Se alcanzó el límite de 100 intentos de voz en 24 horas para las muestras. Revisa la actividad antes de volver a generar.",
  voice_configuration_changed: "La configuración o la clave cambió durante la generación. El audio se canceló para respetar la configuración vigente. Revisa el historial antes de iniciar otra muestra.",
  voice_catalog_timeout: "ElevenLabs no terminó de devolver el catálogo. Conservamos tus perfiles; vuelve a cargar las voces cuando se recupere la conexión.",
  voice_catalog_required: "La voz o el modelo ya no están disponibles para esta clave. Carga el catálogo de ElevenLabs y elige de nuevo en el perfil.",
  voice_insufficient_credits: "ElevenLabs no tiene saldo suficiente. Revisa tu saldo en ElevenLabs. La conversación puede continuar por texto.",
  voice_payment_required: "ElevenLabs requiere revisar el plan o el pago. Comprueba tu cuenta antes de generar otra muestra.",
  voice_model_access_denied: "Tu cuenta no tiene acceso a este modelo de voz. Carga el catálogo y elige un modelo permitido por tu plan.",
  voice_account_restricted: "ElevenLabs restringió temporalmente esta cuenta. Revisa los avisos de seguridad del proveedor antes de repetir la generación.",
  voice_invalid_key: "ElevenLabs rechazó la clave. Reemplázala directamente en APIs y modelos → Credenciales → ElevenLabs.",
  voice_insufficient_permissions: "La clave no permite esta operación. En ElevenLabs habilita lectura de voces y modelos y generación de texto a voz; luego guarda la clave en RinovaPlus.",
  voice_forbidden: "ElevenLabs denegó el acceso. Revisa los permisos de lectura de voces/modelos y generación de audio, además del acceso al modelo y la voz elegidos.",
  voice_access_denied: "La voz elegida no está disponible para tu cuenta. Actualiza el catálogo y selecciona otra voz.",
  voice_invalid_parameters: "ElevenLabs rechazó la combinación de voz y modelo. Actualiza el catálogo y selecciona valores compatibles.",
  voice_preview_unavailable: "La muestra venció, cambió de usuario o su archivo ya no está disponible. Genera una muestra nueva desde tu sesión.",
  voice_channel_required: "Configura primero un canal de Meta para vincular el registro de generación institucional.",
  ads_meta_permission_required:
    "Meta no concedió acceso de lectura a Publicidad (ads_read). Activa ese permiso en la configuración de la app y vuelve a Conectar con Meta desde Publicidad.",
  ads_meta_login_source_required:
    "Elige una conexión de Facebook de CBN con inicio de sesión de Meta y una credencial vigente para consultar Publicidad.",
  ads_meta_token_expired:
    "La autorización de publicidad venció o fue revocada. En Publicidad abre Conexión y cuentas y vuelve a Conectar con Meta.",
  ads_meta_context_changed:
    "La cuenta o su credencial cambió durante la consulta. Revisa la cuenta seleccionada y sincroniza de nuevo.",
  ads_meta_invalid_period:
    "Selecciona un período válido de hasta 93 días, con fecha final posterior a la inicial y sin fechas futuras.",
  ads_meta_rate_limited:
    "Meta limitó temporalmente las consultas. Espera al menos un minuto antes de sincronizar; la consulta anterior se conserva.",
  ads_meta_oauth_not_ready:
    "La autorización aún no está lista o venció. Completa el inicio de sesión en Meta y vuelve aquí; si ya venció, inicia una conexión nueva.",
  ads_meta_sync_required:
    "Sincroniza primero esta cuenta con Meta para preparar y revisar borradores con los objetos correctos.",
  ads_meta_scope_limit:
    "La cuenta excede la capacidad de esta consulta (1000 objetos por nivel o el tiempo disponible). Consulta los detalles en Meta; no se guardaron resultados parciales.",
  ads_meta_unavailable:
    "Meta no respondió a tiempo. Conservamos tus datos guardados; vuelve a sincronizar cuando se recupere la conexión.",
  ads_meta_request_rejected:
    "Meta rechazó esta consulta. Revisa que la conexión tenga acceso a esta cuenta publicitaria y que la versión Graph configurada admita Publicidad.",
  ads_meta_invalid_response:
    "Meta devolvió datos incompletos. No los reemplazamos por ceros. Vuelve a sincronizar o revisa la cuenta en Meta.",
  ads_meta_draft_scope_limit:
    "Esta cuenta alcanzó el límite de versiones consultables de borradores. Conserva su historial y solicita revisión del administrador.",
  ads_meta_draft_not_found:
    "El borrador no pertenece a esta cuenta o ya no está disponible. Actualiza la biblioteca de esta cuenta.",
  password_policy: "La contraseña debe tener entre 15 y 128 caracteres y no puede ser una secuencia o clave demasiado común. Elige una frase personal más segura y vuelve a guardarla; el enlace sigue disponible si no ha vencido.",
  email_access_link_required: "La plantilla de invitación o recuperación debe incluir {{enlace}} para que la persona pueda crear su contraseña. Añade un enlace HTTPS usando esa variable, valida y publica la plantilla.",
  email_template_not_published: "Selecciona una plantilla publicada antes de activar esta regla o informe.",
  email_recipient_selection_required: "Selecciona al menos un usuario, rol o grupo de destinatarios antes de activar esta regla o informe.",
  email_invalid_configuration: "Hay un valor de configuración no permitido. Revisa identificador, evento, destinatarios y plantilla antes de guardar.",
  email_invalid_header: "Revisa el nombre o asunto del correo: debe contener texto y no incluir saltos de línea.",
  email_template_too_large: "El HTML debe ocupar entre 1 byte y 100 KB. Reduce su tamaño e incrusta las imágenes desde la biblioteca.",
  email_invalid_image: "Usa una imagen PNG, JPEG o WebP estática, de hasta 1 MB y 2048 píxeles.",
  email_asset_quota: "La biblioteca llegó a 20 MB. Solicita revisión del almacenamiento antes de cargar más recursos.",
  email_asset_not_found: "Una imagen de la plantilla no está en esta biblioteca. Vuelve a subirla e insértala desde Logos y firmas.",
  email_user_already_activated: "Esta cuenta ya tiene contraseña. Su titular puede usar Olvidé mi contraseña en el login si necesita recuperar el acceso.",
  email_invalid_receipt: "Revisa el correo y la fecha del recibo de Oracle. Debe corresponder a un envío aceptado o incierto y a una observación posterior a su creación.",
  email_invalid_daily_limit: "El límite diario de correo debe ser un número entero entre 1 y 10.000.",
  email_migration_required: "Notificaciones necesita su instalación en PostgreSQL. Un administrador debe aplicar la migración P15 antes de guardar; la salida está pausada.",
  email_provider_not_configured: "Faltan las credenciales SMTP de Oracle. Guarda CRM_SMTP_HOST, CRM_SMTP_USERNAME y CRM_SMTP_PASSWORD en las variables de producción del backend y redespliega.",
  email_sending_paused: "El correo está pausado. Revisa Habilitar salida en Notificaciones y CRM_EMAIL_ENABLED en Coolify antes de enviar la prueba.",
  email_unsafe_html: "El HTML contiene scripts, formularios o atributos no permitidos. Retíralos y vuelve a validar la vista previa.",
  email_unsafe_css: "El estilo del correo incluye una propiedad o instrucción no permitida. Usa colores, tipografía, márgenes y tablas sin scripts ni recursos externos.",
  email_unsafe_url: "Los enlaces del correo deben usar HTTPS y no contener credenciales. Corrige el enlace y vuelve a validar.",
  email_image_requires_library: "Sube la imagen en Logos y firmas e insértala desde esa biblioteca. Las imágenes externas de seguimiento están bloqueadas.",
  email_unknown_variable: "La plantilla tiene una variable desconocida. Usa únicamente las variables que aparecen debajo de la vista previa.",
  email_missing_variables: "Faltan valores para completar la plantilla. Revisa sus variables antes de enviarla.",
  email_invalid_address: "El correo destinatario o remitente no es válido. Escribe sólo la dirección, sin nombres ni saltos de línea.",
  email_invalid_schedule: "Revisa la hora, el día y la zona horaria IANA; por ejemplo America/Bogota.",
  email_not_cancellable: "El envío ya comenzó o terminó. Actualiza el historial; no se puede cancelar una entrega aceptada por Oracle.",
  comment_source_unavailable: "Meta no permite consultar este comentario. Revisa la publicación y los permisos del canal; luego pulsa Sincronizar comentario.",
  comment_is_account_reply: "Esta respuesta pertenece a la cuenta conectada. Abre el hilo y selecciona el comentario de la persona a la que quieres responder.",
  invalid_notification_cutoff: "La lista de notificaciones cambió. Actualízala y vuelve a marcarla como leída.",
  learning_purpose_authorization_required: "Esta finalidad necesita una autorización vigente. Revisa las autorizaciones del pack.",
  learning_authorization_changed_rebuild_required: "Cambió una autorización usada por el dataset. Revisa las muestras y crea un dataset nuevo.",
  learning_dataset_corrected_rebuild_required: "Una muestra fue corregida. Crea un dataset nuevo para incorporar la revisión.",
  learning_temporal_group_split_insufficient: "Se necesitan al menos 16 muestras de entrenamiento y 8 de validación, con ambas clases y sujetos separados por el corte temporal.",
  learning_samples_24_to_1000_required: "El dataset necesita entre 24 y 1000 muestras revisadas.",
  learning_shadow_observations_required: "Registra al menos cuatro predicciones en sombra antes de promover esta versión.",
  learning_shadow_required: "Selecciona primero esta versión para evaluar en sombra.",
  learning_drift_review_required: "Las observaciones muestran deriva. Revisa los datos y la evaluación antes de promover el modelo.",
  learning_evaluation_gate_failed: "El modelo no supera la evaluación frente al baseline y por segmento.",
  learning_training_paused: "Este pack tiene detenidos los nuevos entrenamientos. Puedes habilitarlos al editar el pack.",
  learning_inference_paused: "La predicción de este pack está pausada.",
  learning_model_not_selected: "Selecciona un modelo en sombra o una versión aprobada antes de calcular la predicción.",
  learning_pack_version_changed: "El pack cambió de versión. Revisa sus muestras y crea un dataset actualizado.",
  learning_subject_changed_rebuild_required: "Cambió la identidad del contacto en CRM. Revisa la autorización y reconstruye el dataset.",
  learning_source_not_found: "El origen no pertenece al contacto autorizado o ya no está disponible.",
  learning_source_after_features: "La fecha de observación precede a la creación del registro de origen.",
  learning_feature_schema: "Completa exactamente las observaciones numéricas del objetivo seleccionado.",
  learning_feature_range: "Los valores deben ser números finitos entre 0 y 1000000.",
  learning_correction_already_superseded: "Esta muestra ya tiene una corrección. Revisa su versión más reciente.",
  learning_previous_approved_required: "Sólo puedes revertir a una versión previamente aprobada.",
 ads_comment_link_ambiguous:"El comentario tiene varios vínculos en CRM. Revisa las cuentas y los contactos antes de convertirlo.",
  ads_account_not_found: "La cuenta publicitaria ya no está disponible.",
  ads_record_not_found: "El registro de captación ya no está disponible.",
  ads_account_identity_immutable:
    "El proveedor y el ID externo identifican esta cuenta. Registra otra cuenta si son distintos.",
  ads_account_binding_in_use:
    "Esta cuenta ya tiene captaciones. Conserva su canal de origen y registra otra cuenta para un canal diferente.",
  ads_campaign_identity_immutable:
    "Una campaña registrada conserva su cuenta e ID de origen.",
  ads_capture_identity_immutable:
    "La captación conserva su cuenta, canal e ID externo.",
  ads_account_channel_mismatch:
    "El canal seleccionado no corresponde al proveedor de esta cuenta.",
  ads_account_paused:
    "Esta cuenta está pausada o desconectada. Revisa su disponibilidad antes de continuar.",
  ads_channel_binding_required:
    "Vincula esta cuenta a un canal antes de procesar sus eventos.",
  ads_program_review_required:
    "El programa dejó de estar disponible en el catálogo CRM. Revisa la selección.",
  ads_stage_review_required:
    "La etapa inicial cambió o está inactiva. Revisa la configuración de la cuenta.",
  ads_converted_state_immutable:
    "La captación ya está vinculada a CRM; conserva ese vínculo al editarla.",
  ads_convert_requires_review:
    "Utiliza la opción de vincular a CRM para marcar esta captación como convertida.",
  ads_capture_unavailable:
    "Esta captación está oculta o eliminada y no puede convertirse.",
  ads_conversation_link_changed:
    "El vínculo con la conversación cambió. Actualiza los datos antes de continuar.",
  ads_comment_link_changed:
    "El comentario ya tiene otro vínculo en CRM. Actualiza y revisa su origen.",
  ads_retry_requires_quarantine:
    "Sólo se pueden reintentar eventos pendientes de revisión con la versión vigente.",
  ads_account_limit: "Se alcanzó el límite de 200 cuentas de esta instalación.",

  broadcast_provider_approved_template_required:
    "Sincroniza una plantilla aprobada de Meta para esta cuenta. Un borrador local no permite enviar.",
  broadcast_crm_variable_unknown:
    "Hay una variable que no pertenece al CRM. Insértala desde el selector de campos o usa una variable numérica y asígnala al preparar la campaña.",
  broadcast_crm_field_unavailable:
    "Un campo personalizado está inactivo o dejó de existir. Revisa la asignación de variables de la campaña antes de enviar.",
  broadcast_segment_field_unavailable:
    "Un campo de segmentación está inactivo o ya no existe. Revisa los campos de género, fecha de nacimiento, ubicación y filtros adicionales en la campaña.",
  broadcast_birth_date_field_required:
    "Selecciona un campo CRM de tipo Fecha para calcular la edad. No se estima a partir de otros datos.",
  broadcast_analytics_scope_limit:
    "El informe supera 5.000 destinatarios. Acota el estado o la búsqueda para consultar los gráficos sin truncar los resultados.",
  broadcast_variable_value_missing:
    "Falta un dato del contacto para completar esta plantilla. Completa su ficha del CRM o exclúyelo de este envío.",
  template_header_one_variable:
    "La cabecera de texto admite una variable. Conserva un solo campo del CRM en la cabecera.",
  template_sample_format_invalid: "El archivo de muestra no coincide con el formato. Usa JPG/PNG para imagen, MP4 para video o PDF para documento.",
  template_sample_upload_rejected: "Meta rechazó la muestra. Comprueba el formato, el tamaño y que el acceso de esta cuenta siga vigente.",
  template_sample_upload_unknown: "Meta no confirmó la carga. Conserva el borrador y revisa Actividad en Canales antes de repetirla. No se ha activado ninguna campaña.",
  template_sample_handle_missing: "Meta no devolvió el identificador del archivo. Revisa el estado de la conexión antes de repetir la carga.",
  template_sample_session_invalid: "Meta devolvió una sesión de carga que RinovaPlus no puede usar. Revisa el acceso de la cuenta y contacta al administrador.",
  template_sample_confirmation_required: "Confirma que autorizas enviar el archivo de muestra a Meta antes de cargarlo.",
  broadcast_media_upload_required: "El adjunto ya no está vinculado a esta cuenta o cambió su conexión. Vuelve a cargar el archivo en la campaña y revisa los destinatarios.",
  template_button_type_limit: "La plantilla permite hasta dos botones de enlace y uno de teléfono. Los demás pueden ser respuestas rápidas, hasta diez botones en total.",
  template_button_grouping_invalid: "Agrupa juntas las respuestas rápidas y después los enlaces/teléfono, o al revés. Usa Subir/Bajar para ordenarlos.",
  template_button_url_variable_invalid: "El enlace admite una variable {{1}} al final de la URL. Corrige su posición o usa un enlace fijo.",
  template_button_url_example_required: "Añade un ejemplo ficticio para la variable del enlace. Meta lo necesita para revisar la plantilla.",
  template_footer_variables_unsupported:
    "El pie de la plantilla debe ser texto fijo. Coloca los campos del CRM en el cuerpo o en la cabecera.",
  template_example_unused:
    "Los ejemplos ya no coinciden con las variables. Revisa los campos del mensaje y guarda el borrador de nuevo.",
  broadcast_template_refresh_required:
    "Sincroniza el catálogo de Meta y revisa otra vez los destinatarios.",
  broadcast_no_eligible_recipients:
    "No hay destinatarios elegibles. Revisa el consentimiento, la plantilla y las exclusiones.",
  broadcast_retry_only_definitive_unaccepted_failure:
    "Selecciona únicamente fallos definitivos sin aceptación de Meta. Los resultados inciertos requieren revisión.",
  broadcast_pause_before_edit: "Pausa la campaña antes de editarla.",
  broadcast_pause_before_prepare:
    "Pausa la campaña antes de volver a preparar destinatarios.",
  broadcast_account_changed:
    "La cuenta o su credencial cambió. Sincroniza las plantillas y revisa la campaña.",
  broadcast_authority_revoked:
    "La autorización de envío dejó de estar vigente. Revisa la campaña con un usuario autorizado.",
  knowledge_use_versioned_source_editor:
    "Revisa y publica esta fuente desde Conocimiento para conservar su historial.",
  memory_conversation_context_changed:
    "El contexto de la conversación cambió. Revisa de nuevo el hecho antes de publicarlo.",
  memory_incoming_evidence_mismatch:
    "El hecho debe estar contenido en la cita literal de un mensaje entrante de esta conversación.",
  knowledge_expired:
    "La vigencia terminó. Corrige la fecha en un nuevo borrador y revísalo antes de publicar.",
  knowledge_approved_version_required:
    "Selecciona una versión que haya sido publicada después de revisión.",
  knowledge_pdf_no_text_ocr_required:
    "Este PDF no contiene texto extraíble. Prepara una versión con texto u OCR y vuelve a cargarla.",
  knowledge_DNA_already_published:
    "Ya hay un ADN publicado. Edita y revisa su registro para conservar la continuidad.",
  knowledge_shared_context_limit:
    "Hay 20 memorias colectivas vigentes. Archiva las que ya no deban usarse antes de publicar otra.",
  public_https_origin_required:
    "Configura primero la URL pública HTTPS en Ajustes → Webhooks.",
  application_client_id_required:
    "Introduce el App ID o Client Key de tu aplicación del proveedor.",
  configured_waba_required:
    "Guarda el ID de la cuenta de WhatsApp Business (WABA) de la institución y abre Meta de nuevo.",
  oauth_session_expired:
    "La autorización venció. Inicia una conexión nueva con Meta.",
  comment_preview_unavailable:
    "Meta no permitió consultar esta publicación. Revisa los permisos de lectura de la cuenta en Canales y vuelve a actualizar la publicación.",
  credential_required:
    "Falta una credencial para esta cuenta. Guárdala antes de verificarla.",
  provider_verification_required:
    "Verifica el token y la identidad de la cuenta antes de conectarla.",
  whatsapp_webhook_setup_required:
    "Habilita la recepción firmada de esta cuenta y configura una URL pública HTTPS en Ajustes → Webhooks.",
  whatsapp_webhook_route_unavailable:
    "Meta no devolvió la ruta del número. Revisa el identificador del número y los permisos del token.",
  whatsapp_phone_webhook_override_conflict:
    "Meta tiene una URL alternativa en este número que prevalece sobre la de la cuenta. Revisa el webhook del número en Meta.",
  api_version_required: "Indica la versión de la API del proveedor.",
  comment_ai_not_configured:
    "Configura y habilita el modelo de texto para solicitar un borrador.",
  comment_ai_credential_required:
    "Falta la clave del proveedor de IA en Ajustes → Proveedores.",
  comment_ai_pricing_review_required:
    "Un administrador debe revisar el límite de tarifa de IA para esta cuenta.",
  comment_ai_budget_disabled:
    "Define los límites de tokens y gasto de IA antes de solicitar borradores.",
  comment_ai_budget_exhausted: "Se alcanzó el presupuesto de IA del día.",
  comment_deleted:
    "El proveedor eliminó este comentario; sus acciones están bloqueadas.",
  comment_reply_already_pending:
    "Esta respuesta ya está en curso. Consulta su estado antes de repetirla.",
  initial_stage_review_required:
    "Revisa la etapa inicial del CRM en la configuración de esta cuenta.",
  tiktok_accounts_authorization_profile_required:
    "La autorización de TikTok Accounts requiere configurar su aplicación y producto. Login Kit tiene permisos distintos.",
  invalid_credentials: "Correo o contraseña incorrectos.",
  provider_key_missing: "Guarda una clave de este proveedor en Credenciales y vuelve a consultar el catálogo.",
  provider_key_rejected: "El proveedor rechazó la clave guardada. Actualízala en Credenciales y vuelve a consultar.",
  provider_endpoint_missing: "Configura la dirección del proveedor antes de consultar sus modelos.",
  provider_rate_limited: "El proveedor limitó las consultas. Espera un momento y actualiza el catálogo.",
  provider_catalog_timeout: "El catálogo tardó en responder. Actualízalo para volver a intentarlo.",
  confirmation_failed: "No se pudo confirmar tu identidad.",
  invalid_request: "Revisa los campos y sus límites antes de guardar.",
  revision_conflict:
    "Hay una versión más reciente. Tu borrador se conserva; consulta la versión guardada antes de volver a editar.",
  conversation_control_changed:
    "Otra operación cambió el modo de atención de este chat. Revisa la posición actual del interruptor antes de volver a cambiarla.",
  conversation_closed:
    "El chat está cerrado. Ábrelo antes de cambiar el modo de atención.",
  permission_denied: "Tu rol no permite esta operación.",
  session_required: "Tu sesión terminó. Inicia sesión de nuevo.",
  module_disabled: "Este módulo está deshabilitado por la institución.",
  server_temporarily_unavailable:
    "El servidor tardó demasiado o no pudo completar la consulta. Tu configuración se conserva. Espera unos segundos y vuelve a cargar RinovaPlus.",
  invalid_server_response:
    "El servidor devolvió una respuesta incompleta. Tu configuración se conserva; vuelve a cargar RinovaPlus cuando termine la actualización.",
  rate_limit: "Alcanzaste el límite temporal. Espera antes de reintentar.",
  rate_limited: "RinovaPlus alcanzó el límite temporal de solicitudes.",
  last_active_owner: "Debe quedar al menos un propietario activo con acceso.",
  last_active_admin: "Debe quedar al menos un administrador activo.",
  email_already_registered: "Este correo ya tiene una cuenta.",
  account_identity_immutable:
    "Esta cuenta ya tiene una identidad externa. Crea otra cuenta para usar una diferente.",
};
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public retryAfterSeconds?: number,
  ) {
    super(
      messages[detail] ??
        (status === 429
          ? "Espera antes de reintentar esta operación."
          : status === 403
            ? "Tu rol no permite esta operación."
            : status === 409
              ? "La operación entra en conflicto con el estado guardado. El borrador se conserva."
              : status === 503
                ? "No se pudo validar el acceso a la información. Reintenta más tarde."
                : "No se pudo completar la solicitud. Revisa los campos."),
    );
  }
}

export function operationFailure(
  error: unknown,
  fallback: string,
): OperationFailure {
  return error instanceof ApiError
    ? { message: error.message, code: error.detail, status: error.status }
    : { message: error instanceof Error ? error.message : fallback };
}
export async function send<T>(
  path: string,
  method = "GET",
  body?: unknown,
  csrf = "",
): Promise<T> {
  if (method === "GET") {
    const seconds = readRetrySeconds();
    if (seconds) throw new ApiError(429, "rate_limited", seconds);
    return coordinatedRead(`${csrf}:${path}`, () => request<T>(path, method, body, csrf));
  }
  return request<T>(path, method, body, csrf);
}
async function request<T>(path: string, method: string, body: unknown, csrf: string): Promise<T> {
  const response = await fetch(`/api/institution/${path}`, {
    method,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      "X-CRM-Local": "1",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(45000),
  });
  const result = (await response.json().catch(() => null)) as { detail?: string } | null;
  if (response.ok && result === null) throw new ApiError(502, "invalid_server_response");
  if (!response.ok) {
    if (response.status === 401 && result?.detail === "session_required")
      institutionUnauthorized(401);
    const retryAfter = Number(response.headers.get("Retry-After"));
    if (response.status === 429) observeReadLimit(response.headers.get("Retry-After"));
    throw new ApiError(
      response.status,
      result?.detail ?? ([502, 503, 504].includes(response.status) ? "server_temporarily_unavailable" : "request_failed"),
      retryAfter > 0 ? retryAfter : undefined,
    );
  }
  return result as T;
}
type Call = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
const Context = createContext<{
  session: Session;
  call: Call;
  refresh: () => Promise<void>;
  expire: () => void;
} | null>(null);
export const useInstitution = () => {
  const value = useContext(Context);
  if (!value) throw Error("Institution session unavailable");
  return value;
};
export function SessionBoundary({
  initial,
  expire,
  children,
}: {
  initial: Session;
  expire: () => void;
  children: ReactNode;
}) {
  const [session, setSession] = useState(initial);
  const [confirm, setConfirm] = useState(false);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef<((accepted: boolean) => void) | null>(null);
  const ask = useCallback(() =>
    new Promise<boolean>((resolve) => {
      if (pending.current) return resolve(false);
      pending.current = resolve;
      setConfirm(true);
    }), []);
  const close = (accepted: boolean) => {
    pending.current?.(accepted);
    pending.current = null;
    setConfirm(false);
    setPassword("");
    setCode("");
    setError("");
  };
  useLayoutEffect(() => {
    bindInstitutionSession(session.csrf_token, expire);
    return () => {
      bindInstitutionSession("");
      pending.current?.(false);
      pending.current = null;
    };
  }, [session.csrf_token, expire]);
  const call = useCallback<Call>(async (path, method, body) => {
    try {
      return await send(path, method, body, session.csrf_token);
    } catch (failure) {
      if (
        failure instanceof ApiError &&
        failure.status === 428 &&
        (await ask())
      )
        return send(path, method, body, session.csrf_token);
      if (
        failure instanceof ApiError &&
        failure.status === 401 &&
        failure.detail === "session_required"
      ) {
        bindInstitutionSession("");
        expire();
      }
      throw failure;
    }
  }, [session.csrf_token, ask, expire]);
  const refresh = async () => {
    const next = await call<Session>("auth/me");
    setSession(next);
  };
  return (
    <Context.Provider value={{ session, call, refresh, expire }}>
      {children}
      {confirm && (
        <div className="institution-modal">
          <form
            className="panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            onSubmit={async (event) => {
              event.preventDefault();
              setBusy(true);
              try {
                await send(
                  "auth/confirm",
                  "POST",
                  { current_password: password, ...(code ? { code } : {}) },
                  session.csrf_token,
                );
                close(true);
              } catch (failure) {
                setError(
                  failure instanceof Error
                    ? failure.message
                    : "No se pudo confirmar.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            <h2 id="confirm-title">Confirma tu identidad</h2>
            <p>Esta acción necesita una confirmación reciente.</p>
            <Field
              id="confirm-password"
              label="Contraseña actual"
              type="password"
              autoComplete="current-password"
              autoFocus
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Field
              id="confirm-code"
              label="Código de autenticación o recuperación, si está activo"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            {error && <Notice error>{error}</Notice>}
            <div className="institution-actions">
              <Button type="submit" disabled={busy}>
                Confirmar
              </Button>
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => close(false)}
              >
                Cancelar
              </Button>
            </div>
          </form>
        </div>
      )}
    </Context.Provider>
  );
}

export function useIntent() {
  const attempt = useRef<{ key: string; id: string } | null>(null);
  const intent = (body: unknown) => {
    const key = JSON.stringify(body);
    if (attempt.current?.key !== key)
      attempt.current = { key, id: crypto.randomUUID() };
    return attempt.current.id;
  };
  return {
    get: intent,
    clear: () => {
      attempt.current = null;
    },
  };
}
export function useTask() {
  const report = useContext(ErrorFeedbackContext);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [success, setSuccess] = useState("");
  const run = async (
    work: () => Promise<void>,
    message = "Cambios guardados.",
  ) => {
    if (busy) return;
    const trigger = report ? document.activeElement : null;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await work();
      setSuccess(message);
    } catch (failure) {
      const details = operationFailure(
        failure,
        "No se pudo completar la operación.",
      );
      setError(report?.(details, trigger)?.detail ?? details.message);
    } finally {
      setBusy(false);
    }
  };
  return {
    busy,
    error,
    success,
    run,
    notices: (
      <>
        {error && <Notice error>{error}</Notice>}
        {success && <Notice>{success}</Notice>}
      </>
    ),
  };
}
