# Comentarios por persona y publicación

Mejora solicitada el 18 de noviembre de 2026. La bandeja agrupa por **institución, cuenta conectada, publicación y persona**. Un mismo autor en otra publicación o cuenta tiene otro hilo. Cada comentario de esa persona conserva su propio botón Responder, control IA/Humano, estado, versión y vínculo CRM. Las respuestas de la cuenta conectada se muestran debajo del comentario exacto que contestan.

## Presentación

Se conserva la identidad CBN: Manrope/Source Sans 3 y tokens petrol/lima/claro del producto. El directorio muestra autor, canal, cuenta, publicación y cantidades; el centro conserva la vista previa del post y un hilo con jerarquía de encabezados. Las respuestas de la cuenta tienen nombre, fecha, estado y la etiqueta Cuenta conectada. El comentario elegido queda señalado también con texto, y el compositor explica a quién y a qué texto responderá. Cambiar destinatario respeta el guard de borrador; el botón Responder lleva el foco al compositor. Colores/transiciones usan tokens y respetan movimiento reducido.

Se aplicaron frontend-design y UI/UX Pro Max. La consulta UX específica se afinó a jerarquía/navegación después de descartar un primer resultado de apilamiento visual que no correspondía al problema. Se conservó la paleta autorizada; no se generó otra identidad ni se añadieron bibliotecas de interfaz.

## Vínculos y seguridad

- El GET de comentarios admite `view=threads` en la producción PostgreSQL. Agrupación, filtros, totales y paginación se calculan en SQL sobre la institución autorizada, no agrupando sólo los primeros 25 registros en el navegador.
- `GET /api/institution/comments/{identity}/thread` resuelve el grupo del comentario o de su respuesta de CBN; conserva enlaces de notificaciones antiguas y mantiene visible el comentario original aunque esté fuera de la página.
- Las respuestas se vinculan por parent_id, parent_comment_id o reply_to_comment_id del proveedor; el ID de proveedor del SendJob resuelve ecos propios sin padre. La cadena está acotada, detecta ciclos y no cruza cuentas o publicaciones explícitamente distintas.
- Un eco de Meta y su envío CRM con el mismo ID se muestran una sola vez. Los envíos sin eco aún conservan estado en cola/aceptado/fallido/incierto; no se fabrica publicación ni se reintenta un efecto incierto.
- Si falta evidencia del comentario original, se conserva la respuesta como contexto no recibido. No se deduce el destinatario por coincidencia de texto, nombre o proximidad de fechas.
- Las notificaciones excluyen respuestas propias mediante ID de cuenta, ID Instagram, proyección propia o envío CRM. Marcar todas leídas mantiene el cursor por usuario y no cambia el control IA ni borra comentarios.
- Los webhooks conservan metadatos de padre/publicación al recibir una edición parcial. Las respuestas propias no son nuevos prospectos ni destinos para otra respuesta pública.

La vista nueva no añade tablas, permisos, claves ni llamadas de escritura a Meta. Los controles de autorización, CSRF, versión e idempotencia existentes siguen aplicándose a cada comentario seleccionado. El transporte histórico SQL conserva su lista anterior; no se recertifican releases ni checkers congelados.

## Verificación

189 pruebas backend seleccionadas y 23 frontend correctas; TypeScript, lint modificado y build workspace correctos. La advertencia previa de bundle grande permanece. La primera invocación apuntó a una ruta de suite inexistente y no ejecutó tests; se corrigió la ruta. Una aserción inicial de UI buscaba un contador exacto sin su texto de contexto; se corrigió el selector, sin alterar el comportamiento para hacer pasar el ensayo.

Ensayo SELECT en el PostgreSQL existente, sin escrituras ni contenedores nuevos: 44 registros, 24 propios y 24 propios vinculados; 17 grupos. Tres detalles reales devolvieron 1 comentario y 2/2/1 respuestas, respectivamente. Un SELECT con 15 filas ficticias probó mismo autor/post, otra persona, otra cuenta, otra publicación, padre ausente, padre de otro post, ciclo, eco de SendJob y respuestas anidadas. La comprobación de consultas se realizó en un proceso operador separado; la autorización de la aplicación no se modificó.

La comprobación desplegada y el estado final se registran en `tasks/comment-threads-progress.json`. No se publica un comentario de prueba nuevo ni se envía una respuesta pública por el mero despliegue de esta mejora.

## Relación con el roadmap

Es una mejora del flujo de Comentarios sobre el alcance existente, con peso adicional cero. El cierre original P0–P11 y P12 auxiliar conservan la aceptación explícita; las fases adicionales y las seis mejoras de operación mantienen sus estados propios. Al informar pendientes siempre se incluye nombre y propósito, según [el resumen vigente](PENDING_PHASES.md).
