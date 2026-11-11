# SQL-C6 · Siguiente paquete CRM y límite académico

2026-10-25, America/Bogota. **Definición revisada offline; no se conectó SQL ni se aplicaron migraciones.** Continúa el [runtime y la interfaz SQL-C5](SQL_C5_REVIEW.md), que conservan su destino y perfil. El resultado es un contrato de preparación para SQL-C7, no un release ejecutable ni una nueva aceptación de datos. [Plan estructurado](crm-extension-plan.json), [validación](sql_c6_validation.json), [ADR-018 propuesto](../../decisions/ADR-018-crm-extension-partition.md).

## Paquete seleccionado

Se propone **`CBN-channels-local-v1`**, grupo **CBN-B011**, sintetizando la forma final de **011+012** en un SQL nuevo para una restauración independiente. Depende de B000 y B001; conserva también B006 y los datos CRM ya poblados. No se ejecutan los archivos históricos ni se modifica el release C3 `CBN-foundation-local-v2`.

Es el siguiente bloque útil para preparar Inbox, comentarios de redes y campañas sin depender de `GEEmpleado`. Crear estas tablas no habilita esas funciones: en SQL-C7 sólo se acepta la estructura vacía. Los consumidores, rutas, permisos de ejecución y capacidades se integrarán por separado después del ensayo.

| Nueva tabla | Responsabilidad | Filas iniciales |
|---|---|---:|
| crm_channels.Account | Configuración y estado del canal | 0 |
| crm_channels.Credential | Credenciales cifradas por canal | 0 |
| crm_channels.webhook_events | Recepción durable y deduplicación | 0 |
| crm_channels.ExternalIdentity | Vínculo de identidad externa con CRM | 0 |
| crm_channels.ExternalMessage | Identificador y contenido del mensaje externo | 0 |
| crm_channels.outbound_queue | Cola de transporte única | 0 |
| crm_channels.social_comments | Comentarios recibidos de redes | 0 |
| crm_channels.Audit | Auditoría del canal | 0 |

El inventario acredita **8 tablas, 57 columnas, 10 FK y 3 CREATE INDEX explícitos**; PK/UQ tienen índices adicionales. Cuatro FK apuntan a tres tablas foundation: Contact, Conversation y Message; las otras seis quedan dentro de Canales. Ninguna depende de tablas académicas. El plan conserva los nombres y mayúsculas de cada objeto.

La nueva construcción debe crear directamente la forma 012: BIN2 en `ExternalIdentity.ExternalId`, `ExternalMessage.ExternalId`, `outbound_queue.ExternalId`, `social_comments.ExternalId` y `social_comments.AuthorId`; conserva tamaños y nulabilidad. Mantiene las claves finales `UQ_Channels_Identity`, `PK_Channels_ExternalMessage`, `UQ_Channels_Comment` y el índice único filtrado de MessageId. No convierte Channel ni todos los textos a BIN2, ni ejecuta el DROP dinámico de 012 sobre objetos existentes. Se revisarán nombres estables de restricciones y snapshots completos antes de congelar el nuevo release.

## Partición que deberá implementar SQL-C7

| Conjunto exacto | Cantidad | Tratamiento |
|---|---:|---|
| Tablas académicas capturadas en HORARIOSSIIE | 50 | Forma, datos, identidades, dependencias y ACL íntegros; sin DDL/DML académico |
| Tablas foundation aceptadas | 7 | Conservar forma y datos CRM; el diario admite únicamente nuevos eventos válidos |
| Tablas nuevas B011 | 8 | Crear sólo en ensayo independiente y comprobar forma final y cero filas |
| Otras tablas CRM declaradas | 54 | Diferidas; su aparición no prevista también es drift |
| Otros objetos, esquemas o metadatos no reconocidos | Sin cantidad asumida | Rechazar o declarar inconcluso; nunca ignorar por prefijo |

Los nombres completos están en `partition` del JSON. Las tablas declaradas son 68: seis pertenecen al foundation, ocho al paquete y 54 siguen diferidas. El diario es adicional a esas 68; por eso el total propuesto del ensayo es **15 tablas CRM, además de las 50 académicas**. HORARIOSSIIE original continúa con su captura histórica sin CRM; C6 no volvió a consultar su estructura.

La partición se hace por nombre de esquema/objeto y tipo, comprobando colisiones con la collation real. Debe cubrir objetos no tabulares, propietarios, definiciones, índices, restricciones, triggers, permisos y dependencias entrantes/salientes. Se congela también todo objeto preexistente fuera de las tablas CRM enumeradas, contrastando su universo con los metadatos C5 aceptados: capturar un catálogo inicial nuevo no autoriza adoptar objetos desconocidos. La visibilidad incompleta es inconclusa, no ausencia. No basta comparar conteos ni excluir `crm_*`, `dbo` u otros schemas en bloque.

