# Inicio comercial desde el botón de campaña

El botón «Hablar con Juan Pablo» inicia la atención comercial de IA. Su título, por sí solo, no pide transferencia a una persona real. La excepción se aplica únicamente cuando el contexto del backend acredita una respuesta de botón a una plantilla de campaña aceptada por el canal; una petición explícita de humano mantiene su derivación normal.

La entrada real incorpora el hilo al Inbox mediante el filtro existente de campañas sin respuesta, conservando la conversación y el historial. No se crean hilos adicionales, se altera el consentimiento o se cambia Humano a IA. Los ecos, recibos y borradores sin entrada no promueven el hilo.

## Contexto y comportamiento

El proveedor debe aportar context.id que coincida con el ID de salida de una campaña de esa institución, cuenta e identidad. También deben coincidir conversación, orden de mensajes y cola actual del Snapshot. El texto de payload del botón se ignora como autoridad. Ante ausencia de evidencia no se finge atribución.

Se recupera el programa de la campaña, contrastado con el mensaje preparado y el catálogo activo. Si es inequívoco, se resuelve el especialista con las reglas existentes. Una aclaración posterior, cambio explícito o solicitud de otro programa prevalece sobre esa referencia. La referencia comercial no acredita matrícula ni modifica el expediente.

En el turno de entrada la IA usa el nombre de atención Juan Pablo, saluda con el nombre conocido del contacto, enlaza con su programa y aplica apertura/descubrimiento/valor y negociación según la consulta. Una pregunta útil y respuestas breves; sin volcar de nuevo toda la información ni repetir una presentación ya enviada en ese inicio. No se afirma ser empleado físico ni humano. El cuerpo antiguo de campaña no se incluye como nueva fuente financiera: importes y condiciones se consultan en la ficha vigente.

El contexto sólo se añade a respuestas privadas, tanto automáticas como sugeridas. El resto de mensajes mantiene su política habitual. La espera, citas, cuotas de voz, guardas de envío y control Humano permanecen.

## Verificación

181 pruebas seleccionadas pasan y Ruff pasa. Incluyen una base relacional aislada con la consulta real traducida y parseada para PostgreSQL: rechazo de otra institución, cuenta, identidad, cita distinta, texto que no es botón, salida no aceptada, Snapshot cambiado y mensajes futuros. Se comprueba el cambio de interés, ausencia de datos de campaña privados en público, clasificación de apertura y transición de campaña a Inbox por entrada real.

La selección amplia encontró ocho fallos reproducidos en una copia aislada de la revisión anterior: tres pruebas de filtro de riesgo usan un mapa parcial sin tablas de campañas, una espera34guías frente a37actuales y cuatro mocks de audio carecen de Cursor.description. Se excluyen explícitamente de las181 y no se declara toda la suite verde.

Publicación pendiente. No se enviaron mensajes de prueba, activaron campañas, cambiaron controles ni hicieron escrituras SIIE. Una prueba real de un nuevo clic posterior a la publicación queda separada de las pruebas automatizadas. Roadmap y aceptaciones de fases conservados.
