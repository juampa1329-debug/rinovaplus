# P8 · Campañas, flujos y remarketing · SQL Server 2019

## Alcance y estado

P8 tiene 95,00% de trabajo técnico ponderado y tres de cuatro criterios aceptados: P8.1, P8.2 y P8.3. El hito P8.close.m5 conserva su peso y queda pendiente del cierre real de P7 y sus dependencias P4. No existen aún dominio público, aplicaciones Meta/TikTok ni catálogo/recibos reales. No se otorga aceptación externa a respuestas de proveedores controlados.

Se conserva el denominador canónico: 22 hitos P8, 279 globales y 56 criterios. Los criterios aceptados cubren el contrato, integración SQL/API/interfaz y pruebas locales descritas aquí. P8.close conserva cuatro de cinco hitos; la fase no se presenta como cerrada.

## Contrato y destino propios

Vista integrada: http://127.0.0.1:4178/#/campaigns. Imagen crm-cbn-workspace:p8es-r7; perfil privado .local/p8-es/final-runtime; base CBN_P8ES_TRIAL_20261027_1908de72. Motor SQL15, compatibilidad150, TLS validado (Encrypt=yes, TrustServerCertificate=no). 167 tablas totales, 284 claves foráneas y 137 mapeos CRM; las otras 30 tablas académicas están protegidas.

Release inmutable backend/migrations/cbn_campaign_operations_v1: P8ES-000/P8ES-001 y diario. Nombres físicos dbo.CRMFlujoOperacionMigracion, CRMFlujoDefinicion, CRMFlujoVersion, CRMFlujoObservacion, CRMFlujoInscripcion, CRMFlujoPaso, CRMFlujoEvento. Versiones y eventos son append-only; el principal de ejecución no ejecuta DDL ni modifica el historial. Los nuevos metadatos de adjuntos usan eventos JSON tipados; no se alteró la release congelada para añadirlos. No hay DDL en el arranque.

La copia proviene de un respaldo COPY_ONLY/CHECKSUM P7. No se vuelve a consultar ni escribir SIIE Windows. El catálogo y huellas de la fuente P7 se contrastan en lectura. C5/C9 y P4/P5/P6/P7, perfiles, volúmenes y releases anteriores se conservan. P7 está detenido como crm-cbn-preview-p7-preserved, imagen p7es-r3. Ningún perfil previo apunta al destino nuevo.

## Comportamiento integrado

Cinco tipos de registros: campañas, flujos, activadores, plantillas CRM y segmentos guardados. CRUD con CAS, permisos y CSRF; versiones inmutables, copia/restauración idempotente como borrador con reautenticación reciente. Preview no activa ni prepara envíos. Preflight revisa cuenta, credenciales, permisos, versión y documento; la aprobación explícita está vinculada al actor, sesión, revisión y vencimiento.

Pasos persistidos de espera, condición y envío; zona IANA, horarios de silencio que cruzan medianoche y cambios DST. Eventos futuros de mensaje, etapa, programa e inactividad, con prioridad, cooldown, deduplicación y salida al responder. Se comprueban identidad canónica, consentimiento/no-contactar, programa, etapa, control humano/epoch, respuesta y autoridad antes de efectos. Una espera futura se cancela cuando cambia su contexto. Pausa/reanudación conserva partes aceptadas y plazos. Los efectos inciertos nunca se reenvían automáticamente; sólo fallos definitivos sin aceptación admiten reintento revisado.

Plantillas CRM y aprobadas Meta tienen contratos distintos. Las primeras incluyen bloques de texto, enlace e imagen/audio/video/documento, archivo inspeccionado o HTTPS público, grabación de audio por gesto, preview/descarga autenticados y demoras entre partes. Cada parte conserva su propio trabajo C10, índice y aceptación. Texto asociado en IG/Messenger/TikTok se envía como parte separada, evitando perderlo o confundir dos efectos. WhatsApp conserva caption y nombre editable del documento. Plantillas sólo multimedia son válidas y la simulación muestra un marcador, sin inventar caption de audio.

Instagram Login usa una URL de entrega temporal HMAC, vinculada al perfil/institución/cola/archivo y válida por 600 segundos. El endpoint verifica estado del flujo/ejecución/cuenta, permisos/contexto vigentes e integridad del archivo; pausa, cambio de contexto o vencimiento retiran acceso. No publica permanentemente la biblioteca. Requiere configurar la URL HTTPS pública institucional; el destino principal permanece sin ella y no emite envíos.

