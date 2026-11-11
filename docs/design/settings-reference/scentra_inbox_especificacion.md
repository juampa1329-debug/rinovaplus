# Especificación funcional de Inbox — Scentra +AI

**Aplicación:** [Scentra +AI][1]  
**Revisión:** 13 de octubre de 2026

## Estructura de la pestaña

Inbox es una vista operativa de tres zonas: una columna para la bandeja y sus filtros, un panel central para el hilo seleccionado y un panel lateral CRM que se puede ocultar. En la parte superior de la bandeja hay dos modos: **Mensajes** y **Comentarios**. El modo cambia el contenido de la lista y el panel central; en Comentarios, el panel lateral pasa a mostrar los ajustes de IA para comentarios. La estructura y estos controles se reflejan en la interfaz y en el bundle público del front-end. [1] [2]

## Bandeja de Mensajes

### Sincronización y búsqueda

El encabezado **Inbox** muestra un contador que cambia según el modo: conversaciones/chats o elementos sin leer en Mensajes, y comentarios en Comentarios. El indicador de sincronización puede mostrar **Sincronizando**, **Actualizado** con hora o **Sincronización pendiente**; la ayuda dice que la bandeja permanece visible cuando la sincronización en segundo plano se pausa.

El buscador tiene el placeholder `Buscar nombre, teléfono o vista previa...` y el nombre accesible **Buscar conversaciones**. El botón de borrar búsqueda aparece cuando hay una consulta. La consulta filtra la lista por datos de búsqueda y no abre por sí misma una conversación.

### Filtros

El botón **Filtros** despliega un panel con:

- **Canal**: botones de canal, más **Todos**. Las opciones disponibles dependen de los canales presentes en la bandeja.
- **Agente IA**: selector con **Todos los agentes** y los agentes activos compatibles con el canal.
- Un resumen de operación con contadores **sin leer**, **asignadas** y **SLA**.
- **Vistas rápidas**: `Todos`, `Sin leer`, `Míos`, `Sin asignar`, `SLA`, `Calientes`, `Abandono`, `Humano` e `IA`.
- **Restablecer filtros**, que limpia búsqueda, canal, vista rápida y agente IA.

La ayuda recomienda empezar con **Sin leer**, elementos asignados a la persona operadora y **SLA** vencido. El contador de los filtros rápidos se actualiza con la lista.

### Elementos de la lista

En Mensajes, cada fila puede representar una conversación o una notificación interna de Scentra. Una conversación muestra avatar/nombre, canal, estado leído/no leído, responsable humano, agente IA, etapa de seguimiento y vista previa del último mensaje. Si hay datos disponibles, puede añadir puntaje/temperatura comercial, probabilidad de conversión, riesgo de abandono y vencimiento SLA. La lista carga más elementos al desplazarse.

Las notificaciones internas aparecen diferenciadas como elementos de Scentra, con severidad/estado y marcas como **Interno**, **Sin respuesta**, **Leída** o **Fijada**. Estos elementos no son mensajes salientes al cliente.

## Hilo de conversación

### Encabezado y estado de atención

Al seleccionar una conversación, el encabezado central muestra el contacto, el canal y su identificador/nombre de origen. Debajo presenta indicadores del modo actual —IA o atención humana—, el SLA, pedidos pendientes cuando existen y un resumen del estado de atención.

Los controles observados en el encabezado son:

- **Humano inactivo / Humano activo**: activa o pausa la intervención humana. La ayuda indica que, con takeover humano, la IA se pausa para evitar respuestas duplicadas; sin takeover, la IA puede asistir.
- **Marcar leído**: actualiza el estado de lectura.
- **Sonido activo / Sonido inactivo**: alterna el sonido de notificación.
- **Avisos activos / Avisos inactivos**: alterna avisos del navegador; aparece deshabilitado si el navegador no lo admite.
- **CRM / Ocultar CRM**: muestra u oculta el panel lateral.

El hilo presenta mensajes entrantes y salientes, separadores por fecha y la vista correspondiente al tipo de mensaje. La ayuda recomienda comprobar destinatario y contexto antes de enviar media o productos, y evitar que una persona, un trigger y la IA respondan al mismo tiempo.

