# SQL-C2 — Plan CRM sobre HORARIOSSIIE sin modificar SIIE

Fecha: 2026-10-24, America/Bogota. **Comparación y plan; no DDL/DML aplicado.** Continúa SQL-C1 por solicitud del propietario. HORARIOSSIIE es un fragmento académico, no una DBSIIE completa. El plan permite preparar un primer conjunto CRM independiente sin inventar tablas SIIE; crear estructura y habilitar funciones son aceptaciones distintas.

## Resultado comprobado

Se volvió a leer la estructura mediante el selector existente con TLS validado. Las 50 tablas, 437 columnas y 41 FK coinciden con la captura SQL-C1. La instancia local es SQL Server 2022 Express, motor16/compat160, collation `Modern_Spanish_CI_AS`. El objetivo institucional SQL Server 2019 sigue pendiente de aceptación propia; no se cambió compatibilidad ni el guard de P1.2.

Contra las 19 migraciones históricas, **faltan las 68 tablas CRM de 13 esquemas**. Tampoco hay otros objetos o esquemas `crm`/`crm_*` visibles que permitan adoptar una instalación previa. El inventario contiene 596 columnas CREATE, una columna RunId añadida por ALTER, 93 FK (92 CREATE y una ALTER) y 31 CREATE INDEX explícitos; los índices de PK/UQ son adicionales. Como no hay tablas CRM, no hay columnas CRM existentes cuya forma pueda aceptarse o corregirse.

Las 93 FK son **CRM → CRM**; ninguna apunta a `dbo`. Sin embargo, la fuente003 exige el contrato académico `dbo.GEEmpleado`: su ausencia bloquea003 y los grupos dependientes004/005/009/017/019/020. Resultado: **36 tablas candidatas estructurales condicionadas y 32 pendientes del contrato de empleados**. Ninguna está autorizada/lista para aplicar por este documento.

El código activo referencia literalmente 22 tablas académicas: ocho presentes y14 ausentes. La comparación por nombre no certifica tipos, PK, permisos o datos. [Detalle completo de las68tablas, grupos y22referencias](HORARIOSSIIE_COMPARISON.md), [resultado estructurado](horariosiie-comparison.json), [verificación conectada](sql_c2_preflight.json), [metadatos adicionales](sql_c2_destination_metadata.json).

## Protección de las tablas académicas

El futuro paquete sólo podrá crear/alterar objetos CRM enumerados y el diario propuesto `crm_meta.MigrationJournal`; este diario es adicional a las68tablas de los históricos. No crear, renombrar, alterar, poblar, borrar ni sustituir tablas `dbo`, ni modificar sus índices, claves, triggers o permisos. No crear vistas/sinónimos académicos ficticios para que pasen los contratos. No convertir `GEUsuarios` o `GEDocente` en `GEEmpleado` por semejanza de nombres.

Contrato directo de003: `CnsctvoEmpldo int NOT NULL` como única columna de PK; `NmbrePrsna varchar(20)`, `AplldosPrsna varchar(30)` y `Actvo bit NOT NULL`. La tabla no existe aquí. **No crearla desde CRM**. El plan conserva el bloqueo hasta disponer de su fuente académica correcta o de una adaptación explícita del contrato, revisada como unidad separada. No eliminar su guarda ni crear un registro de empleado ficticio.

Las otras ausencias afectan funciones aunque su DDL CRM sea independiente: ACAspirante/ACDetalleJornada/ACSeguimiento/ACEstadoSeguimiento para Admisiones; GETipoIdentidad/GEPoblacion para identidad; ACEscuela/ACModalidad para catálogos; AFPlanes/AFTarifas/AFDetallePlanPago para tarifas; GEImgenProg/GETipoImagen para documentos. Crear002/007/013 no resuelve esas lecturas. No copiar matrículas, precios, catálogo ni estudiantes a tablas CRM para ocultar la falta de SIIE.

La revisión estática no encontró DDL/DML explícito académico en los19SQL. La lectura adicional con visibilidad de metadatos de base y acceso sysadmin no encontró triggers DDL de base ni servidor en este corte. Esto no sustituye la comprobación inmediata anterior a aplicar ni un ensayo de efectos indirectos. La primera sesión aislada no heredaba el bundle TLS del proceso web; se reutilizó el mismo bundle público ya configurado, manteniendo validación de certificado. No se cambió la confianza ni se ejecutó SQL en el intento fallido.

