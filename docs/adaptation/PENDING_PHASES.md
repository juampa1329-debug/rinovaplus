# Fases adicionales pendientes

Corte: 22 de noviembre de 2026. El roadmap original P0–P11 está aceptado al 100% en sus alcances documentados; P12 auxiliar de puesta online está aceptada para PostgreSQL/Meta. Las fases siguientes tienen seguimiento propio y no aportan peso a los 56 criterios originales. P16 ya tiene despliegue y pruebas reales de clave única, aspirantes y estudiantes; la primera página de 25 programas ya se copió localmente; el detalle financiero sigue bloqueado por el productor. La evidencia del18-11 se conserva como historia.

| Fase | De qué trata | Estado |
|---|---|---|
| P13 · Académico y agentes de venta por programa | Fichas por escuela, 34 guías nativas de ventas, prompts, memoria/grafo y calificación con evidencia. | Aceptada en alcance inicial, 4/4 (100%). Fichas/fuentes, orientación, financiación/objeciones y cambio Barismo→Software comprobados; nombre/ciudad/objetivo conservados. Entrada real en Humano sin respuesta automática durante más de cuatro minutos; chat restaurado a IA. Inglés sin tarifa confirmada y SLA sin umbral permanecen explícitos. Agentes/modelos por etapa corresponden a P22. Evidencia: artifacts/live/p13-close-review-20261120.json. |
| P14 · Entrenamiento y mejora del agente de ventas | Definir datos y evaluación para mejorar orientación comercial a partir del comportamiento de clientes; concretar un plan medible. | Plan pendiente; no se acredita una red neuronal nueva ni eficacia institucional. |
| P15 · Correos y notificaciones | Recuperación/invitaciones, destinatarios y preferencias por evento, alertas, informes y plantillas HTML con logos y firmas visuales. | Aceptada en alcance inicial, 7/7 (100%). Informes de auditoría y recibos manuales; monitor automático de respaldos sigue OPS-05. |
| P16 · Integración SIIE | Programas/ofertas y planes financieros; aspirantes, estudiantes y matrículas con contactos nativos. | Parcial, 0/5. Clave única, dos páginas de25aspirantes y8estudiantes comprobados. Alcance actualizado por el propietario: período no obligatorio para catálogo base y fechas financieras opcionales. Copia local de25programas verificada. Ajustes manuales, botón por ficha, reporte de faltantes y rediseño en validación; detalle financiero aún pendiente. Los503 de Offer sin datos parciales conservan su evidencia y deben volver a consultarse. |
| P17 · TikTok | Conexión y automatizaciones permitidas por la API, con cuenta y pruebas reales propias. | Diferida por el propietario, 0/5. |
| P18 · Seguridad y ciberseguridad | Tokens/sesiones, límites por IP y cuenta, 2FA, CAPTCHA, inyecciones, infraestructura y respuesta a incidentes. | Planificada, 0/8; controles previos conservados, auditoría integral pendiente. |
| [P19 · Voces y notas de audio](P19_VOICES_AUDIO.md) | ElevenLabs, voces por escuela/agente, generación contextual y notas compatibles con WhatsApp; ampliación de ambiente y tecleo. | Alcance técnico inicial aceptado, 5/5. Faders, ducking y generador de muestras aceptados. El propietario rechazó las pistas sintéticas y también las sustitutas CC0 grabadas por sonar artificiales. Propone aportar sus propias grabaciones; archivos y nueva escucha pendientes. Preview de Juampa de 12,2465 s con oficina 60%/tecleo 40%, sin guardar ni enviar; contador 6.761 sin incremento, política vigente 23 conservada. No declarar aceptada la ampliación sonora. |
| [P20 · Llamadas de WhatsApp y agentes de voz](P20_WHATSAPP_CALLS.md) | Número colombiano institucional, entrantes/salientes, seguimiento con contexto CRM, tomar/transferir y escuchar en vivo por un recorrido compatible. | Planificada, 0/8; implementación 0%. Cuenta/ruteo, audio en vivo, transferencia y coste pendientes de validar; sin exigir Twilio ni otro número. |
| [P21 · Catálogos y respaldo de modelos de lenguaje](P21_LANGUAGE_RESILIENCE.md) | Catálogo por empresa/familia, pruebas aisladas y alternativas compatibles ante rechazos del principal. | Aceptada en alcance inicial, 4/4 (100%). 503 privado y429 público simulados → GPT-4.1 mini real respondió en una consulta por caso, con hechos conservados y memoria privada excluida en público. GET sin duplicar; Humano/principal saludable cero llamadas y reservas. Gemini y configuración29 intactos. Sin caída productiva ni envío WhatsApp; ASR/monitor proactivo/circuito distribuido fuera del alcance. Ampliación20Nov publicada/activa en revisión30: recuperación explícita de DM leída; timeout privado/público sintético con GPT-4.1 mini real satisfactorio, una generación por caso y GET sin repetir. No se indujo caída real ni se incluyó ASR/TTS. Ver p21-timeout-recovery-20261120.json. |
| [P22 · Pruebas de modelos candidatos](P22_MODEL_CANDIDATES.md) | Comparar modelos con las mismas skills, fichas, memoria y casos de venta; decidir por función y etapa. Incluye Mistral y ensayos de DeepSeek/Qwen. | En evaluación: 3 hitos técnicos trabajados de5 (60% técnico), 0/5 aceptaciones comerciales (0%); elección del titular pendiente. Matriz inicial25respuestas/5modelos y2fallos de proveedor; presupuesto total USD10 autorizado. Muestras al44 para revisión, versiones breves y calendario comercial en validación. Recomendaciones por etapa preparadas, sin cambiar modelos activos. Faltan elección del titular, enlace con el pipeline y piloto/reversión. Nueva matriz21Nov: 25/25 respuestas de Gemini3.8, Sonnet4.6, GPT4.1 completo, Sonnet5.5 y Opus5.5; 25 copias al44 entregadas, chat restauradoIA. USD1,091842 estimados en esta ronda; acumulado conocido+reservado USD1,925462831/10. Defectos comerciales señalados y selección del titular pendiente. Informe: [comparativa21Nov](P22_COMPARISON_20261121.md); matriz20Nov conservada. |

