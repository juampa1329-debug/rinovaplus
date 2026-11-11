# SQL-C3 — B000+B001+B006 implementado y ensayado

Fecha: 2026-10-24, America/Bogota. **Resultado: paquete creado y aceptado en restauraciones independientes de HORARIOSSIIE. La fuente permanece intacta.** El propietario autorizó implementación de seis tablas CRM y diario, pruebas y ensayo restaurado. No se activa CRM de negocio en esta unidad.

## Resultado concreto

Release aceptado: `CBN-foundation-local-v2`, SHA-256 `b8de5466cd6c0e8b373490cc0987bacbf90deff95ffe45e8d84f54f6dc08827a`. [Manifiesto](../../../backend/migrations/cbn_foundation/release.json), [formas congeladas](../../../backend/migrations/cbn_foundation/expected-shapes.json), [ADR-015](../../decisions/ADR-015-foundation-restored-rehearsal.md).

Base principal de ensayo: **CBN_C3_TRIAL_20261024_ac8505b8**. Copia para fallos: **CBN_C3_TRIAL_20261024_df12f51b**. Referencia de construcción: CBN_C3_REF_20261024_6a5ce20c. Son bases separadas en la instancia local, con archivos nuevos; no reemplazan HORARIOSSIIE ni la convierten en DBSIIE.

| Unidad | Objetos creados | Estado principal |
|---|---|---|
| B000 | crm_meta.MigrationJournal | Creado y COMMITTED atómico |
| B001 | crm.Contact, crm.Conversation, crm.Message, crm.Operation | Cuatro tablas creadas, sin contactos/mensajes demo |
| B006 | crm_config.Configuration, crm_config.Operation | Dos tablas; singletonId1/Revision1 y cuatro listas vacías |

El paquete suma **7 tablas, 69 columnas, 12 índices, 16 CHECK y5 FK**. El diario conserva el éxito de las tres unidades. La repetición es NOOP, no vuelve a sembrar ni modifica la configuración. Los contadores IDENTITY pueden tener huecos tras pruebas rechazadas/rollback; no se interpretan como pérdida del diario.

## Fuente y tablas académicas preservadas

HORARIOSSIIE mantiene **50 tablas, 437 columnas y41 FK**, sin esquemas CRM. Se usó para SELECT de verificación y BACKUP COPY_ONLY/CHECKSUM; no recibió DDL/DML. El backup registra historia de respaldo normal en msdb, sin cambiar filas o tablas académicas. No se cambió el recovery model SIMPLE ni la compatibilidad160.

Se verificó igualdad de metadatos y contenido académico antes/después de preparar/aplicar/ensayar. Las50 tablas y44.180 filas de la captura se procesaron privadamente. El hash usa representaciones binarias SQL y conserva la séptima fracción de datetime2, evitando la pérdida de precisión del datetime de Python. No se publicaron filas ni hashes de personas/filas/tablas individuales. Las siete restauraciones retenidas, incluidas las retiradas, conservan las firmas académicas de la fuente.

No se concedieron permisos de lectura o escritura sobre tablas académicas al nuevo usuario. El cálculo de huellas usa la sesión administrativa autorizada. La preparación crea sólo usuario de base sin login, permisos CRM y tres esquemas vacíos, fuera de la atomicidad posterior de B000. Su estado exacto es el contrato preparado; se bloquearon namespace/forma desconocidos. Los permisos directos no convierten al usuario en sandbox contra SQL arbitrario por ownership chaining; las capas de SQL inmutable, formas externas y comprobaciones de datos son necesarias.

## Backup, referencia y release

La cabecera confirmó backup full COPY_ONLY, checksums y ausencia de daño; VERIFYONLY pasó. Cada restauración usó nombre y archivos inexistentes, MOVE explícito, sin REPLACE, y pasó CHECKDB. El expediente privado conserva GUID/LSN/cabecera/rutas/identidades, tickets de destino, firmas y auditorías. No se copió el estado IA ni se modificaron sus volúmenes o credenciales.

La primera construcción detectó que faltaba REFERENCES para crear FK; se concedió **sólo en crm** y se usó otra referencia. Una exportación de artefactos también falló por permisos del directorio de código Docker: se pasó a una salida privada escribible y se mantuvo el código separado. Esas dos referencias son construcciones retiradas, no releases aceptados. Tras actualizar el modelo de ACL se comprobó su proyección anterior y el nuevo modelo, sin sustituir un checksum para ocultar drift.

La referencia final se validó contra los contratos originales y pruebas de integridad. Se congelaron cuatro formas: preparado, B000, B001 y B006. El release sólo se aceptó después de aplicar esas formas en otra restauración; no se usaron markers/hash autocotejados de la misma base como criterio de aceptación.

