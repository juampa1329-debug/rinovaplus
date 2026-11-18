# RinovaPlus: avance y pendientes verificables

Corte: 18 de noviembre de 2026. Este registro complementa el checkpoint SQL local del 28 de octubre con la operación actual en https://app.rinovaplus.com. No reemplaza ni modifica releases, grafos, pruebas o recibos históricos.

## Qué ya se comprobó en producción

| Área | Evidencia disponible | Límite de la evidencia |
|---|---|---|
| Identidad RinovaPlus | Login, aplicación, iconos y menú plegable publicados en Coolify. | No equivale a auditoría formal de accesibilidad. |
| WhatsApp | OAuth descubre números institucionales. Texto, imagen, sticker y voz tienen pruebas previas en la cuenta anterior; el recurso gratuito tiene plantilla y recibos reales. | «WhatsApp · CBN» aún figura pendiente de verificar. Las pruebas anteriores no aceptan su corte institucional; conservar el número anterior hasta completar ese recorrido. Video y sticker estático salientes comprobados en recurso gratuito: recibos firmados, un intento y reproducción confirmada por propietario. Salida animada implementada y probada al 44: 159 KB, 32 fotogramas conservados, un intento y recibo firmado de leído. El propietario confirmó la animación correcta en el teléfono. |
| Messenger CBN | Mensaje real entrante, Gemini y envío con recibo entregado. Nombre Juan Pablo recuperado por participantes autorizados. | Foto sólo si Meta la entrega; no se inventa un perfil. |
| Instagram CBN | DM real, Gemini y control Humano. `messaging_seen` suscrito; prueba nueva manual marcada Leído con un intento y recibo firmado verificado/procesado. | La lectura de esa prueba no actualiza otros mensajes aceptados sin su propio evento. |
| Comentarios Meta | Respuestas personalizadas reales de Gemini en Instagram y Facebook observadas de vuelta por webhook con el mismo ID. Facebook «Necesito orientación» en un intento y con publicación real identificada. | No acredita datos del catálogo aún ausentes, edición/borrado ni una carrera nueva de toma de control durante inferencia. |
| Publicación y navegación | Vista previa de un carrusel real con siete imágenes y enlace original; menú con iconos, plegado y etiquetas al foco/cursor. | Fotos y medios dependen de acceso y vigencia de Meta. |
| IA/Humano | Respuestas personalizadas reales en Messenger/Instagram. Nuevos mensajes en Humano observados con cero operaciones de IA y cero respuestas bot; guard de comentario Humano rechazado. | Pendiente ampliar la carrera de toma de control durante inferencia y el piloto con hechos revisados de programas. |
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
| P4 | 82,29% | Operación vigente limitada a Meta: [matriz WhatsApp, Facebook/Messenger e Instagram](P4_META_ACCEPTANCE_MATRIX.md). Facebook comentarios e Instagram leído ya comprobados. Video, sticker estático y sticker animado WhatsApp salientes aceptados en cuenta gratuita con confirmación del propietario. Pausa/recuperación real comprobada en los cuatro canales Meta; edición y borrado Facebook aprobados. Falta conciliar el borrado externo Instagram, el corte institucional WhatsApp y completar aceptación de reintentos/resultados inciertos. TikTok pasa a P16 por decisión humana; se conserva la definición histórica sin recalcular pesos. Hitos P4.3.m6/m7, P4.4.m4/m5 y P4.close.m5. |
| P5 | 100,00% local | Respuestas personalizadas y silencio Humano posteriores al cambio ya probados en Messenger/Instagram; comentario y sugerencias reales verificados. Falta el piloto con hechos revisados de dos programas y ampliar la prueba de carrera durante inferencia. No se atribuyen estas ampliaciones a la aceptación local antigua. |
| P6 | 100,00% local | Revisar y publicar información real de programas, fuentes y vigencias para el piloto. La función de conocimiento local ya está aceptada. |
| P7 | 89,14% | Catálogo real aprobado, respuesta citada atribuida y estados reales hasta leído/fallido comprobados. Falta aceptación formal completa de catálogo e informe/reintento/recuperación y dependencia de P4. Hitos P7.1.m7, P7.4.m5 y P7.close.m5. |
| P8 | 95,00% | Cierre de recorrido/dependencias P4/P7, hito P8.close.m5. No activar campañas comerciales para simular aceptación. |
| P9 | 93,75% | Aceptación externa y dependencias de P4, hito P9.close.m4. |
| P10 | 95,00% | Cerrar P8/P9 y dependencia P10.close.m4. El algoritmo actual es logística revisada; no se afirma red neuronal ni eficacia real. |
| P11 | 72,50% | Puesta institucional y recuperación específica, aceptación de alcance y cierres P1–P10. PostgreSQL publicado no acredita por sí solo el criterio original de migración SQL2019/SIIE. |
| P12 | 0,00% de aceptación formal | La infraestructura online YA existe y los despliegues/HTTPS se han comprobado. Falta conciliarla formalmente con los criterios originales, custodios, restauración/RPO/RTO, mapeo académico y aceptación institucional; el 0% es del checkpoint formal, no significa que no exista aplicación publicada. |
| P13 | 0/4 hitos aceptados | Revisar fichas de Enfermería y Software con fuentes manuales o institucionales; aceptar especialista/enrutamiento y piloto real de ambos programas con control humano. SIIE no es dependencia obligatoria: pasa a P15. |
| P14 | Plan pendiente | Definir dataset autorizado, finalidad, variables/resultados, baseline, evaluación temporal y por sujeto, revisión humana y monitoreo. Primero completar P4/P7 y el piloto P13; no habilitar entrenamiento con mensajes por defecto. |
| P15 | Diferida; 0/5 unidades aceptadas | Integración SIIE: contrato/acceso, dos ofertas reales, sincronización revisada, uso por agentes y operación institucional. Base técnica implementada, conexión no configurada. |
| P16 | Diferida; 0/5 unidades aceptadas | [Todo TikTok en plan independiente](P16_TIKTOK_PLAN.md): documentación/capacidades, app y OAuth, adaptación, pruebas reales y aceptación/reversión. No bloquea la ejecución operativa Meta solicitada; el checkpoint canónico histórico se conserva. |