## Secuencia propuesta

Se reutilizan los identificadores y dependencias del [manifiesto P1.3](migration-plan.json). Es una vista condicionada de ese DAG, no una nueva numeración ni una modificación de los originales. Se conservan los19SQL y nueve runners byte por byte; no se crea el ordinal010. El grafo comparativo muestra cada FK y las dependencias de grupos.

| Paso | Grupo y fuentes históricas | Tablas | Condición y alcance |
|---|---|---:|---|
| Preparación | Destino, respaldo/ensayo, paquete nuevo, principal y forma final | 0 | Resolver todas las condiciones comunes antes de DDL |
| Historial | CBN-B000 | Adicional a68 | Implementar diario append-only y runner P1.3; todavía no existen |
| Núcleo | CBN-B001 ←001 | 4 | Contacto/conversación/mensaje/operación; primera unidad de ensayo |
| Configuración | CBN-B006 ←006 | 2 | Depende deB001; definiciones CRM sin población académica |
| Extensiones de ficha | CBN-B007 ←007, CBN-B008 ←008 | 1+2 | Dependen deB001; identidad académica y unificación siguen pendientes de aceptación funcional |
| Canales | CBN-B011 ←011+012 | 8 | Depende deB001; forma BIN2/PK/UQ final, cuentas y colas sin activar |
| Proveedores | CBN-B013 ←013+014 | 3 | Depende deB001; CHECK final y salida desactivada |
| Perfil y medios | CBN-B015 ←015, CBN-B016 ←016 | 3+1 | B015 depende deB001/B011; B016 añadeB015 en orden conservador |
| Marketing | CBN-B018 ←018 | 9 | Depende deB001/B011/B015; RunId/FK tras EvaluationRun; evaluación y transporte apagados en el paquete nuevo |
| Estado de admisiones | CBN-B002 ←002 | 3 | Depende deB001; puede diseñarse vacío, pero no habilita Admisiones sin fuentes académicas |
| Pendiente académico | B003/B004/B005/B009/B017/B019/B020 | 32 | No aplicar mientras el contrato deGEEmpleado y dependencias no estén aceptados |

Los bloques candidatos suman36tablas; los pendientes32. Cada grupo también depende deB000, como indica P1.3. Dentro de cada grupo respetar FK y orden de fuentes; ninguna extensión requiere adelantar003. La tabla reorganiza grupos independientes para priorizar núcleo/configuración; no cambia sus dependencias.

**Primer paquete de implementación recomendado:** B000+B001+B006, cuatro tablas de núcleo y dos de configuración, más el diario. Implementar y ensayar ese resultado pequeño antes de preparar la aplicación del resto. No aplicar36/68tablas en lote por estar inventariadas. B002 puede quedar al final porque su utilidad funcional requiere la fuente académica ausente.

## Paquete futuro y condiciones de ejecución