El primer release ensayado (`12049a…`) falló en la reconciliación de un ACK perdido simulado: SQL devolvía el GUID en mayúsculas y la auditoría externa en minúsculas. Aunque B001 estaba confirmado, la comparación textual lo clasificó como no aplicado. La comprobación de forma/historial bloqueó la continuación; no hubo reintento DDL. Se preservaron sus filas, manifiesto, SQL y bytes de herramientas. **No se editó el historial para que pasara.** La corrección usa `uuid.UUID`; v2 se congeló y aplicó en dos restauraciones nuevas.

Se retienen tres copias vigentes (referencia, ensayo principal y fallos) y cuatro retiradas (dos construcciones y dos del releasev1), además del backup. Las rutas y el inventario de artefactos están sólo en `.local/sql-c3`; no se aplicó limpieza o DROP genérico.

## Pruebas realizadas

| Capa | Resultado y alcance |
|---|---|
| Offline | **34 pytest aprobados**, sin conexiones SQL/red: hashes y scope, destino fuente/sistema, historial alterado, intentos incompletos, singleton/configuración y regresión UUID SQLuppercase/auditlower |
| Integridad SQL | **31 comprobaciones** con valores sintéticos y rollback: CHECK/JSON/enums, cincoFK, unicidad, revisión, diario/successkey y UPDATE/DELETE del diario denegados |
| Ensayo del release | **24 escenarios** reales sobre copias: aplicación/repetición, principal/destino/TLS/transacción ajenos, drift de columna/CHECK/FK/índice/marker/objeto parcial, dos migradores y writer lock, fallos B000/B001/B006, ACK incierto, reconciliación, reanudación y configuración editada/ausente |
| Integridad física | CHECKDB al restaurar cada copia y al terminar en ensayo principal/fallos, sin errores |
| Preservación | Firmas académicas iguales en fuente y siete copias; sin grants académicos, SQL histórico/runners/runtime/referencia Scentra intactos |
| Estática | Ruff de los cinco helpers y nuevo test aprobado; no suite completa ni frontend build porque no cambió producto |

La pérdida de ACK es una excepción inyectada **después de COMMIT real**, no una caída real de red/proceso. El runner bloquea nuevos intentos hasta reconciliación explícita y ésta no ejecuta DDL. Los fallos previos al commit devolvieron cada unidad a su prefijo; el diario registró el resultado y la auditoría externa conservó el bootstrap sin tabla.

La copia de fallos contiene una edición sintética de configuración usada para comprobar que repetir no la sobrescribe. La copia principal conserva el singleton vacío inicial. No se insertaron contactos demo persistentes ni se modificaron tablas académicas como parte de los negativos. La comprobación de permisos académicos fue introspección, sin ejecutar ALTER/INSERT/UPDATE/DELETE sobre ellas.

## Contrato entregado y límites

[cbn_foundation.py](../../../backend/tools/cbn_foundation.py) verifica destino, principal, prefijo, dependencias, bytes, forma e historial; usa locks y transacción por unidad. [foundation_snapshot.py](../../../backend/tools/foundation_snapshot.py) calcula metadatos/huellas. [foundation_contract.py](../../../backend/tools/foundation_contract.py) verifica el contrato independiente y restricciones. [rehearse_foundation.py](../../../backend/tools/rehearse_foundation.py) prepara backup/restauraciones/referencia; [foundation_rehearsal_checks.py](../../../backend/tools/foundation_rehearsal_checks.py) ensaya el release. Ninguno se ejecuta al arrancar la app. El diario SQL reserva eventos para futuras etapas, pero el runner sólo implementa estos tres grupos y sus fallos/reconciliaciones; no adopta legados ni implementa DOWN genérico.

Los markers son `CBN-foundation-B001-v1`, `CBN-foundation-B006-v1` y `CBN-migrations-v1`. No equivalen a la aceptación histórica ADR-006 ni habilitan automáticamente los repositorios actuales. El selector permanece sobre HORARIOSSIIE con credenciales cifradas, TLS estricto, modo local_demo y salida IA apagada. Las14 fuentes académicas ausentes y32 tablas dependientes deGEEmpleado no se fabricaron ni desbloquearon.

**No acredita SQL Server2019 institucional, operación de Inbox/CRM completa, proveedores, autenticación institucional, producción ni recuperación global después del commit.** El ensayo local es motor16Express/compat160. Los19 SQL históricos, nueve runners y guardP1.2 se conservan. [Validación saneada](sql_c3_validation.json); expediente privado `.local/sql-c3`.

Siguiente unidad: integrar los repositorios con el contrato nuevo en el destino de ensayo y aceptar funciones independientes del fragmento, manteniendo diagnósticos/bloqueos para fuentes académicas ausentes. La aplicación sobre HORARIOSSIIE original no se hizo en esta unidad y debe mantenerse distinguida del ensayo verificado.

Grafo específico del release: [HTML](../../../graphify-out/sql-foundation/graph.html), [JSON](../../../graphify-out/sql-foundation/graph.json), [Canvas Obsidian](../../../graphify-out/sql-foundation/obsidian/graph.canvas).118nodos/143relaciones/8comunidades, con columnas calificadas por esquema; no mezcla la copia ensayada con la fuente.
