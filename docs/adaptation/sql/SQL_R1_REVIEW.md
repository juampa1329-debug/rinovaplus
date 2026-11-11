# SQL-R1 — Inspección local de metadatos: preflight bloqueado

Fecha: 2026-10-24, America/Bogota. El propietario autorizó expresamente conectar a la copia local configurada para revisar tablas, columnas y relaciones, sin leer filas de negocio, modificar datos o aplicar migraciones.

## Resultado actual

**No se obtuvo una conexión autenticada.** Tres intentos con ODBC Driver 18, `readonly=True`, `autocommit=True`, timeout de conexión 5 s y TLS estricto fallaron en preflight con SQLSTATE `08001` y diagnóstico SSL/TLS. No se imprimieron mensajes brutos ni credenciales. No se ejecutó ninguna consulta SQL de identidad, tablas o filas; no hay un inventario SQL actualizado que presentar.

Se conservaron `Encrypt=Yes`, `TrustServerCertificate=No` y el nombre de certificado configurado. Se usó el constructor/validación de configuración existente sin importar la aplicación ni el workspace; no se cambió el contrato SQL Server 2019 ni se iniciaron workers. No se probó un destino alternativo saltando controles de identidad.

## Hechos observados sin cambios del sistema

| Comprobación | Resultado |
|---|---|
| Configuración privada efectiva | Copia local `local_sql_copy`; credenciales presentes, valores no exportados. |
| Transporte configurado | `host.docker.internal`; nombre resuelve, con endpoint TCP explícito. |
| Cliente | ODBC Driver 18 disponible. |
| Conexión TLS | Rechazada; SQLSTATE 08001. El diagnóstico SSL/TLS no establece por sí solo una causa única. |
| Archivo público configurado para la CA del contenedor | Ruta inexistente en este equipo. No es prueba por sí sola del estado de confianza Windows. |
| Docker | Engine no disponible; no hay un contenedor existente desde el cual reutilizar el bundle de CA. No se arrancó Docker. |
| Instancia Windows | Servicio `MSSQL$SQLEXPRESS` activo y proceso SQL escuchando TCP. No se autenticó ni se verificó su base/versión. |
| Máquina esperada por configuración | Difiere del nombre de este Windows. No se sustituyó por una identidad derivada del servidor. |
| Certificado histórico `.local/sql-tls` | Hay un archivo público antiguo; no se instaló ni se asumió que pertenezca al endpoint actual. |

La configuración apunta a un contexto de Docker anterior y existe una instancia Windows local. No se puede afirmar que sean el mismo destino ni rebajar TLS para conseguir acceso. Se pidió aclarar **instancia Windows local SQLEXPRESS/DBSIIE frente al entorno Docker original**. La lectura queda pendiente de esa identificación y de una ruta de confianza TLS válida para el destino confirmado. No hace falta reenviar contraseñas en el chat.

## Contexto disponible que se conserva

[CONNECTION_CONTEXT.md](CONNECTION_CONTEXT.md) identifica consultas y rutas existentes de catálogo, admisiones e identidad. El [informe académico del 14 de octubre](../../reports/dbsiie-schema-inventory.md) y sus hashes coincidentes siguen siendo evidencia histórica, sin atribuirles vigencia actual. [P1.1](P1_1_REVIEW.md) inventaría 19 migraciones y 68 declaraciones CRM; no prueba que existan en esta instancia. [P1.3](P1_3_MIGRATION_PLAN.md) sigue siendo definición, sin migrador/DDL institucional aplicado.

El informe TLS histórico documentó motor 17.x en una sesión anterior. P1.2 exige motor 15 para el runtime SQL2019; esa diferencia requiere observación y tratamiento explícitos, no cambiar el guard. La versión actual no pudo consultarse. Ningún catálogo de tablas ni grafo de esquema observado se ha generado con datos nuevos.

## Continuación segura

Tras aclarar el destino y resolver su confianza TLS sin relajar controles: comprobar base/instancia/máquina contra identidad aprobada; observar versión/compatibilidad/edición; consultar sólo `sys.tables`, `sys.columns`, tipos, claves, índices y relaciones FK con columnas y orden; contrastar mapeos y captura histórica; guardar evidencia saneada y construir un grafo separado de **metadatos observados**. No ejecutar rutas de negocio, procedimientos de usuario, migradores o preflights de migración.

Este corte sólo registra el intento fallido y su bloqueo en grafos/memoria. No completa el objetivo conectado. [Estado](../../../tasks/TASK_STATE.md), [evidencia](sql_r1_validation.json).