Las plantillas oficiales WhatsApp se materializan por el dispatcher P7 existente, con la misma cola C10 y cadencia en la frontera del POST. Los workers heredados B011/campañas siguen cerrados. Variantes A/B se asignan de forma determinista y persistida; métricas consultan intentos reales inmutables. Sólo se atribuye una respuesta por contexto explícito de mensaje, cuenta y remitente; no se inventan conversiones ni ganadores.

## Pruebas y evidencia

361 pruebas backend y 332 frontend; TypeScript y ESLint pasan. Estos totales y los recibos siguientes son alcances separados, no una suma de pruebas únicas.

- API16; runtime13 (continúa9 comprobaciones registradas tras ajustes del calificador); extras6 (continúa5 registradas). No se presentan como dos ejecuciones completas nuevas.
- Storage12 sobre cuatro copias de fallo: diario, interrupciones antes/después de commit, concurrencia, drift y prohibiciones del usuario de ejecución.
- Recuperación9 sobre copia poblada propia:155 tablas estables, incertidumbre preservada, 11 blobs (7 adjuntos C10 y4 biblioteca) copiados y revalidados en raíz nueva. El backup SQL solo no contiene sus bytes. Los consumidores recuperados no hacen POST ni reencolan incertidumbre.
- Espera real de dos minutos y reinicio de contenedor4; resynchronización de plazos3; límites/cadencia3.
- Multimedia9 con inspección real de imagen/documento/audio/video y codecs del contenedor propio; texto+4adjuntos aceptados en orden con transporte controlado, caption de video WhatsApp y demora de15segundos persistida.
- Caption/nombre4, con adaptador real C10 y HTTP controlado. Instagram Login/entrega6: archivo recuperable sin cookie humana, firma alterada/vencida, cambio de identidad y pausa rechazados.
- Navegador, demo de adjunto y reinicio general constan en artifacts/p8-es/browser/ y demo-media-result.json. Preservación y despliegue se documentan por separado.

Las respuestas HTTP controladas ejercen los adaptadores, no prueban permisos ni recepción de proveedores reales. La recuperación poblada v2 precede a las comprobaciones adicionales de caption/Instagram; no se afirma que contenga efectos posteriores a su snapshot. Las primeras ejecuciones de calificación Instagram rechazaron una fixture con variable declarada sin uso; se corrigió la fixture sin relajar el validador.

## Límites conservados

5.000.000 bytes por archivo; imágenes PNG/JPEG; documentos PDF, Office OpenXML y TXT inspeccionados; audio hasta300segundos normalizado; video hasta120segundos y1920×1080, transcodificado y sin metadatos. Cuota total compartida biblioteca+archivos C10 y cuotas por conversación. TikTok conserva imagen≤3MB, permiso IMAGE_SEND y consulta de conversación; audio/video/documento se rechazan en preflight. No se fabrican permisos ni productos aprobados.

Audiencias académicas usan campos declarados del CRM; no se afirma mapeo completo de DBSIIE. Hay límites explícitos de500registros,500inscripciones abiertas,100activadores,5000contactos y20pasos; no se afirma escala ilimitada. La simulación resume los pasos; las demoras de partes se persisten y comprueban en ejecución, no se muestran como un cronograma exacto del simulador.

## Reversión y continuidad

Para revertir un flujo, pausar, revisar intentos y conservar toda incertidumbre; restaurar versión anterior como borrador y aprobar de nuevo. No borrar ni fusionar trabajos para aparentar limpieza. Para recuperación nativa, crear destino/perfil/raíz multimedia nuevos, validar catálogo/huellas/blobs y retirar sesiones y aprobaciones copiadas. Para volver a P7, conservar primero P8/base/volumen, detener P8 y arrancar el contenedor P7 retenido, sin dos procesos en4178.

Continuidad: tasks/p8-es-progress.json, docs/adaptation/sql/P8_ES_CHECKPOINT.md, phase-work-progress.json, p8_es_validation.json y graphify-out/p8-es/. Los grafos semánticos no acreditan ejecución. Verificación offline y replay de1464preimágenes mantienen intactos los verificadores/releases/grafos anteriores. Uso de tokens no medido.
