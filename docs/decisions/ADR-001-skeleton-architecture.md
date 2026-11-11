# ADR-001 — Arquitectura base del skeleton local

**Fecha:** 2026-10-13, America/Bogota. **Estado:** aceptado por el propietario para la arquitectura base; sin implementación. **Reemplaza / reemplazado por:** no aplica.

## Aprobación y alcance

Ante la pregunta «¿Aprobás la arquitectura propuesta como base del skeleton?», el propietario respondió: **«YES, comienza dejando la fase cero al 100%.»** Esta respuesta acepta la arquitectura enlazada en esa pregunta y expresa intención de implementar fase 0. No constituye aprobación implícita de diseño visual, idioma UI, tooling, contratos de datos, políticas de seguridad ni asignación de responsables.

## Decisión

- Construir una plataforma CRM nueva e independiente como **monolito modular**, con límites de dominio, aplicación, adaptadores y entradas descritos en [arquitectura](../architecture.md).
- Mantener **FastAPI y React** como base; **Celery/Redis** para tareas cuando su fase y configuración estén listas. Redis no es fuente de verdad ni obliga a instalar/ejecutar colas en el skeleton.
- Mantener **SQL Server SIIE como fuente transaccional única del negocio**, sin base alternativa autoritativa del CRM.
- La fase 0 prevista es un skeleton local sin conexión de datos, credenciales reales, auth completa, IA, proveedores, envíos ni escritura core. Su aceptación debe comprobarse mediante el [checklist del roadmap](../roadmap.md), no mediante un porcentaje estimado.

## Contexto y tradeoff

El monolito modular conserva límites de negocio sin agregar la operación distribuida de microservicios. A cambio, exige respetar esos límites y medir carga/aislamiento antes de extraer servicios. No se adopta una alternativa de microservicios ni otra base transaccional; esos cambios requieren una decisión futura expresamente aprobada.

## Consecuencias y límites

Se puede planificar el skeleton sobre esta arquitectura aceptada. Las puertas documentadas antes del scaffold siguen vigentes: **P-001**, partes restantes de **P-002**, **P-003/P-004**, diseño de **P-017/P-026** y aceptación visual aplicable **P-015/P-018**. Este ADR no las cierra ni crea excepciones.

No se autoriza conectar, consultar o modificar producción; crear tablas/migraciones core; inicializar o publicar Git; crear repositorios/PR; desplegar ni contratar servicios. Ningún nombre `CRM_` autoriza DDL. No se han aprobado personas responsables para los roles técnicos, DBA, seguridad, diseño y operación.

## Validación, reversión y siguiente paso

- Esta unidad solo verifica estructura documental, enlaces y consistencia del alcance; no prueba runtime, DB, navegador o integración.
- No existe migración técnica que revertir. Cambiar esta arquitectura requiere un nuevo ADR aprobado que conserve esta decisión histórica.
- Resolver o revisar explícitamente las puertas pendientes con el propietario antes del scaffold; después implementar y comprobar la fase 0, emitir su cierre y señalar qué prosigue.

**Documentos/pendientes afectados:** [arquitectura](../architecture.md), [avance](../progress.md), [P-002 y puertas vigentes](../pending.md).
