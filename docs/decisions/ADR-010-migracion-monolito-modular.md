# ADR-010 — Migración incremental a monolito modular

**Estado:** Fases 1, 2 y 3 implementadas localmente el 2026-10-19; puentes de compatibilidad conservados.

## Contexto

El backend y el frontend concentran capacidades de negocio en archivos y carpetas transversales. Esto dificulta localizar cambios y aumenta el riesgo de acoplar módulos no relacionados. El proyecto conserva un solo despliegue y una única fuente transaccional SIIE; esta decisión no introduce microservicios, bases de datos, dependencias ni rutas nuevas.

## Decisión

Se adopta un monolito modular. Cada capacidad nueva tendrá una carpeta propia en `backend/app/modules/<modulo>` y `frontend/src/modules/<modulo>`. Los consumidores externos usarán únicamente el límite público del módulo; los imports temporales anteriores se conservarán como compatibilidad hasta que cada corte los retire con evidencia.

La migración se realizará en tres fases:

1. **Fundación y Catálogos:** crear la raíz modular y migrar los contratos, casos de uso y router de Catálogos; el frontend enruta su pantalla de Catálogos mediante el límite del módulo. Los adaptadores SQL y la implementación visual conservan puentes compatibles mientras siguen siendo compartidos por otras capacidades.
2. **Capacidades de operación:** Clientes, Inbox con Operaciones, Admisiones y Configuración CRM viven en verticales completos. Sus puentes se conservan hasta que no tengan consumidores comprobados.
3. **Capacidades especializadas y consolidación:** migrar Identidad, actividad/unificación, eventos, análisis, estrategia e IA; eliminar compatibilidades que hayan quedado sin uso y verificar límites entre módulos.

Cada módulo backend organiza `api`, `application`, `domain` e `infrastructure`. Cada módulo frontend organiza `api`, `model`, `components` y `pages`. `main.py` y `App.tsx` se mantienen como composición de módulos, no como ubicación de reglas de negocio.

## Consecuencias

- Se preservan `/api/v1/catalog/*`, sus `operationId`, los contratos OpenAPI y el modo `local_sql_copy` durante la Fase 1.
- No se realizan cambios SQL, migraciones, configuración, secretos, datos, red ni despliegue.
- La reversión de una fase consiste en restaurar los imports de composición a los puntos de compatibilidad anteriores; no hay estado de datos que revertir.

## Evidencia requerida por fase

La migración debe normalizar sus archivos antes de comprobar formato, lint, tipos, pruebas focales y build aplicables. Una comprobación de código no acredita SQL conectado, navegador, proveedor o producción.
