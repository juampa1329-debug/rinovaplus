# P23 · Preparación de RinovaPlus para el webhook SIIE

25 de noviembre de 2026. El titular autoriza adelantar el lado RinovaPlus mientras SIIE prepara el emisor y el contrato de volantes.

## Alcance

Panel de preparación basado en configuración guardada: firma compartida, etapa activa, recepción y dependencia del contrato de pagos/PDF PRE-ICFES. Las modificaciones de configuración son un borrador separado; no alteran la disponibilidad mostrada ni los permisos de envío hasta guardarlas. Se pueden descartar. Una recepción habilitada puede desactivarse aunque su firma o etapa requieran revisión.

Historial de recibos de 25 por página, fecha Bogotá, referencia de evento y estado. Recarga explícita, sin sondeo automático; un listado vacío no se confunde con prueba exitosa. El detalle privado, sólo para operadores CRM/Admisiones, muestra documento, nombre, contacto, referencias SIIE y la última instantánea de identidad recibida, conservando separado el evento original. Cambiar de página cierra la revisión anterior y las respuestas tardías no la reabren.

La confirmación de un vínculo incluye la revisión de la instantánea. Si llega otro evento mientras se revisa, se detiene con `siie_contact_link_changed` y obliga a consultar nuevamente. Una repetición del mismo vínculo ya confirmado devuelve el resultado sin crear otra ficha. No se fusionan personas por teléfono, no se sobrescriben nombres editados ni se concede consentimiento comercial.

El Markdown único para el desarrollador se conserva en `SIIE_WEBHOOK_CONTRACT_V1.md`. Sus rutas de volante son propuestas expresas; no se llaman ni se convierten en endpoints productivos por esta preparación. El receptor sigue sin iniciar mensajes ni órdenes.

## Verificación

186 pruebas backend focalizadas SIIE y 23 frontend pasan. Incluyen ensayo HTTP firmado con base aislada: preinscripción→repetición→inscripción, un contacto, dos recibos y exclusión de promociones, conservando modo Humano. La base SQLite de este ensayo permite el hilo del receptor; no es una conexión productiva. También se prueban revisión obsoleta, vínculo actual e idempotencia, datos actuales frente a evento antiguo, navegación de recibos y configuración guardada frente a cambios sin guardar.

Tipos, ESLint, Ruff y build institucional pasan; advertencia histórica de bundle grande. No se declara la suite completa verde ni un piloto real SIIE→RinovaPlus.

Publicación y configuración nativa de etapa pendientes en este corte. No hay secreto nuevo generado, eventos sintéticos inyectados en producción, altas remotas, archivos, órdenes, PDFs, mensajes, DDL, seeds ni servicios nuevos. Recepción/envíos finales se conservarán desactivados hasta preparar firma y piloto. La retención definitiva y el contrato de pagos siguen pendientes. P23 conserva 0/9 aceptados; otras fases y P22 intactas.
