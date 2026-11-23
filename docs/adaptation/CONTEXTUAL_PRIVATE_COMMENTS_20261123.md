# Comentarios con entrega privada contextual — 23 de noviembre de 2026

Alcance autorizado: Facebook e Instagram de CBN, dentro de RinovaPlus. Distinguir información, preguntas, apoyo y quejas; consultar la publicación y la ficha vigente; entregar lo solicitado por privado sin repetir saludos nativos de Meta. No modifica modelos, voces o perfiles activos ni habilita campañas masivas.

## Biblioteca de la IA

Se instalan tres procedimientos revisados en la biblioteca del backend, con archivos SKILL.md y SHA-256 en manifest.json: `social-comment-intent`, `publication-context` y `private-reply-care`. La biblioteca pasa de 34 a 37 guías. Son adaptaciones propias para CBN a partir de las guías locales ig-reply/ig-dm y de las restricciones oficiales de Meta, no ejecutores externos ni permisos de un plugin. find-skills se usó para revisar disponibilidad; no se atribuye una instalación de terceros no realizada. El trabajador añade íntegramente las tres guías al contexto y conserva sus hashes en la operación.

## Flujo

1. Sólo comentarios nuevos elegibles de cuentas seleccionadas en Comentarios → IA para comentarios; opción apagada por defecto para las demás cuentas.
2. Consulta autenticada de la publicación: pie y, cuando no se identifica ningún programa, una imagen o miniatura real de Meta. La lectura visual sólo extrae el tema; no acredita el contenido completo de un video ni valida precios del anuncio. Descarga HTTPS desde CDN de Meta, sin redirecciones, DNS público fijado, máximo 2 MB, 16 millones de píxeles y reducción a 768 px. Un máximo de una lectura visual adicional, con reserva y trazabilidad; sin reintentos de resultados inciertos.
3. Una decisión estructurada: solicitud de información con programa presente en las fichas recuperadas → privado; apoyo → público breve; queja, solicitud humana o ambigüedad → revisión. La ficha vigente prevalece sobre el anuncio y las instrucciones configuradas. El contexto público nunca incorpora memoria privada de otros contactos.
4. Un único envío por turno. No se publica «te enviamos un privado» antes de la aceptación ni se confunde aceptación con entrega o lectura.
5. Antes del efecto se revalidan cuenta, fuente, texto original, control Humano, versión de política, arrendamiento y presupuestos. La fecha usada es la creación en Meta, no la fecha de importación. Un primer privado por comentario dentro de siete días; Live requiere revisión. Un intento anterior, incluido incierto, impide otro alta automática para ese comentario.
6. El proveedor recibe recipient.comment_id, nunca el ID público del autor como destinatario de chat. La aceptación conserva el recipient_id retornado por Meta. Cuando esa persona contesta en la misma aplicación/cuenta, el mensaje entrante conserva el programa de origen para la selección del especialista; una preferencia explícita posterior prevalece. Los siguientes mensajes dependen de la ventana ordinaria de 24 horas tras respuesta.
7. En el hilo se distingue «Mensaje privado» de la respuesta pública, con estado de cola y sin opción de editar el DM como si fuera un comentario. El operador también puede elegir «Enviar por privado» sobre el comentario concreto, con límite de 900 caracteres.

## Meta y conciliación histórica

El 23 de noviembre se desactivaron las tres reglas nativas de comentarios «Información», «Cuál es la dirección» y «Cómo se participa!!?». Respuesta automática, Mensaje automático y Preguntas frecuentes ya estaban apagados. No se cambiaron las reglas de organización de clientes potenciales.

La ronda anterior está documentada en PREICFES_INBOX_20261123.md y su registro privado ignorado por Git: 25 comentaristas del video de Facebook, un hilo adicional relacionado y tres destinatarios de Instagram. No se consideran atendidos sólo por la bienvenida antigua. En esta revisión se observaron los privados informativos con cuotas, total, vigencia y horarios, y los 39 hilos del CRM en ambas páginas. No se repiten estos envíos ni se declara que una nueva automatización haya entregado mensajes sin un evento nuevo comprobado.

