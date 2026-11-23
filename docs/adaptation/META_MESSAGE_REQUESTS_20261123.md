# Solicitudes de mensajes de Meta — 23 de noviembre de 2026

## Solicitudes Meta: fallo de contrato localizado y corrección preparada — 2026-11-23

El titular pide atender solicitudes de Instagram/Messenger y autoriza responder un DM concreto de Inglés. Sus dos entradas14:40/14:41 ya estaban en CRM: no fue un filtro de Solicitudes. Diagnóstico15:20:17 muestra una generación control_or_history_changed y otra Sonnet4.6 completed seguida de gemini_whatsapp_invalid_response, sin salida; borrador/campo exacto no conservados. Se reforzó JSON Schema estricto para decision/text/observaciones en principal y respaldos. Claude no recibe maxLength/maxItems no soportados; límites y citas siguen validados en backend. Solo se canonicalizan mayúsculas/espacios de responder/revisar; decisiones desconocidas fallan. Nuevos errores distinguen JSON/contrato/longitud/incompleto sin cuerpos ni reintento automático.310backend seleccionadas/Ruff pasan. Publicación y prueba automática posterior pendientes.

Respuesta humana autorizada de información confirmada enviada17:49 y Aceptado por el canal, modo IA restaurado. Inglés revisión4 confirma A1+A2 en un semestre, sin precios ni planes aprobados y con instrucción explícita no cotizar; confirmación de tarifas solicitada al titular. No inventar ni publicar importes de la hoja provisional. Meta documenta que responder por API a solicitudes IG las mueve a General, sin endpoint separado de aceptar ni campo de carpeta en webhook. No se cambiaron permisos/ruteo ni se aceptaron solicitudes del buzón personal del destinatario. P4/P13/P21 iniciales y P22 3/5técnico/0aceptación conservados. SinDDL,seeds,nuevoscontenedores niSIIEwrites.

## Comportamiento de Meta y RinovaPlus

Una entrada de texto entregada por el webhook de Instagram o Messenger se procesa igual independientemente de la carpeta de la aplicación nativa. La identidad nueva comienza en IA; se conservan las decisiones humanas de hilos existentes, el estado del canal y los presupuestos. Responder una solicitud en Instagram desde la API la mueve a General. Esto no permite aceptar desde la cuenta de CBN la solicitud que un destinatario tiene en su propio buzón, ni forzar mensajes bloqueados por Meta. Las carpetas no forman parte de los eventos de mensajería expuestos por Meta. No se inventa un endpoint accept ni se procesan eventos standby como si la app tuviera el control.

La importación histórica actual copia salientes y no dispara IA histórica; no se transforma esta revisión en un envío masivo a solicitudes antiguas. Si una entrada no llegó al webhook, se debe contrastar ruteo, acceso y entrega de Meta; si llegó, Diagnósticos permite distinguir el fallo de generación/envío. No se afirma aceptación general de todas las solicitudes a partir de un solo contacto.

## Diagnóstico concreto

Dos mensajes entrantes visibles a las14:40/14:41, sin respuesta previa. Operaciones8aa1d189-6e44-4bf7-9e28-76ac70fbbb69 y0af4bd5e-4223-4221-8a78-e2bbd902329a fallaron a las15:20:17. La segunda traza confirma OpenRouter/Sonnet4.6 completado, seguido del validador de respuesta. No se conserva el JSON rechazado ni se conoce su campo exacto: formato estricto y canonicalización de enum son prevención comprobable, no una reconstrucción del borrador perdido.

Se respondió desde Inbox con información local confirmada y aclaración de tarifa por confirmar. Aceptado por el canal a las17:49; no acreditar lectura ni entrega sin recibo posterior. El modo IA original quedó restaurado. No se repite la generación fallida ni se reenvía un resultado incierto.

## Contrato y comprobaciones

OpenRouter usa JSON Schema estricto también para respuestas ordinarias de mensajes y comentarios, con objetos cerrados y decisión responder/revisar. Observaciones CRM se limitan a campos conocidos con cita y valor; el registro sigue verificando cita literal y máximo8. Las restricciones de cadena/array no admitidas por Claude pasan a descripciones, sin omitir la validación local. El esquema Gemini original se conserva. Cada ruta realiza un POST; no hay corrección con una segunda inferencia oculta.

310pruebas seleccionadas cubren contrato, respaldo, principal explícito, Humano, voz, recuperación, canales y proyección. Ruff E4/E7/E9/F pasa. Despliegue y comprobación real de respuesta automática siguen pendientes en este corte.

## Referencias oficiales

- [Instagram Messaging overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview): carpetas y respuesta a solicitudes.
- [Conversation routing](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/conversation-routing): no responder standby sin control.
- [Claude Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs): restricciones no admitidas y posible variación de mayúsculas en enums.