### Compositor de mensajes

El compositor aparece al tener una conversación seleccionada. Incluye un campo de texto `Escribe un mensaje...`, un botón de emojis, **Adjuntar**, **Grabar nota de voz** y **Enviar mensaje**. Envío queda deshabilitado si no hay texto, adjunto o producto, o si ya se está enviando.

**Adjuntar** abre un menú con `Imagen`, `GIF`, `Sticker`, `Video`, `Documento`, `Audio` y `Producto (Catálogo)`. El selector de archivo acepta imágenes, video, audio, PDF, DOC/DOCX, XLS/XLSX y TXT. Los adjuntos y productos muestran una vista previa y **Quitar** antes de enviarse. La grabación ofrece **Listo** o **Cancelar**; el selector de emojis puede abrir un buscador de emojis. [2]

El botón **Enviar mensaje** es una acción externa que entrega el mensaje al contacto por el canal de la conversación; no se activó durante la revisión.

## Modo Comentarios

El modo **Comentarios** reemplaza la lista de chats por una lista de comentarios sociales. Las filas muestran autor, canal y estado —pendiente/abierto o respondido—. Al elegir un comentario, el panel central muestra la publicación asociada, medios disponibles, el comentario seleccionado y el hilo de respuestas.

El compositor de comentarios incluye:

- Área de texto `Responder comentario...` y control para insertar emojis.
- Selector **Tipo de media**: `Imagen`, `GIF`, `Sticker`.
- URL pública de media opcional para Facebook, Instagram o TikTok; **Quitar** elimina esa URL.
- **Reaccionar**, que abre opciones de reacción (👍, ❤️, 👏, 🔥, 😍, 😂, 😮, 😢).
- **Generar con IA**, que prepara una respuesta sugerida, y **Usar sugerencia**, que la copia al compositor.
- **Responder**, que publica la respuesta. Se deshabilita si el texto está vacío o hay una operación en curso.
- **Refrescar**, que actualiza la lista de comentarios.

El panel lateral de este modo se llama **IA Comentarios**. Tiene casillas **Activar IA para comentarios**, **Generar sugerencias automáticas** y **Responder automáticamente comentarios nuevos**; campo **Tono**, área **Entrenamiento** y **Guardar entrenamiento**. La ayuda explica que con IA activada se pueden generar respuestas manualmente; las sugerencias automáticas preparan borradores. Al activar respuesta automática, la IA puede responder públicamente comentarios nuevos procesados por webhook. No se cambió esta configuración ni se publicó una respuesta. [2]

## Panel CRM del contacto

El panel lateral **CRM - Cliente** se abre desde el encabezado del hilo y puede cerrarse. El panel presenta un resumen de contacto con canal, estado, puntaje IA, etapa CRM, modo humano/IA, pedidos pendientes y etiquetas; después agrupa datos y controles comerciales. Los valores mostrados dependen de la conversación seleccionada y no se reproducen aquí.

### Asignación, modo y etapa

La tarjeta de acciones contiene:

- **Asignarme**: asigna la conversación al usuario actual.
- **Takeover humano / Takeover activo**: activa o desactiva atención humana.
- **Score IA**: recalcula el puntaje.
- **Etapa**: selector de etapa CRM. Si la empresa no define etapas, el front-end ofrece `Sin etapa`, `Contactado`, `Interés`, `Intención compra`, `Pago pendiente` y `Pago confirmado`; con un pipeline configurado, las etapas provienen de ese pipeline.

La ficha muestra teléfono y canal, persona asignada con **Liberar**, y **Agente IA responsable** con selector —incluida `IA general`—, **Liberar IA**, **Reiniciar contexto IA** y **Procesar IA ahora**. Las opciones de agentes se filtran por compatibilidad con el canal.

### Ficha editable y operación

Los campos CRM base son **Nombre**, **Apellido**, **Ciudad**, **Tipo** (`Sin definir`, `Minorista`, `Mayorista`, `VIP`), **Tipo de identificación**, **Número de identificación**, **Etapa**, **Pago** (`Sin estado`, `Pendiente`, `Pagado`, `Fallido`), **Intereses**, **Etiquetas** y **Notas**. **Guardar ficha** persiste los cambios. La casilla **Intervención humana** permite incluir takeover en la ficha. El tipo de identificación y las etapas pueden depender de la configuración de la empresa.