1. **Destino explícito.** Crear una línea nueva revisada para HORARIOSSIIE local, separada de los históricos que exigen DBSIIE/SQLEXPRESS. Fijar identidad externa confirmada, base, perfil, versión local16 y TLS, con rechazo previo a DDL de cualquier destino distinto. No reemplazar cadenas ni retirar guardas. El guard institucional2019 permanece15; aceptar una instancia2022local no acredita2019.
2. **Copia recuperable.** Backup COPY_ONLY/CHECKSUM y restauración independiente con validación. Ninguno se ejecutó en SQL-C2. Ensayar en la restauración el paquete, repetición sin cambios, drift, fallos y recuperación antes de usar la copia local compartida.
3. **Límite académico demostrable.** Capturar firma completa previa/posterior de las50tablas preexistentes y dependencias relevantes: columnas/tipos/collations/identities, claves/índices, CHECK/defaults, triggers/definiciones y permisos. Incorporar verificación de efectos DML indirectos; sólo contar filas no prueba que los valores no cambiaron. Toda diferencia académica exige fallo y revisión. La captura actual de tablas/columnas/FK no cumple aún esta firma completa.
4. **Visibilidad y permisos.** Usar principal de migración distinto del runtime, privilegios acotados a objetos CRM/diario, sin permisos DML/ALTER sobre tablas académicas. La inspección actual con acceso elevado no es aprobación de ese principal. Volver a verificar objetos/schemas en collation del destino y colisiones por mayúsculas/acentos/tipo de objeto. Metadatos ocultos son inconclusos, no ausencia.
5. **Transacción e historial.** Runner nuevo dueño de transacción para grupos nuevos, sin envolver uniformemente los históricos. Pausar escritores, lock de migración `crm.schema.migrate.v1` y coordinación con `crm.local.commit`. Registrar intento y éxito atómico con DDL; UNKNOWN se reconcilia, no se reintenta ciegamente. Diario/migrador todavía sin implementar.
6. **Forma final.** Sintetizar y revisar snapshots por prefijo/final antes de checksums:011+012 con collations/claves finales;013+014 con CHECK final;018 conRunId/FK sobre ChurnAssessment en su propio archivo. Conservar defaults, precisión, nulabilidad, filtros/columnas de índices y confianza deFK/CHECK. No aceptar una tabla por existir ni por marker.
7. **Datos iniciales explícitos.**006 deriva configuración de contactos; en instalación vacía no copiar etapas/etiquetas de otra institución.013 inicia Connection Outbound0;017 inicia AdmissionsPolicy Enabled0.018 histórico inicia EvaluationEnabled1: el paquete nuevo debe proponerlo desactivado y comprobarlo expresamente, sin modificar018 ni habilitar el worker. Crear la estructura no configura credenciales, consentimiento, asignación ni transporte.
8. **Aceptación de una unidad.** Preflight sin escrituras, DDL sólo allowlist CRM, forma final y objetos académicos idénticos, segunda ejecución sin cambios, FK/CHECK/index alterado detectado, dos ejecutores/reintento incierto y ensayo de recuperación. Guardar evidencia por grupo. La autorización de aplicar se evalúa sobre ese paquete concreto; este plan no lo contiene ni lo ejecuta.

## Activación y reversión

El selector sigue administrando metadatos. Preview conserva `local_demo`, salida IA apagada y repositorios SQL de negocio sin activar. No cambiar a `local_sql_copy` apuntando al fragmento para sortear contratos. Antes de habilitar una función, aceptar su conjunto de tablas/lecturas académicas/permisos y pruebas reales; las funciones con fuentes ausentes deben quedar deshabilitadas con diagnóstico explícito, no ejecutar consultas que fallan ni mostrar datos inventados.

Si falla antes del commit, rollback de la unidad y registro de fallo. Si el commit es incierto, pausa/reconciliación según P1.3. Tras commit, preferir aplicación compatible/corrección hacia delante; no DROP genérico ni restauración global sobre operaciones académicas posteriores. La recuperación de ensayo se hace en copia independiente. Conservar diario, datos CRM y dependencias. No se generó DOWN ejecutable ni se probó restauración en esta unidad.

## Verificación de este plan

Lecturas exclusivamente de catálogos, sin filas de negocio, DDL/DML, migraciones, backup o restore. Se preservaron los278archivos protegidos de fuente/runtime/tests/migraciones/runners/referencia del baseline SQL-C2. El helper offline comprueba cobertura68/68, FK93internas, cierre36/32, referencias22/14, hashes, DAG heredado y rechazos de visibilidad restringida/FK académica nueva. Ruff pasa. La revisión semántica independiente no ejecuta SQL ni sustituye el ensayo de aplicación.

Artefactos: [comparación](HORARIOSSIIE_COMPARISON.md), [JSON](horariosiie-comparison.json), [evidencia](sql_c2_validation.json), [grafo HTML](../../../graphify-out/sql-comparison/graph.html), [JSON grafo](../../../graphify-out/sql-comparison/graph.json), [canvas Obsidian](../../../graphify-out/sql-comparison/obsidian/graph.canvas). Este grafo es un plan comparado; el [observado](../../../graphify-out/sql-observed/graph.html) y el [de declaraciones](../../../graphify-out/sql-inventory/graph.html) conservan sus significados separados.

Siguiente unidad propuesta: implementar el paquete acotado B000+B001+B006 con contrato local revisado, snapshots y pruebas offline, preparando el ensayo en restauración independiente. No exige fabricar SIIE ni esperar a diseñar todas las capacidades; la activación académica y los32objetos dependientes siguen condicionados a su fuente correcta.

Alcance de paridad: estas68tablas son las declaraciones actuales de CRM CBN. Las capacidades Scentra sin esquema equivalente todavía se diseñarán en sus etapas; esta comparación no inventa tablas adicionales ni acredita paridad completa.
