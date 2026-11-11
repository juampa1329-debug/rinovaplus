# SQL-C8 · Repositorios Canales en copia de ensayo

Fecha: 2026-10-25, America/Bogota. **Aceptación limitada a repositorios y API local de ensayo. El preview compartido continúa en C5.**

## Resultado

Los repositorios de Canales usan un perfil cifrado, login SQL, clave AES y ticket propios en `CBN_C8_TRIAL_20261025_ca9bec36`. Es otra restauración del trial C7 aceptado; no se modificaron HORARIOSSIIE, C5 ni C7. No hubo migraciones ni cambios en tablas académicas. El esquema sigue siendo B000+B001+B006+B011, con los releases C3/C7 intactos.

Se aprobaron **189 pruebas offline** —44 nuevas de C8 y 145 de regresión— y **38 comprobaciones conectadas**. Se ensayaron las ocho tablas de Canales, con crecimiento legítimo de CRM y rollback de operaciones parciales. El guard nuevo no compara cantidades ni firmas de datos mutables para aceptar operaciones.

[Evidencia estructurada](sql_c8_validation.json), [resultados conectados](../../../artifacts/sql-c8/final-result.json), [JUnit](../../../artifacts/sql-c8/unit-results.xml), [progreso por fase](../../../tasks/sql-c8-progress.json), [ADR-020](../../decisions/ADR-020-channels-repository-rehearsal.md).

## Fases y verificación

| Fase C8 | Resultado |
|---|---|
| 1. Contrato y baseline | 469 entradas y preimágenes públicas conservadas; dependencias B011/B015 distinguidas. |
| 2. Perfil, permisos y guard | Perfil cifrado independiente, 33 GRANT por operación/catálogo y siete DENY dbo; igualdad exacta entre metadatos administrativos y runtime. |
| 3. Repositorios y composición | Rama local_channels propia, configuración compartida con el repositorio existente, API local acotada y ninguna instancia de workers. |
| 4. Pruebas offline | 189 pytest, Ruff de fuentes nuevas/contratos y checks de archivos legacy; sus SQL largos preexistentes se excluyen de E501. |
| 5. Ensayo conectado | 16 comprobaciones de repositorios/API, 17 de permisos/drift y cinco de concurrencia/confirmación incierta. |
| 6. Continuidad | Cadena C4→C5→C7→C8, historial previo fijado, grafos, memoria y roadmap actualizados. |

## Contrato de entorno y destino

`local_channels` sólo funciona con `channels_rehearsal`, un destino C8 de ensayo y el login derivado de ese destino. No acepta C5, C7, SIIE, perfiles mezclados o fallback demo. C8 carga su propio directorio mediante `CRM_CHANNELS_PROFILE_DIR`; el selector y `CRM_FOUNDATION_PROFILE_DIR` no se reutilizan. Los secretos se conservan fuera de Git y no se envían al navegador.

TLS conserva ODBC18, Encrypt=Yes, TrustServerCertificate=No, nombre localhost y verificación de identidad real: base, ID, fecha de creación, instancia, máquina, servidor, motor y compatibilidad. El motor ensayado sigue siendo SQL Server 2022 Express/160; no acredita SQL Server 2019 institucional ni modifica ese contrato.

El ticket privado vincula identidad nueva, SID, catálogo y diario. Las siete filas heredadas del diario mantienen sus identidades C3/C7; no se reescriben como eventos del destino C8. La clave de credenciales de Canales es propia, se prepara antes de las transacciones y no se regenera si falta o no coincide. SQL rollback no se presenta como reversión de ficheros.

## Validaciones y permisos

El lector C8 exige VIEW DEFINITION y SELECT explícito sobre `sys.sql_expression_dependencies`. Al preparar se comprobó que el catálogo completo leído por el login restringido coincide con el administrativo. Conserva columnas, tipos, defaults, identidades declaradas, índices, filtros, CHECK/FK y confianza, propiedades, módulos, dependencias, sinónimos, principales, roles y permisos, incluidos los de columna. Quita `identity_last_value` antes de ordenar; el valor consumido por un rollback no representa drift estructural.

Cada operación adquiere, dentro de su transacción serializable, el lock compartido de migración y el lock exclusivo existente de escritor. Entonces verifica identidad, ACL directa y efectiva, permisos globales/impersonación, catálogo y hash binario del diario. No requiere CONTROL, no excluye prefijos desconocidos y no usa el guard administrativo C7. Catálogo incompleto, drift, permisos adicionales, diario modificado o locks no disponibles bloquean antes de la operación de negocio.

| Destino | Permisos runtime C8 |
|---|---|
| Account / ExternalIdentity / ExternalMessage / social_comments | SELECT, INSERT, UPDATE |
| Credential | SELECT, INSERT, DELETE para sustitución cifrada |
| webhook_events | SELECT, INSERT |
| outbound_queue | SELECT, UPDATE; **INSERT denegado** |
| Audit | SELECT, INSERT |
| Contact / Message | SELECT, INSERT |
| Conversation | SELECT, INSERT, UPDATE |
| Configuration / MigrationJournal | SELECT |
| sys.sql_expression_dependencies | SELECT de metadatos |
| Base | CONNECT, VIEW DEFINITION |
| dbo académico | DENY SELECT/INSERT/UPDATE/DELETE/ALTER/REFERENCES/EXECUTE |

