# SQL-C7 · B011 y extensión CRM ensayada

Fecha: 2026-10-25, America/Bogota. **Aceptación limitada al esquema de restauraciones independientes. El runtime compartido continúa en SQL-C5.**

## Resultado

`CBN-channels-local-v2`, unidad `CBN-B011`, implementa la forma final de 011+012. Se ensayó sobre `CBN_C7_TRIAL_20261025_634a9b9e`, restaurada desde el CRM C5 poblado. La primera ejecución devolvió APPLIED y la segunda NOOP. Se crearon ocho tablas vacías, 57 columnas, diez FK, tres índices explícitos, once índices de PK/UQ, catorce defaults y ocho CHECK. La partición aceptada enumera 50 tablas académicas, siete foundation y ocho nuevas; no ignora esquemas por prefijo.

Release SHA-256: `49f72eb835ce46b83ec9c6267da2f73c9d7799990de6fab8ed28762565985998`. Formato canónico `cbn-extension-shape-v3`. Sus nueve assets están fijados; el contrato semántico y su especificación se reutilizan desde v1 con verificación transitiva. [Manifiesto](../../../backend/migrations/cbn_channels_v2/release.json), [SQL](../../../backend/migrations/cbn_channels_v2/B011_channels.sql), [partición](../../../backend/migrations/cbn_channels_v2/partition.json).

| Tabla nueva en crm_channels | Preparación habilitada por el esquema |
|---|---|
| Account | Configuración, capacidades, revisión y estado del canal |
| Credential | Contenedor de credenciales cifradas; sin claves reales cargadas |
| webhook_events | Eventos e idempotencia de recepción |
| ExternalIdentity | Referencia CRM a identidad externa y conversación |
| ExternalMessage | Referencia de mensaje externo con identificador BIN2 |
| outbound_queue | Cola persistente con unicidad filtrada por mensaje |
| social_comments | Comentarios con identificadores externos BIN2 |
| Audit | Registro técnico del canal, inicialmente vacío |

Crear estas tablas no habilita consumidores, endpoints nuevos, proveedores, recepción pública, workers ni envíos. Las 54 tablas CRM declaradas restantes siguen diferidas. La paridad general de Scentra no queda aceptada por este ensayo.

## Fases verificadas

| Fase C7 | Resultado y evidencia |
|---|---|
| 1. Contrato y pruebas offline | 119 pytest: 113 del contrato v1 conservado y seis regresiones de canonicalización v3. Ruff de fuentes nuevas/modificadas aprobado. |
| 2. Respaldo y restauraciones | Nuevo COPY_ONLY con CHECKSUM, VERIFYONLY, tres restauraciones iniciales sin REPLACE y CHECKDB. Ocho copias adicionales para confirmar resultados inciertos: once copias v2 en total. |
| 3. Referencia y congelación | Verificador independiente de forma física, datos preservados y prueba Audit INSERT+ROLLBACK antes de fijar el release. |
| 4. Aplicación e idempotencia | APPLIED+NOOP; diario de cinco a siete filas y prefijo original conservado; ocho tablas nuevas vacías. |
| 5. Fallos y recuperación | 51 comprobaciones distintas, sin fallo pendiente; matriz desglosada abajo. |
| 6. Continuidad | Cadena explícita C4→C5→C7; C6 reproducida desde sus preimágenes autenticadas; grafos, memoria y roadmap actualizados. |

[Evidencia estructurada](sql_c7_validation.json), [resultados conectados](../../../artifacts/sql-c7/v2/final-result.json), [JUnit](../../../artifacts/sql-c7/v2/unit-results.xml), [progreso por fases](../../../tasks/sql-c7-progress.json).

## Seguridad, datos e historial

El lector exige visibilidad administrativa completa y congela también objetos no tabulares, dependencias, sinónimos, tipos, permisos, principales y roles. El sinónimo académico preexistente `dbo.HOTiposAula` se autentica contra el catálogo C5 y se conserva; no se ejecuta ni publica su destino. Objetos desconocidos, cifrados o catálogos incompletos bloquean. Los valores binarios SQL preservan la séptima cifra de datetime2(7); las firmas de filas quedan sólo en evidencia privada.

La preparación crea un principal WITHOUT LOGIN exclusivo, con diez GRANT directos y siete DENY sobre dbo. REFERENCES de crm_channels es necesario para sus FK internas; sólo REFERENCES sobre los tres padres CRM y SELECT/INSERT sobre el diario se permiten fuera de ese esquema. Se comprobaron derechos efectivos, membresías, ownership, impersonación y acceso a sinónimos. No se ampliaron los permisos del login C4 ni se otorgó CONTROL al runtime. TLS siguió validando certificado y nombre con ODBC18, Encrypt=yes y TrustServerCertificate=no.

Se conserva el esquema del diario y sus cinco filas originales, con su identidad y semántica históricas. Los eventos C7 usan nueva identidad de restauración, release y formato. STARTED es durable antes del DDL; COMMITTED se confirma en la misma transacción serializable que el DDL. Ante confirmación incierta se bloquean nuevas aplicaciones hasta reconciliar el estado global de esquema e historial bajo los locks existentes. SuccessKey impide un segundo éxito de B011 con otros bytes. Una transacción ya abierta por el llamador se rechaza sin hacer rollback de ella.