## Validación y límites

Pruebas de elegibilidad, esquema, guías completas, decisión de canal, trabajador, proveedor, resultados inciertos, Humano, hilos y ventas. Tipos, lint y compilación de la interfaz. El cierre productivo se documentará con los identificadores de despliegue y la activación observada; una prueba simulada no acredita la aceptación de Meta ni lectura humana. El ensayo real de un comentario nuevo por canal sigue siendo distinto de publicar el código.

Documentación primaria consultada: [Facebook Private Replies](https://developers.facebook.com/documentation/business-messaging/messenger-platform/discovery/private-replies), [Instagram Private Replies](https://developers.facebook.com/documentation/instagram-platform/private-replies).

P4/P13 conservan su aceptación inicial; esta ampliación añade capacidad y validación propia. P22 conserva 3/5 hitos técnicos y ninguna aceptación comercial final. Sin DDL, seeds, contenedores nuevos ni escrituras SIIE.

## Ampliación solicitada durante la integración

Los privados nativos previos no estaban todos en CRM porque el ingreso sólo registraba entradas. Se añade importación por cuenta en Inbox → Traer historial de Meta, con GET autenticado y paginación, sin enviar ni regenerar respuestas. Copia hasta20 mensajes salientes recientes por hilo, fecha original, destinatario verificado por participantes y nombre disponible; deduplica por cuenta/ID externo y omite salientes que ya pertenecen al outbox. No amplía la ventana de respuesta, cambia Humano, marca matrícula ni procesa IA histórica. La recepción futura de ecos de Messenger requiere message_echoes en la app y en la Página; Instagram usa los eventos de mensajes disponibles. La proyección de un privado aceptado se realiza después de guardar su aceptación, por lo que un error de proyección no repite el envío.

Se corrigió la detección del literal Contacto de Instagram/Messenger y se persiste sólo el nombre público verificado sobre etiquetas generadas; los nombres declarados o revisados permanecen. La vista ordena los mensajes cargados por su fecha original y distingue Importado de Meta. La paginación conserva el cursor de secuencia; la consulta no acredita recuperar todo el histórico remoto ni los adjuntos cuyos datos Meta no entregue.

Validación previa a publicación:279backend y59frontend;tipos,ESLint,Ruff ybuild aprobados. Advertencia histórica del bundle conservada.


## Inbox saliente verificado; politica acotada preparada - 2026-11-23

81dbf7b publicado: backend zhut9vvwzimdq1jdormu7c96 Success/Running4m17s y frontend cgurkkjqbnmcnhlvso4hi2a2 Success38s. Importacion real Messenger:66+4+0 mensajes incorporados, cero envios; busqueda PRE-ICFES muestra28conversaciones. message_echoes suscrito en app y sincronizacion de Pagina confirmada por proveedor. Nombres reales visibles en listado. Guardado general de IA devolvio422 al activar cuentas; campo exacto no identificado. Se separa PUT comments/policy con validacion propia, revisionCAS, permiso/reautenticacion/historial y mezcla solo de cuatro campos sin tocar modelos/voces. Se corrige indicador de carga residual y hora previewAt original.281backend/60frontend,tipos/ESLint/Ruff/build pasan; advertencia historica de bundle. Publicacion del ajuste, activacion y nuevo comentario real aun pendientes; no acreditar automatizacion por importar. P4/P13/P22 conservan estados. SinDDL,seeds,nuevoscontenedores niSIIEwrites.



## Origen de comentarios y bandeja sin respuesta preparados - 2026-11-23

El titular pide etiqueta discreta y clasificar fuera del Inbox los privados iniciados por comentario hasta que la persona responda. Se agregan Desde comentario, vista rapida Desde comentarios (sin respuesta) y filtro Desde comentarios todas. La bandeja principal excluye solo origen comentario sin ninguna entrada; una entrada real lo incorpora automaticamente conservando origen, sin cambiar etapa, control, SLA ni enviar mensajes. Origen acreditado por cola privada, atribucion real de comentario o texto explicito de la ronda nativa PRE-ICFES confirmada; no se clasifica cualquier DM por mencionar un programa. Consulta PostgreSQL parseada y ensayo relacional de transicion sin escrituras de negocio;319backend y47frontend focalizadas pasan (60frontend previas), tipos/ESLint/Ruff/workspacebuild pasan. eff0c99 backend c6fpptvpsuxotqmhzdsdbtyz Success4m16s, frontend6a810dqznwuwrnv45clw6jy5Success. Publicacion y validacion visual de esta ampliacion pendientes. P4/P13/P22 conservan estados.



## Inbox de comentarios publicado y verificado - 2026-11-23

e748487 backend uavozvcl3ln0gx1fvgyfg0yk Success/Running4m17s, frontend6cznheznzfgqcil8tkfzgcmxSuccess44s. Vista real Desde comentarios:23hilos sin entrada, etiqueta compacta sin sustituir preview y hora original; bandeja principal filtrada PRE-ICFES:6hilos activos, conservan origen cuando esta acreditado. Antes de clasificar se verificaron29hilos de la ronda (26Messenger/3Instagram), incluido privado nativo de Instagram;70mensajes Messenger incorporados (66+4+0), sin reenviar. Primera consulta IG fallo temporalmente; posteriores completaron y mostraron el hilo privado, sin afirmar total exacto ni todo el historico remoto. Perfiles disponibles se resuelven sin abrir; Meta puede devolver usuario en lugar de nombre completo. Tres reglas nativas de comentarios apagadas; saludos/FAQ ya apagados, reglas organizativas preservadas. App message_echoes y reconciliacion de Pagina confirmadas. Politica privada solo CBN Facebook/Instagram guardada y comprobada tras recarga, ScentraWPP no seleccionada. Nuevo comentario real corto de prueba recibio una respuesta publica pertinente; no acredita DM automatico. Ensayo explicito privado solicitado y pendiente en este corte.319backend/47frontend focalizadas (60previas),tipos/ESLint/Ruff/workspacebuild pasan; bundlehistorico. Evidencia artifacts/live/contextual-private-comments-20261123.json. P4/P13 iniciales y P22 3/5tecnico/0aceptacion conservados. SinDDL,seeds,nuevoscontenedores niSIIEwrites.



## Ensayo real de privados: rechazo de borrador y contrato de respaldo reforzado - 2026-11-23

Dos comentarios reales nuevos del titular: el corto se publico con informacion pertinente; la solicitud explicita de precios por privado fallo comment_ai_invalid_draft antes de encolar. Diagnostico confirma Gemini provider_temporary_failure y OpenRouter GPT4.1mini completed en ambos; no se conserva el contenido rechazado ni se atribuye un campo/longitud concreto. Se elimina la instruccion incondicional de entrega publica solo del contexto de decision privada, sin incorporar memoria privada. Respaldo usa json_schema estricto para los cinco campos de entrega, enums de programas recuperados y texto max900; rutas ordinarias conservan contrato anterior. Intencion information con programa validado se entrega por privado; apoyo sigue publico y ambiguedad revision. Huella incluye instrucciones sociales completas. Errores futuros distinguen extension/incompleto/contrato sin exponer borradores.342backend/Ruff y tipos/ESLint/workspacebuild pasan; sin reintento ni envio de operaciones fallidas. Publicacion y ensayo posterior pendientes. Filtros de origen e importacion ya verificados en e748487; P4/P13/P22 no cambian.



## Compatibilidad del identificador de programa en revision - 2026-11-23

f1c0421 publicado saludable: backend ntg6s7ruukfvxwkfrv0y83xz4m19s, frontend4yr2cxqiycmpzqhqo9tbyyfz45s. Tercer comentario real recibido: Gemini rechazo provider_rejected_request antes de generar y no se ejecuto respaldo; ningun privado enviado por ese intento. Se retira el enum con valor vacio introducido en program_id del esquema Gemini; identificador sigue string y la pertenencia a fichas se valida en backend antes de entregar. Esquema estricto de campos/canal y max900 en OpenRouter conservados.78pruebas focalizadas pasan. No se identifica otro campo de rechazo a partir del mensaje sanitizado. Ensayo real posterior pendiente; sin replay de intentos anteriores.



## Principal OpenRouter por instruccion del titular preparado - 2026-11-23

El titular solicita Sonnet4.6 principal y Sonnet5.5 respaldo, en lugar de generar lenguaje primero con Gemini; no se atribuye el rechazo previo al plan gratuito sin evidencia. P21 agrega primary opcional, misma biblioteca/contexto/guardas y reserva por ruta, sin ejecutar la funcion Gemini cuando hay principal explicito. Respaldo ante404/429/503 o timeout puro optativo; sin replay de Meta. Seleccion y tarifas desde catalogo autenticado, omision de temperatura no soportada y razonamiento low solo declarado. Claude no recibe maxLength no soportado; limite900 permanece en instrucciones y validacion backend, sin cortar mensajes. Guardado acotado con CAS/reautenticacion/historial conserva prompts/voces/privados. Simulador y ASR/vision conservan motores propios; ensayo sintetico no se sustituye por principal productivo.391backend/67frontend,tipos/ESLint/Ruff/workspacebuild pasan; bundlehistorico. Publicacion, seleccion nativa de ambos modelos y pruebas reales pendientes. Seleccion operativa autorizada no cierra por si sola P22 ni su reparto por etapas/piloto comercial.

## Sonnet principal y respaldo publicados; privado real entregado — 2026-11-23

Por instrucción del titular, OpenRouter/Sonnet4.6 es el principal de lenguaje automático para mensajes y comentarios; Sonnet5.5 es el respaldo. Configuración32 guardada y confirmada tras recarga, con topes del catálogo3/15 y2/10USD por millón entrada/salida respectivamente. Gemini conserva ASR/visión y los simuladores mantienen selección propia. No se atribuye el rechazo anterior al plan gratuito sin evidencia.

b80151b saludable: backend leys9qoufgwqpqtd3p2csudg Success/Running4m18s, frontend qryv2boms7e1yphqvjdgfq6g Success40s. Un comentario técnico nuevo en el video PRE-ICFES generó con Sonnet4.6: IA confirmada13:41:04, privado entregado13:41:20, una salida visible en Comentarios y en Inbox con nombre público y etiqueta Desde comentario. La bandeja sin respuesta pasó23→24 por esta prueba; no se reenviaron los intentos fallidos previos. Nueva prueba automática de Instagram todavía pendiente. El comentario técnico permanece publicado; no se elimina sin confirmación específica.

Ensayo aislado3b6a952c-9ed7-44cf-896e-8e265638e469:503sintético→Sonnet5.5 real superado, una generación,5560/154tokens, reservaUSD0,036368 dentro0,05; reserva no es factura. Programa/duración/jornada conservados y memoria privada excluida en público, cero mensajes/CRM. El principal sintético del ensayo conserva etiqueta Gemini; no acredita una caída natural de Sonnet4.6.391backend/67frontend,tipos/ESLint/Ruff/workspacebuild pasan; bundlehistórico. Evidencia artifacts/live/sonnet-routing-20261123.json. P4/P13 iniciales conservadas. P22 sigue3/5técnico/0aceptación comercial: selección operativa de cadena autorizada, pipeline por etapas y piloto/reversión pendientes. SinDDL,seeds,contenedores nuevos niSIIEwrites.