No hay DDL, REFERENCES, escritura al diario, DELETE general, membresías de roles, ownership ni impersonación. Se probó además la denegación real de acceso del login C8 a HORARIOSSIIE, C5 y C7. La comprobación de lectura académica usa TOP(0); no hubo pruebas DML sobre tablas académicas.

## Integración y límites funcionales

`ChannelStore` tiene una transacción C8 independiente y comparte `save_configuration` con el router legacy. La API C8 sólo monta lista/lectura de Canales, draft de configuración sin secretos, estado local de transporte y lectura paginada de comentarios. Toda `/api/` exige la barrera local existente, incluido el manifiesto de capacidades. Los errores de validación o SQL no devuelven credenciales ni detalle de conexión.

Los helpers existentes de recibos, mensajes entrantes, comentarios y estados se ejecutaron sólo con entradas y claves sintéticas internas. `append_message(foundation=True)` valida B006 sin consultar SIIE y omite las ramas B015/media/IA. Los mensajes repetidos no crean duplicados; BIN2 conserva identificadores distintos por mayúsculas. Se probaron cifrado/descifrado, redacción, firmas inválidas, revisión obsoleta, cambio de identidad con historia y rollback atómico.

`enqueue_message` depende de MessageRoute/B015 y queda fuera del corte. El runtime no puede insertar en la cola. Se creó una sola fila sintética como fixture administrativo en la copia C8 para probar `record_delivery`; no se despachó. Su estado «delivered» es un resultado de prueba, no evidencia de entrega a un proveedor. No se montan recepción pública de webhooks, discovery, test remoto, activación, reply, retry ni APIs de otros módulos; no hay workers o llamadas a proveedores.

La composición se probó con TestClient real y SQL real dentro de Docker; no se arrancó otro servidor ni se cambió el preview de 4173. La interfaz de Canales sigue pendiente de aceptación por capacidades en el corte siguiente.

## Concurrencia, fallos y preservación

Dos conexiones que guardan la misma revisión producen un éxito y un conflicto. El migrador y otro escritor excluyen al runtime. Se inyectó pérdida de ACK tras COMMIT real y tras rollback real: la API devuelve resultado incierto, el cliente consulta la revisión y el reintento no duplica una configuración confirmada. No hubo cortes eléctricos o pruebas de proveedores reales.

La comparación final preserva las 50 tablas/44.180 filas académicas, sus contadores, catálogo y permisos anteriores. También conserva byte a byte los 199 registros CRM originales del ensayo y las siete entradas heredadas del diario. El CRM C8 creció a 203 registros: un contacto, una conversación y dos mensajes sintéticos nuevos. Las ocho tablas de Canales contienen únicamente datos del ensayo; las firmas e identificadores por fila se conservan privados.

HORARIOSSIIE, el C5 compartido y el trial C7 se volvieron a comprobar completos sin cambios. Perfiles, login, ticket y ACL de C5 no se redirigieron. Las alteraciones negativas de catálogo, permisos y diario ocurrieron exclusivamente en C8 y se revirtieron; el gate final volvió a exigir las firmas originales.

## Correcciones durante el ensayo

La primera copia `CBN_C8_TRIAL_20261025_ed9c8349` quedó sin aceptar porque SQL Server requiere SELECT explícito para leer las dependencias del catálogo. Se deshabilitó su login, se conservó la copia y se repitieron respaldo/restauración/preparación con otro destino y clave. No se amplió CONTROL ni se editó un release congelado. [Registro saneado](../../../artifacts/sql-c8/draft-retired-result.json).

La revisión independiente detectó que el manifiesto C8 también debía pasar la barrera local; se corrigió y se añadieron regresiones. El primer paquete de pruebas omitía la plantilla pública `.env.example` y Compose, necesarios para una prueba de entorno existente; se corrigió el paquete aislado sin cargar `.env`. La prueba de alteración del diario pasó de asumir EventId=7 a seleccionar la fila final real y exigir una fila afectada: siete filas no implican contador de identidad siete. No se reiniciaron identidades, se borraron datos para validar ni se ocultaron fallos; el gate final exige todos los grupos y labels distintos.

## Continuidad y reversión

El baseline C8 de 469 entradas mantiene su hash. La nueva transición fija la prueba C7, sus documentos/fragmento/ADR y los releases anteriores, sin reescribir sus bytes. Se conserva la reproducción C6 con sus preimágenes. Las adiciones SQL siguen prohibidas en C8; esta unidad no es una migración.

Para revertir operación de ensayo, detener la composición C8 y conservar su base, perfil y evidencia; C5 ya sigue activo. Ante cambios de esquema o nuevas capacidades, definir otro corte/perfil/restauración y aceptación explícita. No relajar el ticket ni los permisos C8 para evitar drift.

Siguiente unidad **SQL-C9**: definir y adaptar la UI por capacidades a Canales en una composición separada, revisar los permisos requeridos por CRM/Inbox y ensayarlos con perfil/ticket nuevos si se amplía su alcance. No redirigir C4/C5, no activar B015, workers, recepción pública o proveedores por inferencia. Paridad general, suite completa e institucional SQL2019 siguen pendientes.

El refresco de anclas de los cuatro fragmentos vivos de paridad tiene un [baseline suplemental](sql_c8_graph_input_baseline.json) y un [registro de cambios](sql_c8_anchor_changes.json): sus preimágenes coinciden con el manifiesto anterior y se conservan junto a él. Sólo cambian posiciones de fuente; IDs, estados y relaciones se verifican sin cambios. No se altera el baseline principal de 469 entradas ni los fragmentos históricos C6/C7.
