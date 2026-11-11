# ADR-007 — Operación local de Inbox con asignación dual y seguimiento

Fecha: 2026-10-15. **Alcance solicitado por el propietario; contrato de implementación de la extensión local R2.** No modifica el stack ni autoriza producción. Aplicación y evidencia se registran en el informe del corte; ningún umbral SLA queda aprobado por este documento.

## Actualización aceptada por el propietario — agentes personalizados, 2026-10-21

**Elección posterior de Bety como orientadora principal:** el propietario pidió restaurar su perfil y usarlo en Asistente. La sustitución del orientador creado por el coordinador se ejecuta como mantenimiento local único de tres filas, conservando el agente del programa 331 y su configuración. Bety queda activa; el orientador anterior archivado; el hijo conserva programa/etapa/estado y cambia de supervisor con versión/revisión e historial coherentes. Se conserva el índice que permite un solo orientador no archivado. Esta excepción acotada de reubicación no convierte el cambio normal de ámbito en editable ni añade un servicio de sustitución; requiere las precondiciones y transacción del mantenimiento revisado. No autoriza DDL, cambios core, transporte o activación global. La aceptación real y conservación se registran en el contrato.

La solicitud humana vigente autoriza completar **Mis agentes** conforme a la referencia de video y retirar la aprobación/revisión obligatoria de los perfiles: **guardar una configuración válida la deja disponible**, sin una segunda aprobación del agente. El diagnóstico es opcional. Se conservan pausa, archivo y restauración como controles directos, sin motivo/casilla adicional. Un archivo anterior no se restaura automáticamente.

La columna histórica `ApprovedVersion` se mantiene únicamente como sello técnico de compatibilidad con la restricción SQL existente: guardar una versión disponible actualiza ese sello en la misma transacción. No representa una aprobación humana ni modifica la auditoría anterior. Las revisiones optimistas, idempotencia, jerarquía y validación de configuración se mantienen. Guardar un perfil pausado conserva la pausa. Una restauración explícita permite editar un histórico sin activar una configuración incompleta.

Esta decisión no elimina la aprobación del ámbito de una fuente publicada, las condiciones académicas de una etapa o la aprobación de una acción sensible. Tampoco activa conexiones, política automática, marketing o envíos; control humano, identidad explícita del programa, fuentes institucionales y fronteras previas al despacho conservan su prioridad. No autoriza escrituras en el core SIIE ni delega SQL o decisiones académicas a un modelo.

La expansión aislada `020_agent_execution.sql` añade únicamente el registro de ejecuciones relacionado con `crm_agents.Usage` y el registro único existente. El coordinador la aplicó explícitamente en la copia local con TLS/target verificados; no hay DDL al arrancar. Esta decisión autoriza campos y operación del módulo, no afirma que todas las combinaciones de proveedor, A/B o acción hayan sido ejecutadas. Aceptación y límites en [contrato de agentes](../contracts/admissions-agents.md), [guía de uso](../guides/agentes-ia.md) y [avance](../progress.md).

## Contrato

Extender únicamente la copia local DBSIIE mediante el esquema aislado `crm_inbox`, con migración explícita 003, versión `inbox-v1` y huella de forma. Conservar `crm`, `crm_admissions`, sus datos y el core. No ejecutar DDL al arrancar. Mantener TLS, guard de destino, trigger DDL existente y bloqueo transaccional compartido `crm.local.commit`.

| Tabla | Responsabilidad |
|---|---|
| Member | Membresía explícita del equipo de Admisiones por ID real `GEEmpleado.CnsctvoEmpldo`, habilitación y fechas. Sin copiar población ni FK core. Nuevas membresías/asignaciones requieren empleado activo. |
| Agent | Registro real de agente con UUID, nombre, descripción y disponibilidad para asignación. No registra credenciales ni habilita ejecución. |
| Assignment | Referencias independientes a humano y agente IA por conversación; cambiar control humano/IA conserva ambas. |
| Task | Título, prioridad, responsable humano opcional, vencimiento UTC y estado pendiente/completada/cancelada por conversación. No hay borrado físico. |
| SlaPolicy | Una política opcional, umbral explícito en minutos y habilitación. Sin fila inicial ni valor prellenado. |
| Operation | Idempotencia, revisión propia, acción/entidad, huella del payload y actor local. No acredita usuario autenticado. |

Equipo y agentes empiezan vacíos; la persona operadora configura miembros seleccionando empleados activos reales. Un responsable deshabilitado conserva referencias históricas; no recibe nuevas asignaciones. Completar/cancelar tareas existentes sigue permitido. No se infiere pertenencia por área, cargo o nombre.

Toda mutación usa operationId, expectedRevision y payload canónico; replay devuelve la revisión originalmente confirmada antes de comprobar revisión actual. Configuración y operación comparten su revisión `crm_inbox`, independiente de la revisión `crm`. Asignar humano actualiza la etiqueta compatible de conversación y su operación `crm` dentro de la misma transacción, sin tocar control/estado. Después de activar este contrato, la ruta antigua no admite cambiar responsable mediante texto libre; sí conserva cambios de control/estado/prioridad. No se convierten etiquetas históricas automáticamente.

## SLA de próxima respuesta local

Solo tiempo transcurrido **24/7**, sin calendario laboral ni pausas. El inicio es el mensaje entrante más antiguo posterior al último saliente local, ordenados por Sequence. Un saliente local registrado cuenta como respuesta local; **no acredita envío ni entrega externa**. Espera, prioridad y control IA no pausan el reloj; una conversación cerrada queda excluida. El vencimiento exacto ya cuenta como vencido. Sin política habilitada: no configurado. Sin entrante pendiente: sin medición. Activar/cambiar política evalúa el pendiente real existente; no inventa un inicio ni reescribe mensajes. La política debe presentarse expresamente antes de confirmarla.

Una tarea vencida y el SLA de respuesta son indicadores distintos. No hay avisos externos, worker, recepción simulada, análisis IA ni autenticación compartida incluidos.

## Recuperación y aceptación

Preflight del destino local, respaldo/restauración conservados y ensayo en restauración antes de aplicar. Repetición no-op, rechazo de forma desconocida y rollback parcial comprobables. La reversión conserva tablas/filas: detener el preview y mantener esquema/filas para recuperación; no volver a un escritor anterior que ignore referencias estables, ni ejecutar DROP/restauración destructiva sobre cambios posteriores. Preservar auditorías DDL automáticas, sin borrarlas ni desactivar triggers.

Aceptar por capas: tests con dobles, migración y lecturas SQL reales, pruebas reversibles de mutación/idempotencia/conflicto, HTTP, mismo preview local y navegador. Sin registros técnicos finales ni afirmaciones de identidad autenticada, canal externo o política institucional aprobada por defecto.
