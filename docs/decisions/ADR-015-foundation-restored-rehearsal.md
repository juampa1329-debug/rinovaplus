# ADR-015 — Primer paquete CRM y ensayo en restauraciones

Fecha: 2026-10-24. Estado: implementado y ensayado en copias restauradas; alcance SQL-C3. Solicitud humana: B000+B001+B006, seis tablas CRM y diario, pruebas, preservación académica y continuidad con grafos/memoria.

## Alcance

La única fuente del backup es HORARIOSSIIE local. La aplicación del paquete se limita a restauraciones nuevas con nombres `CBN_C3_REF_20261024_*` y `CBN_C3_TRIAL_20261024_*`, identidad/base/fecha de creación fijadas en un expediente privado. Se rechazan la fuente, bases de sistema, otro servidor, principal, motor o destino. TLS permanece obligatorio, sin reconnect ni pooling. El motor ensayado es SQL Server2022Express/compat160; el contrato institucional2019 de P1.2 permanece intacto y pendiente de ensayo propio.

La línea [cbn_foundation](../../backend/migrations/cbn_foundation/release.json) contiene tres SQL nuevos, sin editar los19 históricos o sus nueve runners. B000 crea `crm_meta.MigrationJournal`; B001 crea Contact, Conversation, Message y Operation en `crm`; B006 crea Configuration y Operation en `crm_config`. No modifica ni fabrica tablas académicas. Los markers nuevos describen este contrato, sin afirmar ejecución o compatibilidad del legado.

## Preparación y privilegios

La preparación administrativa es un paso explícito separado de las transacciones B000/B001/B006: crea sólo un usuario de base **WITHOUT LOGIN** y tres esquemas vacíos propiedad de dbo. No crea login de servidor. Concede CREATE TABLE/VIEW DEFINITION y permisos sobre esos tres esquemas; REFERENCES sólo en crm para sus cinco FK. Niega UPDATE/DELETE en crm_meta. No concede SELECT/DML/ALTER académico. El estado preparado exacto, incluidos sus permisos, es el prefijo0; no se acepta cualquier esquema parcial por estar vacío.

El runner ejecuta con `EXECUTE AS USER`, valida USER_NAME y permisos antes de cada batch y revierte/cierra la sesión al terminar. Los permisos directos académicos son cero y NULL se considera inconcluso. Esto **no es un sandbox para SQL arbitrario**: los esquemas dbo pueden participar en ownership chaining. La protección exige SQL revisado e inmutable, contrato de destino, firmas de forma/contenido y ausencia de triggers DDL. El paquete no crea triggers ni ejecuta procedimientos académicos.

## Forma, datos e historial

Primero se construyó una referencia restaurada. Un verificador independiente contrastó tipos/longitudes/precisión/nulabilidad/collations, defaults UTC, identities, PK/UQ/clustered, índices, CHECK, cinco FK y su confianza/acciones contra001/006 y el contrato del diario. Las formas completas por prefijo se congelaron después de esa revisión y de pruebas SQL en rollback. Otra restauración aplicó el release con esas formas ya fijadas; el runner nunca aprende aceptación desde su propio destino.

El paquete verifica hashes de SQL, herramientas, fuentes legacy, manifiesto y modelo de forma. Un marker por sí solo no sirve. B006 exige instalación con contactos vacíos y crea un único documento institucional con cuatro listas vacías y Revision1; repetir verifica su invariancia estructural/singleton y conserva una configuración legítimamente editada. No importa datos demo, Scentra, catálogo o usuarios SIIE.

B000 crea diario y COMMITTED en una sola transacción. B001/B006 confirman STARTED aparte y DDL+COMMITTED juntos. Se usa la misma conexión física, lock exclusivo de migración y lock transaccional de escritores, con timeout. La auditoría externa conserva intentos incluso sin diario. Un resultado incierto bloquea nuevas aplicaciones hasta reconciliación explícita de historial y forma; no repite DDL. Se reconocen únicamente prefijos exactos de estas tres unidades. Adopción legacy, compensaciones/DOWN posteriores al commit y demás grupos P1.3 no están implementados aquí.

El diario permite sólo INSERT/SELECT al proceso previsto; un administrador privilegiado o alguien capaz de alterar el esquema puede manipularlo. No es una auditoría criptográficamente inviolable. Se conservan manifiestos, herramientas y expediente fuera de SQL. Un release ya ejecutado no cambia sus checksums para aceptar otro resultado.

## Ensayo y recuperación

Backup COPY_ONLY/CHECKSUM, cabecera y VERIFYONLY, restauraciones reales en bases/archivos nuevos sin REPLACE y CHECKDB fueron comprobados. La firma académica cubre metadatos y contenido de las50 tablas preexistentes: valores SQL convertidos a binario para conservar precisión completa, sin exportar filas ni hashes individuales. La lectura administrativa calcula esas huellas; no se amplían ACL académicas del migrador. Los permisos/principales de preparación se distinguen de las tablas protegidas.

El release v1 reveló en el ensayo un defecto de comparación textual de GUID SQL en mayúsculas frente a UUID externos en minúsculas. Se bloqueó; sus filas no se editaron. Se conservaron manifiesto/SQL/tres herramientas y copias retiradas. El release v2 usa comparación canónica UUID y se ensayó en restauraciones nuevas. Las siete copias retenidas conservan las mismas firmas académicas que la fuente.

Reversión de fallo previo a commit: rollback de la unidad al prefijo anterior y registro de resultado. Ante commit incierto: pausa y reconciliación. Tras commit no se promete DROP/RESTORE global ni DOWN genérico: conservar datos y diario, usar corrección compatible o recuperación separada revisada. Nada se restauró encima de HORARIOSSIIE ni se activaron repositorios, workers o proveedores.

Evidencia y límites: [SQL_C3_REVIEW.md](../adaptation/sql/SQL_C3_REVIEW.md), [sql_c3_validation.json](../adaptation/sql/sql_c3_validation.json). No acredita producción, paridad funcional ni SQL Server2019 institucional.
