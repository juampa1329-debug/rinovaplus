# SQL-C4 · Integración de repositorios en la copia restaurada

2026-10-24, America/Bogota. **Aceptada para el núcleo CRM en la restauración**, con [evidencia estructurada](sql_c4_validation.json) y [ADR-016](../../decisions/ADR-016-foundation-repositories.md).

## Resultado

Contactos, conversaciones, mensajes locales, diario de operaciones y configuración usan el contrato B000+B001+B006 de `CBN_C3_TRIAL_20261024_ac8505b8`. El Inbox básico permite listar/filtrar/paginar conversaciones, consultar la ficha, opciones y mensajes, editar datos base y escribir texto local sin consultar tablas ausentes de canales o SIIE.

No se crearon tablas ni se ejecutaron migraciones. La única preparación administrativa nueva fue un login/usuario exclusivo y su ACL mínima en la restauración. El diario de migraciones conserva sus bytes SQL y filas; las operaciones de negocio nuevas se registran en `crm.Operation` y `crm_config.Operation`.

La fuente HORARIOSSIIE sigue intacta: 50 tablas, 437 columnas y 41 FK, sin tablas CRM. La prueba compara las 50 tablas preexistentes y 44.180 filas en fuente y restauración, con representaciones binarias SQL que conservan la séptima cifra de `datetime2(7)`. Se conserva además la forma académica y toda ACL anterior; sólo se proyecta el actor runtime nuevo, tras verificar por separado su ACL exacta. No se publican datos, firmas por fila/tabla, nombres de máquina, SID o credenciales.

## Contrato de ejecución

Modo `local_foundation`, entorno `foundation_rehearsal`. Son distintos del modo legacy `local_sql_copy` y del selector de catálogos. Requieren el destino exacto, identidad completa, SQL auth restringida, nombre certificado `localhost`, ODBC18 `Encrypt=Yes;TrustServerCertificate=No` y ticket privado con SHA explícito. No hay fallback al perfil de inspección HORARIOSSIIE, SA, credenciales de migración o datos demo.

Cada transacción verifica el destino y contrato bajo el bloqueo global. La forma C3 conserva owners, definiciones, tipos, índices, CHECK, FK, propiedades y permisos originales. Se fija el release v2 `b8de5466cd6c0e8b373490cc0987bacbf90deff95ffe45e8d84f54f6dc08827a`; no se cambiaron los tres SQL, snapshots, lector/herramientas congelados ni `inventory.json`.

El usuario nuevo puede escribir sólo lo necesario en las seis tablas de negocio y leer el diario. No puede borrar, alterar/crear objetos, modificar el diario ni leer/escribir datos académicos. Se contrastan además los permisos efectivos globales de servidor/base para bloquear elevación por roles, impersonación o cambios en public. Se exige visibilidad completa de metadatos y cada permiso efectivo esperado: NULL no equivale a denegación comprobada. El ticket fija además el historial ya aceptado. Una variación de identidad, diario, ACL o forma bloquea antes de entregar el cursor al repositorio.

`create_app(settings=...)` permite componer una aplicación aislada sin cargar otra configuración privada. El perfil de credenciales del ensayo se guardó cifrado en un directorio privado independiente y se conservó una copia local protegida; no se editó `.env`, el perfil del selector ni Compose. No se inicia ningún worker/proveedor. El preview continúa `local_demo` con outbound desactivado.

## Pruebas y evidencias

| Alcance | Resultado |
|---|---|
| Seis archivos: contrato runtime, SQL target, foundation, configuración, workspace e Inbox | 204 pasan; 51 casos nuevos runtime |
| Núcleo más salud, contenedor, clientes y credenciales | 269 pasan y 1 omitida (plataforma); incluye las 204 anteriores |
| [API y permisos reales](sql_c4_verify_result.json) | 76 comprobaciones |
| [Drift y preservación repetibles](sql_c4_audit_result.json) | 8 comprobaciones |
| Ampliación de regresión terminada | 1.110 pasan, 23 fallan, 1 omitida |
| Ampliación de proveedores, interrumpida por fixture singleflight bloqueada | 313 pasan, 18 fallan, 1 omitida; no resultado de suite completa |
| Los 41 fallos observados en esas ampliaciones, con la aplicación anterior | Se reproducen los 41; 122 archivos de aplicación de la imagen coinciden byte a byte con el baseline previo C4 |

