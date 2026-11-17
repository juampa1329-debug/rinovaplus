# RinovaPlus: avance y pendientes verificables

Corte: 17 de noviembre de 2026. Este registro complementa el checkpoint SQL local del 28 de octubre con la operación actual en https://app.rinovaplus.com. No reemplaza ni modifica releases, grafos, pruebas o recibos históricos.

## Qué ya se comprobó en producción

| Área | Evidencia disponible | Límite de la evidencia |
|---|---|---|
| Identidad RinovaPlus | Login, aplicación, iconos y menú plegable publicados en Coolify. | No equivale a auditoría formal de accesibilidad. |
| WhatsApp CBN | OAuth descubre números institucionales; token, cuenta, recepción firmada, texto, imagen y sticker probados. El propietario confirmó reproducción de voz en ambos extremos y ausencia del modal anterior. | Conservar el número de prueba hasta aceptar el institucional completo; no se afirma aquí prueba de video/sticker saliente. |
| Messenger CBN | Mensaje real entrante, Gemini y envío con recibo entregado. Nombre Juan Pablo recuperado por participantes autorizados. | Foto sólo si Meta la entrega; no se inventa un perfil. |
| Instagram CBN | DM real entrante y envío aceptado; nombre Juampa. Campos messages y comments suscritos. | Aceptado no significa entregado o leído. |
| Comentarios Instagram | Comentario real del propietario, respuesta institucional publicada por RinovaPlus y observada por el webhook con el mismo ID de proveedor. | La versión anterior seleccionaba una bienvenida fija. No acredita respuestas personalizadas ni comentarios Facebook reales. |
| Publicación y navegación | Vista previa de un carrusel real con siete imágenes y enlace original; menú con iconos, plegado y etiquetas al foco/cursor. | Fotos y medios dependen de acceso y vigencia de Meta. |
| IA/Humano | Pruebas previas de primera respuesta de Gemini y toma de control humano; cola única y comprobaciones de epoch. | La nueva generación personalizada necesita su propio recorrido de regresión real. |
| Académico | Fichas comerciales por escuelas, importación revisable Firecrawl y selector de modelos implementados. | Falta aceptación humana del piloto y réplica con dos programas. OpenRouter sin clave no acredita consulta real. |

Referencias de código desplegado: `ae3ca08` (canales sociales, publicaciones y menú), `25fac06` (nombres visibles), `f1aa463` (protección previa de comentarios). Estas revisiones pertenecen a la rama `deploy/coolify-rinovaplus`. El comportamiento nuevo descrito abajo sustituye la protección amplia de `f1aa463`: una automatización propia de Meta no se considera un envío de RinovaPlus.

## Ampliación actual: respuestas personalizadas

Implementación en revisión y pruebas locales:

- Gemini redacta el texto de mensajes WhatsApp, Messenger e Instagram con el prompt global, las instrucciones del agente, el historial acotado y los hechos del catálogo CRM.
- Para comentarios Facebook/Instagram usa el prompt global y el de comentarios, la publicación obtenida de Meta y hechos públicos revisados. Nunca incluye memoria privada ni historial de DM en un comentario público.
- Precio sólo con concepto y vigencia; datos ausentes no se inventan. Consultar un programa no confirma una asignación académica ni cambia el expediente.
- Sugerencias de comentarios y botón de sugerencia en el compositor del Inbox. Copiar una sugerencia no envía; sólo Humano puede enviarla manualmente.
- IA se detiene ante toma de control humano, cambio de fuente/prompt/modelo o mensaje que deja obsoleta la respuesta pendiente. No hay reintento automático de inferencia incierta.
- Una respuesta nativa de Meta no silencia a Gemini. Un envío real existente del CRM impide duplicados. El CRM incluye acceso a la administración de Automatizaciones de Meta; no simula un interruptor remoto no soportado.

Prueba necesaria tras el despliegue: preguntar por Software, continuar con duración/precio/materias sin repetir el nombre; repetir en Messenger e Instagram; comentar una pregunta de programa; generar y aplicar sugerencias; tomar control Humano mientras hay una inferencia pendiente. Registrar texto observado, operación, estado del envío y recibo. Hasta entonces esta ampliación no se declara aceptada en producción.

Bloqueo de contenido detectado en producción: **Académico muestra “Aún no hay programas registrados”**. El propietario precisó que la fuente será una **API SIIE conectada con DBSIIE**, incluyendo contado, planes financiados, abono, cuotas, fechas y costo completo. Se preparó el [contrato y conexión propuesta](../contracts/SIIE_COMMERCIAL_API.md). Sin catálogo revisado, Gemini debe reconocer el dato faltante; no puede responder precios o duración reales que el CRM aún no contiene. Firecrawl queda como apoyo documental, no como fuente financiera prioritaria.

Despliegue `10b9004` confirmado en Coolify para backend y frontend. Consulta de sólo lectura en el backend publicado confirmó que el contexto de Gemini se construye correctamente, con **0 programas y 0 documentos** disponibles en esa consulta; el agente activo tiene capacidades de programa y fuentes. La base de integración financiera SIIE se prepara en una revisión posterior. Pruebas nuevas de preguntas personalizadas solicitadas al propietario; no se afirma su recepción hasta observarla.

