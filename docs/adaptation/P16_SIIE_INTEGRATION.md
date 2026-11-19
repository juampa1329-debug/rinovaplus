## P16 retomada: consumidor de la API recibida — 2026-11-18

El propietario autorizó continuar la integración con la guía/colección recibidas. Se implementan nueve consultas GET de programas, ofertas, períodos, filtros, aspirantes y seguimientos, con dos credenciales separadas, paginación y revisión de datos financieros. HTTPS público responde401sin clave. Las pruebas autenticadas reales y cinco unidades de aceptación siguen pendientes: **P16:0/5**, implementación parcial, no0% de código. Todas las ofertas resolubles actualmente devuelven422no cotizable por mapeos incompletos de SIIE; el consumidor lo presenta sin publicar precios ni sobrescribir fichas. Estudiantes matriculados y cartera personal todavía no tienen rutas en el contrato recibido. POST/PUT de seguimiento documentados pero no habilitados en este corte; requieren comprobantes, persistencia de operación y revisión antes de efectos.

Configuración y recorrido: docs/adaptation/P16_SIIE_OPERATOR_RUNBOOK.md. Claves originales sólo en Coolify Runtime; nunca en chat/Git. Evidencia y pendientes: tasks/p16-siie-progress.json. No nuevas tablas, seeds ni escrituras académicas.

General original P0–P11:100% cada una (56/56,279/279), P12auxiliar100% PostgreSQL/Meta. P13 Académico/agentes parcial0/4; P14 entrenamiento comercial plan; P15 correos100%7/7 en alcance inicial documentado; P16 SIIE en implementación0/5; P17 TikTok diferida0/5; P18 seguridad plan0/8. OPS01–06 conservan sus límites. Los cortes inferiores son historia, incluida la anterior decisión de diferir SIIE ahora revocada por el propietario.

> Numeración vigente desde el 18 de noviembre de 2026: P16. Antes P15; mismo alcance, estado y evidencia.

# P16 · Integración académica y financiera con SIIE

Estado al 17 de noviembre de 2026: **diferida por decisión del propietario**. La base técnica está implementada y probada, pero no hay conexión real ni aceptación de datos oficiales. Esta fase adicional no añade peso al denominador canónico de 56 criterios/279 hitos.

## Decisión de alcance

El propietario pidió separar SIIE y continuar cerrando el CRM. Por tanto, la API de DBSIIE deja de ser condición obligatoria de P13. P13 se valida con fichas revisadas manualmente o fuentes institucionales publicadas. La consulta de una oferta SIIE será una fuente adicional cuando se ejecute P16. No se inventan precios para sustituir esa integración.

El checkpoint histórico de P11 conserva sus requisitos y su evidencia SQL de 2026-10-28: esta separación no los acredita ni reescribe sus releases. La equivalencia de puesta institucional PostgreSQL y el alcance académico pendiente se revisarán explícitamente en el cierre correspondiente.

## Base ya disponible

- Modelos de contado, costo completo, planes, abono, cuotas, vencimientos y vigencias; validación de suma y fechas.
- Adaptador GET de sólo lectura, apagado sin variables del servidor, sin redirecciones ni URLs arbitrarias del usuario.
- Preview en Académico con aplicación explícita al borrador y guardado humano. No sincroniza ni escribe a SIIE.
- Procedencia por programa/oferta/sede/jornada/período y revisión; precios futuros o vencidos excluidos de Gemini.
- [Contrato para SIIE y pasos de conexión](../contracts/SIIE_COMMERCIAL_API.md).

## Pendientes de P16

| Unidad | Entregable | Aceptación pendiente |
|---|---|---|
| P16.1 | Contrato y acceso | URL HTTPS, credencial de sólo lectura, OpenAPI, IDs y ofertas de prueba acordados con SIIE. |
| P16.2 | Consulta oficial | Dos ofertas reales con datos completos y vigentes; rechazo de credencial, oferta distinta, respuesta vencida y totales inconsistentes. |
| P16.3 | Catálogo y sincronización revisada | Listado paginado, selección de ofertas, vínculo estable local/externo, cambios y bajas; sin sobreescribir correcciones humanas. |
| P16.4 | Uso en agentes | Comparar cada precio, cuota y fecha en respuestas con la API; reconocer datos ausentes y respetar Humano. |
| P16.5 | Operación institucional | Custodia y rotación, recuperación, disponibilidad, límites, alertas, responsables y aprobación institucional. |

**0/5 unidades aceptadas.** No representa 0% de implementación: la base ya existe. Se conserva hasta que se retome la fase. No solicitar credenciales ni activar consultas mientras esté diferida.
