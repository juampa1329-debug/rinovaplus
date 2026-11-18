# Plantillas WhatsApp de CBN: creación, adjuntos y ejemplos

El creador está en **Mensajería masiva → Plantillas WhatsApp → Crear plantilla** y también dentro de una campaña. El flujo estándar sigue los componentes de Meta: categoría/idioma, cabecera, cuerpo, variables de ejemplo, pie, botones y vista previa. Guardar un borrador, cargar un archivo y solicitar revisión son acciones distintas. Sólo Meta aprueba la plantilla.

## Crear una plantilla con imagen, video o PDF

1. Selecciona la cuenta de WhatsApp correcta. La aprobación pertenece a su WABA; no se traslada por cambiar de número/cuenta en la campaña.
2. Define un nombre en minúsculas con guion bajo, idioma y categoría según la finalidad real.
3. Elige **Imagen**, **Video** o **Documento** en Tipo de cabecera. Adjunta la muestra y pulsa **Cargar muestra en Meta** después de revisar su autorización. RinovaPlus inspecciona el archivo y obtiene el identificador de Meta; no hace falta copiarlo desde herramientas de desarrollo.
4. Usa una muestra institucional sin nombres, teléfonos ni documentos personales. RinovaPlus admite JPG/PNG, MP4 y PDF de hasta 5 MB. El MP4 tiene un límite local de 2 minutos y 1920×1080. Son límites del CRM, no una afirmación de los máximos generales de Meta.
5. Escribe el cuerpo, hasta 1024 caracteres, e inserta los campos desde el selector CRM. Proporciona ejemplos ficticios. La cabecera de texto admite 60 caracteres y una variable; el pie admite 60 caracteres y es fijo.
6. Agrega respuestas rápidas, enlaces HTTPS o teléfono. Máximo diez botones, con hasta dos enlaces y un teléfono; las respuestas rápidas deben quedar juntas. El enlace dinámico admite una variable `{{1}}` al final y necesita un ejemplo. Su valor se asigna explícitamente desde la campaña.
7. Revisa la vista previa y guarda el borrador. Después confirma **Enviar a revisión de Meta**. Sincroniza el catálogo para consultar aprobado/rechazado, calidad y motivo informado por Meta. Una solicitud confirmada no significa aprobación.

La muestra de revisión y el archivo enviado son distintos. En **la campaña**, adjunta el archivo definitivo y pulsa **Cargar archivo de la campaña**. Se carga a la cuenta de WhatsApp elegida y queda vinculado a su conexión. Como alternativa avanzada se conserva una URL HTTPS pública. Si cambias cuenta, plantilla o credencial, revisa/carga el adjunto nuevamente. Subir un archivo no envía la campaña.

## Mensajes naturales y categorías

Habla como el equipo de CBN: identifica el motivo concreto, usa frases breves y termina con una pregunta útil. No uses urgencia falsa, MAYÚSCULAS insistentes, promesas de empleo, descuentos inventados o precios/duraciones no revisados. Un emoji ocasional no sustituye información clara. No pidas contraseñas, claves ni datos de pago por una plantilla.

**Utilidad** requiere una solicitud, trámite o actualización real y específica, sin promoción. **Marketing** puede incluir información general de programas, invitaciones o reactivación de interesados aunque el texto no tenga presión comercial. No elijas Utilidad sólo para intentar cambiar la clasificación o el costo; Meta evalúa contenido y contexto. La autorización de contacto sigue siendo necesaria. El CRM conserva su revisión de consentimiento antes de enviar.

| Situación real | Ejemplo adaptable | Categoría orientativa |
|---|---|---|
| La persona solicitó un documento | Hola {{customer_first_name}}, te compartimos el documento que solicitaste para continuar tu trámite con CBN. Si necesitas aclarar algún punto, responde a este mensaje. | Utilidad, si corresponde a la solicitud real. Cabecera PDF. |
| La persona pidió una imagen informativa | Hola {{customer_first_name}}, aquí está el material que nos pediste. Si algo no queda claro, cuéntanos y lo revisamos contigo. | Utilidad sólo para atender esa solicitud. Cabecera imagen. |
| La persona pidió un video de orientación | Hola {{customer_first_name}}, te compartimos el video de orientación que solicitaste a CBN. Puedes responder aquí si necesitas ayuda con el siguiente paso. | Utilidad sólo para la solicitud concreta. Cabecera video. |
| Actualización de un trámite existente | Hola {{customer_first_name}}, tenemos una actualización sobre la solicitud que registraste en CBN. Responde a este mensaje para revisarla con tu asesor. | Utilidad, si existe la solicitud y la actualización. |
| Cita realmente acordada | Hola {{customer_first_name}}, te recordamos la cita que acordaste con CBN. Si necesitas cambiarla, responde a este mensaje y te ayudamos. | Utilidad. Añade fecha/hora sólo desde campos CRM revisados. |
| Invitación general sobre programas | Hola {{customer_first_name}}, somos el equipo de CBN. Si te interesa conocer nuestros programas, podemos orientarte por aquí. ¿Quieres recibir información? | Marketing; no se convierte en Utilidad por usar un tono cercano. |
| Retomar a alguien interesado anteriormente | Hola {{customer_first_name}}, la última vez conversamos sobre tu interés en {{program}}. ¿Quieres que retomemos tus preguntas o prefieres dejarlo para otro momento? | Marketing salvo contexto específico que Meta acepte como Utilidad. |

Botones útiles: **Tengo una pregunta**, **Recibido**, **Hablar con asesor**, **Ahora no**, **No recibir mensajes**. El texto de un botón no constituye por sí solo una revocación en el CRM: registrar No contactar/revocar consentimiento requiere su flujo operativo. No afirmar una baja automática si no está configurada y probada.

La guía integrada permite usar los primeros ejemplos como borradores editables. Nunca envía al seleccionarlos. Revisa la finalidad y los datos de cada persona antes de preparar destinatarios.

## Preparar y comprobar una campaña

Selecciona la plantilla aprobada, el archivo definitivo, los destinatarios/filtros y la zona horaria local. Usa Vista previa: debe mostrar cuántos coinciden, cuántos son elegibles y por qué se excluyen. Faltan datos del programa, consentimiento revocado, Humano o No contactar son motivos para detener ese destinatario, no para inventar valores.

Preparar no envía. Activa sólo después de revisar. Revisa aceptado, enviado, entregado, leído y fallido por separado; un fallo posterior a aceptación conserva su ID. Nunca repitas automáticamente un envío aceptado o de resultado incierto. El modal explica el problema y el siguiente paso.

## Alcance de este editor

Este flujo cubre plantillas estándar de texto/imagen/video/PDF y sus botones. Los formatos especializados de Meta —autenticación OTP, catálogos/productos, carruseles, Flows y funciones exclusivas de Marketing Messages API— necesitan su contrato, activos y envío específicos; no se simulan con controles que la API actual ignore. La creación de esos formatos queda pendiente de ampliación y aceptación propias. Audio y stickers se envían como medios de conversación cuando el canal/ventana lo permite; no son cabeceras de una plantilla estándar.

Fuentes oficiales consultadas el 17 de noviembre de 2026: [componentes de plantillas](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/components), [carga reanudable de archivos](https://developers.facebook.com/documentation/video-api/graph-api/guides/upload) y [creación y categoría de la plantilla](https://developers.facebook.com/docs/graph-api/reference/whats-app-business-account/message_templates/).
