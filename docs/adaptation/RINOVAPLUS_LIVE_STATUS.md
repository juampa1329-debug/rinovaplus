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

Despliegue de la base SIIE `a333463` confirmado sano en backend y exitoso en frontend. También se generaron borradores reales visibles en **Inbox Messenger** y **Comentarios Instagram**, sin publicarlos ni enviarlos. El primer borrador del Inbox se confirmó en el servidor pero la pantalla mostró un aviso genérico durante la actualización; una prueba manual posterior mostró correctamente el resultado. Se conserva esta observación sin atribuir una causa no demostrada. La interfaz conserva ahora el ID de la solicitud al recuperarla, para reutilizar el resultado confirmado en vez de repetir consumo. Un nuevo mensaje/control o versión del agente genera otro contexto.

Regresión final de frontend: **46 pruebas en cuatro suites**, TypeScript y ESLint de los componentes nuevos correctos. Incluye recuperación con el mismo identificador, descarte de respuesta tardía y aplicación explícita de los planes SIIE al borrador. El acceso a Meta abre directamente su pantalla de Automatizaciones observada; las reglas nativas existentes no se desactivaron ni se atribuyen al interruptor de Gemini.

Validación local de esta entrega: **179 pruebas backend**, **42 frontend** en tres suites, TypeScript y build institucional correctos. Tras ajustar el ciclo de vida de sugerencias se repitieron sus dos casos y lint/tipos/build. Ruff F sin errores en los ocho módulos backend afectados; ESLint sin errores en los componentes/pruebas nuevos. El build mantiene el aviso de tamaño de bundle mayor de 500 kB; no es una aceptación de rendimiento. Las primeras preparaciones del arnés temporal necesitaron rutas/dependencia de emojis y mocks corregidos; no se presentan como ejecuciones aprobadas. No se crearon contenedores ni se modificaron datos para los tests.

## Decisión vigente: SIIE pasa a P15

Por instrucción posterior del propietario, la integración DBSIIE queda en **[P15, diferida con base técnica conservada](P15_SIIE_INTEGRATION.md)**. Deja de ser una dependencia obligatoria de P13. Las fichas piloto se pueden revisar manualmente o desde fuentes institucionales. Los registros anteriores sobre la prioridad de la API reflejan la decisión previa; no exigen activarla ahora. No se modifican denominadores ni se acredita una aceptación externa por moverla de fase.

## Aceptación real de Gemini y Humano — 17 de noviembre

[Recibo de prueba](../../artifacts/live/social-ai-20261117.json): entró la pregunta «Que duración y formas de pago tiene cada programa?» por Messenger, Instagram DM y comentario de Instagram. Las tres operaciones Gemini terminaron confirmadas con un intento; las respuestas se refieren a duración/financiación y piden el programa, sin cifras inventadas. Messenger tiene recibo entregado. Instagram DM figura aceptado. La publicación del comentario fue observada de vuelta por webhook con el mismo ID de respuesta.

Después de pasar los dos chats a **Humano**, llegaron nuevas preguntas a las 22:09:36 y 22:09:50 UTC. Ambas conservaron control humano/epoch 1, **cero operaciones de Gemini para esos mensajes y cero mensajes de bot posteriores** en la observación. El propietario confirmó la prueba. El comentario quedó en Humano y se comprobó sin proveedor que la guarda rechaza incluso la versión vigente de ese comentario. No equivale a una nueva publicación bajo Humano ni a la prueba de carrera durante inferencia.

Esto cierra el recorrido positivo personalizado y el silencio posterior al cambio de modo para los dos canales probados. No acredita fuentes/precios reales de programas, recibos Instagram entregado/leído, comentarios Facebook ni la matriz completa de P4/P7. Los dos chats y el comentario de prueba se dejan en Humano al terminar esta comprobación.

## Qué falta por fase

