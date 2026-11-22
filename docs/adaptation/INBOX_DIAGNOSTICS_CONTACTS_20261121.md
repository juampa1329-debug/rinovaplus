# Inbox, diagnóstico y contactos públicos · 21-11-2026

## Diagnóstico confirmado

Tres salidas de un hilo WhatsApp real quedaron canceladas con cero intentos. La primera parte del último grupo indicó `gemini_reply_context_changed`; la segunda `gemini_whatsapp_previous_part_not_sent`. No fue rechazo de Meta ni fallo de generación. Se conserva la evidencia de cancelación, sin copiar textos, teléfonos privados ni tarifas en Git. El código histórico no permite reconstruir qué componente cambió: no atribuir una causa más específica sin evidencia.

La respuesta se comprueba antes de guardar. Tras las proyecciones CRM validadas dentro de esa misma transacción se fija la autorización al estado resultante; cambios externos posteriores siguen cancelando. Se registran hashes por componente y nombres de los componentes que cambian, sin sus contenidos. La recuperación explícita sólo admite generaciones sin salida o con todas sus partes canceladas, cero intentos y sin ID externo, fuente actual, IA/epoch vigentes y máximo tres intentos. Nunca recupera un envío aceptado o incierto.

## Operación

- **Ajustes → Diagnósticos**: recepción, IA, respaldo y envíos; filtros de sección/canal/incidencias. Hasta50recientes por sección, no un archivo completo de logs. Sólo lectura para `users.manage`; sin prompts, cuerpos, claves o URLs privadas. Desde Inbox, **Ver diagnóstico de esta conversación** aplica el filtro del hilo.
- Los estados **Cancelado · ver motivo** abren causa y solución. La recuperación sigue siendo una acción explícita y no se dispara al consultar.
- **Ajustes → Institución → Contactos públicos**: nombre, número, uso llamadas/WhatsApp/ambos, indicaciones y activación. Guardar cambios publica el directorio para IA general, especialistas, sugerencias y comentarios. No configura telefonía ni activa P20. El titular confirmó WhatsApp institucional y una segunda línea para llamadas; guardado vivo pendiente de esta publicación.
- Menciones `story_mention` y respuestas `reply_to.story` se identifican por el payload Meta. Una mención sin texto no se entrega a Gemini como una pregunta inventada. La recepción nueva registra el medio; la vista histórica deriva el tipo del evento firmado conservado. **Recuperar vista previa** solicita sólo un medio de una mención existente, de forma idempotente, con inspección y descarga HTTPS restringida a CDN Meta y cuotas existentes. Historias vencidas o inaccesibles no se fabrican. No se amplían suscripciones ni permisos.

## Referencia revisada

Scentra: `H:/saas-version/frontend/src/App.jsx`, sección debug/diagnóstico operativo, y `backend/app_saas/diagnostics/router.py`: estados, IA, eventos y colas. RinovaPlus conserva el concepto de trazabilidad y usa sus propios permisos y tablas; no copia tenant ni billing ni reprocesamiento global.

Meta: [referencia oficial de Instagram](https://developers.facebook.com/docs/graph-api/webhooks/reference/instagram) y [mensaje de Graph API](https://developers.facebook.com/docs/graph-api/reference/v27.0/message). La presencia de un evento no garantiza que su historia siga descargable.

## Verificación

270backend seleccionadas/2omitidas,8frontend,tipos/lint/build pasan al corte local. SQL del diagnóstico parseado para PostgreSQL con parámetros y proyección sin secretos comprobada. La conmutación P21 y Humano conservan sus guardas. Pendientes: publicación, directorio guardado, lectura real de menciones, diagnóstico y recuperación del hilo cancelado. No DDL, seeds ni escrituras SIIE.

## Corte vivo posterior

`fd2f291` saludable en Coolify (`kzjc0dmcpuywyquov8tjjceb`, 05m44s); frontend `habqfrnv3zkla91tfj0isqm7` Success 01m10s. Contactos públicos guardados en revisión2, dos líneas con usos separados. Por instrucción expresa del titular se recuperó sólo la última generación del hilo afectado: dos nuevas partes **Entregadas**, un intento por parte, a las19:27 locales; modo IA conservado y cancelaciones históricas intactas. La causa histórica sigue siendo contexto cambiado, sin componente específico registrado.

La lectura viva del historial detectó un import JSON ausente en la proyección de eventos; se corrigió en `4df3ee0` y se añadió regresión ejecutando el método de historial. 270backend/2omitidas y Ruff de todos los módulos modificados pasan. Redeploy de esa corrección y lectura de menciones aún en verificación.

## Verificación del arreglo final

`b2de74c` saludable, backend `gbugn3gjzp7aqzizuscbl5do` Success04m18s y frontend `awyam8j78wmvye98qmmcvzzs` Success00m25s. La comparación de IDs de Meta usa la misma colación binaria explícita que los recibos existentes. Además, la presentación social queda en una lectura aislada: un fallo de esa vista no bloquea el historial base. Historial completo de WhatsApp real abierto sin aviso; dos partes de recuperación con recibo **Leído**, sin duplicados ni reenvío de cancelaciones.

Mención real de Instagram identificada como «Te mencionó en una historia», incluyendo el historial anterior. Recuperación de un archivo reciente solicitada una vez; en preparación al corte, sin respuesta saliente. No acreditar archivo visualizado mientras no esté listo. 270backend seleccionadas/2omitidas,8frontend,tipos/lint/build y Ruff pasan. Los controles de IA/Humano y envío incierto se conservan.

## Cierre de esta revisión

Los dos hilos Instagram reportados muestran «Te mencionó en una historia», sin generar respuestas ficticias por una mención sin texto. La solicitud única de vista previa pasó a «No se pudo preparar». El worker anterior conserva sólo `media_download_or_inspection_failed`, por lo que no se puede atribuir con evidencia a caducidad, formato o tamaño. Una historia nueva sigue siendo necesaria para aceptar la visualización del archivo; no declarar ese extremo aprobado. No se reintentó el mismo archivo ni se envió ningún DM desde esas menciones.

Luisa: dos respuestas nuevas leídas, historial visible y modo IA. Los cancelados previos quedan como auditoría; no son envíos pendientes. Los cambios del directorio y las lecturas del diagnóstico no cambian modelos activos ni alteran fases pendientes.
