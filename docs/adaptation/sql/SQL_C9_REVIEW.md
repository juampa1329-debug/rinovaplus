# SQL-C9 · Interfaz de Canales por capacidades

Fecha: 2026-10-25. Aceptación limitada a la interfaz y API locales en una restauración independiente: `CBN_C9_TRIAL_20261025_23ac78d3`. No equivale a aceptación institucional o paridad completa de Canales.

## Resultado

La composición C9 permite consultar y guardar configuración de cinco canales, seleccionar etapas activas y leer comentarios sociales y actividad local. Conserva los componentes, temas y tokens Azul noche · Glass. Se sirve en [el preview C9](http://127.0.0.1:4175/#/settings), con proyecto Docker y origen propios. El preview de 4173 conserva C5.

La precisión del propietario se incorpora antes del cierre: estructura y funciones deben igualar Scentra, cambiando la persistencia a SQL Server. La pantalla se organiza en los seis grupos verticales de la fuente: WhatsApp, verificación de número, Instagram, Facebook Messenger, TikTok y Webhooks. Los comentarios Facebook conservan su cuenta heredada dentro del grupo Facebook. Las acciones de conexión aún pendientes se identifican y permanecen deshabilitadas. La [matriz de paridad con Scentra](SQL_C9_SCENTRA_PARITY.md) registra campos, OAuth, secretos, números/PIN, TikTok y Webhooks faltantes; C9 no acredita una copia funcional completa de Canales.

El manifiesto estricto `cbn-ui-capabilities-v2` se valida antes de montar la pantalla. La shell de C9 evita montar los propietarios y hooks CRM/Inbox. La versión v1 de las composiciones anteriores mantiene su contrato. Las credenciales y acciones de proveedor, respuestas, recepción pública, reintentos y workers permanecen bloqueados en UI y API.

El guardado envía sólo revisión y configuración. Ante conflicto o resultado incierto conserva el borrador y consulta la versión almacenada; una versión distinta exige descartar explícitamente o revisar el borrador. Si no puede confirmar la versión, bloquea nuevos guardados. Las consultas tienen cancelación y límite de 15 segundos. Los comentarios son de sólo lectura y paginados; los contadores de ensayo no se presentan como entregas reales.

## Copia y permisos

Se realizó BACKUP COPY_ONLY con CHECKSUM del C8 aceptado, VERIFYONLY, restauración sin REPLACE y CHECKDB. No se aplicaron migraciones ni se alteraron tablas académicas. C9 tiene perfil SQL cifrado, login y ticket propios. No se copió ni generó la clave de cifrado de credenciales de Canales. El perfil SQL sí conserva su propia clave de protección local.

La ACL contiene 15 GRANT y siete DENY sobre dbo: Account SELECT/INSERT/UPDATE, Audit INSERT, lecturas de actividad, configuración B006 y diario, metadatos de dependencias y CONNECT/VIEW DEFINITION. Credential sólo permite SELECT de Channel y Kind; KeyId, Nonce y Ciphertext se deniegan efectivamente. No hay CONTROL, DDL, DML CRM ni INSERT en cola. El catálogo administrativo y el observado por el login runtime son idénticos.

El guard verifica destino/identidad/TLS, SID, catálogo completo, permisos directos y efectivos por columna, diario y cadena de ownership segura. Un GRANT temporal de SELECT KeyId realizado sólo en C9 bloqueó manifiesto y lecturas; tras revertirlo se recuperó el contrato exacto. Las respuestas de error no publican excepciones SQL ni credenciales. Los tres archivos de perfil/ticket privados tienen ACL sólo del propietario.

## Verificación

| Comprobación | Resultado |
|---|---|
| Backend offline | 244 aprobadas: 55 C9 y 189 regresiones C8/C5/entorno/TLS |
| Frontend | 42 aprobadas: 30 C9 y 12 regresiones foundation/Canales |
| SQL/API real | 35 comprobaciones: permisos, guard, DTO, conflictos, simultaneidad, rollback y drift |
| Navegador | Escritorio y móvil 390 px; guardado/recarga, borradores, conflicto, caída/recuperación, temas, teclado y rutas bloqueadas |
| Estática | TypeScript, ESLint de archivos afectados, Ruff E/F/I de fuentes nuevas y build aprobados |
| Historia | C4→C5→C7→C8→C9; 573 preimágenes C9 verificadas, evidencia anterior congelada |

El primer pase del harness corrigió dos aserciones del propio comprobador antes de escribir datos: el guard HTTP exige Content-Type JSON y SQL Server devuelve error 230 para denegaciones por columna. Las comprobaciones completas posteriores pasaron. El arranque inicial de nginx en rootfs de sólo lectura requirió declarar todos sus directorios temporales en tmpfs. No se cambió el despliegue C5 para resolverlo.

El build conserva el aviso previo de bundle mayor de 500 kB. Se ejecutaron suites focalizadas; no se recertificó la suite general con fallos previos. La revisión semántica independiente está en [sql-c9.json](../fragments/sql-c9.json); la evidencia de navegador es independiente de esa revisión estática.

## Preservación y reversión

SIIE y C5 se comprobaron en lectura. Se compararon además catálogo y filas binarias completos de C5/C7 con sus capturas históricas y de C8 con la captura anterior al backup C9. Coinciden. En C9 siguen intactos las 50 tablas/44.180 filas académicas, los 203 registros CRM heredados y las siete entradas del diario. Sólo Account y Audit reciben escrituras de configuración; las otras seis tablas de Canales mantienen su firma.

Para retirar la interfaz basta detener el proyecto independiente con `docker compose -f compose.channels-ui.yaml stop`. No ejecutar down con volúmenes, DROP, reset de identidades o migraciones de reversión sobre SIIE/C5/C7/C8. Conservar la copia, backup y recuperación privada como evidencia. No reutilizar prepare sobre la copia poblada ni usar sus credenciales para otro destino.

## Continuidad

La evidencia cerrada C6/C7/C8 conserva sus bytes y sus anclas históricas. Sólo se actualizan posiciones de los cuatro fragmentos de paridad vivos, sin alterar sus hallazgos ni relaciones. Los grafos son evidencia de estructura, no una certificación SQL o de proveedor.

P0 completo; P1 y P4 en curso. P2/P3 conservan avances foundation C5; la paridad de Ajustes y CRM/churn sigue pendiente. P5–P11 no están aceptadas. La siguiente unidad propuesta SQL-C10 detalla el contrato SQL y los ensayos de toda la matriz de paridad Scentra, incluidos OAuth, secretos, activos, verificación de números, controles TikTok y Webhooks, y sitúa B015/MessageRoute en la secuencia de transporte. No autoriza proveedores, envíos, workers o recepción pública por inferencia. El motor ensayado es SQL2022 Express/compatibilidad160; SQL Server 2019 institucional continúa pendiente.

Evidencias: [validación C9](sql_c9_validation.json), [progreso por fases](../../../tasks/sql-c9-progress.json), [ADR-021](../../decisions/ADR-021-channels-capability-ui.md), [preparación](../../../artifacts/sql-c9/preparation.json), [backend](../../../artifacts/sql-c9/backend-results.xml), [frontend](../../../artifacts/sql-c9/frontend-results.xml), [SQL/API](../../../artifacts/sql-c9/connected-checks.json), [preservación](../../../artifacts/sql-c9/preservation-result.json), [navegador](../../../artifacts/sql-c9/browser-validation.json).


Cierre de grafos C9: código 2496 nodos/6586 relaciones; adaptación 399/657. 41 hallazgos, 12 fases acíclicas, 75 enlaces locales válidos y 573 preimágenes verificadas. El diagnóstico no detecta extremos ausentes o colgantes; los bucles del grafo AST requieren interpretación de alias y no prueban recursión. La paridad funcional con Scentra sigue parcial; el cierre de C9 corresponde sólo al ensayo por capacidades.