**Total técnico actualizado: 94,23%, 263/279 hitos y 45/56 criterios aceptados.** Son 16 hitos originales pendientes. P7.1.m5 se acredita con [el catálogo real observado](../../artifacts/live/p7-catalog-20261117.json) y P7.4.m4 con [recibos, respuesta atribuida y fallo real](../../artifacts/live/p7-replies-failure-20261117.json). No se aceptan aún P7.1/P7.4 completos. Se conservaron definición, pesos y denominadores. P12–P16 quedan fuera del denominador original. El verificador histórico completo no pudo ejecutarse: faltan 20 artefactos históricos referenciados en este checkout. El cálculo usa la función existente de fracciones exactas, pero no se presenta como replay histórico aprobado ni se recrea evidencia ausente.

## Cómo se actualizará desde ahora

Preparación de prueba gratuita P7: Meta identificó el recurso de test `+1 555 162-0221` y validó al destinatario terminado en 44. Se creó el canal separado «WhatsApp · Pruebas Meta» mediante OAuth con la aplicación existente; no sustituye el institucional. El primer intento de configurar recepción detectó que Meta omitía `webhook_configuration` antes de la primera configuración. El ajuste permite iniciar la suscripción sólo con el ID correcto, pero exige la ruta positiva en la lectura posterior; una omisión posterior mantiene resultado incierto. Pasan 77 pruebas de Canales y Ruff F. Este párrafo no acredita aún el envío desde Mensajería masiva ni sus recibos reales.

El propietario confirmó que recibió `hello_world` enviada desde la pantalla de pruebas de Meta, sin tarjeta. [Evidencia y límites](../../artifacts/live/p7-free-test-20261117.json): ese envío no pasó por la cola masiva de RinovaPlus. Durante la preparación se detectó además PostgreSQL `42601` al editar una campaña: la cancelación de trabajos anteriores usaba dos JOIN en un UPDATE no portable. Se sustituyó por EXISTS correlacionado, conservando campaña/institución/cola y sólo trabajos pendientes. Las suites de Canales y Mensajería masiva pasan **112 pruebas**, incluida preservación de otras campañas/instituciones y envíos iniciados; Ruff F correcto. Queda comprobar el guardado y el recorrido masivo en producción.

