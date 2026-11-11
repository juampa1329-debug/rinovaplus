# Cierre técnico P1: esquema español y SQL Server 2019

Fecha: 26 de octubre de 2026. **P1: 5/5 criterios aceptados, 100% técnico.** P2 continúa en implementación. La aceptación institucional y productiva corresponde a P11.

El paquete entregado por el propietario se trató como referencia, sin ejecutar sus generadores Python/PowerShell/JavaScript. Se inspeccionaron 55 miembros y sus rutas antes de extraerlos. El SHA256 del ZIP es `f6a8468291c022b85b8c953cbcf6291d384258115fc443698be0b6f35ca69b40`.

## Resultado

Los SQL originales crean y verifican correctamente su esquema en SQL Server 2019 real, motor 15, compatibilidad 150. Se conserva TLS verificado: cifrado obligatorio, validación de certificado y rechazo de un hostname incorrecto. La ejecución original se hizo en `DBSIIE_CRM_Esquema_ES_20261026`; una segunda creación rechazó el destino existente antes de escribir.

| Estructura del paquete | Cantidad |
|---|---:|
| Tablas CRM con nombres españoles | 68 |
| Estructuras académicas seleccionadas y sus padres | 30 |
| Tablas del paquete | 98 |
| Columnas | 795 |
| Índices | 162 |
| CHECK | 170 |
| Claves foráneas | 125 |
| Diario adicional del release nuevo | 1 |
| Tablas en la copia migrada | 99 |

La nueva versión `cbn-spanish-baseline-v2` fija nueve entradas por hash y dos unidades: ES-B000 crea el diario y ES-B001 instala el esquema. Manifiesto SHA256 `5457c8da43a9c303c5b7032cff625a3d7ae112c876187c61fdb31e7a8948e2d3`. La copia principal es `CBN_P1ES_TRIAL_20261026_fe815d77`, restaurada nativamente desde un respaldo vacío verificado **antes de la primera aplicación**. No se reutilizó una base poblada ni se borraron registros para repetir pruebas.

## Controles comprobados

El migrador exige aprobación externa del manifiesto, nombre/identidad del destino, motor/compatibilidad, catálogo inicial aprobado y actor sin CONTROL/db_owner. Valida bytes, rutas exactas y cuerpos DDL; no acepta SQLCMD inclusiones/comandos arbitrarios. Rechaza una transacción ya abierta sin apropiarse de ella. Usa locks, historial SQL y WAL durable con enlace por destino, unidad, intento y catálogo. Una confirmación incierta exige reconciliación mediante conexión independiente antes de continuar. Las conexiones que no puedan liberar locks o revertir la identidad se descartan.

El lector independiente compara definición de columnas, tipos, defaults, índices, filtros, columnas FK, CHECK, estado/trust, ANSI y opciones de tabla. Incluye `STATISTICS_NORECOMPUTE` y `OPTIMIZE_FOR_SEQUENTIAL_KEY`, además del catálogo de objetos, tipos, principales, permisos y roles. No basta que coincidan nombres o conteos.

| Verificación ejecutada | Resultado |
|---|---|
| 75 pruebas focalizadas de catálogo/protocolo/perfil/release | Aprobadas |
| 61 regresiones institucionales puras de P2 | Aprobadas, sin aceptación SQL/UI P2 |
| Ocho fallos reales: antes/después de commit, DDL erróneo, conexión cerrada y ventanas WAL→SQL STARTED | Reconciliación independiente y reintento aprobados |
| Confirmación perdida después de sintetizar STARTED durante recuperación | Segundo reconciliador, reintento y NOOP aprobados |
| Dos migradores simultáneos | Un COMMITTED y un NOOP; dos claves de éxito únicas |
| Ocho negativos de identidad, transacción, baseline, permisos, bytes y restauración | Rechazados antes de los efectos no autorizados |
| Seis drift: CHECK con mismo conteo, dos opciones de índice, tipo de columna, vista extra y ACL | Detectados, sin continuar la migración |
| Perfil propio, cifrado y ticket: sólo seis tablas CRM con SELECT/INSERT/UPDATE | Lectura/CRUD local y rollback aprobados |
| Seis sentencias reales: lectura/borrado académico, DELETE CRM, otra tabla CRM, diario y suplantación de dbo | Denegadas por SQL |
| Respaldo COPY_ONLY/CHECKSUM y header/GUID ligados a origen | VERIFYONLY y rechazo de sustitución aprobados |
| Restauración previa y posterior | CHECKDB, catálogo y firma binaria de datos iguales |
| Reversión del esquema a otro destino nuevo | Baseline restaurado, historial y datos de la copia principal conservados |
| Reinicio del contenedor SQL2019 propio | Catálogo, datos, diario y perfil iguales |
| Seis bases anteriores | Catálogos y firmas binarias exactamente iguales antes/después |

