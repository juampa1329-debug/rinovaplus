# SQL-C11 · Tablas de paridad ensayadas en otra restauración

25 de octubre de 2026. Resultado: release físico local aceptado; no cambia las aplicaciones C5/C9 ni activa proveedores.

## Resultado y preservación

Se implementaron las cinco unidades del contrato C10, con 24 tablas nuevas en `crm_channels2`: 343 columnas, 78 FK y 79 CHECK. La copia principal de ensayo es `CBN_C11_TRIAL_20261025_d30e2cb2`, con 89 tablas. Conserva 50 tablas/44.180 filas académicas, 203 registros foundation y 23 registros B011. El valor 203 de cortes anteriores corresponde a foundation; el total CRM previo, sumando B011, es 226.

El diario contiene diecisiete entradas: conserva byte por byte las siete originales y añade STARTED/COMMITTED por cada unidad. Una segunda ejecución termina NOOP. El nuevo Context tiene una fila institucional de ensayo; las otras tablas nuevas permanecen vacías tras revertir fixtures.

HORARIOSSIIE, el C5 compartido y C9 conservan sus catálogos y firmas binarias completas de datos. Las firmas C9 también coinciden con la captura inicial C11, anterior a cualquier restauración de esta unidad. Se autenticaron identidad, catálogo y bytes del diario contra el ticket C9 antes del backup. Los propietarios por objeto se capturaron adicionalmente en C11: el lector cerrado C9 no se modifica ni se le atribuye esa cobertura retrospectivamente.

[Preservación](../../../artifacts/sql-c11/preservation.json) · [Ensayo principal](../../../artifacts/sql-c11/trial-result.json) · [Release](../../../backend/migrations/cbn_channels_parity_v1/release.json).

## Implementación y pruebas

El paquete se sella por hashes de SQL, herramientas, modelo, seis prefijos y corpus revisado de CHECK. El guard comprueba la partición exacta y rechaza tablas/columnas desconocidas, FK deshabilitadas, cambios de propietario o ACL. El actor WITHOUT LOGIN recibe diez GRANT específicos y siete DENY académicos; no recibe CONTROL/db_owner ni DML de negocio. Las aplicaciones y sus tickets anteriores no se redirigen.

El lector independiente contrasta tipos, longitudes, NULL, collation, defaults, PK/UQ, índices/filtros, origen/destino de FK y confianza. Las 79 definiciones reales de CHECK se revisaron semánticamente y se comparan exactamente con el corpus pinneado, conservando literales y agrupación. Se distingue SQL físico de reglas transaccionales pendientes en el [mapa de enforcement](../../../backend/migrations/cbn_channels_parity_v1/constraint-coverage.json).

- **39 pruebas offline:** identificadores/destinos inseguros, fuente del contrato, secuencia, preservación de TX del caller, ownership, aislamiento del audit, historial imposible y pérdidas de respuesta de commit.
- **32 negativos SQL:** XOR/ámbito de secretos, JSON, OAuth/TTL, contadores/reservas, firma/retención, cruces de cuenta, evidencia, score/epoch, jobs/rutas y espacios finales en IDs. **Cuatro positivos:** fixtures válidos con rollback, distinción de mayúsculas, dos tombstones con nonce NULL y estado confirmado de operaciones.
- **21 escenarios:** dos fallos por cada unidad —incluido después de escribir COMMITTED antes del commit—, seis ACK inciertos y cinco cambios de drift. Incluyen reintento bloqueado, reconciliación idempotente y pérdida de ACK en la propia reconciliación.
- Respaldo COPY_ONLY/CHECKSUM, VERIFYONLY, restauraciones sin REPLACE y CHECKDB. Recuperación a `CBN_C11_RECOVERY_20261025_a679da98` idéntica al estado anterior al release. Ninguna base se borra o reemplaza para repetir una prueba.

[Pruebas offline](../../../artifacts/sql-c11/offline-results.xml) · [Constraints reales](../../../artifacts/sql-c11/constraints-result.json) · [Fallos y recuperación](../../../artifacts/sql-c11/faults-result.json). Las pérdidas de ACK son inyecciones controladas; no se presentan como una caída real de la red. Los fallos de cleanup por desconexión se comprueban con regresiones offline.

Continuidad offline: 648 preimágenes públicas con CRC/SHA verificados y 64 transiciones históricas inválidas rechazadas. Se conservan los 432 inputs de runtime, pruebas, migraciones anteriores, composición y referencia Scentra presentes en la línea base. Ruff E/F/I y AST aprobados. [Resultados](../../../artifacts/sql-c11/offline-checks.json). Los dos previews responden con sus perfiles C5/C9 anteriores según [GET de manifiestos](../../../artifacts/sql-c11/previews.json); no se cambia su navegación ni su base.

TLS conserva Encrypt=Yes, validación del certificado y hostname revisado. Se utiliza la CA local existente para el proceso de ensayo; no se activa TrustServerCertificate. No se exportan credenciales, claves ni filas personales. Los valores binarios heredados sólo se leen para hash de preservación; no se descifran ni se publican.

## Límites y siguiente unidad

El motor ensayado es **SQL Server 2022 Express, compatibilidad160**. Los tipos y sentencias apuntan a SQL2019, pero falta su aceptación institucional real. No se ejecutan los SQL históricos 015/011 sobre la fuente ni se alteran tablas académicas/foundation/B011. Las cinco unidades y herramientas selladas no se editan para repetir el ensayo.

[B011 inventariado](../../../artifacts/sql-c11/legacy-readiness.json): 23 registros conservados, sin copiar a las tablas nuevas. Identidad insuficiente, clave no verificada o evento sin firma bloquean su promoción. Faltan correspondencias, recifrado, repositorios/API, autenticación P2, permisos de operación, UI completa y proveedores. Crear las tablas no acredita esas funciones.

SQL-C12 propuesto integra esos repositorios y mappings con perfil propio antes del preview general unificado. [Estado completo y acceso a previews](../../ADAPTATION_STATUS.md) · [Seis etapas C11](../../../tasks/sql-c11-progress.json) · [ADR-023](../../decisions/ADR-023-channels-parity-schema-rehearsal.md).


Cierre Graphify C11: código 2496 nodos/6586 relaciones; adaptación 625/1018, con 43 hallazgos y 12 fases acíclicas. El fragmento C11 contiene 125 nodos/216 relaciones y conserva las 78 FK mediante nodos de constraint, evitando colapsar FK paralelas en DiGraph. Siete grafos sin extremos ausentes/colgantes o nodos/aristas duplicados; cero bucles en adaptación y nueve AST anteriores. El inventario SQL histórico de 19 archivos sigue separado del release C11; sus conteos no describen las 89 tablas de la copia de ensayo. Estos tamaños no son porcentajes de paridad.