| Fase | Avance canónico | Qué falta para cerrar |
|---|---:|---|
| P0 | 100,00% | Sin pendientes canónicos de esta fase. |
| P1 | 100,00% | Sin pendientes canónicos de esta fase. |
| P2 | 100,00% | Sin pendientes canónicos de esta fase. |
| P3 | 100,00% | Sin pendientes canónicos; las mejoras nuevas de Inbox se registran aparte. |
| P4 | 82,29% | Matriz de aceptación externa por canal: OAuth, identidad, medios, entrega, recuperación y efectos inciertos. Falta completar Facebook comentarios, Instagram recibos, medios salientes y TikTok dentro del alcance canónico; consolidar evidencia y reversión. Hitos P4.3.m6/m7, P4.4.m4/m5 y P4.close.m5. |
| P5 | 100,00% local | Respuestas personalizadas y silencio Humano posteriores al cambio ya probados en Messenger/Instagram; comentario y sugerencias reales verificados. Falta el piloto con hechos revisados de dos programas y ampliar la prueba de carrera durante inferencia. No se atribuyen estas ampliaciones a la aceptación local antigua. |
| P6 | 100,00% local | Revisar y publicar información real de programas, fuentes y vigencias para el piloto. La función de conocimiento local ya está aceptada. |
| P7 | 85,14% | Catálogo real aprobado y ligado a credencial verificado (P7.1.m5). Pendientes: envío hello_world desde Mensajería masiva con número de test y destinatario autorizado; enviado/entregado/leído y fallo real controlado. Hitos P7.1.m7, P7.4.m4/m5 y P7.close.m5. |
| P8 | 95,00% | Cierre de recorrido/dependencias P4/P7, hito P8.close.m5. No activar campañas comerciales para simular aceptación. |
| P9 | 93,75% | Aceptación externa y dependencias de P4, hito P9.close.m4. |
| P10 | 95,00% | Cerrar P8/P9 y dependencia P10.close.m4. El algoritmo actual es logística revisada; no se afirma red neuronal ni eficacia real. |
| P11 | 72,50% | Puesta institucional y recuperación específica, aceptación de alcance y cierres P1–P10. PostgreSQL publicado no acredita por sí solo el criterio original de migración SQL2019/SIIE. |
| P12 | 0,00% de aceptación formal | La infraestructura online YA existe y los despliegues/HTTPS se han comprobado. Falta conciliarla formalmente con los criterios originales, custodios, restauración/RPO/RTO, mapeo académico y aceptación institucional; el 0% es del checkpoint formal, no significa que no exista aplicación publicada. |
| P13 | 0/4 hitos aceptados | Revisar fichas de Enfermería y Software con fuentes manuales o institucionales; aceptar especialista/enrutamiento y piloto real de ambos programas con control humano. SIIE no es dependencia obligatoria: pasa a P15. |
| P14 | Plan pendiente | Definir dataset autorizado, finalidad, variables/resultados, baseline, evaluación temporal y por sujeto, revisión humana y monitoreo. Primero completar P4/P7 y el piloto P13; no habilitar entrenamiento con mensajes por defecto. |
| P15 | Diferida; 0/5 unidades aceptadas | Integración SIIE: contrato/acceso, dos ofertas reales, sincronización revisada, uso por agentes y operación institucional. Base técnica implementada, conexión no configurada. |

**Total técnico actualizado: 93,88%, 262/279 hitos y 45/56 criterios aceptados.** Son 17 hitos originales pendientes. P7.1.m5 se acredita con [el catálogo real observado](../../artifacts/live/p7-catalog-20261117.json); no cierra P7.1 ni los recibos masivos. Se conservaron definición, pesos y denominadores. P12–P15 quedan fuera del denominador original. El verificador histórico completo no pudo ejecutarse: faltan 20 artefactos históricos referenciados en este checkout. El cálculo usa la función existente de fracciones exactas, pero no se presenta como replay histórico aprobado ni se recrea evidencia ausente.

## Cómo se actualizará desde ahora

Preparación de prueba gratuita P7: Meta identificó el recurso de test `+1 555 162-0221` y validó al destinatario terminado en 44. Se creó el canal separado «WhatsApp · Pruebas Meta» mediante OAuth con la aplicación existente; no sustituye el institucional. El primer intento de configurar recepción detectó que Meta omitía `webhook_configuration` antes de la primera configuración. El ajuste permite iniciar la suscripción sólo con el ID correcto, pero exige la ruta positiva en la lectura posterior; una omisión posterior mantiene resultado incierto. Pasan 77 pruebas de Canales y Ruff F. Este párrafo no acredita aún el envío desde Mensajería masiva ni sus recibos reales.

En cada entrega: añadir revisión Git y despliegue, pruebas ejecutadas y resultado observable; actualizar el estado de los pendientes afectados. Cambiar un hito a aceptado sólo con su evidencia completa. Cuando se complete la matriz, actualizar el registro canónico mediante sus herramientas existentes, conservando peso y definición. Si el alcance institucional cambia de SQL2019 a PostgreSQL, aprobar explícitamente esa equivalencia; no reinterpretar el criterio antiguo de forma silenciosa.

Orden inmediato: respuestas personalizadas y silencio Humano → aceptación restante P4 → hello_world/recibos P7 → piloto de programas P13 con datos revisados → cierres dependientes P8/P9/P10/P11 y conciliación P12 → diseño P14. P15 se retoma bajo nueva instrucción.
