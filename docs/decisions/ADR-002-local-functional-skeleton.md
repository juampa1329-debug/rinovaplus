# ADR-002 — Fase 0 aislada y diseño funcional local

**Fecha:** 2026-10-13, America/Bogota. **Estado:** aceptado por el propietario para el alcance local; herramientas mínimas delegadas al responsable técnico. Complementa ADR-001 y reemplaza exclusivamente sus puertas previas al skeleton aislado.

## Aprobación y decisión

El propietario respondió **«si»** a: «¿Autorizás ajustar esa puerta para construir y verificar el skeleton local, elegir las herramientas mínimas compatibles y diferir el inventario SIIE y el diseño funcional a sus fases correspondientes?». A continuación precisó: **«Después trabajaremos la integración con base de datos y API. por ahora necesito el diseño funcional.»**

Se autoriza una base FastAPI/React ejecutable y un prototipo funcional local con fixtures sintéticos, estado temporal, navegación y pruebas. La interfaz no necesita ni consume el backend; este solo expone salud local. La prioridad de esta entrega es revisar flujos y diseño, no integrar negocio. La propuesta visual y el español neutral del preview permanecen provisionales, pendientes de aprobación definitiva.

## Puertas y responsabilidades

- P-001, partes restantes de P-002, P-003/P-015/P-018, P-017/P-026 y contratos de P-027 continúan abiertos para las funcionalidades conectadas correspondientes, antes de fase 1 o de la capacidad aplicable. No bloquean este prototipo aislado.
- P-004 permite elegir herramientas locales mínimas, fijar versiones/lockfiles y registrar pruebas; no elige driver SQL ni tecnología de identidad.
- El propietario mantiene aprobación de producto, visual y autorizaciones. El agente técnico implementa y comprueba el alcance local. No se asignan personas DBA, seguridad u operación inexistentes.

## Tradeoff y límites

La demostración permite evaluar formularios y navegación antes de comprometer contratos DB/API. El coste es reemplazar estado temporal por casos de uso y contratos autorizados en fases posteriores; ningún guardado local se presenta como persistencia SIIE. No replica todavía toda la lógica ni los permisos de Scentra.

Sin datos reales, secretos, auth, consultas DB, DDL, servicios externos, workers, envío, pagos, Git/publicación, despliegue o cuentas. Celery/Redis siguen diferidos. Ningún botón de integración se habilita por este ADR.

## Aceptación y reversión

Checklists locales: instalación reproducible, health/readiness honesta, lint/tipos/pruebas/build, navegación/teclado/móvil en navegador y reporte de límites. Solo se declara fase 0 completa tras esas comprobaciones; no acredita fases posteriores ni aprobación visual humana.

Reversión: retirar `frontend/`, `backend/`, configuración local del skeleton y sus instrucciones; conservar referencias, decisiones e historial documental. No existe dato remoto o migración que revertir. Sigue revisión visual humana y después fase 1 con contrato y autorizaciones de datos/API por separado.