Los campos personalizados se generan desde la configuración CRM: pueden ser casillas booleanas, selectores con opciones o entradas de texto/número según el tipo definido. La interfaz no fija una lista universal de campos personalizados.

La tarjeta **Operación** contiene **Prioridad** (`Baja`, `Normal`, `Alta`, `Urgente`), **Puntaje** numérico de 0 a 100, **Temperatura** (`Frío`, `Tibio`, `Caliente`), **SLA** de fecha/hora y **Recalcular puntaje**.

### Inteligencia y contexto

**Inteligencia predictiva** muestra probabilidad de conversión, engagement, riesgo de abandono, acción recomendada y sugerencias de canal/horario/frecuencia. Sus controles ejecutan `Puntaje comercial`, `Riesgo de abandono` y `Remarketing`; no envían mensajes automáticamente por el solo hecho de generar la predicción.

**Panel de análisis Inbox** muestra señales de voz, visuales y memoria, además de referencias aprobadas. Tiene **Refrescar** y **Sincronizar** para actualizar el análisis y sincronizar memoria. Las señales pueden incluir intención, sentimiento, urgencia, confianza y resumen, según el material recibido.

**Referencias visuales aprobadas** permite **Usar** una imagen como borrador o **Enviar** al hilo. **Web/Image Search Intelligence** ofrece consulta de texto, tipo de búsqueda (`Web + imagen`, `Solo web`, `Solo imagen`), proveedor y botón **Buscar**. Los resultados aparecen con estado y acciones **Aprobar**, **Rechazar**, **Usar** o **Enviar**. La interfaz advierte que los resultados externos no se envían automáticamente y deben revisarse por seguridad; los resultados bloqueados no se pueden aprobar/enviar. Enviar una referencia es una acción externa al contacto. [2]

### Seguimientos, duplicados y auditoría del contacto

- **Tareas y follow-up**: título, fecha/hora de vencimiento, prioridad (`Normal`, `Alta`, `Urgente`, `Baja`) y **Crear**. La lista muestra hasta cinco tareas; una tarea abierta puede marcarse completa.
- **Duplicados posibles**: presenta candidatos y razón/puntaje de coincidencia. **Fusionar** une registros; es una acción que puede afectar datos CRM y no se probó.
- **Contexto IA**: muestra resumen y hechos recordados; **Refrescar** actualiza el contexto y **Procesar con IA ahora** solicita un nuevo procesamiento.
- **Timeline del cliente**: registra eventos CRM y tiene **Refrescar**.
- **Estados Meta**: muestra eventos de entrega/estado asociados al canal.

### Cobros Stay, cuando el módulo está disponible

El panel puede mostrar **Cobros Stay**. Incluye **Refrescar** y un formulario con **Valor**, **Moneda**, **Proveedor**, **Canal de entrega**, **Concepto**, **Correo opcional** y **Link de pago opcional**. Los canales incluyen WhatsApp, correo, sitio web, punto de venta y copiar link; los proveedores dependen de la configuración.

**Enviar cobro** crea el registro de cobro. Cada cobro puede ofrecer **Usar mensaje**, **Email**, **Web/POS**, **Copiar**, **Enviado** o **Pagado**, según su estado. Crear o marcar cobros modifica registros financieros; estas acciones no se ejecutaron.

## Dependencias y límites de la observación

Los modos, filtros, datos del hilo y las secciones del CRM cambian según canal, permisos, configuración de la empresa y módulos activos. En la sesión revisada no se abrió una conversación de cliente ni se leyó el contenido de mensajes. La especificación se construyó con ayuda contextual, etiquetas y tipos de control visibles, y con el código público de la interfaz para describir controles condicionales. No se enviaron mensajes/comentarios, no se asignaron contactos, no se guardaron fichas ni se ejecutaron búsquedas, fusiones o cobros.

## Referencias

[1]: https://app.scentra-ai.online/ "Scentra +AI"
[2]: https://app.scentra-ai.online/assets/index-DWDcwbSI.js "Bundle público de la interfaz de Scentra +AI"
