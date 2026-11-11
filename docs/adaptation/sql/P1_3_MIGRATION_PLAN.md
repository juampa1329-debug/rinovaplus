# P1.3 — Secuencia, historial, drift y recuperación

Fecha: 2026-10-24, America/Bogota. **Definición offline, sin SQL aplicado ni conexión.** Esta unidad entrega el contrato de migración; no implementa un migrador, DDL institucional ni una aceptación conectada. [ADR-013](../../decisions/ADR-013-migration-lifecycle.md), [manifiesto no ejecutable](migration-plan.json), [evidencia](p1_3_validation.json), [P1.1](P1_1_REVIEW.md), [P1.2](P1_2_CONTRACT.md).

## Decisiones de alcance

1. Conservar los **19 SQL históricos y nueve runners** byte por byte, incluido el salto 010. Son evidencia local y no una receta institucional. Nada se aplica por ordenar archivos, comprobar un marker o arrancar FastAPI/Docker.
2. Preparar una línea institucional nueva `CBN-B…`, con unidades pequeñas, nombres explícitos y transacción del futuro runner. Sus identificadores son lógicos: **no existen aún archivos SQL ni hashes de ejecución/forma final**. El manifiesto tiene `execution_authorized=false`, `sql_file=null` y `expected_shape_sha256=null`; no puede usarse como paquete aplicable.
3. Separar instalación/adopción del registro de historia y de la activación de producto. No crear nuevas tablas Scentra por analogía; las 68 declaraciones CBN son referencia, no prueba de objetos existentes en SIIE. Las capacidades faltantes del mapa se diseñarán en sus etapas.
4. Conservar el bloqueo del workspace institucional y TLS/identidad de P1.2. El futuro migrador será un proceso separado con principal DDL temporal y autorización acotada; no usará `catalog=True` para evadir ese bloqueo, ni dará DDL al login readonly/web. La ruta de transporte de migración queda por implementar/revisar, no habilitada aquí.

## Orden del legado y dependencias

Orden conservador de referencia: **001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 011 → 012 → 013 → 014 → 015 → 016 → 017 → 018 → 019 → 020**. No es un comando de ejecución. La numeración establece un orden total para revisión; `depends_on` conserva las dependencias mínimas conocidas y las conservadoras del runner, no presupone que todas sean FK.

| ID | Predecesores conservadores | Propietario de transacción histórico | Cambio y precaución |
|---|---|---|---|
| 001 | — | Script; rechaza transacción previa | Contacto, conversación, mensaje y diario CRM. Bootstrap no puede exigir que este CRM ya exista. |
| 002 | 001 para composición/runner | Script | Estado de Admisiones; referencias SIIE se validan aparte, sin duplicar autoridad. |
| 003 | 001; contrato académico GEEmpleado | Script | Agentes/miembros, asignación, tareas y SLA. |
| 004 | 001, 003 | Script | Eventos y recuperación incremental; guards de fuentes más amplios que sus FK. |
| 005 | 001, 003, 004 | Script | Análisis, contexto y feedback de conversación; no crea ChurnAssessment. |
| 006 | 001 | Script | Deriva configuración de Contact; no es una migración sin DML. |
| 007 | 001 | Script | Perfil institucional, sin importar identidades académicas. |
| 008 | 001 | Script | Merge lógico reversible de contactos; no equivale a DOWN de esquema. |
| 009 | 001, 003 | Script | Estrategia; FK TaskId exige 003 aunque el guard no lo explique. |
| 011 | 001 | Caller para atomicidad | Canales, identidades, comentarios y outbox única. |
| 012 | 011 | Caller para atomicidad | Cinco collations y reconstrucción de PK/UQ; no repetir a ciegas. |
| 013 | 001 por runner/composición | Caller para atomicidad | Configuración IA; Connection apagada. El runner puede importar ai-settings.json. |
| 014 | 013 | Caller para atomicidad | Sustituye CHECK de proveedores; no tiene marker propio de versión. |
| 015 | 001, 011; 012 antes por secuencia aprobada | Caller para atomicidad | Perfil/control de conversación y MessageRoute. |
| 016 | 001, 011, 015 | Caller para atomicidad | Metadatos media; no respalda ni crea los binarios. |
| 017 | 001, 003, 011, 013, 015 | Caller para atomicidad | IA de admisiones, conocimiento y memoria; política inicial deshabilitada. |
| 018 | 001, 011, 015 | Caller obligatorio | Campañas; crea ChurnAssessment y añade RunId/FK dentro del mismo archivo. Policy histórica inicia evaluación interna habilitada. |
| 019 | 001, 003, 017 | Caller obligatorio | Jerarquía de agentes; conservar uso directo al guardar perfil válido. |
| 020 | 001, 019 | Caller obligatorio | Ejecución, consumo, historial y FK. |