El lector congelado [foundation_snapshot.py](../../../backend/tools/foundation_snapshot.py) define managed como tres esquemas y academic como su complemento. El guard [foundation.py](../../../backend/app/foundation.py) espera exactamente 50 tablas fuera de esos esquemas y la forma de siete tablas. Añadir `crm_channels` al ensayo hace que esos contratos anteriores lo rechacen. **Se necesita un lector y un guard versionados nuevos**, sin editar los tres helpers C3 ni sus hashes. No se puede reutilizar el lector antiguo y cambiarle sólo la lista de esquemas.

Antes y después del ensayo se compararán metadatos/ACL completos y representaciones binarias SQL de las 50 tablas académicas y de los datos foundation, con precisión temporal de siete dígitos y sin publicar firmas de filas/tablas. Se congelan firmas nuevas del estado real inmediatamente anterior; los conteos C5 son evidencia histórica y no sustituyen esa captura. No se eliminan contactos, mensajes, configuración ni operaciones para volver a las condiciones de instalación vacía de C3.

## Historial, destino y permisos

El diario existente conserva su esquema y sus cinco filas iniciales, byte por byte; los eventos posteriores son append-only. El migrador nuevo valida primero el prefijo C3 y luego la cadena de release B011, con hashes de SQL, herramientas y formas. Conserva la semántica y hashes de ShapeVersion antigua y valida la versión nueva por separado, dentro del varchar(32) existente, sin ALTER del diario. SuccessKey es globalmente único por UnitId: B011 confirmado no admite otros bytes; una corrección requiere otra unidad hacia delante. No vuelve a ejecutar B000/B001/B006, no edita markers históricos y no usa `current_history` C3 como si admitiera automáticamente releases nuevos.

El contrato de ejecución conserva el lock de sesión `crm.schema.migrate.v1` y después `crm.local.commit` en la transacción, siempre en el mismo orden. STARTED se confirma en una transacción independiente anterior; COMMITTED se confirma atómicamente con el DDL; un fallo se registra después de revertir. Cualquier COMMIT incierto, incluido STARTED, bloquea el avance hasta reconciliar diario y forma. Repetir una unidad ya aceptada es NOOP; un estado parcial o desconocido no se adopta por existencia de tablas.

La preparación del esquema/principal queda fuera del paquete y se audita por separado. Se propone un usuario DB nuevo WITHOUT LOGIN: CREATE TABLE y VIEW DEFINITION a nivel base, ALTER sólo de `crm_channels`, REFERENCES sólo de Contact/Conversation/Message y SELECT/INSERT del diario. No recibe DML académico/foundation ni UPDATE/DELETE del diario, roles elevados, ownership o EXECUTE general. El SQL del paquete y sus efectos indirectos siguen requiriendo revisión; estos permisos no aíslan SQL arbitrario. Los permisos de preparación no se heredan al runtime. La lectura académica administrativa para evidencia es separada de ambos. Deben comprobarse permisos efectivos por roles/public, impersonación, ownership y efectos indirectos, además de los grants directos. La proyección de una nueva ACL exige verificar primero el overlay exacto del actor conocido; no excluye otros permisos o principales. No se añaden permisos ni credenciales a C4 en C6/C7.

El ensayo tendrá otra base, archivos y ticket ligados a su identidad, SID, TLS y forma. El perfil/ticket C4 no se redirige ni se amplía para aceptarla. El runtime antiguo debe rechazar el destino extendido. La integración C8 exige guard, perfil y ACL propios antes de promover capacidades. El objetivo institucional sigue siendo SQL2019 motor15, con compatibilidad130/140/150 según P1.2; el ensayo local motor16/compat160 requiere su contrato separado y no certifica el institucional. No se cambia TLS ni la compatibilidad del servidor para superar un check.

## Secuencia y aceptación siguiente

1. **SQL-C7, contrato offline.** Implementar lector por objetos explícitos, migrador y guard de ensayo versionados; pruebas de partición, visibilidad, colisiones, permisos, historial y forma. Preparar SQL B011 final sin tocar históricos.
2. **Copia poblada y referencia.** Validar la identidad del destino C5, estado real y TLS; crear COPY_ONLY/CHECKSUM, VERIFYONLY y restauraciones independientes de referencia/ensayo, con archivos nuevos y sin REPLACE. Asegurar consistencia del respaldo y coordinar escritores cuando corresponda. La copia compartida de C5 no recibe DDL.
3. **Construcción revisada.** Crear referencia aislada, comprobar datos y forma previa/final, fijar snapshots canónicos y hashes del paquete antes de aplicarlo al ensayo intacto. La preparación de ACL se registra separada de la migración.
4. **Ensayo B011.** Verificar prefijo, partición e identidad, adquirir locks, ejecutar sólo B011 y registrar el resultado. Comparar preservación completa, claves/índices/collations y ocho tablas vacías. Repetir NOOP y probar drift, permisos insuficientes/elevados, objetos inesperados y concurrencia.
5. **Fallo y recuperación.** Inyectar fallo en fronteras de DDL/diario y simular ACK perdido en COMMIT. Comprobar rollback/reconciliación sin repetir DDL ni perder CRM poblado. Conservar las copias y evidencia; no resetear ni borrar para repetir.
6. **SQL-C8, integración separada.** Aceptar consumidores y UI contra ese contrato nuevo. No activar módulos por la mera existencia de tablas; workers, proveedores y salida continúan bloqueados hasta su unidad de aceptación.

