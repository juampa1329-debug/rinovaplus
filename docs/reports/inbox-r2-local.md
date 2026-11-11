# Inbox R2 local — responsables, tareas y SLA explícito

Corte del 2026-10-15, completado y aceptado por capas, incluido navegador real. Extensión local autorizada sobre R1.1: equipo de Admisiones por empleado real, registro de agentes IA, dos responsables independientes, tareas por conversación y política opcional de próxima respuesta **local**. No ejecuta agentes ni envía mensajes. Contrato: [ADR-007](../decisions/ADR-007-local-inbox-operations.md).

## Uso

1. En **Inbox → Configurar operación → Equipo de Admisiones**, buscar y seleccionar empleados activos reales, y añadir únicamente los integrantes que determine la persona operadora. El equipo empieza vacío; no se deduce del nombre ni del departamento.
2. En **Registro de agentes IA**, crear las definiciones reales y habilitar expresamente su disponibilidad para asignación. Registrar/asignar no activa IA ni conecta proveedores. El registro empieza vacío.
3. En la ficha derecha, elegir **Responsable humano** y **Agente IA asignado**, y confirmar **Guardar responsables**. Ambos permanecen asignados al cambiar control humano/IA. Los filtros por ID se aplican antes de paginar.
4. Crear una tarea con título y prioridad elegidos; responsable y fecha son opcionales. Las fechas se introducen/muestran en America/Bogota y persisten en UTC. Editar permite completar/cancelar; no se reabre una tarea cerrada. Deshabilitar un miembro conserva el historial y permite cerrar sus tareas.
5. Configurar SLA solo después de elegir el umbral real. No hay valor inicial. La política disponible mide tiempo transcurrido 24/7, sin pausas, desde el entrante más antiguo posterior al último saliente local. Espera/control IA no pausan; cerrado queda excluido. Igualar el vencimiento ya es vencido. No hay medición sin entrante pendiente. Un saliente local no acredita entrega externa.

SLA y filtro se refrescan cada minuto. Una tarea vencida es un indicador distinto. Los borradores conservan su revisión base frente a actualizaciones; un 409 exige revisar los datos actuales y descartar el borrador para iniciar una edición nueva. La revisión es global dentro de `crm_inbox`: un cambio de otra operación también puede generar ese conflicto conservador.

## Persistencia y recuperación

[Migración 003](../../backend/migrations/003_local_inbox.sql) explícita, sin DDL al arrancar: seis tablas `crm_inbox`, versión/huella y guardas de destino, tipos y PK del origen `GEEmpleado`. No copia empleados ni añade columnas al core. Todas las escrituras usan idempotencia, revisión y el bloqueo compartido `crm.local.commit`. Configuración no altera revisión global CRM; la asignación actualiza etiqueta y operación compatible en la misma transacción. La ruta anterior rechaza nuevos responsables de texto libre.

Respaldo COPY_ONLY/CHECKSUM nuevo, restauración independiente y CHECKDB comprobados. El ensayo de fallo revierte el esquema; aplicar dos veces conserva el resultado. Aplicación durable vacía en DBSIIE: metadatos core y hashes de todos los registros CRM/Admisiones preservados. El trigger existente añadió diez auditorías DDL, conservadas. La reversión operativa consiste en detener este preview y conservar esquema/filas para recuperación; no usar un escritor anterior que ignore las referencias estables ni ejecutar DROP/restore sobre cambios posteriores.

## Evidencia por capa

| Capa | Resultado |
|---|---|
| Migración | Respaldo/restauración, fallo/reversión y repetición aprobados; seis tablas vacías. |
| SQL de negocio | 23 comprobaciones en transacción siempre revertida: directorios, doble asignación/control, revisión independiente, replay/409, inactivos, tareas, fechas/SLA y filtros. Sin filas técnicas finales. Prueba transaccional, no afirmación de COMMIT de datos de negocio. |
| Backend | 381/381 pruebas enfocadas y contratos; Ruff y exportaciones canónicas aprobados. |
| Frontend | 21/21 pruebas enfocadas; lint, tipos y build aprobados tras normalización. |
| Runtime/HTTP | Mismo preview 4173 reconstruido y saludable; 15 comprobaciones HTTP de lectura aprobadas. Snapshot CRM, volumen IA y Admisiones conservados. |
| Navegador | Aprobado: búsqueda AJAX de empleados reales, vacío veraz, borradores y descarte, filtros SLA, tres paneles/scroll independiente y navegación móvil. Sin escrituras de negocio. |

Evidencia saneada local: `.local/inbox-r2-20261015/backup-result.json`, `backup.json`, `restore.json`, `migration-result.json`, `repository-result.json`, `http-result.json`, `docker-final.json` y `runtime-freeze.json`, `browser-result.json` y captura saneada `browser-operation-settings.png`. Imagen verificada: `sha256:ff66d47a7d175facd114b55d5882b56ae00c4872859d12099c16ffe8ed742479`. No contienen nombres, documentos ni credenciales. No se hicieron envíos externos ni publicación Git.

## Aceptación de navegador

Búsqueda exacta de empleado devuelve una coincidencia real y búsqueda inexistente devuelve cero. Equipo/agentes siguen vacíos; el umbral SLA aparece vacío. Borradores de agente y política sobreviven a navegación; la tarea temporal queda aislada por conversación y reaparece al volver a su hilo. Todos se descartaron sin guardar. SLA no configurado muestra las dos conversaciones existentes; vencido muestra cero sin perder la ficha seleccionada; restablecer recupera ambas.

En 1440 × 1000, los tres paneles miden 717 px y terminan en 975 px. Desplazar la ficha de 3000 a 2000 mantiene lista/mensajes en cero y documento en 58. En 390 × 844, el ancho de página es 375 px y la ficha termina en 751,625 px; controles de tarea, cierre/regreso y configuración son accesibles sin desbordamiento horizontal. Se retiraron borradores y búsquedas temporales; no se operó la pestaña del usuario. Esta aceptación comprueba lectura e interacción; la prueba de escritura SQL sigue siendo transaccional con rollback.

## Límites y continuación

R2 queda limitado a operación individual en la copia local. Miembros no equivalen a usuarios autenticados ni permisos; faltan autenticación/RBAC antes de compartir. El propietario debe configurar integrantes, definiciones de agentes y umbral/activación SLA desde la UI. No hay política institucional preaprobada, calendario laboral, recordatorios, canal entrante, banco de especialistas ejecutable, análisis continuo, puntuación ni entrenamiento. Los eventos R3A pueden avanzar sin esperar un canal externo; respetar las decisiones abiertas del [roadmap](../roadmap.md).
