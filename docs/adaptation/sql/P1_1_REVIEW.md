# Resultado del inventario de persistencia

Nota de continuidad: este informe conserva el corte P1.1. P1.2 cambió legítimamente configuración/runtime y regeneró inventario de consumidores/grafos; [contrato vigente](P1_2_CONTRACT.md). `input-baseline.json` conserva las huellas históricas P0/P1.1; no debe reescribirse para ocultar cambios posteriores. Las migraciones y runners permanecen intactos.

P1.1 · 24 de octubre de 2026, America/Bogota. Destino CRM CBN; referencia funcional Scentra. Revisión de fuente y documentación oficial, sin conexión, consultas, migraciones ni cambios en la base de datos.

## Resultado

Hay **19 archivos**, 001–009 y 011–020, que declaran **68 tablas en 13 esquemas**. El ordinal 010 no existe; 020 era el máximo número, no el total de migraciones. El inventario conserva 596 columnas CREATE, 132 restricciones de tabla, 92 FK en CREATE y 31 CREATE INDEX explícitos. Además registra 12 apariciones ALTER TABLE: entre ellas cinco ALTER COLUMN de collation y un ADD RunId con otra FK en 018. No son conteos del esquema aplicado; tampoco incluyen todos los índices implícitos de PK/UNIQUE como CREATE INDEX.

La sintaxis observada es compatible con funciones disponibles en SQL Server 2019. Hay bloqueos para operar en un destino institucional: guards SQLEXPRESS/local, comparación NULL de 011–017, modelos transaccionales diferentes y controles de drift desiguales. [Compatibilidad y siguiente cambio propuesto](COMPATIBILITY_SQL2019.md).

## Entregables

| Artefacto | Contenido |
|---|---|
| [MIGRATIONS.md](MIGRATIONS.md) | Cada archivo, propósito, dependencias FK, runner, reejecución, datos iniciales y efectos core. |
| [SCHEMA_CATALOG.md](SCHEMA_CATALOG.md) | Columnas, tipos, nulabilidad declarada, DEFAULT/CHECK/PK/UNIQUE, FK, índices, ALTER y consumidores literales. |
| [inventory.json](inventory.json) | Inventario estructurado y hashes de fuentes/runners/revisiones; reconstrucción determinista. |
| [CAPABILITY_MAP.md](CAPABILITY_MAP.md) | 31 grupos, con cobertura exacta 68/68 tablas del destino y referencias Scentra verificadas. |
| [capability-map.json](capability-map.json) | Evidencia estructurada del mapeo: 20 grupos reutilizables con adaptación, tres educativos a preservar y ocho áreas faltantes por diseñar. |
| [Grafo SQL](../../../graphify-out/sql-inventory/graph.html) | Declaraciones de migración, tabla, columna y FK con fuentes, más relaciones revisadas de contrato/runner. No es un schema leído de SQL Server. |
| [Revisión 001–009](reviews/001-009.json), [revisión 011–020](reviews/011-020.json) | Contratos/guards/semillas/atomicidad/compatibilidad, con evidencia y clasificación de relaciones. |

Las ocho áreas sin estructura equivalente declarada son autenticación institucional, Meta Ads, campañas/segmentos CRM completos, flujos multipaso, memoria colectiva, ADN, gobernanza de entrenamiento y ML. Esto orienta las etapas P2/P6/P8/P9/P10; no autoriza crear una tabla por cada tabla PostgreSQL ni sustituir entidades SIIE. La superficie del churn disponible sigue en P3 y el modelo entrenado en P10.

## WooCommerce retirado del destino

La búsqueda en código de aplicación, frontend, catálogo JSON, migraciones y herramientas no encontró un conector o capacidad activa de WooCommerce. Su candidata positiva estaba en la copia documental `docs/design/settings-reference/scentra-settings-specification-2026-10-13.md`; se eliminó de esa lista y se identificó la referencia como adaptada para educación.

El alcance, AGENTS y roadmap ahora lo excluyen explícitamente. Las menciones históricas que dicen «excluido» o documentan esa decisión se conservan como rastro; no se presentan como capacidad disponible. No se borraron secretos, tablas, datos, migraciones ni conectores del Scentra original. La auditoría se registra en [validation.json](validation.json).

## Verificación y reanudación

Se comprobaron cobertura/duplicados del mapa, citas y líneas, huellas de fuentes, estructura del inventario, dependencias y extremos de grafos. La herramienta lleva una comprobación mínima de separación por paréntesis y literales para columnas con comas en tipos/JSON; también registra ALTER fuera de CREATE. No sustituye un compilador T-SQL ni un ensayo conectado. La evidencia y los límites de este cierre están en [validation.json](validation.json).

```powershell
python backend/tools/inventory_migrations.py --check
python backend/tools/adaptation_graphs.py --check
```

Estos son validadores offline. No ejecutar `migrate_*.py`, ni siquiera `--preflight`, para repetir P1.1: esos runners abren conexión y su preflight no significa «sin acceso SQL».

P1.1 se cierra con documentación y mapas. **P1.2 queda pendiente de selección:** contrato de entorno y verificación de destino institucional, conservando identidad y TLS. No se inicia aplicación de migraciones como continuación automática de este inventario.