Además siguen abiertas OPS-01–OPS-06: copia externa, custodia independiente de clave, RPO/RTO, retención/espacio, alertas entregadas y conciliación adicional DB/archivos. Se registran en `tasks/operations-hardening-backlog.json`; fueron aceptadas como límites del alcance actual y no se declaran implementadas.

### Revisión de audio y agentes del 20-11-2026

La muestra de pistas grabadas CC0 también fue rechazada por el propietario.
No se guardaron sus niveles; se esperan las grabaciones propias propuestas.
La carga de pistas personales desde el frontend no está implementada todavía.
P13 aceptada en alcance inicial tras el piloto real, no por el mero despliegue.
El plazo institucional de SLA aparece sin configurar: no se inventó un umbral.

### OpenRouter — 20-11-2026

Clave guardada directamente por el propietario y catálogo autenticado cargado:
408 modelos de texto antes del filtro interactivo. Empresas y familias funcionan.
Se corrige la oferta de variantes batch/no-chat para evitar elecciones incompatibles.
Actualización: Gemma4 26B gratuito respondió en el simulador. Se guardó como selección de OpenRouter y respaldo institucional autorizado; Gemini permanece principal.
Conectar este proveedor no cierra la validación comercial de P13 ni las demás fases.

### P22 · Cobertura explícita de skills — 22-11-2026

Evaluación solicitada por el titular terminada: siete situaciones con las17guías comerciales completas y los cinco candidatos,35/35respuestas válidas. Inclusión completa y SHA comprobados para cada modelo;35copias al44 (6leídas/29entregadas), chat restauradoIA tras recarga. USD1,52840825estimados nuevos; acumulado conocido+reservado USD3,453871081/10. Se documentan suposiciones sobre horarios, reglas de reserva no sustentadas y exceso de extensión. [Informe detallado](P22_FULL_SKILLS_20261122.md). P22 conserva60%técnico/0%aceptación comercial: elección del titular, pipeline y piloto/reversión pendientes. Consulta manual de cuentas OpenRouter/ElevenLabs publicada y comprobada: consumo/límite de la clave OpenRouter y plan/unidades/renovación/voces ElevenLabs reales. Saldo global OpenRouter pendiente de la clave administrativa que el titular añadirá después. No cambia la elección de agentes ni cierra la fase. Ver [cuentas de proveedores](PROVIDER_BALANCES_20261122.md).

### Manual comercial CBN — 22-11-2026