La matriz de 14 escenarios está en `acceptance_cases`. Si falla antes de commit, revertir la unidad y registrar el fallo. Ante commit incierto, pausar y reconciliar. Tras commit, conservar la copia para inspección y usar corrección compatible hacia delante; no generar DROP genérico ni restaurar sobre el SIIE original o sobre operaciones posteriores. La composición C5 actual permanece disponible con su destino anterior.

## Capacidades posteriores y bloqueos reales

| Bloque | Después de B011 | Límite funcional |
|---|---|---|
| B015, tres tablas Inbox unificado | B000+B001+B011 | Revisar consumidores completos; ConversationControl por sí sola no basta |
| B018, nueve tablas de churn/marketing | B000+B001+B011+B015 | Proponer EvaluationEnabled=0; no worker, evaluación, campañas o transporte por crear tablas |
| B013, tres tablas de proveedores/modelos | B000+B001, rama independiente | Forma final 013+014; credenciales y Outbound=0 con aceptación propia |
| B007/B008, identidad y unificación | DDL con FK CRM, pero consumidores adicionales | Identidad consulta SIIE ausente; unificación actual lee `crm_inbox.Operation` |
| B003 y dependientes, incluidos B009/017/019/020 | Contrato correcto de GEEmpleado y dependencias | No fabricar empleados, tablas SIIE, credenciales o modelos para quitar el bloqueo |

[ContactMerge.state](../../../backend/app/modules/contacts/application/merge.py#L363) consulta `crm_inbox.Operation` aunque 008 sólo declare FK hacia Contact. [Identidad](../../../backend/app/modules/contacts/api/router.py#L99) valida tipos/períodos/programas y sus búsquedas referencian ACAspirante/GEPoblacion. [Control de Inbox](../../../backend/app/modules/inbox/application/state.py) puede detectar una tabla parcial como instalado y después usar outbound_queue/MessageRoute. Estas dependencias explican el orden; el DAG de DDL por sí solo no demuestra disponibilidad funcional.

`social_comments` almacena recepción de comentarios del canal; no sustituye las tablas/servicios de hilos y tareas de B009. Churn sigue pendiente: no se muestra un score, probabilidad o aprendizaje sin evaluación y evidencia reales. No se incluye WooCommerce ni billing en ningún bloque.

## Verificación realizada en C6

El [comprobador documental](check_c6_plan.py) usa únicamente la biblioteca estándar, JSON públicos y hashes de archivos. Conserva los **402 inputs** fijados al inicio, incluidos código actual, migraciones, herramientas, C3/C4/C5, capturas públicas y referencias Scentra. Verifica partición, tablas/FK/orden, 011+012, collations, dependencia del DAG y límites de activación; sus 20 casos negativos son pruebas del plan, no del futuro migrador.

```powershell
python -B docs/adaptation/sql/check_c6_plan.py --self-test
python -B backend/tools/adaptation_graphs.py --check
```

La evidencia C6 informa sólo definición offline. El checkpoint de runtime sigue siendo C5: no se modificaron backend/frontend, Compose, perfiles, permisos, datos ni el preview; no se ejecutó SQL, Docker, proveedores o pruebas conectadas. La suite general y los 41 fallos previos de C4 no se recertifican. Los grafos son trazabilidad, no un esquema aplicado ni aceptación SQL2019.

C6 es un checkpoint de diseño, no uno de runtime. C7 conservará plan, comprobador, baseline y evidencia C6, además de las preimágenes públicas recuperables que necesita la comparación histórica. Registrará las transiciones explícitas de código C5→C7 y los hashes del diseño C6. El comprobador C6 sin adaptación histórica rechazará correctamente fuentes C7 cambiadas; no se debe editar o volver a firmar C6 para evitar ese rechazo.

**Siguiente unidad concreta: SQL-C7**, implementar este contrato y B011 con pruebas offline y ensayo aislado sobre una copia del CRM poblado, manteniendo intactos el SIIE original y la copia compartida C5. La activación de consumidores queda para C8.
