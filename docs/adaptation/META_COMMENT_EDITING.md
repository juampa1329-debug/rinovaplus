# Edición de respuestas publicadas en Meta

Corte: 19 de noviembre de 2026. Mejora de Comentarios; no añade peso ni reabre la aceptación histórica de P4.

| Canal y objeto | Capacidad documentada | RinovaPlus |
|---|---|---|
| Comentarios y respuestas de la Página de Facebook | Actualizar el nodo de comentario con `POST /{comment-id}` y `message`. | Editor para contenido propio de la cuenta conectada, escrito por humano o Gemini. |
| Comentarios de otras personas | No se pueden convertir en contenido propio editable. | Sin editor; comprobar propiedad local y mediante `from.id` en Meta. |
| Comentarios de Instagram | La moderación documenta lectura, respuestas, ocultar/mostrar y borrado. La actualización del nodo sólo documenta ocultar/mostrar. | Sin edición de texto; explicación visible en el hilo. No se elimina ni publica otra respuesta para simular edición. |
| DM Messenger e Instagram | El nodo Message indica que Update no está disponible. Recibir eventos de una edición no habilita editar mensajes enviados mediante API. | Se conserva el envío normal; no se ofrece una edición ficticia. Puede enviarse una aclaración nueva manualmente. |
| WhatsApp Cloud API | El contrato de mensajes publica envío, respuestas, reacciones y lectura; no documenta una operación de edición de texto enviado. | Sin edición de mensajes enviados. No se equipara la capacidad de la aplicación móvil a la API. |

## Recorrido

Comentarios → seleccionar persona/publicación → respuesta de **Cuenta conectada** → **Editar comentario**. También funciona para una respuesta publicada desde el CRM que todavía no tenga eco del webhook. Preparar el texto, **Revisar cambio** y **Guardar en Facebook**. El modal muestra el texto exacto antes de publicarlo. Se conserva el borrador al fallar y la versión anterior aparece en **Editado · Historial**.

Se exige Inbox escritura, institución y cuenta correctas, canal conectado/verificado y salida activa. Antes del POST se consulta el comentario en Meta: identificador, autor y texto anterior deben coincidir. Después se exige `success: true` y una lectura del nuevo texto exacto. No se modifica un comentario del cliente ni otra Página. La versión original enviada en el cuerpo de SendJob permanece intacta; la proyección editada se guarda por separado. Los últimos20cambios están disponibles en el hilo; ProviderOperation conserva cada intención, actor, texto anterior/nuevo y resultado.

Un resultado incierto bloquea otro envío de edición para ese comentario. **Comprobar texto en Facebook** consulta Meta mediante GET y concilia el estado local tras vencer el lease; también permite recuperar un texto modificado directamente en Facebook; nunca repite el POST. Si Meta conserva el texto anterior o devuelve otro cambio, se actualiza la proyección y el operador puede revisar una nueva versión. Repetir la misma petición/OperationId no repite un efecto externo. Un permiso revocado o una cuenta cambiada durante la llamada impide dar por confirmado el guardado local.

No se crean tablas, no se ejecutan seeds ni se cambian permisos de Meta en este corte. Requiere que la Página ya disponga de sus permisos de administración de comentarios. La disponibilidad real depende de Meta, la autoría y el acceso de la cuenta; un anuncio/objeto inaccesible se presenta con causa y solución.

## Fuentes oficiales consultadas

- [Facebook Comment: Updating](https://developers.facebook.com/docs/graph-api/reference/comment).
- [Messenger/Instagram Message: Update no disponible](https://developers.facebook.com/docs/graph-api/reference/message).
- [Instagram Comment Moderation: endpoints permitidos](https://developers.facebook.com/documentation/instagram-platform/comment-moderation).
- [WhatsApp Message API](https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/whatsapp-business-phone-number/message-api).

La revisión de WhatsApp es una conclusión sobre el contrato publicado consultado, no una garantía sobre funcionalidades futuras o sobre aplicaciones móviles. No se cambia la versión Graph configurada por la cuenta al implementar el editor.

## Verificación de este corte

231pruebas backend seleccionadas (edición, hilos, eventos, canales, HTTP y P13),19frontend seleccionadas; tipos, ESLint modificado y build workspace pasan. La prueba de edición comprueba lectura/propiedad, texto cambiado fuera del CRM, rechazo, timeout, lectura final, replay, conciliación sólo GET y aislamiento de cuentas. SQL nuevo traducido/parseado para PostgreSQL; estos dobles no equivalen a una prueba nativa de rollback. La advertencia histórica de bundle grande permanece.

El despliegue y el recorrido publicado se registran en `artifacts/live/meta-comment-editing-20261119.json`. No se acredita una edición real de Meta hasta que aparezca allí su lectura final confirmada.