El titular autoriza adaptar sus pautas a todos los programas con datos de las fichas vigentes. Política v7 publicada en def2232, patrones por situación y cuatro skills revisadas;204pruebas backend/Ruff pasan.35respuestas válidas,17skills completas verificadas por modelo en los casos pertinentes y35copias entregadas al44. Chat restauradoIA tras recarga; modelos activos conservados. USD1,5569715nuevos; acumulado conocido+reservado USD5,010842581/10. Se documentan supuestos de horario de GPT, generalización de reglas de reserva y extensión/advertencias. Elección del titular/pipeline/piloto pendientes. [Seguimiento](P22_MANUAL_CBN_20261122.md). No cambia selección de modelos ni aceptación de P22.

### Inbox responsive — 23-11-2026

Cierre de menú móvil y retorno al listado hasta900px preparados,46pruebas frontend/tipos/lint/build institucional pasan. [Detalle](INBOX_RESPONSIVE_NAV_20261123.md). No cambia aceptaciones de fases ni acredita los envíos PRE-ICFES pendientes.


## PRE-ICFES e Inbox, 23 de noviembre de 2026
Ficha local y especialista creados desde UI; 27 programas y 28 agentes. Una respuesta Instagram aceptada y otra en cola por ventana cerrada; sin acreditar el segundo envío ni todos los comentarios. Navegación c987d85 publicada/verificada. Carga progresiva de nombres y cancelación de cola humana sin intentos en validación; ver docs/adaptation/PREICFES_INBOX_20261123.md. P22 conserva 60% técnico y elección/piloto pendientes. Sin DDL, SIIE writes ni nuevos contenedores.


## PRE-ICFES e Inbox verificados, 23 de noviembre de 2026
46b15cf backend ofbym6w7x2vpyqbgyjaurq3u Success/Running 5m27s y frontend vhst4alryrae5xbdzi7yoidm Success44s. Ficha local y especialista creados, 27programas/28agentes. Video Facebook25/25privados, un hilo relacionado adicional y3Instagram (2Inbox/1comentario):29salidas nativas/aceptadas, no29lecturas. Cola antigua cancelada con0intentos antes de respuesta nativa; amboschats vuelvenIA. Nombres cargan progresivamente sin abrir hilos. Gemini preview nuevo uncertain7513ms sin tokens, no repetido; contexto sí pasó. P22 conserva3/5técnico/0aceptación; no motor nuevo de privados automáticos por comentario ni cambios de modelos. Evidencia artifacts/live/preicfes-inbox-20261123.json y docs/adaptation/PREICFES_INBOX_20261123.md; detalle nominal sólo.local. SinDDL,seeds,nuevoscontenedores niSIIEwrites.


## Comentarios privados e historial Meta preparados — 2026-11-23

Por instrucción del titular se añaden tres SKILL.md nativas revisadas (biblioteca37), clasificación contextual y privado por comentario para cuentas seleccionadas; límites7días/900caracteres, fuente Meta y Humano revalidados, un intento sin replay incierto, respaldo de lenguaje conservado. Lectura visual acotada sólo para identificar tema sin ficha recuperada, nunca para validar precios. Registro de privados aceptados en Inbox, importación GET de salientes nativos por cuenta (25hilos/20mensajes,últimos7días), ecos propios sin IA ni apertura de ventana. Nombres genéricos precargados y persistidos sobre placeholders sin pisar revisión manual. 279backend/59frontend,tipos/lint/build pasan; bundlehistórico. Meta: tres reglas de comentarios desactivadas y verificado tras recarga; bienvenidas/FAQ ya apagadas. Ronda previa25Facebookvideo+1hilo+3IG conservada, no reenviada. Publicación/activación/importación real pendientes en este corte. P4/P13 aceptación inicial y P22 3/5técnico/0aceptación sin cambios. Ver docs/adaptation/CONTEXTUAL_PRIVATE_COMMENTS_20261123.md. SinDDL,seeds,nuevoscontenedores niSIIEwrites.


## Inbox saliente verificado; politica acotada preparada - 2026-11-23

81dbf7b publicado: backend zhut9vvwzimdq1jdormu7c96 Success/Running4m17s y frontend cgurkkjqbnmcnhlvso4hi2a2 Success38s. Importacion real Messenger:66+4+0 mensajes incorporados, cero envios; busqueda PRE-ICFES muestra28conversaciones. message_echoes suscrito en app y sincronizacion de Pagina confirmada por proveedor. Nombres reales visibles en listado. Guardado general de IA devolvio422 al activar cuentas; campo exacto no identificado. Se separa PUT comments/policy con validacion propia, revisionCAS, permiso/reautenticacion/historial y mezcla solo de cuatro campos sin tocar modelos/voces. Se corrige indicador de carga residual y hora previewAt original.281backend/60frontend,tipos/ESLint/Ruff/build pasan; advertencia historica de bundle. Publicacion del ajuste, activacion y nuevo comentario real aun pendientes; no acreditar automatizacion por importar. P4/P13/P22 conservan estados. SinDDL,seeds,nuevoscontenedores niSIIEwrites.



