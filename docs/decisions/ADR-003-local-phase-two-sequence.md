# ADR-003 — Fase 2 funcional local antes de las integraciones

**Estado:** aceptado por instrucción explícita del propietario. **Fecha:** 2026-10-13, America/Bogota.

## Decisión

El propietario solicita implementar fase 2, actualizar el roadmap, dejar fase 1 para el final del desarrollo local y no implementar todavía autenticación, permisos ni seguridad operacional. Añade ficha mini CRM con contexto conversacional para el humano y una subsección de comentarios en Inbox. Confirma WhatsApp, Facebook, Instagram y TikTok como canales de producto. Su instrucción previa mantiene DB/API para después.

Se implementa exclusivamente la experiencia funcional local con fixtures sintéticos y estado temporal: Clientes configurables, contexto mini CRM demostrativo, cuatro canales de mensajes y comentarios Facebook/Instagram/TikTok. El análisis local utiliza reglas explícitas, no un modelo de IA ni probabilidades predictivas. No se entrena ni conecta un proveedor.

Fase 1 se difiere al cierre de las fases de diseño funcional local, **antes** de cualquier dato real, conexión externa, despliegue compartido o piloto. La seguridad no se elimina: aislamiento loopback, banners, ausencia de secretos y operaciones reales bloqueadas se mantienen. Contratos SQL/API y pruebas de permisos/transacciones no se cierran mediante una demo.

## Consecuencia y alternativa

El alcance permite revisar flujos sin cuentas, costes ni acceso SIIE. A cambio, recargar pierde datos y borradores; las reglas de temperatura/abandono son provisionales y pueden equivocarse. Una integración inmediata daría evidencia operacional, pero contradice la secuencia solicitada y requiere autorizaciones/contratos aún pendientes.

## Aceptación y reversión

La aceptación local exige validación de configuración y fichas, estado compartido Clientes/Inbox, borradores separados, filtros y respuestas exclusivamente locales; pruebas y revisión escritorio/móvil. La evidencia conectada permanece diferida. Reversión: retirar la unidad de interfaz/modelo/tests de fase 2 y restaurar la navegación/documentación anterior; no existen datos persistentes ni migraciones que revertir. ADR-001/002 e informe fase 0 se preservan como históricos.