Prueba real del simulador sobre duración y financiación de Software: la interfaz confirmó **Proveedor consultado** y devolvió una respuesta específica solicitando período académico, sin inventar cifras, con derivación a asesor. Acredita inferencia real personalizada en el simulador; no sustituye mensajes/recibos nuevos en cada canal. La base SIIE añadió **193 pruebas backend aprobadas** en ocho suites y **19 frontend** en tres suites (incluye la regresión de sugerencias); TypeScript/build correctos. Es otro alcance de prueba, no se suma a los totales de la revisión previa.

Validación local de esta entrega: **179 pruebas backend**, **42 frontend** en tres suites, TypeScript y build institucional correctos. Tras ajustar el ciclo de vida de sugerencias se repitieron sus dos casos y lint/tipos/build. Ruff F sin errores en los ocho módulos backend afectados; ESLint sin errores en los componentes/pruebas nuevos. El build mantiene el aviso de tamaño de bundle mayor de 500 kB; no es una aceptación de rendimiento. Las primeras preparaciones del arnés temporal necesitaron rutas/dependencia de emojis y mocks corregidos; no se presentan como ejecuciones aprobadas. No se crearon contenedores ni se modificaron datos para los tests.

## Qué falta por fase

| Fase | Avance canónico | Qué falta para cerrar |
|---|---:|---|
| P0 | 100,00% | Sin pendientes canónicos de esta fase. |
| P1 | 100,00% | Sin pendientes canónicos de esta fase. |
| P2 | 100,00% | Sin pendientes canónicos de esta fase. |
| P3 | 100,00% | Sin pendientes canónicos; las mejoras nuevas de Inbox se registran aparte. |
| P4 | 82,29% | Matriz de aceptación externa por canal: OAuth, identidad, medios, entrega, recuperación y efectos inciertos. Falta completar Facebook comentarios, Instagram recibos, medios salientes y TikTok dentro del alcance canónico; consolidar evidencia y reversión. Hitos P4.3.m6/m7, P4.4.m4/m5 y P4.close.m5. |
| P5 | 100,00% local | Nueva extensión de generación libre con fuentes: probar respuestas personalizadas, sugerencias y control humano en producción; no se atribuye a la aceptación antigua. |
| P6 | 100,00% local | Revisar y publicar información real de programas, fuentes y vigencias para el piloto. La función de conocimiento local ya está aceptada. |
| P7 | 82,29% | Sincronizar catálogo Meta aprobado; envío hello_world desde Mensajería masiva con destinatario autorizado; comprobar enviado/entregado/leído y fallo real controlado, sin confundir aceptado con entrega. Hitos P7.1.m5/m7, P7.4.m4/m5 y P7.close.m5. |
| P8 | 95,00% | Cierre de recorrido/dependencias P4/P7, hito P8.close.m5. No activar campañas comerciales para simular aceptación. |
| P9 | 93,75% | Aceptación externa y dependencias de P4, hito P9.close.m4. |
| P10 | 95,00% | Cerrar P8/P9 y dependencia P10.close.m4. El algoritmo actual es logística revisada; no se afirma red neuronal ni eficacia real. |
| P11 | 72,50% | Puesta institucional y recuperación específica, aceptación de alcance y cierres P1–P10. PostgreSQL publicado no acredita por sí solo el criterio original de migración SQL2019/SIIE. |
| P12 | 0,00% de aceptación formal | La infraestructura online YA existe y los despliegues/HTTPS se han comprobado. Falta conciliarla formalmente con los criterios originales, custodios, restauración/RPO/RTO, mapeo académico y aceptación institucional; el 0% es del checkpoint formal, no significa que no exista aplicación publicada. |
| P13 | 0/4 hitos aceptados | Acordar y conectar API SIIE; revisar ofertas/financiación de Enfermería y Software; aceptar especialista/enrutamiento; piloto real de ambos programas con datos y control humano. Hay implementación parcial, no cuatro hitos terminados. Importación desde URL es auxiliar. |
| P14 | Plan pendiente | Definir dataset autorizado, finalidad, variables/resultados, baseline, evaluación temporal y por sujeto, revisión humana y monitoreo. Primero completar P4/P7 y el piloto P13; no habilitar entrenamiento con mensajes por defecto. |

**Total canónico: 93,62%, 261/279 hitos y 45/56 criterios aceptados.** Son 18 hitos originales pendientes. No se recalcula como promedio de fases ni se suman P12/P13/P14 al denominador. El avance publicado de canales se registra arriba y puede cerrar hitos sólo cuando alcance su matriz completa. Con esto se evita tanto ocultar trabajo nuevo como inflar el porcentaje sin aceptación.

## Cómo se actualizará desde ahora

En cada entrega: añadir revisión Git y despliegue, pruebas ejecutadas y resultado observable; actualizar el estado de los pendientes afectados. Cambiar un hito a aceptado sólo con su evidencia completa. Cuando se complete la matriz, actualizar el registro canónico mediante sus herramientas existentes, conservando peso y definición. Si el alcance institucional cambia de SQL2019 a PostgreSQL, aprobar explícitamente esa equivalencia; no reinterpretar el criterio antiguo de forma silenciosa.

Orden inmediato: respuestas personalizadas → aceptación restante P4 → hello_world/recibos P7 → piloto de programas P13 → cierres dependientes P8/P9/P10/P11 y conciliación P12 → diseño P14.