El ensayo API cubre configuración válida/replay/conflicto; Contact+Conversation atómicos; edición compartida; replay sin duplicados; mensajes locales; conversación cerrada; rechazo de capacidades ausentes; guard local; paginación de 26 contactos y 52 mensajes; fallo inyectado tras escribir con rollback de mensaje y operación. SQL rechaza SELECT académico, DELETE, escritura del diario y CREATE/ALTER. CHECKDB de la restauración concluyó sin errores.

Las sondas adicionales concedieron temporalmente DELETE en `crm.Message` al usuario nuevo y agregaron una propiedad de ensayo a `crm`. Ambas bloquearon el runtime y se revirtieron en `finally`, comprobando después el contrato exacto. Las pruebas de ticket con identidad/diario incorrectos no modificaron el diario. Se repitieron las firmas académicas después de las sondas.

El primer ensayo se detuvo por una expectativa de test incorrecta: la primera revisión se suponía 1, aunque los ensayos rollback C3 ya habían consumido identidades. Se corrigió la expectativa a monotonía y se recuperó sólo la semilla sintética inicial mediante replay con su hash exacto, sin borrar operaciones ni reiniciar identidades. Después pasaron las 76 comprobaciones. En pruebas offline se actualizaron fixtures legacy de canales/media, revisión actual en replay y Settings explícitos del fixture de contenedor; no se alteraron las políticas IA.

Los fallos ampliados quedan como deuda previa: respuestas/mock de proveedores y el nuevo argumento `before_attempt`; contratos stub de canales/webhooks que esperan 501/422 frente al guard/rutas vigentes. Los IDs concretos están en la evidencia. **No se declara verde la suite completa del repositorio.** No hubo llamadas reales a proveedores. Ruff estricto pasa en los archivos nuevos y en la selección de archivos reorganizados; los SQL largos heredados de workspace/Inbox/router IA se verifican sin E501, sin reescribir esas consultas por estética.

## Grafos y continuidad

`inventory.json` y el baseline C2/C3 permanecen históricos. `inventory.active.json` y `horariosiie-comparison.active.json` describen consumidores actuales frente a la captura histórica de HORARIOSSIIE; no afirman que las 68 tablas históricas estén aplicadas a la fuente. La forma C3 se sigue mostrando como historia de su release, distinta de la ACL runtime C4.

`historical_checkpoint.py` verifica el SHA del baseline C4, cada transición antes/después, nuevas fuentes y todos los artefactos inmutables. No permite justificar cambios a C3/SQL/runners/Scentra mediante una excepción C4. Los grafos se regeneran offline con Graphify y el fragmento revisado `sql-c4.json`; cifras finales y huellas en [source-manifest](../../../graphify-out/source-manifest.json).

## Reanudar y límites

Para comprobaciones rutinarias, usar `python -B backend/tools/adaptation_graphs.py --check` desde CRM_CBN: no carga aplicación, ODBC, secretos o SQL. Los helpers de ensayo sí conectan y no deben confundirse con ese check offline.

La preparación/CRUD real se ejecutó expresamente en Docker mediante `python -m tools.rehearse_repositories prepare|verify --private-directory /tmp/cbn-c4`. `prepare` rechaza un perfil ya preparado; `verify` requiere una base CRM vacía o exclusivamente la semilla inicial recuperable por replay. No reejecutarlo sobre el ensayo ya poblado ni limpiar tablas para hacerlo pasar. `audit` es la comprobación repetible posterior, con las sondas CRM reversibles documentadas; exige conservar el contexto/ticket C3 y las credenciales privadas. Nunca iniciar estos comandos por una comprobación de memoria.

SQL-C5 propuesto: conectar la interfaz existente a este perfil mediante capacidades explícitas y comprobar CRM/Inbox/mini CRM en navegador. El detalle foundation indica ausencia de operaciones avanzadas; no activar la UI actual sin adaptarla a esas capacidades. Mantener bloqueados perfiles y asignaciones académicas hasta disponer del esquema completo y contrato correcto. Campañas, agentes, memoria/ADN, canales y sus demás grupos tienen sus propias etapas.

Motor real local SQL2022 Express, compatibilidad160; la aceptación conectada institucional SQL Server2019 permanece pendiente. El guard P1.2 para 2019 no se relajó. No hay aceptación del CRM completo, activación del preview compartido, despliegue, envíos, commit/push o cambios a Scentra.
