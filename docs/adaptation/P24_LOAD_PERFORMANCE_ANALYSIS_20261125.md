# P24 — Inicio, carga del Inbox y capacidad de atención

Estado: diagnóstico preliminar y plan registrados. **Implementación: 0 %. Aceptación: 0/6.** El titular pidió analizar la demora después de corregir los comentarios y no implementar optimizaciones todavía. Este informe no cambia servicios, colas, consultas, índices, límites HTTP ni cachés de producción.

## Evidencia disponible

| Señal | Condiciones y alcance | Resultado | Límite de interpretación |
|---|---|---|---|
| Bundle institucional | Build local Vite de esta revisión | JS principal1202,69 kB;348,19 kB gzip. CSS164,12/31,00 kB gzip. Fuentes24,53+28,87 kB | Tamaño de artefactos, no tiempo de descarga o LCP |
| Datos del selector de emojis | Chunk compact571,10 kB /79,74 kB gzip; import dinámico en InboxComposer | Se carga al abrir el selector | No se suma como descarga inicial obligatoria |
| Transacciones lentas | Ventana de registros nativos del backend8bff156, inicio01:56:35UTC26Nov.26 coincidencias en la vista consultada | Repetición de held_ms y statement_ms alrededor de1100ms; origen reconcile_receipts:385, ID0c3ce6f3ff1a | Muestra del visor, no muestra completa ni percentiles. stage=commit es el punto final observado, no prueba que COMMIT dure1,1s |
| Respuestas sociales recuperadas | Consulta nativa individual posterior al arreglo funcional | Diez públicos Publicado en Meta; tres privados Aceptado por proveedor | Recuperación funcional, no benchmark ni entrega/lectura del privado |
| Inferencia aislada previa | Dos casos P22 distintos, sin envío/CRM | Sonnet4.6:8,892s; Flash3.8:4,869s | Casos/contextos distintos; no comparación homogénea, no latencia del Inbox |
| Experiencia de usuario | Avisos y demora reportados por el titular | Afectación declarada al iniciar sesión y consultar información | No sustituye una traza ni mediciones p50/p95/p99 |

No hay en este corte RUM/CrUX del producto autenticado, traza DevTools, medición equivalente fría/caliente ni ensayo de carga multiusuario. Las duraciones de automatización del navegador no se presentan como latencias de API o de render.

## Hipótesis y cómo verificarlas

1. **Consulta recurrente de recibos bajo la transacción de escritura.** broadcast_dispatch.reconcile_receipts actualiza eventos quarantined/delivery_unmatched con EXISTS contra SendJob. El registro identifica esta sentencia como la más lenta de transacciones de aproximadamente1,1s. channel_workers la ejecuta en cada ronda de campañas. Las mutaciones mantienen un bloqueo institucional serializado. Verificar volumen, selectividad, índices existentes y EXPLAIN en un entorno autorizado; distinguir ejecución, espera de bloqueo y conexión. No eliminar ni relajar el bloqueo de idempotencia para acelerar.
2. **Costo del arranque y vistas importadas anticipadamente.** InstitutionApp importa Académico, Agentes, Publicidad, campañas, SIIE y otras vistas antes de elegir la pestaña. Verificar cobertura de JS y traza de CPU en el login y el primer Dashboard. Evaluar división por rutas sólo después de medir; no prometer un ahorro específico.
3. **Cadena de lecturas iniciales.** auth/status precede a auth/me; después Shell carga runtime/contracts en paralelo y la vista solicita sus datos. Medir cada tramo con una traza fría y tres navegaciones equivalentes calientes. No fusionar autorización con caché pública ni persistir contexto privado en el navegador.
4. **Lecturas de Inbox y paneles.** Workspace.useRead tiene demora inicial180ms, revisiones condicionales y algunas consultas cada15s; detalle, mensajes, agentes, memoria y notificaciones pueden consultar por separado. readCoordinator ya agrupa lecturas concurrentes iguales y respeta Retry-After. Medir cantidad/bytes por pantalla y por contacto, cancelación de vistas obsoletas, foco/visibilidad y multiplicación entre usuarios. No eliminar el control HTTP600/usuario ni repetir POST para ocultar demoras.
5. **Espera deliberada y espera de cola.** Los60s desde el último mensaje son la configuración del titular para reunir el turno, distinta de generación/entrega. La ronda de inferencia actual recorre mensajería y comentarios secuencialmente: una inferencia lenta puede posponer la siguiente. Medir encolado→elegible→inicio de inferencia→primera aceptación→recibo y saturación por tipo. Evaluar concurrencia acotada sólo en una fase posterior, conservando orden por conversación y controles de envío.
6. **Recargas y versión del frontend.** Una pestaña abierta conservó la validación anterior step128 mientras una navegación nueva a la publicación mostró step1. Comprobar navegación normal/recarga, caché del documento, control de versión y protección de borradores. No afirmar causa CDN/service-worker sin headers/traza que lo demuestren.

## Plan de implementación pendiente y aceptación

| Criterio | Trabajo posterior | Cierre exigido | Estado |
|---|---|---|---|
| P24.1 Línea base | Tres navegaciones equivalentes por ruta fría/caliente y perfil de equipo/red; registrar versión y autenticación | Medianas/rango, LCP/INP/CLS de laboratorio si se dispone de traza; p50/p95/p99 API y errores con alcance claro | Pendiente |
| P24.2 Datos | Revisar plan de la sentencia identificada y rondas sin trabajo útil, con índices existentes documentados | Antes/después con la misma carga, sin pérdida ni duplicación de recibos; cualquier DDL se propone por separado | Pendiente |
| P24.3 Cliente inicial | Probar carga por rutas y prioridad de datos críticos | Mejora repetible de arranque sin regresión de permisos, Dashboard, navegación móvil o borradores | Pendiente |
| P24.4 Consultas | Revisar composición de ficha/paneles y actualización por revisión; coordinación entre usuarios/pestañas | Menos solicitudes/bytes por recorrido, sin datos privados obsoletos ni aumentar errores429/503 | Pendiente |
| P24.5 Atención | Separar métricas de espera configurada, cola, modelo y canal; proponer capacidad acotada | Orden conservado por hilo, Humano detiene la IA, sin replay incierto, imágenes/audio no bloquean consultas de texto ajenas | Pendiente |
| P24.6 Carga y despliegue | Definir con Admisiones la concurrencia representativa y objetivos antes de ejecutar | Informe comparable, publicación saludable, verificación de varios usuarios y reversión documentada | Pendiente |

Los objetivos de tiempos y concurrencia se fijarán con la línea base y el uso de Admisiones; este corte no acredita SLA ni carga máxima. Este plan no modifica los denominadores históricos de P0–P11, ni las aceptaciones P13/P19/P21. P22 conserva3/5 técnico y0/5 comercial; P23 conserva0/9.

Skill usada para el método de auditoría: performance (host). Se separan tamaño de artefactos, observaciones de registros, hipótesis y datos todavía no medidos. No se implementaron recomendaciones de rendimiento.
