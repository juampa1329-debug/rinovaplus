# P4 · Evidencia de validación de Canales

Corte del 16 de noviembre de 2026. Los identificadores y números completos se conservan en RinovaPlus.

## WhatsApp Cloud

- **Cuenta y credencial.** Tras confirmar identidad en Canales, Meta confirmó la verificación de la cuenta y la consulta mostró un número autorizado en su WABA. El webhook figura habilitado y verificado.
- **Recepción.** Una imagen JPG enviada desde el teléfono de prueba terminado en 44 llegó a las 12:52 p. m., hora de Bogotá. El Inbox descargó y abrió el archivo de 1284 × 1450 píxeles en la conversación asociada.
- **Salida.** A las 12:55 p. m. se envió una sola imagen PNG de prueba al mismo teléfono con el pie «Prueba P4 de salida». Meta reportó Entregado y luego Leído. El operador confirmó que abrió la imagen en el teléfono.
- **Control humano.** Al volver a IA, la revisión general de la bandeja invalidó el cambio y apareció un modal de conflicto a pesar de que el envío ya estaba entregado. Se recuperó el control en IA tras recargar. La corrección compara la versión del control de ese chat y preserva la prioridad, el estado de lectura y la asignación. La regresión de PostgreSQL comprueba un cambio de revisión por dos envíos, el cambio de modo, el reintento idempotente y el rechazo de una versión antigua del control.

## Alcance pendiente

| Hito | Evidencia obtenida y pasos pendientes |
|---|---|
| P4.3.m6 | WhatsApp con credenciales reales, número, webhook, identidad, adjuntos y recibos acreditados. Quedan OAuth y pruebas con la página autorizada de Facebook/Messenger, una cuenta profesional de Instagram y el producto autorizado de TikTok. |
| P4.4.m4 | En PostgreSQL aislado pasaron recuperación de colas, conciliación de un recibo adelantado e incertidumbre con proveedor simulado. Falta revisar la recuperación externa por los canales del alcance. |
| P4.3.m7, P4.4.m5 y P4.close.m5 | Requieren aceptar la matriz de canales y revisar evidencia, límites y reversión antes de cerrar P4. |

Scentra separa diagnóstico, números de WhatsApp, autorización por producto, suscripción, eventos entrantes y colas. La validación de RinovaPlus sigue ese recorrido por cuenta. En Facebook/Messenger se valida la página elegida, los mensajes y los comentarios donde correspondan. En Instagram se prueba el flujo profesional y los permisos de mensajes y comentarios. En TikTok se identifica primero el producto aprobado. Login Kit acredita identidad, mientras que la mensajería y los comentarios comerciales dependen de las autorizaciones del producto Business.

Tras el cierre de P4, la prueba de P7 parte de la plantilla `hello_world · en_US` que el catálogo de Meta muestra como `APPROVED`. El envío de prueba se hará desde Mensajería masiva a un contacto autorizado y con consentimiento registrado. El envío individual por Inbox aporta evidencia de transporte para P4.