Fuentes y hashes por ID en [migration-plan.json](migration-plan.json), contrastados con [inventario](inventory.json), [revisión 001–009](reviews/001-009.json), [revisión 011–020](reviews/011-020.json) y grafo SQL. Dependencia DDL, guard, runtime y política de orden son evidencias distintas. Por ejemplo, [009:48](../../../backend/migrations/009_conversation_strategy.sql#L48) y [017:7](../../../backend/migrations/017_ai_admissions.sql#L7). Las 001–009 gestionan su transacción; 011–017 no garantizan atomicidad en autocommit; 018–020 la exigen. **No envolver estos 19 scripts bajo un único wrapper.** El runner de canales histórico agrupa 011/012; esto no vuelve equivalentes todos los runners.

## Secuencia institucional nueva

| Orden | Unidad lógica propuesta | Fuente de comportamiento | Contrato de la unidad |
|---|---|---|---|
| 0 | Preflight y expediente de recuperación | P1.2 + este contrato | Identidad, permisos, destino, versión 15/compatibilidad, colisiones, estado y respaldo ensayado; sin DDL. |
| 1 | `CBN-B000` historial | Nueva, no creada | Esquema `crm_meta` y diario descrito abajo, sin dependencia previa de crm. |
| 2–10 | `CBN-B001`…`CBN-B009` | 001…009 | CRM → Admisiones → Inbox → eventos → análisis → configuración → identidad → merge → estrategia. |
| 11 | `CBN-B011` canales finales | 011 + 012 | En instalación vacía, crear directamente la forma BIN2 final, sin DROP/ALTER intermedio. |
| 12 | `CBN-B013` IA final | 013 + 014 | CHECK final de proveedores y configuración institucional explícita; sin importar archivos privados automáticamente. |
| 13–18 | `CBN-B015`…`CBN-B020` | 015…020 | Inbox unificado → media → IA admisiones → campañas → agentes → ejecución. |
| Final | Verificación de release | Vector completo de unidades | Forma final completa, historia, controles de datos y permisos. Producto/workers siguen apagados. |

Las 18 unidades lógicas incluyen historial y 17 grupos funcionales; 012 y 014 se incorporan a las formas finales de sus grupos. No se crea el histórico 010 ni se reutilizan IDs legacy como si se hubieran ejecutado. Cada unidad nueva requiere SQL inmutable, contrato de entrada/salida, metadatos esperados por prefijo, pruebas de fallo y compensación antes de adquirir estado ejecutable.

Perfiles iniciales permitidos, a materializar y aprobar antes de aplicación:

- **SIIE sin objetos CRM administrados:** crear únicamente las unidades CRM aprobadas, una por transacción, con contratos académicos de lectura verificados. Un nombre que colisione, incluso con distinta capitalización, bloquea; no renombrar ni borrar.
- **CRM legacy completo hasta 020 y reconocido:** comprobar la forma final y reglas de datos contra un perfil objetivo revisado; registrar `ADOPTED` para el vector completo, sin ejecutar otra vez sus SQL ni atribuirles una fecha de ejecución inventada. Los hashes de fuente prueban procedencia, no que esos bytes hayan sido aplicados.
- **Esquema parcial/desconocido o metadatos incompletos:** `BLOCKED`. Requiere una transición nueva revisada para ese estado concreto; no completar huecos a partir de markers, inferir un máximo ordinal ni reparar objetos automáticamente. Un prefijo creado por el nuevo migrador sí podrá reanudarse si su historia y contrato exacto coinciden.

En adopción, el registro del vector completo será una transacción de auditoría tras validar todo el perfil. Si sólo algunas partes coinciden, no se registra un éxito parcial. El bootstrap del diario se valida primero; un diario ya existente sin contrato reconocido también bloquea. No convertir la configuración/datos existentes en defaults nuevos durante adopción.

Instalación nueva: análisis, autonomía, proveedores, salida externa, evaluación de campañas y workers **deshabilitados explícitamente**. La diferencia con `EvaluationEnabled=1` de 018 histórica es deliberada en la nueva línea, sin editarla. La configuración inicial 006 se definirá con parámetros institucionales, no copiando seeds de Scentra ni contactos de otro entorno. Habilitar cada capacidad requiere su propia aceptación.

## Historial: contrato propuesto, todavía sin tabla

Un único diario append-only `crm_meta.MigrationJournal`, con marker propuesto de esquema `crm_meta.contract=CBN-migrations-v1`; el estado se deriva de sus eventos. No incorporar Alembic/Flyway ni otra base de datos. Los registros pertenecen a la misma base que los cambios CRM para poder confirmar éxito y DDL en la misma transacción. Marker y forma completa son obligatorios para reconocer un diario existente.

| Campo propuesto | Tipo SQL Server 2019 | Significado / invariante |
|---|---|---|
| EventId | bigint IDENTITY, PK | Orden durable; no contar huecos como pérdida de eventos. |
| AttemptId | uniqueidentifier | Un intento nuevo por reintento; nunca reutilizar para encubrir fallo. |
| UnitId / EventKind | nvarchar(80) / varchar(32) | Unidad inmutable y evento de enumeración cerrada. |
| RecordedAtUtc | datetime2(7) | UTC del servidor; no fecha histórica de ejecución deducida. |
| ReleaseId / ToolVersion | nvarchar(80) / nvarchar(40) | Paquete y herramienta responsables. |
| ManifestSha256 / UnitSha256 | binary(32) | Hash del manifiesto liberado y del artefacto de unidad. En adopción UnitSha identifica contrato de adopción, no SQL ejecutado. |
| ShapeVersion | varchar(32) | Versión del modelo/normalizador, inicialmente `cbn-shape-v1`; no reinterpretar hashes antiguos con otra versión. |
| TargetSha256 | binary(32) | Identidad aprobada de base/servidor/instancia/máquina/motor; separado del hash de forma. |
| BeforeShapeSha256 / AfterShapeSha256 | binary(32), NULL según evento | Estado observado; NULL significa desconocido, nunca forma vacía aceptada. |
| EvidenceRef / ApprovalRef / BackupRef | nvarchar(160), según evento | Identificadores opacos de expedientes privados; sin rutas con secretos/datos académicos. |
| PrincipalRef | nvarchar(128) | Referencia del ejecutor validado; metadatos de conexión privados, sin contraseñas. |
| ErrorCode | varchar(60), NULL en éxito | Código saneado, sin mensajes SQL libres ni valores de filas. |
| SuccessKey | nvarchar(80), NULL salvo COMMITTED/ADOPTED | Igual a UnitId en éxito; índice único filtrado no nulo impide un segundo éxito de la misma unidad. |
| RelatedAttemptId / RelatedUnitId | uniqueidentifier / nvarchar(80), NULL | Reconciliación, compensación o restauración relacionadas sin borrar historia. |

DDL futuro: nombres explícitos de constraints/índices, CHECK de tipos de evento y correspondencia de SuccessKey; el principal runtime no tendrá INSERT/UPDATE/DELETE aquí. El proceso de migración inserta eventos por un camino acotado; UPDATE/DELETE no forman parte del contrato. Un administrador privilegiado podría alterar la historia: mantener además el expediente/checksums fuera de la base con control de acceso; no declarar el diario criptográficamente inalterable.

Eventos: `STARTED`, `COMMITTED`, `ADOPTED`, `FAILED_ROLLED_BACK`, `UNKNOWN`, `RECONCILED_COMMITTED`, `RECONCILED_NOT_APPLIED`, `RECOVERY_REQUIRED`, `COMPENSATED`, `RESTORED`. COMMITTED/ADOPTED crean SuccessKey; reconciliación y recuperación referencian el éxito/intento original. Una compensación tiene ID nuevo y éxito propio, y marca la unidad afectada fuera del vector activo mediante evento relacionado; no borra su éxito ni permite reaplicar el mismo ID. El estado efectivo es un vector de unidades y compensaciones verificadas, **no MAX(UnitId)**.

### Protocolo transaccional futuro

1. Proceso explícito de mantenimiento, release/hash y autorización exactos, respaldo restaurado de ensayo y escritores CRM/colas detenidos. Nada al arranque del producto. Verificar P1.2 sin exigir un marker CRM que aún no existe; comprobar contratos académicos por separado. El principal de migración tiene visibilidad/DDL sólo del alcance revisado; el login readonly conserva sus restricciones.
2. Tomar lock exclusivo de sesión `crm.schema.migrate.v1` en la base verificada, timeout finito 5 s y retorno no negativo. Mantener **la misma conexión física**, sin pooling ni reconnect transparente durante el intento. Antes de cada unidad, tomar también `crm.local.commit` exclusivo con propietario transacción, en ese orden; las escrituras existentes usan ese recurso. El lock de sesión serializa migradores; los locks no sustituyen la pausa de todos los productores/escritores, especialmente SIIE y procesos externos.
3. Bootstrap: crear diario y primer evento COMMITTED dentro de su propia transacción del runner; aún no existe dónde guardar STARTED. El expediente externo conserva intento/fallo incluso si el bootstrap revierte. Si el diario ya existe, comparar su forma/contrato antes de usarlo.
4. Para unidades posteriores, STARTED se confirma en una transacción corta de auditoría. Abrir **una** transacción de runner para la unidad: `XACT_ABORT`, timeout, lock, revalidar identidad, historial/dependencias y forma de entrada; aplicar SQL liberado, validar salida y reglas de datos; insertar COMMITTED y confirmar una sola vez. DDL y éxito comparten commit. Nunca confirmar DDL y escribir éxito después.
5. Ante fallo conocido antes de commit, rollback y comprobar estado de transacción. Registrar FAILED_ROLLED_BACK después del rollback si la base sigue disponible; no escribir auditoría en una transacción no confirmable. Si no se puede verificar, registrar expediente externo y tratar como UNKNOWN.
6. Pérdida de conexión/ACK de commit: **UNKNOWN**, detener la secuencia y cualquier reintento automático. En una conexión nueva autorizada, volver a validar destino, obtener locks y reconciliar evento durable + forma actual + datos de la unidad. Éxito presente y salida correcta: RECONCILED_COMMITTED. Sin éxito, entrada exacta y ausencia comprobada de efectos: RECONCILED_NOT_APPLIED; permitir sólo un nuevo intento explícito. Cualquier discrepancia: RECOVERY_REQUIRED, sin borrar ni repetir DDL.
7. Si ya hay éxito reconocido y estado actual coincide con el modelo liberado del vector activo, NOOP verificado sin nuevo éxito. Un ID con otros bytes o dependencias diferentes bloquea. No usar `--force`, reescribir checksum, deshabilitar constraints o aceptar sólo el marker.

Los scripts históricos con transacción propia quedan fuera de ese ejecutor nuevo. Su eventual uso local conserva su semántica/runner y requiere autorización separada; adoptar un estado reconocido no afirma atomicidad histórica ni inventa un journal retroactivo. [Locks de aplicación](https://learn.microsoft.com/en-sg/sql/relational-databases/system-stored-procedures/sp-getapplock-transact-sql?view=sql-server-ver17), [errores y transacciones no confirmables](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/try-catch-transact-sql?view=sql-server-ver15).

## Detección de drift

Tres comprobaciones diferentes, todas obligatorias antes/después de cada unidad:

| Frontera | Comprobación | Si no coincide |
|---|---|---|
| Artefacto | SHA-256 de bytes exactos de SQL/contrato/manifest liberado; cualquier cambio de finales de línea también cambia hash. Dependencias/orden y versión de normalizador fijados. | Bloquear por artefacto cambiado; nueva unidad/release, sin actualizar el checksum de un éxito. |
| Historial | Éxitos, intentos incompletos, target y vector activo contra paquete aprobado. Un marker o tabla existente no acredita aplicación. | Bloquear/reconciliar; no fingir migraciones pasadas ni aplicar por ordinal máximo. |
| Esquema y datos | Snapshot completo bajo visibilidad suficiente, comparado con **modelo aprobado**, más aserciones de datos explícitas por unidad. | Drift o inconcluso: bloquear; sin reparación automática. |

Modelo de forma `cbn-shape-v1`: JSON canónico `json.dumps(model, ensure_ascii=True, sort_keys=True, separators=(",", ":"))`, bytes ASCII, SHA-256. Colecciones ordenadas por esquema/nombre/tipo con comparación ordinal exacta; conservar capitalización y orden lógico de columnas/columnas de índices. NULL se conserva como NULL. No Unicode folding, LOWER, eliminación de espacios SQL o regex sobre literales.

Incluir esquemas/propietarios; objetos y columnas (nombre, posición visible, tipo/esquema del tipo, longitud SQL en bytes, precisión/escala, nulabilidad, collation, identity seed/increment, computed/persisted, rowversion); PK/UQ/FK (orden de columnas, destino, acciones, habilitación y confianza); CHECK/DEFAULT y sus definiciones; índices (tipo, unicidad, columnas clave/dirección/include/filtro, habilitación); markers exactos y triggers/módulos/permisos del alcance administrado. Nombres de constraints incluidos, incluso los autogenerados en un perfil legacy aprobado para ese destino. Las nuevas DDL usarán nombres deterministas. Definiciones textuales se conservan estrictamente con finales de línea normalizados; diferencias semánticamente equivalentes pueden bloquear para revisión, nunca aprobarse automáticamente.

Excluir IDs físicos de objetos/índices, fechas de creación/modificación, conteos de filas, estadísticas, último valor identity, bytes de archivos, secretos y contenido de documentos. Los datos que importan a una unidad se validan con aserciones revisadas (unicidad, FK huérfanas, JSON válido, políticas deshabilitadas en instalación nueva, compatibilidad de valores antes de restringir tipos/CHECK); no con hash indiscriminado de personas o tablas SIIE. El modelo incluye objetos inesperados dentro del alcance administrado: no ignorarlos. Core SIIE sólo por contrato académico de lectura, sin convertir toda su estructura cambiante en propiedad CRM.

**No usar inventory.json como fingerprint de esquema final.** Contiene declaraciones CREATE y ALTER separados: 012 cambia cinco collations y claves; 014 reemplaza CHECK; 018 crea ChurnAssessment y añade su RunId/FK dentro del mismo archivo, sin dependencia física de 005 por esa tabla. El modelo se construirá aplicando estas transiciones semánticas y se contrastará en copia restaurada. Los contratos por prefijo se fijarán en el release futuro: las huellas históricas AfterShape no se comparan ingenuamente con el esquema actual cuando una unidad posterior autorizada cambió esos objetos. Comparar con el modelo del vector activo completo.

Una consulta de metadatos vacía/NULL por falta de permisos no significa ausencia de objetos. El migrador debe demostrar visibilidad completa del alcance, con permisos específicos revisados; no concederlos al lector de catálogos para hacer pasar drift. [Visibilidad de metadatos](https://learn.microsoft.com/en-us/sql/relational-databases/security/metadata-visibility-configuration), [columnas SQL Server](https://learn.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-columns-transact-sql?view=sql-server-ver15).

## Recuperación y reversión por unidad

Rollback de una transacción fallida, volver de versión de aplicación y revertir cambios ya confirmados son operaciones distintas. **No hay DOWN probado** para los históricos; tampoco se entrega aquí un DROP/rollback automático. La estrategia predeterminada tras commit es mantener esquema compatible y corregir hacia delante mediante otra unidad inmutable; la compensación sólo se diseña con precondiciones y datos actuales conocidos.

| Grupo / cambio | Antes de commit | Después de commit |
|---|---|---|
| B000 diario | Rollback de bootstrap; evidencia externa permanece. | Conservar historial. No DROP de diario con eventos; desactivar migrador, no borrar auditoría. |
| 001–005, 007–009, 011, 015–017, 019–020 aditivos | Rollback de unidad nueva, con postcondición de forma inicial. | Volver a aplicación compatible dejando datos/esquema; compensación o recuperación CRM acotada si se necesitan. No DROP por tener tabla vacía ni sin revisar dependientes. |
| 006 configuración derivada | Rollback incluye DML. | Conservar valores previos/revisiones en expediente privado; restaurar sólo filas de la operación cuya versión no cambió. No sobrescribir cambios humanos posteriores. |
| 012 collation/claves | Revertir transacción; verificar claves y forma inicial. | Revertir collation puede colisionar valores según reglas anteriores; exige prueba de unicidad, reconstrucción revisada y ventana. Si falla, mantener estado y corregir hacia delante; no borrar identidades. |
| 013/014 proveedores | Rollback de DDL/DML; sin importar secretos. | CHECK anterior puede rechazar proveedores usados después; comprobar valores antes. Conservar credenciales/configuración y claves cifradas; no recortar proveedores ni vaciar vault. |
| 018 campañas y RunId | Rollback de unidad completa. | Preservar trazabilidad/evaluaciones y FK dependientes; pausar evaluador/envíos, revisar consumidores y corregir hacia delante. Quitar RunId puede perder evidencia; no compensación genérica. |
| Datos o efectos externos | No deben ejecutarse desde migraciones. | Un envío, anuncio o llamada externa no se deshace restaurando SQL; mantener outbox/identificadores y deduplicación. Nunca reenviar pendientes por retroceder el historial. |

Expediente privado obligatorio antes de una aplicación futura: ID del release y target; backup real con checksums y clave de cifrado si corresponde; cadena/logs y recovery model conocidos; restauración de ensayo **en otra base aislada**; versión de SQL/compatibilidad; forma y aserciones antes/después; RPO/RTO medidos/aprobados, no inventados; versión de aplicación compatible; plan para media, estado IA y claves de cifrado; responsable/ventana/reanudación y criterio de abortar. No volcar esos datos o secretos al repositorio.

`VERIFYONLY` comprueba legibilidad/completitud del backup; **no sustituye una restauración ensayada ni verifica por sí solo la estructura de sus datos**. [Microsoft VERIFYONLY](https://learn.microsoft.com/en-us/sql/t-sql/statements/restore-statements-verifyonly-transact-sql?view=sql-server-ver15). Punto en el tiempo/recuperación dependen del recovery model y cadena disponibles; no prometerlo sin evidencia ni cambiar el modelo automáticamente. [Restauración y recuperación](https://learn.microsoft.com/en-us/sql/relational-databases/backup-restore/restore-and-recovery-overview-sql-server?view=sql-server-ver15).

La base es compartida con SIIE: **prohibido restaurar toda la base automáticamente** para deshacer CRM. Primero restaurar en destino separado, comprobar integridad y diseñar recuperación sólo del alcance CRM conservando dependencias y operaciones posteriores; no existe RESTORE de esquema genérico que resuelva eso. Restauración global sólo como decisión institucional específica, con ventana y tratamiento de todas las transacciones académicas posteriores. Hasta aceptarla, el plan operativo es pausa + aplicación compatible/corrección hacia delante. Registrar COMPENSATED/RESTORED y expediente externo; no borrar intentos ni reusar IDs.

## Aceptación y trabajo pendiente

Comprobado aquí: orden/dependencias sin ciclos, cobertura de las 19 fuentes/68 tablas declaradas, propietarios de transacción, hashes de históricos/runners/runtime, referencias, ausencia de SQL ejecutable nuevo y grafos/memoria. El helper [check_migration_plan.py](../../../backend/tools/check_migration_plan.py) sólo usa biblioteca estándar y archivos públicos; no carga app, `.env`, pyodbc o red. [Evidencia P1.3](p1_3_validation.json).

Pendiente de una unidad de **implementación explícita**: DDL institucional y diario, snapshots finales/por prefijo, aserciones de datos, nuevo transporte/migrador acotado y pruebas offline de estado/reconciliación. Luego ensayo autorizado en copia restaurable: destino/TLS/principal incorrectos, instancia DEFAULT/nombre, visibilidad insuficiente, colisión/parcial, hash cambiado, CHECK/FK/collation/índice alterados, fallo antes/durante/después de commit, dos migradores, writer concurrente, reintento desconocido, adopción y restauración con escrituras SIIE posteriores preservadas. Ninguna de esas pruebas conectadas se ha ejecutado.

**P1.3 cierra como definición revisable**, no como migrador implementado ni DB migrada. P1 general conserva esa implementación y aceptación pendientes. P1.4 es la siguiente definición de entorno/imagen si se selecciona; no adelantar DDL ni activar operación institucional. [Estado y reanudación](../../../tasks/TASK_STATE.md).

Precisión posterior del propietario: referencia de contexto = copia local ya configurada; conservar sus rutas/mapeos. [Configuración e inventario académico existente](CONNECTION_CONTEXT.md). Se comprobó presencia de configuración y hashes de la captura histórica, sin probar conectividad ni ejecutar SQL.