Coolify confirmó backend y frontend `f847192` como Success (04m17s y 00m23s). Meta rechazó la configuración automática del override de este recurso de test; no se declaró recepción confirmada. La configuración de callback de WhatsApp de la app estaba vacía: se dejó la URL del canal de test preparada para que el propietario copie el verify token generado y lo verifique directamente en Meta. La prueba completa de Mensajería masiva sigue pendiente, sin autorizar consentimiento comercial ni activar campañas.

En cada entrega: añadir revisión Git y despliegue, pruebas ejecutadas y resultado observable; actualizar el estado de los pendientes afectados. Cambiar un hito a aceptado sólo con su evidencia completa. Cuando se complete la matriz, actualizar el registro canónico mediante sus herramientas existentes, conservando peso y definición. Si el alcance institucional cambia de SQL2019 a PostgreSQL, aprobar explícitamente esa equivalencia; no reinterpretar el criterio antiguo de forma silenciosa.

## Broadcasting publicado y recorrido real desde el CRM

Despliegue `fcf5f28` confirmado sano en backend y exitoso en frontend. El editor adaptado de Scentra permite cabecera/cuerpo/pie/botones, ejemplos ficticios, variables estándar y campos personalizados activos del CRM, vista previa WhatsApp y envío explícito a revisión. La plantilla `cbn_informacion_programas_20261117` se creó desde RinovaPlus: Meta la recibió, informó inicialmente **En revisión de Meta** y posteriormente **Aprobada por Meta**, confirmado mediante sincronización del catálogo. No se envió esa plantilla nueva. Las cabeceras multimedia aún requieren un handle de ejemplo de Meta; la subida directa y la creación OTP no están en ese formulario.

[Evidencia nueva](../../artifacts/live/p7-broadcasting-20261117.json): el propietario verificó el callback de test. Su respuesta real entró y Gemini contestó en IA. La campaña `Prueba P7 gratuita · hello_world · 44` tuvo una audiencia de 1/1, un intento, aceptación 18:19:45, enviado 18:19:46, entregado 18:19:47 y leído 18:19:55, hora Bogotá. Este envío sí pasó por Mensajería masiva. El consentimiento temporal quedó revocado y la cadencia de la cuenta desactivada; no se activó el borrador del número real. La respuesta citada de campaña todavía no se observó; faltan fallo controlado y el resto de la matriz. El informe se actualizó con su botón, sin acreditar actualización en tiempo real. Se conservan los porcentajes canónicos hasta completar criterios.

El párrafo anterior conserva el corte inicial del ensayo. Su continuación comprobó la respuesta citada y el fallo real: [evidencia final](../../artifacts/live/p7-replies-failure-20261117.json). La campaña de `hello_world` tiene una respuesta atribuida; la prueba de cabecera inválida tiene un intento fallido y su ID de Meta, sin reintento habilitado. Consentimiento temporal revocado y cadencia de test apagada al finalizar.

También se publicaron segmentación por personas/grupos/programas/jornadas/tipo/etapa y campos CRM explícitos, programación local IANA, creación de plantillas dentro del editor y gráficos animados de entrega/lectura/respuesta. La edad/género/ubicación sólo salen de campos declarados y se fotografían al preparar; los envíos antiguos sin esa información muestran «Sin dato». La selección vacía de personas no se convierte en toda la cuenta. Se probaron guardado de borrador y vista previa de un único contacto, excluido por consentimiento revocado y programa ausente; no se activó ese borrador. La sincronización de Meta recuperó de forma append-only los enlaces nombre/programa, que se habían perdido por el orden de componentes del proveedor.