Las fuentes preservadas son HORARIOSSIIE, C5/C3, C9, C11, C12 y C13. C5 y C13 siguen saludables y responden HTTP 200 con sus imágenes anteriores. No se modificaron sus perfiles, permisos, imágenes, puertos o volúmenes para adoptar este esquema. Sólo se reinició el SQL2019 nuevo; no SQLEXPRESS/Windows.

## Reversión y límites

La reversión se ensayó mediante restauración nativa del baseline en **otro destino nuevo**, conservando la copia principal y sus recibos. El par anterior de aplicación/base permanece operativo. No se ofrece un downgrade destructivo de una futura instalación poblada; no hay DROP/DELETE para aparentar vuelta atrás. Antes de adoptar el esquema español con datos reales habrá que probar esa transición y su recuperación en su propio alcance.

El ZIP no incluye datos, usuarios, credenciales, procedimientos, vistas ni triggers heredados. Se valida una fundación técnica de estructura, no los 790 objetos/tablas de una DBSIIE completa ni sus procesos académicos. Las 30 tablas académicas de esta copia son estructuras vacías; ninguna se usó para reemplazar la fuente institucional. El CHECK temporal que bloqueó la transferencia académica anterior se conservó intacto.

La nomenclatura `dbo.CRM*` sólo rige este release. No se crearon aliases ni se redirigió el runtime `crm`/`crm_channels2` actual. Los campos y acciones deben seguir Scentra cuando se integre P2; un cambio de nombre de tabla por sí solo no demuestra compatibilidad semántica. No se activaron proveedores, OAuth, recepción pública, mensajes, entrenamiento, listener o nueva UI.

Los ensayos V1 y la candidata V2-R1 se conservan como historia. R1 no comprometió unidades. El V2 aceptado usa el manifiesto anterior; no se reescribieron releases ya comprometidos para corregirlos. Las revisiones R1/R2 detectaron problemas de vinculación/recuperación que se corrigieron antes de la aceptación; R3 y la revisión de la evidencia conectada documentan su resolución. Los primeros errores del harness y la conexión prematura tras reinicio se conservan como intentos privados, sin presentar esos intentos como aprobados.

El paquete enlazaba tres visualizaciones ausentes. El [grafo Graphify nuevo](../../../graphify-out/p1-es/graph.html) aporta la vista de relaciones y trabajo con fuentes; no se afirma que esos archivos faltantes vinieran en el ZIP.

## Roadmap y continuación

La petición nueva del propietario cambia la medida principal: ahora cuenta trabajo parcial con evidencia. Los 56 criterios y sus dependencias no cambian; se fijan 279 hitos con participaciones exactas que suman 1 dentro de cada criterio. Hay 113 hitos completados y 166 pendientes; no se usan sus conteos para ponderar las fases. Aceptación: 10/56 criterios. Ver [tabla por fase](../../ADAPTATION_STATUS.md), [detalle](../WORK_PROGRESS.md), [definición fija](../phase-work-definition.json) y [registro](../phase-work-progress.json).

Sigue P2: migración/perfil propios, integración de acceso/roles/sesiones/ajustes sobre SQL, decisión explícita de bindings del esquema español, UI y navegador. Los 38 tests puros y las fuentes P2 anteriores se conservan. La limpieza de rótulos internos aún debe publicarse en esa interfaz; los previews previos mantienen su versión.

## Evidencia y revisión offline

- [Evidencia conectada](../../../artifacts/p1-es/connected-result.json).
- [Revisión de aceptación](../../../artifacts/p1-es/acceptance-review.json), basada en evidencia pública; no es una segunda ejecución SQL independiente.
- [Revisión R3 de fuente](../../../artifacts/p1-es/implementation-review-r3.json).
- [Manifiesto de migración](../../../backend/migrations/cbn_spanish_schema_v2/release.json).
- [Checkpoint actual](p1_es_validation.json) y [estado de entrega](../../../tasks/p1-es-progress.json).
- [ADR-026](../../decisions/ADR-026-spanish-schema-and-work-progress.md).

```powershell
python -B backend/tools/phase_work_progress.py --self-test
python -B backend/tools/check_p1_es_checkpoint.py --self-test
python -B backend/tools/p1_es_graphs.py --check
```

Estos comandos sólo revisan archivos. No conectan SQL, cargan credenciales o ejecutan DDL. Los validadores C13 y sus grafos se conservan como historia; el checkpoint nuevo registra explícitamente las transiciones documentales y conserva sus preimágenes.
