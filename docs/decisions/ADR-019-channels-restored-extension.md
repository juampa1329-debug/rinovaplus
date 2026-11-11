# ADR-019 · Canales en restauración con historia independiente

Fecha: 2026-10-25, America/Bogota. **Implementada y ensayada en SQL-C7; alcance exclusivo de esquema restaurado.** Continúa [ADR-018](ADR-018-crm-extension-partition.md) sin modificar su diseño histórico.

## Decisión

Implementar B011 como forma final 011+012 en un paquete nuevo, con lector y migrador independientes. El release aceptado es `CBN-channels-local-v2`, SHA `49f72eb835ce46b83ec9c6267da2f73c9d7799990de6fab8ed28762565985998`. Enumera 50 tablas académicas, siete foundation y ocho nuevas, además de proteger el catálogo no tabular y los permisos anteriores. Los contratos, SQL, snapshots y evidencia C3/C4/C5 permanecen congelados.

Una referencia nueva valida la forma física contra una especificación independiente antes de congelar. La preparación administrativa y el actor DDL WITHOUT LOGIN tienen funciones separadas: diez GRANT mínimos y siete DENY dbo, incluidas REFERENCES internas del esquema nuevo. Ningún permiso o ticket del runtime C4 cambia. TLS permanece validado.

El prefijo original del diario no se reidentifica como propio de la restauración. C7 agrega eventos versionados con identidad nueva, locks, transacciones serializables, STARTED durable, DDL+COMMITTED atómicos y reconciliación bloqueante ante resultado incierto. Una transacción ajena se rechaza antes de cualquier limpieza. No se adopta un esquema parcial ni se repite un éxito con otros bytes.

La v1 congelada se retiró por ordenar antes de excluir el contador IDENTITY volátil. Sus assets siguen exactos. V2 usa `cbn-extension-shape-v3`, normaliza antes de ordenar y se ensayó en otras once copias desde C5 poblado. La regresión de IDENTITY por rollback se verificó antes y después de congelar. Se reutilizan contrato/spec v1 porque no cambiaron, fijados por ambos manifiestos y verificación transitiva.

## Validación y consecuencias

119 pruebas offline y 51 comprobaciones conectadas aprobadas; APPLIED+NOOP; ocho tablas vacías, diario5→7. Fuente HORARIOSSIIE, C5 compartido, 50 tablas/44.180 filas académicas, 199 filas CRM y cinco filas originales del diario conservados. Reversión antes de COMMIT por rollback; después, reconciliar y conservar evidencia o restaurar otra copia, sin DROP/reset automático. [Informe y límites](../adaptation/sql/SQL_C7_REVIEW.md).

La historia documental C6 se reproduce con sus preimágenes autenticadas y checker sin cambios. C4→C5→C7 conserva transiciones por ruta y usa la última postimagen como entrada nueva. Se admiten sólo las adiciones congeladas de ambos paquetes; no se flexibilizan las migraciones históricas.

El preview sigue en C5. SQL-C8 debe crear su propio perfil, principal, guard y composición de ensayo para consumidores B011. El lector C7 requiere CONTROL y compara datos previos inmutables; no se reutiliza como guard de runtime mutable ni justifica CONTROL para la aplicación. Crear tablas no activa proveedores, cuentas, workers, endpoints o envíos. Motor local2022Express no equivale a aceptación institucional2019; paridad funcional y suite general siguen pendientes.