La [consolidación de recuperación Meta](P4_META_ACCEPTANCE_MATRIX.md) añade 40 casos locales por canal y conserva límites de pruebas reales. El adaptador de Instagram solicita `messaging_seen` y entiende los dos formatos documentados; sólo se acreditará una lectura cuando llegue su evento real. El [plan P16](P16_TIKTOK_PLAN.md) reúne todo TikTok, diferido por el propietario.

Orden inmediato: matriz restante P4-Meta y aceptación formal P7 → piloto de programas P13 con datos revisados → cierres dependientes P8/P9/P10/P11 y conciliación P12 → diseño P14. P15 y P16 se retoman bajo nueva instrucción.

## Adjuntos y guía del creador estándar de Meta

`fab8b19` está sano en backend y exitoso en frontend. [Pruebas reales de archivos](../../artifacts/live/p7-template-media-20261117.json): PNG, PDF y MP4 neutros se cargaron a Meta desde el creador, se guardaron y se solicitaron las tres plantillas a revisión. Meta aprobó la plantilla de imagen como **UTILITY**; PDF y video siguen **En revisión de Meta** en el último corte. Se probaron también los tres archivos definitivos mediante el upload del número de WhatsApp, guardando revisiones de un único borrador limitado al teléfono de prueba 44. No se activó ni se cambió su consentimiento/cadencia.

El creador estándar admite hasta diez botones con límites y agrupación de Meta, ejemplos del enlace dinámico y codificación de sus valores CRM. La carga inspecciona el archivo, usa credenciales en cabecera, conserva un intento durable y revalida cuenta/credencial antes de efectos. El archivo de campaña queda ligado a su operación confirmada y a esa cuenta. Pasan 209 pruebas backend, 18 frontend, tipos, lint y build institucional. Continúa el aviso de tamaño del bundle; no se afirma una auditoría de rendimiento/móvil.

El [manual de plantillas y mensajes naturales](WHATSAPP_TEMPLATE_OPERATOR_GUIDE.md) distingue solicitudes reales de mensajes generales de programas. Los ejemplos no cambian por sí solos la categoría que decide Meta. OTP, catálogos, carruseles, Flows y formatos exclusivos de Marketing Messages API quedan pendientes de integración/aceptación específicas; no se afirma paridad total con todos los productos de Meta ni se suman hitos nuevos al denominador original.

El cierre de esta sesión añade [el recorrido real Facebook y lectura Instagram](../../artifacts/live/p4-meta-recovery-20261117.json): comentario del propietario a las 20:34:33 Bogotá, Gemini confirmado, respuesta aceptada y observada de vuelta por webhook, un intento. La publicación de origen tiene vista previa real. Se dejó ese comentario en Humano y se rechazó sin proveedor una revisión con su versión vigente. Instagram recibió la prueba nueva manual y notificó `read` firmado/procesado, un intento. Esas pruebas eliminan sus pendientes individuales de la matriz, sin aceptar aún el criterio multicanal completo ni alterar sus pesos.


## Recuperación Meta: corte del 18 de noviembre

[Recibo externo](../../artifacts/live/p4-meta-external-recovery-20261117.json): WhatsApp, Messenger, Facebook e Instagram conservaron eventos firmados durante pausas y recuperaron una sola proyección de cada prueba. Facebook editó y eliminó comentarios propios con sus eventos reales. Las cuentas quedaron conectadas/verificadas y sin envíos pendientes. La mejora fc10635 identifica cada evento de recuperación y conserva permisos del texto; frontend y backend comprobados en Coolify, 140 pruebas backend y 15 frontend correctas.

El borrado externo de Instagram sigue abierto: propietario lo confirmó, Meta rechazó consultar ese objeto y el comentario de control sí fue accesible, pero no se recibió evento de eliminación y el CRM conserva Nuevo/Humano. No se fabricó un estado Eliminado. Próximo ajuste necesario: conciliación explícita de fuente no disponible/cambiada. También faltan el recorrido WhatsApp CBN y escenarios restantes de reintento/resultado incierto antes de aceptación formal. P4.4.m4 enlaza la evidencia parcial nueva y permanece pendiente; 94,23% general y 82,29% P4 se conservan con los mismos pesos.
