# Propuesta en modo oscuro — 12 módulos

**Fecha:** 2026-10-13, America/Bogota. **Estado:** 12 PNG oscuros disponibles; aprobación humana pendiente. Es la misma propuesta de módulos con una variante de color, no una nueva arquitectura, funcionalidad o aplicación.

La [galería clara](README.md) permanece disponible y sus 12 imágenes originales se conservaron byte por byte. Comparar ambas variantes y registrar ajustes o aprobación en el [registro](approval.md); conservar la propuesta no equivale a aprobarla para implementación.

## Recorrido rápido

| Módulo | Pantalla | PNG oscuro |
|---|---|---|
| M-01 | Acceso | [Abrir](mockups-dark/m01-access-dark.png) |
| M-02 | Resumen de admisiones y operación | [Abrir](mockups-dark/m02-overview-dark.png) |
| M-03 | Prospectos | [Abrir](mockups-dark/m03-prospects-dark.png) |
| M-04 | Conversaciones y control humano | [Abrir](mockups-dark/m04-conversations-dark.png) |
| M-05 | Formulario de aspirante | [Abrir](mockups-dark/m05-application-form-dark.png) |
| M-06 | Revisión e integración académica | [Abrir](mockups-dark/m06-admissions-review-dark.png) |
| M-07 | Asistente y automatizaciones | [Abrir](mockups-dark/m07-assistant-dark.png) |
| M-08 | Conocimiento y catálogo SIIE | [Abrir](mockups-dark/m08-knowledge-dark.png) |
| M-09 | Memoria de ventas autorizadas | [Abrir](mockups-dark/m09-sales-memory-dark.png) |
| M-10 | Integraciones y proveedores | [Abrir](mockups-dark/m10-integrations-dark.png) |
| M-11 | Retención estudiantil | [Abrir](mockups-dark/m11-retention-dark.png) |
| M-12 | Relacionamiento corporativo | [Abrir](mockups-dark/m12-corporate-dark.png) |

## M-01 — Acceso

**Fase 2; variante oscura disponible, aprobación pendiente.** Mismo ingreso propuesto para asesor/administrador.

![M-01 Acceso, variante oscura conceptual](mockups-dark/m01-access-dark.png)

## M-02 — Resumen de admisiones y operación

**Fases 3/6; variante oscura disponible, aprobación pendiente.** Atención, solicitudes y alertas con datos de demostración.

![M-02 Resumen de admisiones y operación, variante oscura](mockups-dark/m02-overview-dark.png)

## M-03 — Prospectos

**Fases 3–4; variante oscura disponible, aprobación pendiente.** Captación y ficha sin duplicar la autoridad SIIE.

![M-03 Prospectos, variante oscura conceptual](mockups-dark/m03-prospects-dark.png)

## M-04 — Conversaciones y control humano

**Fase 3; audio futuro 7A; variante oscura disponible, aprobación pendiente.** Bandeja, conversación y resumen con control humano visible.

![M-04 Conversaciones y control humano, variante oscura](mockups-dark/m04-conversations-dark.png)

## M-05 — Formulario de aspirante

**Fase 4; referencia móvil; variante oscura disponible, aprobación pendiente.** Solicitud pública con privacidad; no equivale a matrícula.

![M-05 Formulario de aspirante móvil, variante oscura](mockups-dark/m05-application-form-dark.png)

## M-06 — Revisión e integración académica

**Fase 5; variante oscura disponible, aprobación pendiente.** Revisión humana separada de escritura core, todavía no autorizada/probada.

![M-06 Revisión e integración académica, variante oscura](mockups-dark/m06-admissions-review-dark.png)

## M-07 — Asistente y automatizaciones

**Fases 3/7A/7B; variante oscura disponible, aprobación pendiente.** Estilo/atención conservando invariantes bloqueadas; sin acciones reales.

![M-07 Asistente y automatizaciones, variante oscura](mockups-dark/m07-assistant-dark.png)

## M-08 — Conocimiento y catálogo SIIE

**Fases 3/7C; variante oscura disponible, aprobación pendiente.** Catálogo y procedencia ficticios; no conexión DB ni RAG implementado.

![M-08 Conocimiento y catálogo SIIE, variante oscura](mockups-dark/m08-knowledge-dark.png)

## M-09 — Memoria de ventas autorizadas

**Fase 7C; expansión condicionada, aprobación pendiente.** Concepto sujeto a necesidad, consentimiento y retención; no perfilamiento habilitado.

![M-09 Memoria de ventas autorizadas, variante oscura conceptual futura](mockups-dark/m09-sales-memory-dark.png)

## M-10 — Integraciones y proveedores

**Fases 3/6/7A; variante oscura disponible, aprobación pendiente.** Diagnóstico demostrativo, capacidades separadas y referencias a secretos; ningún servicio conectado.

![M-10 Integraciones y proveedores, variante oscura](mockups-dark/m10-integrations-dark.png)

## M-11 — Retención estudiantil

**Fase 7D; futuro no especificado, aprobación pendiente.** Misma intención conceptual de relacionamiento; no añade scoring, cobros o campañas.

![M-11 Retención estudiantil, variante oscura de alcance futuro](mockups-dark/m11-retention-dark.png)

## M-12 — Relacionamiento corporativo

**Fase 7E; futuro no especificado, aprobación pendiente.** Misma intención conceptual institucional; no añade convenios, vacantes ni facturación.

![M-12 Relacionamiento corporativo, variante oscura de alcance futuro](mockups-dark/m12-corporate-dark.png)

## Procedencia, preservación y límites

[Prompts exactos, paleta y hashes de preservación](generation-prompts-dark.json): edición mediante image_gen de los mockups claros, salida en carpeta separada. El coordinador verificó cabeceras de los 12 PNG oscuros y SHA256 de los 12 claros sin cambios. La [referencia de tokens](../design-system.md) es propuesta, no tema implementado ni conformidad de contraste certificada.

Objetivo de la variante: conservar distribución, contenido y estados de la propuesta; las imágenes no constituyen una prueba automatizada de equivalencia funcional. Los PNG son raster, no UI editable/componentes. Marco lógico no equivale a tamaño físico exacto del archivo; no se renderizaron todas las adaptaciones responsive o estados secundarios.

Solo texto CRM CBN, sin logotipo oficial inventado, con español profesional y datos ficticios. Sin código, DB, Git o despliegue; sin prueba funcional, navegador/dispositivo, permisos/autenticación o accesibilidad. SIIE y producción no se tocaron. La muestra editable y las puertas técnicas siguen pendientes; aprobar color no autoriza implementar.
