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

268backend seleccionadas/2omitidas,8frontend,tipos/lint/build pasan al corte local. SQL del diagnóstico parseado para PostgreSQL con parámetros y proyección sin secretos comprobada. La conmutación P21 y Humano conservan sus guardas. Pendientes: publicación, directorio guardado, lectura real de menciones, diagnóstico y recuperación del hilo cancelado. No DDL, seeds ni escrituras SIIE.
