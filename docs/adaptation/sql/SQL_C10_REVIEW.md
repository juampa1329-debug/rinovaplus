# SQL-C10 · Cierre del contrato de Canales

25 de octubre de 2026. Alcance: definición verificada offline. El contrato exige los mismos campos, acciones y condiciones de Scentra con el estilo CBN y persistencia SQL Server2019. No acredita que la interfaz C9 o los proveedores ya estén implementados.

## Resultado

La [matriz vinculante](SQL_C10_FIELD_MATRIX.md) conserva 115 contextos de campos y salidas y 83 instancias de acciones. Hay modales y botones compartidos; los conteos no representan capacidades únicas. Incluye número/Phone Number ID, WABA, App ID, token permanente, secretos, Graph API, selección y sincronización de números, PIN/registro, OAuth, activos, renovación/diagnóstico, todos los controles TikTok y Webhooks. Etiquetas, opciones, condiciones y anclas se conservan en el [JSON de paridad](channels-ui-parity-contract.json).

El [modelo SQL](channels-parity-contract.json) propone 24 tablas en `crm_channels2`, 78 FK y cinco unidades nuevas CBN-CHP001–005. Mantiene las 65 tablas anteriores y separa aplicaciones, cuentas, versiones de credenciales, sesiones, recepción y efectos externos. B015/MessageRoute tiene equivalentes nuevos con control de conversación y epoch; el 015 histórico no se ejecuta directamente. El [contrato](SQL_C10_CONTRACT.md) explica secuencia, permisos, drift, correspondencias B011, recuperación y gates.

Multicuenta WhatsApp es una ampliación humana explícita C10: el backend Scentra observado limita tenant/proveedor/canal, aunque muestre tarjetas y varios números. Esta precisión corrige la inferencia C9 sin editar sus pruebas o documentos cerrados.

## Revisión y correcciones

Se contrastaron tres inventarios y revisiones semánticas independientes, con hashes del modelo y la matriz finales:

- [Meta/OAuth](../../../artifacts/sql-c10/review-oauth.json): ownership de aplicaciones/sesiones/activos, secreto cliente pinneado, snapshots y tokens por Page, conexiones explícitas y campos/acciones de número y secretos.
- [TikTok](../../../artifacts/sql-c10/review-tiktok.json): reservas concurrentes, incertidumbre remota, refresh sin borrar política, modos y gates, identidad y pistas con autoridad concreta. Los contadores de prospectos B013 y dead letters con triage/cierre permanecen disponibles como campos, con valor no disponible hasta sus propias etapas.
- [Webhooks/SQL](../../../artifacts/sql-c10/review-webhooks.json): rutas/FK compuestas por cuenta, procedencia de evidencia, secreto exacto de firma, retención y tipos/índices compatibles con2019. La unicidad del nonce del cuerpo es filtrada para admitir varios recibos purgados; las importaciones sin firma no fabrican SignatureVerifiedAt.

Las correcciones están en la definición. No equivalen a pruebas conectadas de constraints, concurrencia, OAuth, HMAC, UI o entrega real. La revisión conserva los hallazgos originales y su resolución; no sustituye observaciones por un informe sin historial.

## Verificación reproducible

`python -B docs/adaptation/sql/check_c10_contract.py --self-test`: modelo positivo, cobertura exacta de descriptores y bindings, claves/FK/orden, crypto/roles/gates y **52 diseños inválidos rechazados**. Se verificaron SHA y CRC de **627 preimágenes públicas**: 625 iniciales y dos referencias suplementarias; el suplemento no reemplaza inputs anteriores.

`python -B backend/tools/historical_checkpoint.py --self-test`: **53 transiciones inválidas rechazadas** en la cadena, incluidas diez C10. Las pruebas C6/C7/C8/C9 y sus releases permanecen congelados. Sólo se extendió el checker histórico offline; las anclas cerradas de sus funciones anteriores se conservaron.

Ruff E/F/I y parseo AST aprobados en los dos comprobadores. Se cotejaron **430 archivos de runtime, pruebas, migraciones, composición y referencia Scentra** de la línea base: mismos bytes. [Resultados offline](../../../artifacts/sql-c10/offline-checks.json), [evidencia y transición](sql_c10_validation.json) y [progreso por fase](../../../tasks/sql-c10-progress.json).

No se ejecutaron pruebas de runtime ni SQL en esta unidad: no hubo conexión SQL, DDL/DML, Docker, perfiles privados, credenciales de proveedores, HTTP de la aplicación, workers o cambios en la UI. SIIE/C5/C9 no se tocaron. Las firmas académicas y conteos de C9 son evidencia anterior; C10 no los volvió a consultar. Motor15/compat150 es el objetivo, no una compilación institucional certificada.

## Progreso y continuación

Las seis fases internas de C10 cubren evidencia, modelo, flujos, secuencia/recuperación, revisión/comprobadores y grafos/memoria. El JSON de progreso registra su cierre y las fases generales sin porcentajes estimados. P0 continúa completa; P1/P4 en curso. P2/P3 y las fases de IA/marketing mantienen sus aceptaciones pendientes, con los avances foundation anteriores conservados.

SQL-C11 propuesto implementará este release en otra restauración, con backup/CHECKDB, principal/perfil/ticket propios, correspondencias verificadas y ensayos de fallo/reversión. La UI completa, autenticación P2 y operación real con proveedores tienen gates separados; no se activan por definir tablas. [ADR-022](../../decisions/ADR-022-channels-parity-contract.md).


Cierre de grafos C10: código2496 nodos/6586 relaciones (mismos bytes de runtime), adaptación474/773, 42 hallazgos y12 fases acíclicas. Siete grafos sin extremos ausentes/colgantes ni nodos/aristas duplicados; nueve bucles AST históricos/alias y cero en adaptación. Fragmento C10:60 nodos/100 relaciones con evidencia; 82 enlaces locales comprobados. Son grafos offline, no esquema vivo ni porcentaje de paridad.
