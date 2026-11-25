# Ensayo público PRE-ICFES y recepción firmada

25 de noviembre de 2026. El titular autorizó llenar el formulario con datos de prueba y confirmó puntualmente la aceptación de su política de tratamiento de datos para este ensayo.

## Recorrido comprobado

1. Se llenó el formulario oficial `https://siieplus.online/SIIEWEBPLUS/PreIcfes/Inscripcion.html` desde su interfaz nativa. Registro rotulado PRUEBA TECNICA RINOVAPLUS / WEBHOOK / NO MATRICULAR, identificador alfanumérico `RINOVATEST251125`, contacto ficticio no utilizable y correo bajo `example.invalid`. No se usó el documento ni el teléfono de un estudiante real.
2. Se seleccionó Santa Marta/Magdalena, egresado y G1 sábado de 7 a 12. Se adjuntó un PDF sintético de una página, revisado visualmente y rotulado «PRUEBA TECNICA / NO ES DOCUMENTO DE IDENTIDAD / NO MATRICULAR / NO CONTACTAR». No se fabricó una identificación ni se subió documentación personal real.
3. Una validación inicial detectó la fecha vacía antes del envío. Se introdujo mediante interacción nativa de teclado, se comprobó su persistencia al cambiar de paso y se confirmó una sola solicitud de registro válida. No se repitió una solicitud remota incierta.
4. SIIE mostró **«Tu inscripción fue registrada»**, número **16922**, Grupo A. Esto acredita el guardado del ensayo en SIIE; no acredita matrícula, pago, usuario Moodle ni un volante.
5. RinovaPlus confirmó el secreto Runtime y la recepción habilitada, Calificación y envíos finales desactivados tras recargar. La bandeja de eventos seguía en **cero recibos verificados** después del registro y en las consultas posteriores de este corte.

El titular informó una celda HTTP403 en SIIE y compartió el JSON del evento `edd87d5d-dd6a-49dc-a6cc-147facb87659`: `registration.created`, secuencia2, inscripción16922/estudiante22655/oferta1232/período129. En la validación local, su único campo rechazado fue `occurred_at`: `2026-11-26T01:25:23Z` frente al reloj UTC `2026-11-25T22:35:27Z`, unos10196segundos adelantado. Con una fecha UTC válida el resto del JSON pasó. Esto no reenvió ni modificó datos productivos.

El 403 se comprueba antes del JSON: firma/encabezados y timestamp de firma. Un reloj igualmente adelantado en `X-SIIE-Timestamp` explicaría ese 403; el valor del encabezado y el detalle de la respuesta siguen pendientes del productor. El campo `occurred_at` adelantado produciría422 después de superar la firma, de modo que deben revisarse ambos tiempos. No se amplió la ventana de cinco minutos ni se permitió una fecha futura para aceptar la prueba.

## Diagnóstico y paso que necesita SIIE

El frontend de entrada incorpora un log dedicado `siie_webhook_http` con fecha, estado HTTP, estado upstream y duración. El backend distingue formato de timestamp/firma, desfase de reloj, firma incorrecta o ambos, con `reason` y diferencia de segundos. No registra ruta/query, IP, cuerpo, firmas, claves, cookies ni identificadores personales. Se conservan 64KiB, HTTPS, ventana300segundos y ausencia de reintento automático del proxy.114pruebas backend focalizadas pasan después de integrar los cambios concurrentes de producción, con66frontend/tipos/build; las selecciones se solapan con las anteriores. Despliegue de este diagnóstico en verificación.

El desarrollador de SIIE debe localizar el guardado **16922** y su evento en la outbox. Reintentar el mismo evento con su mismo GUID/contenido/secuencia y timestamp/firma nuevos. Compartir únicamente `event_id`, código HTTP e intento o referencia técnica; no pegar secretos ni firmas. Si el guardado sólo genera una referencia de preinscripción, usar el evento y los IDs que realmente existan según el [contrato único](SIIE_WEBHOOK_CONTRACT_V1.md), sin inventar `idEstudiante` o `idInscripcion`.

No se reinyectó manualmente un evento en producción para simular una entrega de SIIE. La primera recepción, deduplicación real, clasificación y continuidad del mismo registro siguen pendientes. El registro sintético se conserva identificado para conciliación; no se eliminó ni se alteró un registro ajeno. P23 sigue 0/9 aceptados. El contrato de volante y retorno PDF permanece pendiente del productor.