La comparación final volvió a leer HORARIOSSIIE y el C5 compartido: catálogo, datos, permisos anteriores, 50 tablas/44.180 filas académicas, 199 filas de negocio CRM y cinco filas originales del diario siguen intactos. El perfil cifrado, ticket, login, ACL y destino del preview C5 no se redirigieron. Los cambios de preparación/migración ocurrieron exclusivamente en copias nuevas; las pruebas de restricciones sólo insertaron filas sintéticas bajo rollback en la extensión.

## Matriz conectada

| Grupo | Comprobaciones |
|---|---:|
| Fallo en 16 fronteras DDL/diario y recuperación tras COMMIT confirmado con ACK perdido | 17 |
| Ocho resultados inciertos: STARTED, aplicación, fallo y reconciliación, con COMMIT real o rollback simulado | 8 |
| Drift, índices filtrados, FK no confiables, CHECK, objetos extra, visibilidad, roles, impersonación, destino, ticket C5 y precisión temporal | 13 |
| JSON, enumeración, FK, BIN2, unicidad filtrada, NO ACTION y salto normal de IDENTITY tras rollback | 11 |
| Exclusión entre dos conexiones independientes: migrador y escritor | 2 |
| **Total distinto** | **51** |

Los cortes ACK son inyecciones del harness sobre transacciones reales; no se simularon cortes eléctricos del servidor. Los labels completos y reportes por grupo están en [artifacts/sql-c7/v2](../../../artifacts/sql-c7/v2/connected-checks.json). El gate final exige todos los grupos y rechaza labels incompletos o duplicados.

## V1 retirada y correcciones de preparación

La primera versión congelada `e4f76c63…` pasó 113 pruebas offline y 48 comprobaciones conectadas, pero falló al consumir IDENTITY de Audit y hacer rollback. El lector ordenaba antes de quitar `identity_last_value`: las mismas 608 filas de metadatos quedaban en otro orden y cambiaba la firma. No había drift físico ni de datos. Se retiró v1 sin editar su release, nueve assets, contadores o copias; no es una aceptación parcial de v1.

V2 elimina el valor volátil antes de ordenar, reordena después de normalizar el SID verificado y usa otro formato y otras restauraciones. Pasó la regresión offline y conectada antes de congelarse y nuevamente durante la matriz. [Registro de retirada](sql_c7_v1_retirement.json). Se conservan ambos paquetes y los respaldos; no se hizo DBCC CHECKIDENT, DROP ni limpieza para obtener una firma esperada.

Antes de congelar v1 se corrigieron comprobaciones de catálogo (`char` con padding), alias SQL reservados, el contrato físico independiente y REFERENCES del esquema nuevo. Esa ampliación mínima se auditó como corrección de preparación en las tres primeras copias; no afecta a C5 ni reescribe C6. La prueba temporal de lectura de last_value requirió convertir sql_variant a nvarchar; no cambió ninguna columna SQL. En el cierre offline se corrigió la comparación de postimágenes para usar la última por ruta de C4→C5, con una regresión que rechaza estados intermedios antiguos.

## Continuidad, reversión y límites

El baseline de entrada C7 se conserva con 409 archivos. La cadena nueva declara adiciones exactas y cambios antes/después, fija ambos releases, conserva C3/C4/C5 y autentica la prueba, plan, baseline y checker C6. El checker C6 original se ejecuta con sus 402 preimágenes públicas y reproduce sus 20 rechazos; no se actualizan hashes de C6 contra otro corpus. Las nuevas adiciones de migraciones deben pertenecer a los manifiestos fijados; un SQL arbitrario o una edición congelada se rechazan.

La reversión previa a COMMIT es rollback transaccional. Después de un COMMIT confirmado no hay borrado automático ni down migration destructiva: conservar el destino y el diario, reconciliar si la confirmación es incierta y, si se necesita repetir otro release, restaurar el respaldo en otra base. El preview C5 intacto mantiene el punto operativo anterior.

El motor local es SQL Server 2022 Express, compatibilidad160; no acredita el motor institucional SQL Server 2019. No se recertificaron la suite general, el navegador ni las capacidades de negocio de Canales. Las pruebas UI de C5 siguen siendo históricas. No hubo llamadas a proveedores, workers, WooCommerce, billing o cambios en Scentra.

Siguiente corte **SQL-C8**: definir e integrar consumidores de B011 en otra composición/perfil de ensayo, con principal y ACL propios, guard de metadatos/historial y pruebas de repositorios/capacidades. El lector C7 requiere CONTROL administrativo y fija las 199 filas previas: **no sirve como guard de runtime mutable**. No ampliar permisos de la aplicación ni congelar/resetear sus datos para reutilizarlo. No redirigir el ticket C4. B015/B018 y la aceptación de SQL2019 siguen en etapas posteriores.

[ADR-019](../../decisions/ADR-019-channels-restored-extension.md), [reanudación](../RESUME.md), [roadmap](../../SCENTRA_ADAPTATION_ROADMAP.md).

El baseline C7 no incluía Dockerfile y tres artefactos de aceptación UI C5. Sus cuatro últimas postimágenes se declaran como pines heredados exactos en la prueba C7 y se verifican contra la cadena y los archivos actuales; no se altera el baseline de 409 entradas. Las regresiones offline rechazan una postimagen intermedia, pines ausentes, alterados o adicionales y adiciones SQL ajenas a los releases.