## Origen de comentarios y bandeja sin respuesta preparados - 2026-11-23

El titular pide etiqueta discreta y clasificar fuera del Inbox los privados iniciados por comentario hasta que la persona responda. Se agregan Desde comentario, vista rapida Desde comentarios (sin respuesta) y filtro Desde comentarios todas. La bandeja principal excluye solo origen comentario sin ninguna entrada; una entrada real lo incorpora automaticamente conservando origen, sin cambiar etapa, control, SLA ni enviar mensajes. Origen acreditado por cola privada, atribucion real de comentario o texto explicito de la ronda nativa PRE-ICFES confirmada; no se clasifica cualquier DM por mencionar un programa. Consulta PostgreSQL parseada y ensayo relacional de transicion sin escrituras de negocio;319backend y47frontend focalizadas pasan (60frontend previas), tipos/ESLint/Ruff/workspacebuild pasan. eff0c99 backend c6fpptvpsuxotqmhzdsdbtyz Success4m16s, frontend6a810dqznwuwrnv45clw6jy5Success. Publicacion y validacion visual de esta ampliacion pendientes. P4/P13/P22 conservan estados.



## Inbox de comentarios publicado y verificado - 2026-11-23

e748487 backend uavozvcl3ln0gx1fvgyfg0yk Success/Running4m17s, frontend6cznheznzfgqcil8tkfzgcmxSuccess44s. Vista real Desde comentarios:23hilos sin entrada, etiqueta compacta sin sustituir preview y hora original; bandeja principal filtrada PRE-ICFES:6hilos activos, conservan origen cuando esta acreditado. Antes de clasificar se verificaron29hilos de la ronda (26Messenger/3Instagram), incluido privado nativo de Instagram;70mensajes Messenger incorporados (66+4+0), sin reenviar. Primera consulta IG fallo temporalmente; posteriores completaron y mostraron el hilo privado, sin afirmar total exacto ni todo el historico remoto. Perfiles disponibles se resuelven sin abrir; Meta puede devolver usuario en lugar de nombre completo. Tres reglas nativas de comentarios apagadas; saludos/FAQ ya apagados, reglas organizativas preservadas. App message_echoes y reconciliacion de Pagina confirmadas. Politica privada solo CBN Facebook/Instagram guardada y comprobada tras recarga, ScentraWPP no seleccionada. Nuevo comentario real corto de prueba recibio una respuesta publica pertinente; no acredita DM automatico. Ensayo explicito privado solicitado y pendiente en este corte.319backend/47frontend focalizadas (60previas),tipos/ESLint/Ruff/workspacebuild pasan; bundlehistorico. Evidencia artifacts/live/contextual-private-comments-20261123.json. P4/P13 iniciales y P22 3/5tecnico/0aceptacion conservados. SinDDL,seeds,nuevoscontenedores niSIIEwrites.



## Ensayo real de privados: rechazo de borrador y contrato de respaldo reforzado - 2026-11-23

Dos comentarios reales nuevos del titular: el corto se publico con informacion pertinente; la solicitud explicita de precios por privado fallo comment_ai_invalid_draft antes de encolar. Diagnostico confirma Gemini provider_temporary_failure y OpenRouter GPT4.1mini completed en ambos; no se conserva el contenido rechazado ni se atribuye un campo/longitud concreto. Se elimina la instruccion incondicional de entrega publica solo del contexto de decision privada, sin incorporar memoria privada. Respaldo usa json_schema estricto para los cinco campos de entrega, enums de programas recuperados y texto max900; rutas ordinarias conservan contrato anterior. Intencion information con programa validado se entrega por privado; apoyo sigue publico y ambiguedad revision. Huella incluye instrucciones sociales completas. Errores futuros distinguen extension/incompleto/contrato sin exponer borradores.342backend/Ruff y tipos/ESLint/workspacebuild pasan; sin reintento ni envio de operaciones fallidas. Publicacion y ensayo posterior pendientes. Filtros de origen e importacion ya verificados en e748487; P4/P13/P22 no cambian.

