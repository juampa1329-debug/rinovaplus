# ADR-013 — Migraciones institucionales explícitas y recuperables

Fecha: 2026-10-24. Estado: aceptado como definición P1.3 solicitada por el propietario; implementación SQL/runner y cualquier conexión requieren su unidad y alcance propios. No es aprobación de aplicación ni despliegue.

## Contexto

P1.1 inventarió 19 SQL locales, nueve runners, transacciones desiguales, cambios de forma posteriores y ausencia de DOWN. P1.2 separó entorno/destino de modo operativo y bloqueó workspace institucional, conservando TLS/identidad. SIIE comparte la base y no puede perder escrituras académicas al recuperar CRM.

## Decisión

- Preservar el legado y diseñar 18 unidades lógicas institucionales nuevas (diario y 17 grupos), con 012/014 integradas en sus formas finales. No generar ni aplicar esos SQL en este corte.
- Proceso de migración separado, por release inmutable, principal limitado, autorización y mantenimiento explícitos. No DDL al arranque ni uso del lector readonly como vía de escritura.
- Un diario append-only en la misma base; éxito y DDL nuevos atómicos por unidad. Adopción es un evento diferente de ejecución. Commit incierto se reconcilia, nunca se repite automáticamente.
- Drift compara artefacto, historial y forma final/modelo de datos aprobado, no sólo marker ni inventario CREATE. Metadatos ocultos bloquean.
- Reversión preferida: aplicación compatible y corrección hacia delante. Compensaciones nuevas y restauración ensayada separada para CRM; ninguna restauración global implícita de SIIE, borrado de historia o DOWN genérico.

## Consecuencias

El paquete actual no es ejecutable: no hay SQL/hashes finales de las unidades propuestas. Se aceptan inicialmente base sin CRM administrado o adopción de legacy completo reconocido; un parcial desconocido necesita transición revisada. Identidades, respaldo, forma completa y reglas de datos se comprobarán en copia autorizada antes de operación real. RPO/RTO no se fijan sin ensayo. [Contrato P1.3 y manifiesto](../adaptation/sql/P1_3_MIGRATION_PLAN.md), [evidencia](../adaptation/sql/p1_3_validation.json).
