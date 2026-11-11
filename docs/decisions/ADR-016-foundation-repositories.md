# ADR-016 · Repositorios sobre la restauración B000+B001+B006

Fecha: 2026-10-24. Aceptado exclusivamente para el ensayo local SQL-C4 solicitado por el propietario. Continúa [ADR-015](ADR-015-foundation-restored-rehearsal.md); no concede aceptación institucional SQL2019.

## Problema y decisión

El núcleo SQL ensayado tiene seis tablas CRM y el diario, pero los repositorios existentes reconocen contratos legacy y el Inbox consulta también canales, perfiles y operaciones que no están instalados. Abrir sus guards sin adaptar las consultas produciría errores o activaría capacidades sin respaldo.

Se introduce la composición explícita `local_foundation` con entorno `foundation_rehearsal`, limitada a `CBN_C3_TRIAL_20261024_ac8505b8`. Reutiliza `SqlWorkspace`, las validaciones de configuración y los escritores transaccionales. El Inbox tiene consultas B001 específicas. Se mantienen revisión global, bloqueo transaccional, hash de operación, replay y rollback. Una revisión IDENTITY puede tener huecos; el contrato exige monotonía y comparación exacta, no ordinales consecutivos.

El perfil requiere SQL auth independiente, TLS validado, identidad de máquina/instancia/base y ticket privado cuyo SHA se proporciona expresamente. No toma credenciales del selector ni del administrador/migrador. La aplicación no crea tablas, usuarios, permisos o migraciones. La preparación administrativa explícita es una herramienta de ensayo separada.

## Contrato y permisos

El runtime fija el SHA del release C3, la forma final y el lector canónico inmutable. Comprueba identidad incluyendo ID/fecha de creación de la base, SID/login/usuario, ACL exacta, permisos efectivos, visibilidad de metadatos, las 50 tablas no CRM y firma binaria del diario. Los nombres/markers legacy no se falsifican ni se admiten como evidencia de C3.

El nuevo actor tiene SELECT/INSERT/UPDATE en Contact y Conversation; SELECT/INSERT en Message y ambos Operation; SELECT/UPDATE en Configuration; sólo SELECT en MigrationJournal. No tiene DELETE, DDL, ALTER, roles de escritura o permisos sobre datos académicos. Los DENY sobre `dbo` pertenecen sólo a ese usuario nuevo en la restauración.

La ACL C4 es una ampliación explícita. Se valida por separado y se proyecta exclusivamente ese actor al comparar la forma histórica C3 y la evidencia académica. Se siguen comparando todos los objetos, permisos, propietarios, roles y principales anteriores. No se ignoran genéricamente ACL ni se editan snapshots C3. El runner C3 antiguo debe rechazar la nueva ACL como drift; no se debe volver a aplicar para corregirlo.

## Superficie disponible y límites

Disponibles: contactos y sus campos base/personalizados; conversación humana con estado/prioridad/unread básico; texto local; configuración de etapas, etiquetas y campos; consultas Inbox paginadas. Primero se debe guardar una etapa válida: el singleton inicial vacío no autoriza inventar defaults en una lectura.

Se rechazan perfiles/enlaces académicos, asignación, modo IA, evaluación, lectura por secuencia, medios y entrega externa. Catálogos, admisiones, canales, agentes, campañas, proveedores y workers no se componen. Las rutas ajenas devuelven indisponibilidad explícita; no hay fallback demo. Todas las rutas API conservan guard loopback/Host/Origin/cabecera local, límite de cuerpo y respuestas `no-store`.

La composición se probó mediante API aislada, sin activar la vista compartida. Su detalle expone capacidades y ausencia de operación avanzada; la UI existente necesita adaptarse a ese contrato antes de activarla. `/health/ready` sigue indicando integración incompleta. No se modificó el frontend ni Scentra.

## Aceptación y reversión

[SQL-C4](../adaptation/sql/SQL_C4_REVIEW.md) registra 269 pruebas focalizadas y 84 comprobaciones reales, preservación académica y deuda de regresión previa. El inventario firmado C3 permanece histórico; `inventory.active.json` describe los consumidores actuales y las transiciones de código se verifican mediante un nuevo checkpoint.

Para suspender esta integración basta retirar su configuración explícita y deshabilitar el login dedicado desde administración. Conservar tablas CRM, datos y diario; no deshacer B000/B001/B006 ni tocar HORARIOSSIIE. El retiro completo del usuario/grants/login es una operación administrativa posterior, contrastada con el ticket privado y sin ejecutar scripts históricos. La reversión de código se limita a las transiciones SQL-C4, preservando el trabajo anterior del árbol.
