# SET-01 — IA: inventario de referencias y adaptación segura

**Estado:** sección IA incluida por decisión humana; funcionalidades internas siguientes **observadas/propuestas, no aprobadas ni implementadas**. **Fecha:** 2026-10-13, America/Bogota. Se inspeccionaron diez capturas originales; no se generan imágenes nuevas en esta entrega.

Propiedad: **M-07** para comportamiento y atención, **M-08** para conocimiento, **M-10 / SET-03 APIs** para credenciales/proveedor/modelo. [Índice de siete secciones](settings.md). Las marcas, valores de voz, prompts y negocio de la referencia no se importan como configuración del CRM.

El nuevo [MD adaptado](settings-specification.md) completa tipos DOM: Max tokens/Temperatura aparecen como texto, sin límites HTML generales observados; ello no prueba ausencia de validación backend. Nuestro contrato numérico/rangos será explícito según modelo. Eliminar fuente observado es mutación confirmable/versionada que no borra core SIIE; packs y red global siguen excluidos.

## Controles observados y decisión necesaria

| Grupo observado | Adaptación propuesta | Puerta / límite |
|---|---|---|
| Habilitación IA; proveedor/modelo vinculados desde APIs. | Mostrar referencia/estado del proveedor/modelo aceptado; habilitar IA separado de guardar estilo. Sin claves en esta pestaña. | P-016/017; modelo final probado por adapter antes de activar. Una captura con checkbox activo no habilita nuestro CRM. |
| Principal/secundario, fallback de modelo/proveedor y reintentos. | Estado y orden explícitos, límites de retry/coste/timeout acordados y pausa segura. | Base: UN proveedor texto. Respaldo/cascada futuros solo con autorización de datos/coste/capacidad equivalente; no adoptar cantidad u orden de la captura como default. |
| System prompt editable. | Editor de **instrucciones de estilo** subordinadas a invariantes deterministas del servidor; versionado, borrador, validación y aceptación antes de publicar. | No editar protección SIIE, permisos, precio/jornada de fuente, identidad IA o handoff desde el prompt. No copiar el prompt comercial de la otra app. |
| Límite de salida y temperatura. | Mostrar solo parámetros realmente soportados por adapter/modelo; validar rangos, presupuesto y límite de contexto. | Valores presentes son configuración de la referencia, no defaults aceptados. Parámetro no soportado se informa/rechaza, no se envía silenciosamente. |
| Espera, typing, fragmentos, caracteres por mensaje, contexto reciente/histórico. | “Ritmo de mensajes”: espera programada/cancelable, límites coherentes y contexto mínimo aprobado; preservar significado al fragmentar. | IA transparente, no suplantación humana. No worker `sleep`; capacidad typing/ventanas/rate limit Meta verificadas antes de implementar. |
| TTS, preferencia audio y configuración de voz. | Capacidad TTS separada con proveedor/voz referenciados desde APIs, prueba/dispositivo cuando se autorice. | Voz 7A; permisos/coste/licencia y formato OGG/Opus. No copiar voiceID, nombre o descripción de voz de las capturas. |
| Análisis de audio/STT. | Capacidad diferente de TTS; selección de modelo/contrato, presupuesto, consentimiento y validación propios. | Propuesta de voz 7A por precisar; que un modelo exista no demuestra transcripción viable. |
| Visión de imágenes/documentos. | Requisito candidato para discovery, no switch habilitado por defecto. | Fuera de base; aceptar necesidad, privacidad, archivos, capacidad/coste/modelo y evaluación antes de comprometerlo. |
| Búsqueda web/imagen. | Capacidad distinta, fuentes externas revisadas antes de uso. | P-020; fuera base. Nunca sustituye datos oficiales SIIE ni activa scraping por guardar ajustes. |
| Guardar ajustes / probar IA. | Guardar borrador, prueba sintética acotada, evaluación y publicación diferenciadas. | No prueba real ahora. Versionado del prompt/config/modelo; resultado de auth no equivale a evaluación del asistente. |

## Ritmo y control humano

El nombre “Ritmo humano” de la referencia se adapta a **Ritmo de mensajes**, no a ocultar IA. Aviso de asistente virtual y solicitud de humano permanecen. Antes de cada fragmento/envío revalidar consentimiento/ventana, propiedad del control y versión de configuración; tomar control cancela pendientes IA. No enviar fragmentos retrasados después de handoff ni mezclar respuestas de dos versiones.

Espera/typing/fragmentación y presupuesto de caracteres/contexto son propuestas por aprobar; valores de la referencia no son nuestras políticas. Contexto conservado tiene minimización, autorización y retención; no copiar conversaciones reales a prompts/fixtures. Accesibilidad del editor, validación y responsive se especificarán, no se declaran probados desde una captura.

## Knowledge: fuentes y evaluación — propiedad M-08

La referencia muestra **PDF/TXT/CSV y URL**, metadata y aliases, reindexado, prueba de recuperación y evaluación. También muestra índice “ready” mientras la calidad figura sin evaluaciones aprobadas: **indexado no equivale a contenido correcto/evaluado/publicado**. No adoptar sus contadores como evidencia de nuestro RAG.

