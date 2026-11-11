# ADR-017 · Interfaz por capacidades en la restauración CRM

Fecha: 2026-10-25, America/Bogota. Aceptado para SQL-C5, continuación solicitada del [corte de repositorios SQL-C4](ADR-016-foundation-repositories.md).

## Decisión

La entrada real de React espera un manifiesto público de capacidades antes de montar la aplicación. El servidor lo deriva de la composición seleccionada; no incluye credenciales, destino SQL o señales de disponibilidad de la base. Si falta, está mal formado o contradice el perfil, la interfaz muestra un error recuperable y no monta los propietarios de datos. No se adopta un perfil demo tras un fallo.

El perfil foundation admite Resumen, Clientes, Inbox y Ajustes CRM. Las demás rutas se muestran pendientes y sus componentes no se montan. Dentro de CRM e Inbox se omiten catálogos/perfiles académicos, unificación/actividad avanzada, análisis, evaluación, asignación/SLA, agentes, medios, comentarios y envío externo. Los permisos y guards del servidor siguen siendo la autoridad aunque alguien altere el navegador.

La configuración CRM y los borradores de contactos conservan sus propietarios actuales. Clientes y el editor de Inbox reutilizan `ClientFields`, el mismo documento B006 y la misma transacción B001. En foundation se elimina la ficha de lectura duplicada y el encabezado redundante; estado y prioridad quedan en un despliegue independiente debajo del editor. El contrato DTO admite explícitamente la ausencia de operaciones avanzadas, sin inventar una asignación o una evaluación.

## Activación local

Se reutilizan el login, permisos, ticket y credenciales cifradas de C4. Un cargador del runtime lee únicamente ese perfil preparado mediante una ruta explícita; no importa herramientas administrativas, crea permisos/tablas o toma las credenciales del selector. Validación de destino, identidad, ACL, forma, historial y TLS permanece en cada transacción.

`compose.foundation.yaml` activa expresamente esa composición, monta el perfil privado de sólo lectura y vacía las credenciales heredadas de proveedores. El overlay SQL conserva la CA pública y la validación TLS. No se edita `.env`. El mismo preview loopback de 4173 queda en `local_foundation`; no se inicia ningún worker, proveedor o transporte.

El perfil del selector de inspección se conserva para una composición que lo admita; cambiar la fuente de inspección no redirige el runtime CRM. Después de cambiar de composición se recarga la página completa para obtener el nuevo manifiesto y evitar estado de una sesión anterior.

## Aceptación, historia y reversión

[SQL-C5](../adaptation/sql/SQL_C5_REVIEW.md) registra pruebas, navegador real, escrituras CRM sintéticas y firmas académicas antes/después. No hubo DDL, migraciones, cambios de permisos SQL o modificación de tablas académicas en C5.

La cadena de checkpoints conserva C4 y su baseline inmutables y registra las transiciones C4→C5. No se vuelve a firmar C4 ni se permite sustituir los SQL, snapshots o herramientas C3 congelados. Las capturas e inventarios históricos siguen distinguidos de los consumidores actuales.

Para volver al preview anterior se recrea el servicio con Compose base y el overlay TLS, omitiendo foundation, y se recarga el navegador. Esto vuelve al modo local configurado; no revierte tablas, diario o datos. No deshabilitar TLS, limpiar el ensayo ni reaplicar C3. La credencial dedicada puede conservarse cerrando la composición; no se revoca ni se amplía automáticamente.

Permanecen pendientes el siguiente release CRM, la base SIIE completa, autorización/RBAC institucional y aceptación conectada SQL Server2019. El modo de ensayo no certifica la plataforma educativa completa.