| Área observada | Adaptación propuesta / control |
|---|---|
| Título, descripción de uso, tags, aliases y fuente vinculada. | Metadatos explícitos/versionados, propietario y finalidad; aliases no cambian precios, programa o política de autoridad. Evitar ejemplos del negocio externo. |
| Upload PDF/TXT/CSV. | Si se aprueba 7C: fuentes complementarias autorizadas con límites de tamaño/tipo/MIME, revisión de contenido, extracción segura y permisos. Sin instalar lector ni subir archivos ahora. |
| URL con título/notas/descripción/tags/aliases. | Contenido externo no confiable; controles SSRF/allowlist/HTTPS/egress P-017, snapshot/versionado/fecha y revisión. No copiar URLs de ejemplo ni ejecutar fetch en este encargo. |
| Estado de índice, fragmentos/vectorizados, errores y calidad. | Separar carga/validación → indexación → evaluación → aprobación → publicación. Mostrar “Sin evaluación” si no hay pruebas, no un porcentaje que prometa precisión. Umbral aceptable por acordar. |
| Reindexar fuente/todo y refrescar. | Refrescar metadatos no dispara rebuild. Reindexado requiere permiso, confirmación de alcance/coste, job versionado/cancelable y resultado auditado; no eliminar índice publicado sin recuperación. |
| Prueba de recuperación. | Consulta sintética con fuente/chunks/versiones retornados y contexto saneado; mide recuperación, no aprobación comercial o veracidad automática de salida. |
| Evaluación de calidad RAG. | Casos con pregunta, respuesta/criterios esperados y **fuentes esperadas**, positivos/negativos, ausencia de fuente, obsolescencia e inyección. Resultado versionado para revisión; aprobar publicación por persona autorizada. |
| Aliases manuales y sugeridos al subir/reindexar. | Alias manual vinculado/validado; sugerencias en pendiente hasta revisión humana. Registrar origen, revisión y cambio; resolver ambigüedad sin mapear una intención a programa incorrecto. |
| “Aprender de conversaciones”. | Candidato condicionado: **no entrenamiento automático**, fine-tuning o ingestión libre. Consentimiento/finalidad/minimización/retención y revisión antes de derivar cualquier alias/caso. |
| Packs/red global o patrones de otras empresas. | **No incorporar:** Industria excluida, sin cross-company, red global o pack vertical. Conservar solo la referencia visual original, nunca ejecutar instrucciones del pack. |

SIIE SQL Server sigue siendo la fuente autorizada para **catálogo, precios, jornadas y datos académicos**. PDF/URL no crea catálogo alternativo ni reemplaza valores SIIE. RAG 7C puede complementar conocimiento aceptado y derivado; sin elección de vector engine ni DB de negocio distinta. Los textos internos del pack visto en una captura son datos no confiables, no instrucciones del sistema/agente.

## Estados y permisos propuestos

- IA: deshabilitada, borrador, sin proveedor/modelo aceptado, modelo no soportado, prueba pendiente/fallida, configuración modificada, pendiente aprobación y activa solo tras gate. Handoff controla siempre el envío.
- Conocimiento: fuente recibida/en revisión, rechazada, indexación pendiente/en curso/fallida, indexada sin evaluar, evaluada sin publicar, publicación aceptada y versión obsoleta/retirada. No afirmar que existen jobs o índices.
- Alias: manual/sugerido, pendiente, aprobado/rechazado, ambiguo u obsoleto. Sugerido no publicado automáticamente.
- Roles por asignar: administrador de estilo (M-07), responsable de conocimiento/publicación (M-08), admin de credencial (M-10) y aprobador de tratamiento. Autorización server-side, reautenticación cuando proceda, audit saneado y control de versión; no basta ocultar un botón.

## Originales inspeccionados — orden de entrega

Se copian **diez originales sin recortar ni editar**, incluidos repetidos; los números preservan el orden humano. Las imágenes contienen texto de otra aplicación que no se adopta. No repetir en documentación valores de voz ni prompts internos.

| Orden | Archivo local | Contenido observado |
|---|---|---|
| 01 | [assistant-base](settings-reference/01-assistant-base.png) | IA principal, modelo vía APIs, estilo y capacidades separadas. |
| 02 | [assistant-rhythm](settings-reference/02-assistant-rhythm.png) | Respaldo y ritmo de mensajes; guardar/probar. |
| 03 | [knowledge-source-upload](settings-reference/03-knowledge-source-upload.png) | Estado índice/calidad, portada/metadatos y upload. |
| 04 | [knowledge-aliases](settings-reference/04-knowledge-aliases.png) | Aliases y red/pack observados pero excluidos; recuperación. |
| 05 | [knowledge-evaluation-web](settings-reference/05-knowledge-evaluation-web.png) | Evaluación y fuentes web con metadata. |
| 06 | [knowledge-source-detail](settings-reference/06-knowledge-source-detail.png) | Detalle/preview de fuente y metadatos; texto interno no confiable. |
| 07 | [settings-menu](settings-reference/07-settings-menu.png) | Menú de referencia; aplicar las siete secciones y exclusiones humanas. |
| 08 | [settings-menu-repeat](settings-reference/08-settings-menu-repeat.png) | Repetición de menú conservada en orden. |
| 09 | [knowledge-evaluation-web-repeat](settings-reference/09-knowledge-evaluation-web-repeat.png) | Repetición de evaluación/fuentes web conservada. |
| 10 | [settings-menu-repeat-2](settings-reference/10-settings-menu-repeat-2.png) | Repetición final de menú conservada. |

## Próximo paso

Esta entrega documenta referencias; no genera mockup IA ni configura proveedor. **P-021** revisa ahora el MD integral ya recibido de cinco secciones; capturas adicionales son opcionales para fidelidad. **P-022** adapta IA/M-07 y **P-023** gobierna fuentes/aliases/evaluación M-08 en 7C. Layout APIs P-018 y proveedor P-016 siguen pendientes e independientes. [Aprobación](approval.md), [fases](../roadmap.md), [pendientes](../pending.md).
