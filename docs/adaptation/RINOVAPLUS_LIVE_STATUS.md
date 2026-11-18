## P15: editor e informes publicados; revisión final de despacho — 2026-11-18

P15:5/7 aceptadas (71,43%): transporte, reglas, eventos/acceso, editor/marca e informes. Editor real: HTML importado guardado como borrador, preview segura, scripts rechazados con modal explicativo, versión3 recuperada sin publicar y versión4 limpia publicada. PNG de481.084bytes cargado correctamente tras ajustar únicamente la envolvente HTTP de recursos. El backend2972137 está saludable y su consulta de informes se probó sin parches de ensayo:2avisos de transición y1informe tras dos pasadas, rollback ySMTP0.

La prueba adicional de revocación reabre P15.5 hasta verificar el nuevo guard: las pruebas manuales deben conservar el administrador emisor y comprobar que sigue autorizado, aunque el destinatario de prueba sea externo al directorio CRM. El intento fallido usó SMTP simulado y rollback, sin envío externo. Código corregido;343backend seleccionadas (43correo),33frontend y15regresionesPG separadas. Cuenta de prueba inactiva,0sesiones/0desafíos. Pendientes: redespliegue del guard, ensayo ampliado y recuperación final; no declarar P15al100hasta esos resultados. General originalP0–P11:100%, P12auxiliar:100%; demás fases adicionales conservan alcance/estado documentados.

## P15: acceso y cola validados; despliegue final pendiente — 2026-11-18

P15:4/7 aceptadas (57,14%): transporte, reglas/destinatarios, eventos/acceso y outbox. El titular confirmó activación y recuperación. Cuenta de ensayo desactivada:0sesiones y0desafíos vigentes. La respuesta pública para cuenta inactiva y cuenta inexistente es igual y no produce nuevos correos. Cinco correos reales autorizados; recibo de Gmail observado en Oracle y registrado manualmente.

Pasan336 backend seleccionadas,33 frontend, tipos/ESLint/build y15 regresiones separadas de dialecto. Worker real sobre SQL nativo bajo rollback con SMTP simulado: reintento/espera, aceptación sin duplicación, incertidumbre sin reenvío, lease vencido, caducidad, pausa y cupo. Se conservan scripts y límites en artifacts/live/p15-*-20261118.*. El HTML importado y la reversión funcionan; se prueba bloqueo de scripts. Pendientes de despliegue: fecha OccurredAt del informe, modal explicativo y envolvente HTTP2MB para admitir PNG1MB. La aceptación final de editor/informes/operación se mantiene abierta hasta comprobarlos publicados. General P0–P11:100% y P12 auxiliar:100%; P13parcial, P14plan, P16SIIE yP17TikTok diferidas, P18seguridad planificada.

## P15: transporte aceptado y acceso real confirmado — 2026-11-18

P15.1 aceptada: SMTP/TLS, SPF/DKIM activos y entrega real confirmada por el destinatario. P15 avanza 1/7 (14,29% de aceptación), sin modificar el general original P0–P11:100% ni P12 auxiliar:100%. El titular confirmó activación e ingreso y luego recuperación/cambio de contraseña e ingreso, después del arreglo0c4afd1. Se está desactivando la cuenta de ensayo. Cinco envíos transaccionales controlados; la primera invitación tiene recibo de relay Oracle registrado expresamente como observación del operador.

Pasan334 backend seleccionadas (36 de correo),32 frontend, tipos/ESLint/build;15 regresiones separadas de dialecto PG. Prueba nativa con rollback: dos avisos por transición fallo/recuperación, sin duplicar el fallo repetido; un informe tras ejecutar dos veces; cero llamadas SMTP. El primer intento detectó CreatedAt inexistente en auditoría; se corrige a OccurredAt y se valida contra el esquema congelado. La copia aislada conserva siete tablas, tres envelopes autenticados y una imagen SHA verificada, sin CONNECT del runtime ni correo ejecutable. Pendiente completar pruebas del worker y revisión final de P15; OPS01–06 y fases adicionales mantienen sus límites.

## P15: entrega real y corrección de activación — 2026-11-18

Oracle confirma SPF y firma DKIM activos. Tres correos controlados a cbnaudiovisuales@gmail.com fueron aceptados en un intento por envío; el titular confirmó su recepción. El log de Oracle acredita relay de la invitación a Gmail con SMTP 250 y TLS. El usuario de prueba Consulta continúa pendiente de activación; el titular reportó un error de validación y el backend registró ValueError. Se corrige la clasificación de contraseña rechazada (422 explicativo), se refuerza la ruta de activación sin exponer el token al servidor y se diferencia «Activar mi cuenta» de la muestra. No afirmar resuelto hasta repetir el recorrido real.

Pasan 333 pruebas backend seleccionadas (35 de correo); nuevas regresiones de enlaces y múltiples plantillas. La copia P15 aislada conserva las siete tablas nuevas, incluida la imagen y los tres envelopes cifrados, con huellas iguales al snapshot; runtime sin CONNECT y sin consumidor en esa copia. No sustituye la recuperación P11 ni valida copia externa/custodia. Se corrige crear otro registro y recuperar versiones como borrador/pausadas. Historial incorpora observación manual de recibos Oracle, diferenciada de un webhook automático.

P15 permanece 0/7 aceptadas, en validación. General original P0–P11:100%; P12 auxiliar:100% en alcance aceptado. P13 Académico/agentes por programa:parcial (0/4); P14 entrenamiento comercial:plan; P15 correos/notificaciones:pruebas (0/7); P16 API SIIE:diferida (0/5); P17 TikTok:diferida (0/5); P18 seguridad:plan (0/8). No alterar el denominador original ni cerrar OPS-05 por una muestra transaccional.

## P15 en implementación y pruebas — 2026-11-18

Ajustes → Correos y notificaciones incorpora transporte Oracle SMTP/TLS, reglas por evento y destinatarios, grupos, preferencias propias, versiones de HTML y recursos de marca inspeccionados, informes diarios/semanales y outbox cifrado en PostgreSQL. Recuperación por correo sin enumeración y activación revisada desde Usuarios reutilizan códigos de un uso/una hora y conservan 2FA. El consumidor SMTP es independiente de mensajería. SMTP aceptado no equivale a entrega; resultados inciertos no se reenvían automáticamente. Los recibos de Oracle se registran como observación de operador, no como webhook automático.

**P15 sigue abierta: 0/7 unidades aceptadas.** Hay implementación parcial con pruebas; no se declara 100% ni entrega real todavía. Pendientes: propagación/verificación DKIM/SPF, prueba real de SMTP/recibos/invitación/recuperación, validar la cobertura instrumentada de eventos de colas/webhooks y modelo automático, revisión de informes y ensayo de recuperación P15. Oracle: dominio y remitente registrados en Ashburn; credenciales guardadas por el propietario en Coolify, sin valores en el repositorio. Migración manual aplicada: 7 tablas nativas separadas, 155 tablas CRM intactas, runtime sin CREATE ni DELETE; prueba de deduplicación/reclamación con rollback, cero correos persistidos por ese ensayo.

Pasan 330 pruebas backend seleccionadas (33 nuevas P15), 27 frontend seleccionadas, tipos/lint modificado y build de workspace. Backend 1c302ef desplegado saludable con 9 consumidores; autenticación SMTP/TLS verificada sin envío. Plantilla publicada, preview y recurso privado probados en UI. SPF público correcto; DKIM y entrega real pendientes de validar. El ajuste siguiente corrige framing CRLF de SMTP, enlace en texto plano, pausa visual y restauración de sesión sin destello de login. Advertencia previa de bundle grande conservada. Evidencia y manual: `tasks/p15-notifications-progress.json`, `docs/adaptation/P15_ORACLE_OPERATOR_RUNBOOK.md`. Preimágenes: `artifacts/live/history/p15-notifications-20261118/`.

General original P0–P11:100%; P12 auxiliar:100% en el alcance PostgreSQL/Meta aceptado. Las fases adicionales conservan seguimiento separado: P13 Académico/agentes por programa (parcial,0/4), P14 entrenamiento comercial (plan), P15 correos/notificaciones (en pruebas,0/7), P16 API académica/financiera SIIE (diferida,0/5), P17 TikTok (diferida,0/5), P18 seguridad/ciberseguridad (plan,0/8). OPS-05 no se cierra sin alertas realmente entregadas. Los cortes inferiores conservan su evidencia histórica.

## Comentarios agrupados verificados en producción — 2026-11-18

Despliegue `525dae1` confirmado: 17 hilos por persona/publicación/cuenta; cada comentario conserva Responder y muestra debajo su respuesta de la cuenta conectada. Probado con dos comentarios de juampa1329 en el mismo post y con Juan Pablo en Facebook. Los dos botones eligieron el destinatario correcto sin enviar una respuesta nueva. Notificaciones 10→4 al excluir las respuestas propias. Pasan 189 backend/23 frontend seleccionadas, tipos/lint modificado/build; advertencia previa de bundle grande conservada. Se incluyen límites de ancho del listado y regreso en móvil desde un contexto no recibido.

Evidencia: `artifacts/live/comment-threads-20261118.json`; guía `docs/adaptation/COMMENT_THREADS.md`. General original P0–P11:100%; P12 auxiliar:100% en alcance PostgreSQL/Meta. Pendientes, siempre con nombre y finalidad: P13 Académico/agentes por programa (piloto, parcial 0/4); P14 entrenamiento del agente comercial (plan); P15 correos/notificaciones/HTML (0/7); P16 API académica/financiera SIIE (diferida 0/5); P17 integración TikTok (diferida 0/5); P18 seguridad/2FA/IP/tokens/CAPTCHA/inyecciones (planificada 0/8). Seis mejoras operativas aceptadas como límites siguen abiertas. No se suman pesos por esta mejora. Los cortes inferiores son historia.

## Mejora de Comentarios y comunicación de pendientes — 2026-11-18

Preferencia permanente del propietario: **siempre informar ID, nombre, finalidad y estado de cada fase pendiente**, no sólo su numeración. Resumen vigente: `docs/adaptation/PENDING_PHASES.md` (P13 Académico/agentes por programa; P14 entrenamiento comercial; P15 correos; P16 API SIIE; P17 TikTok; P18 seguridad).

La mejora actual agrupa Comentarios por persona/publicación/cuenta y muestra cada respuesta de CBN debajo del comentario original, con Responder por comentario. Las respuestas propias se excluyen de las notificaciones nuevas. Código y pruebas completos, despliegue pendiente al corte: `tasks/comment-threads-progress.json`, guía `docs/adaptation/COMMENT_THREADS.md`. General original P0–P11:100%; P12 auxiliar:100% en alcance PostgreSQL/Meta; no se añade peso ni se acredita implementación de fases adicionales. Los cortes inferiores son historia.

## Aceptación vigente P11/P12 en PostgreSQL — 2026-11-18

**Roadmap original P0–P11: 100,00%; 279/279 hitos y 56/56 criterios aceptados. P11:100%, 4/4.** El propietario aceptó explícitamente «Aceptar ese alcance y registrar las mejoras pendientes»: PostgreSQL actual publicado, recorridos acordados P1–P10 y los límites operativos entregados. Sólo se aceptan P11.3/P11.close y se completan sus cinco hitos pendientes; P11.1/P11.2 y todos los cierres previos conservan sus alcances. La referencia SQL2019 se mantiene con modificación humana explícita del destino a PostgreSQL; no se recertifica SQL2019 ni se afirma mapa completo DBSIIE.

P12 queda al 100% como agrupación auxiliar de los 18 hitos originales ya resueltos en el alcance PostgreSQL/Meta, sin añadir peso. Copia externa, custodia de clave, RPO/RTO, retención/espacio, alertas entregadas y conciliación adicional DB/archivos siguen abiertos como OPS-01–OPS-06 en `tasks/operations-hardening-backlog.json`. La aceptación no los declara implementados ni cubre pérdida total del servidor. SIIE y TikTok continúan diferidos.

Evidencia: `artifacts/live/p11-postgres-acceptance-20261118.json`; guía `docs/adaptation/P11_P12_LIVE_ACCEPTANCE.md`; manual `docs/adaptation/P11_POSTGRES_OPERATOR_RUNBOOK.md`; preimágenes en `artifacts/live/history/p11-postgres-20261118/`. Restauración aislada 157 tablas/19 archivos y reversión frontend 19866a7→9d8d608 verificadas, misma sesión y ocho consumidores. Las 117 pruebas backend/16 frontend seleccionadas, tipos/lint modificado/build son de esa revisión; no equivalen a replay SQL histórico integral, cuyos veinte archivos ausentes siguen declarados. No modificar releases/checkers/grafos anteriores ni ejecutar seeds/preparadores sobre bases pobladas.

P0–P11:100% cada una; P12 auxiliar:100% en el alcance aceptado; P13 parcial 0/4; P14 plan; P15 correos planificada 0/7; P16 SIIE y P17 TikTok diferidas 0/5 cada una; P18 seguridad planificada 0/8. Las fases adicionales no forman parte del denominador de 56 criterios; no declarar implementadas todas sus capacidades. Los cortes inferiores se conservan como historia y prevalece esta aceptación nueva.

## Ensayo de reversión frontend P11 — 2026-11-18

Con autorización específica del propietario, Coolify desplegó `19866a7` y devolvió el frontend a `9d8d608`; ambas imágenes saludables, ambas interfaces abiertas con la misma sesión. Se conservaron ocho procesos frescos, recibo de 19 archivos, totales de salida y tres inferencias inciertas sin reintento. Backend/base/volumen intactos durante el ensayo. La revisión automática inicial quedó resuelta por la autorización humana; evidencia `artifacts/live/p11-postgres-review-20261118.json` y manual `docs/adaptation/P11_POSTGRES_OPERATOR_RUNBOOK.md`.

La aceptación institucional final sigue pendiente de revisión del alcance PostgreSQL y los riesgos entregados: copias locales, destino externo/custodia de clave aún no validados y sin RPO/RTO institucional fijado. **General 98,04%; P0–P10 100% cada una; P11 72,50%; P12 0% formal; P13 parcial 0/4; P14 plan; P15 0/7; P16/P17 diferidas 0/5 cada una; P18 planificada 0/8.** No se añade crédito por repetir una prueba de reversión ya acreditada históricamente ni se acepta la puesta en servicio de forma implícita. Los cortes inferiores se conservan como historia.

## Revisión operativa P11 en PostgreSQL — 2026-11-18

**General 98,04%; P11 72,50% y 2/4 criterios aceptados.** El propietario aceptó PostgreSQL como destino definitivo; la aceptación institucional final sigue pendiente. El backend/frontend `9d8d608` muestran motor 16.16, ocho procesos y recibo de recuperación verificado. Restauración aislada: 157 tablas y 19 archivos coincidentes; secretos autenticados sin exposición. Usuario de ensayo desactivado, cero sesiones/desafíos elegibles. Copias DB/volumen programadas 03:00/03:05 Bogotá con primeras ejecuciones Success; todavía son locales al servidor, sin destino externo ni custodia de clave validados.

Evidencia: `artifacts/live/p11-postgres-review-20261118.json`; procedimiento y límites: `docs/adaptation/P11_POSTGRES_OPERATOR_RUNBOOK.md`. Pruebas seleccionadas: 117 backend/16 frontend, tipos, lint modificado y build; no recertifican los recibos SQL históricos ausentes. La revisión automática rechazó la reversión temporal de la imagen frontend por requerir autorización específica; no se ejecutó y está pendiente. No cambiar aceptación ni declarar P11/P12 al 100% con este corte.

P0–P10:100% cada una; P11:72,50%; P12:0% aceptación formal; P13 parcial 0/4; P14 plan; P15 correos 0/7; P16 SIIE y P17 TikTok diferidas 0/5 cada una; P18 seguridad planificada 0/8. Los porcentajes y denominadores originales permanecen intactos.

## Fase adicional P18 — 2026-11-18

Por petición del propietario, se añade **P18 · Seguridad y ciberseguridad**, planificada 0/8 unidades aceptadas. Incluye tokens/sesiones, rate limit e IP confiable, 2FA, CAPTCHA, inyecciones, infraestructura y respuesta a incidentes. Ver `docs/adaptation/P18_SECURITY_PLAN.md` y `tasks/p18-security-progress.json`. P15 correos, P16 SIIE y P17 TikTok conservan la nueva numeración. No cambia el porcentaje ni los 56 criterios/279 hitos originales. P11 sigue en revisión operativa; los fallos críticos actuales no se difieren a P18.

## Numeración adicional vigente — 2026-11-18

Por petición del propietario, **P15 es Correos y notificaciones** (planificada, 0/7 unidades y 0% implementación); **SIIE pasa a P16** y **TikTok a P17** (diferidas, 0/5 cada una). Ver `docs/adaptation/P15_EMAIL_NOTIFICATIONS.md` y `tasks/p15-notifications-progress.json`. No cambia el porcentaje original, sus 56 criterios/279 hitos ni la evidencia histórica. P11 sigue en revisión operativa; no se acreditan envíos de correo por crear esta fase.

## Corte vigente: P10 técnica aceptada — 2026-11-18

**General 98,04%; P10 100%, 5/5 criterios.** Se completó el ciclo de entrenamiento con datos exclusivamente ficticios en producción: reproducibilidad, baseline, sombra propia por versión, dos promociones, reversión, deriva y pausa. [Pruebas, uso y límites](P10_LIVE_ACCEPTANCE.md). El pack de ensayo conserva su evidencia con entrenamiento detenido y predicción pausada. P11/P12 institucionales siguen pendientes; los cortes inferiores se conservan como historia.

## Corte vigente: P9 aceptada — 2026-11-18

**General 97,59%; P9 100%, 4/4 criterios.** Cbneistas Bienestar (52067617) conectada y contrastada con Meta: inventario completo, KPIs por período y creatividad real. Borradores locales versionados/revisados, captación ficticia repetida sin duplicación, pausa/reactivación y recuperación de errores verificadas. [Pruebas y límites](P9_META_ADS_MANAGER_REVIEW.md). No se publicaron anuncios ni cambios de gasto. P10/P11 conservan su aceptación pendiente; los apartados previos se mantienen como historia.

# RinovaPlus: avance y pendientes verificables

Corte: 18 de noviembre de 2026. Este registro complementa el checkpoint SQL local del 28 de octubre con la operación actual en https://app.rinovaplus.com. No reemplaza ni modifica releases, grafos, pruebas o recibos históricos.

## Corte posterior: P9 con conexión real a Marketing API

[Revisión P9](P9_META_ADS_MANAGER_REVIEW.md): administrador publicado con KPIs/gráfica/jerarquía y borradores locales. OAuth y descubrimiento de dos cuentas reales comprobados, ads_read concedido y ads_management ausente. Falta la selección de cuenta por el propietario y aceptar consultas/borradores reales. P9 permanece 93,75%; general 97,14%. P4 está aceptada y ya no constituye el bloqueo anterior.

## Corte posterior: P8 cerrada al 100% en Meta

La [revisión P8](P8_META_ACCEPTANCE.md) acredita la única plantilla autorizada, conservación exacta de espera/inscripción/paso tras cambio de contenedor, pausa/reanudación, restauración de versión como borrador y cancelación humana de una copia sin envío. El cupo volvió a 2, la cadencia quedó apagada y el consentimiento de prueba revocado. Las secciones fechadas anteriores conservan el historial; la tabla vigente prevalece.

## Cierre anterior P4/P7 Meta del 18 de noviembre

P4 y P7 quedan aceptados dentro del alcance Meta autorizado. La [evidencia por criterio](../../artifacts/live/p4-p7-acceptance-20261118.json) distingue pruebas reales, simuladas y límites. La imagen de Instagram falló antes de obtener ID por usar el ID de Instagram como Page ID; se corrigió el adaptador, se recuperó el envío con un nuevo registro aceptado y el propietario confirmó recepción. Los dos chats siguen en Humano. No hay envíos pendientes al corte.

La campana bajó 31→0 y conservó los comentarios nuevos para su flujo. Sincronizar comentario marca fuente no disponible sin inventar un evento deleted; el comentario de control sigue accesible. WhatsApp CBN recibió/responde y respeta Humano. El receptor gratuito se conserva separado.

Regresiones del cierre: 242 backend correctas y dos skips de ffmpeg del host; 39 de autoridad HTTP en suites separadas y 71 de interfaz. Ampliación posterior de etiquetas: 70 backend y 72 interfaz; tipos y build correctos. El barrido adicional encontró un fallo preexistente del doble ReadCursor en test_inbox_operations y un error ESLint preexistente de setState síncrono en Workspace.tsx: no se cuentan como checks aprobados ni se modifican para simular éxito. Bundle grande conserva su advertencia.

Los párrafos fechados posteriores de esta página conservan observaciones históricas; este corte y la tabla vigente prevalecen sobre sus pendientes antiguos.

## Qué ya se comprobó en producción

| Área | Evidencia disponible | Límite de la evidencia |
|---|---|---|
| Identidad RinovaPlus | Login, aplicación, iconos y menú plegable publicados en Coolify. | No equivale a auditoría formal de accesibilidad. |
| WhatsApp | CBN conectado/verificado, entrada real, Gemini y recibos enviados/entregados/leídos; silencio en Humano y regreso a IA. Multimedia previa confirmada, incluida animación. | Cuenta anterior conservada; no se envió plantilla institucional de pago. |
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

## Decisión vigente: SIIE pasa a P16

Por instrucción posterior del propietario, la integración DBSIIE queda en **[P16, diferida con base técnica conservada](P16_SIIE_INTEGRATION.md)**. Deja de ser una dependencia obligatoria de P13. Las fichas piloto se pueden revisar manualmente o desde fuentes institucionales. Los registros anteriores sobre la prioridad de la API reflejan la decisión previa; no exigen activarla ahora. No se modifican denominadores ni se acredita una aceptación externa por moverla de fase.

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
| P4 | 100,00% Meta | Aceptación acotada completada: cuentas/OAuth, firma/deduplicación, multimedia, recuperación por canal y conciliación explícita Instagram. TikTok permanece en P17. |
| P5 | 100,00% local | Respuestas personalizadas y silencio Humano posteriores al cambio ya probados en Messenger/Instagram; comentario y sugerencias reales verificados. Falta el piloto con hechos revisados de dos programas y ampliar la prueba de carrera durante inferencia. No se atribuyen estas ampliaciones a la aceptación local antigua. |
| P6 | 100,00% local | Revisar y publicar información real de programas, fuentes y vigencias para el piloto. La función de conocimiento local ya está aceptada. |
| P7 | 100,00% | Catálogo/estados Meta, plantillas reales, audiencia, recibos, respuesta citada, informe/CSV y guardas de reintento aceptados. Revisión de Meta de cada nueva plantilla sigue siendo externa. |
| P8 | 100,00% Meta | Cierre completo revisado: espera persistida tras redeploy, pausa/reanudación, una salida real vía P7, versiones y cancelación Humano sin mensaje. [Evidencia y límites](P8_META_ACCEPTANCE.md). |
| P9 | 100,00% | Meta real, informes, creatividad, borradores revisados, captación repetida y pausa/reactivación aceptados; sin publicación de anuncios. |
| P10 | 100,00% | Ciclo técnico con dataset ficticio, reproducibilidad, evaluación, sombra, promoción, reversión y pausa verificados; no eficacia institucional. |
| P11 | 72,50% | Puesta institucional y recuperación específica, aceptación de alcance y cierres P1–P10. PostgreSQL publicado no acredita por sí solo el criterio original de migración SQL2019/SIIE. |
| P12 | 0,00% de aceptación formal | La infraestructura online YA existe y los despliegues/HTTPS se han comprobado. Falta conciliarla formalmente con los criterios originales, custodios, restauración/RPO/RTO, mapeo académico y aceptación institucional; el 0% es del checkpoint formal, no significa que no exista aplicación publicada. |
| P13 | 0/4 hitos aceptados | Revisar fichas de Enfermería y Software con fuentes manuales o institucionales; aceptar especialista/enrutamiento y piloto real de ambos programas con control humano. SIIE no es dependencia obligatoria: pasa a P16. |
| P14 | Plan pendiente | Definir dataset autorizado, finalidad, variables/resultados, baseline, evaluación temporal y por sujeto, revisión humana y monitoreo. Primero completar P4/P7 y el piloto P13; no habilitar entrenamiento con mensajes por defecto. |
| P15 | Planificada; 0/7 unidades aceptadas | [Correos, notificaciones, plantillas HTML, marca e informes](P15_EMAIL_NOTIFICATIONS.md). |
| P16 | Diferida; 0/5 unidades aceptadas | Integración SIIE: contrato/acceso, dos ofertas reales, sincronización revisada, uso por agentes y operación institucional. Base técnica implementada, conexión no configurada. |
| P17 | Diferida; 0/5 unidades aceptadas | [Todo TikTok en plan independiente](P17_TIKTOK_PLAN.md): documentación/capacidades, app y OAuth, adaptación, pruebas reales y aceptación/reversión. No bloquea la ejecución operativa Meta solicitada; el checkpoint canónico histórico se conserva. |
| P18 | Planificada; 0/8 unidades aceptadas | [Seguridad, tokens, límites por IP, 2FA, CAPTCHA e inyecciones](P18_SECURITY_PLAN.md). |

**Total técnico actualizado: 98,04%, 274/279 hitos y 54/56 criterios aceptados.** Quedan cinco hitos originales de P11. P10.close.m4 aceptado con [aprendizaje técnico ficticio](../../artifacts/live/p10-learning-acceptance-20261118.json). P9.close.m4 aceptado con [consulta real y borradores locales](../../artifacts/live/p9-meta-acceptance-20261118.json). P8.close.m5 aceptado con [prueba real y límites](../../artifacts/live/p8-meta-acceptance-20261118.json). Definición, pesos y denominadores intactos; P12–P18 fuera del denominador. Los veinte artefactos ausentes siguen impidiendo el replay íntegro histórico; cálculo y evidencia nueva se validan por separado.

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

La [consolidación de recuperación Meta](P4_META_ACCEPTANCE_MATRIX.md) añade 40 casos locales por canal y conserva límites de pruebas reales. El adaptador de Instagram solicita `messaging_seen` y entiende los dos formatos documentados; sólo se acreditará una lectura cuando llegue su evento real. El [plan P17](P17_TIKTOK_PLAN.md) reúne todo TikTok, diferido por el propietario.

Orden inmediato: puesta institucional P11 y conciliación P12; piloto de programas P13 con datos revisados y diseño P14. P4/P7/P8/P9 aceptadas en Meta y P10 aceptada en el alcance técnico documentado. P16 y P17 se retoman bajo nueva instrucción.

## Adjuntos y guía del creador estándar de Meta

`fab8b19` está sano en backend y exitoso en frontend. [Pruebas reales de archivos](../../artifacts/live/p7-template-media-20261117.json): PNG, PDF y MP4 neutros se cargaron a Meta desde el creador, se guardaron y se solicitaron las tres plantillas a revisión. Meta aprobó la plantilla de imagen como **UTILITY**; PDF y video siguen **En revisión de Meta** en el último corte. Se probaron también los tres archivos definitivos mediante el upload del número de WhatsApp, guardando revisiones de un único borrador limitado al teléfono de prueba 44. No se activó ni se cambió su consentimiento/cadencia.

El creador estándar admite hasta diez botones con límites y agrupación de Meta, ejemplos del enlace dinámico y codificación de sus valores CRM. La carga inspecciona el archivo, usa credenciales en cabecera, conserva un intento durable y revalida cuenta/credencial antes de efectos. El archivo de campaña queda ligado a su operación confirmada y a esa cuenta. Pasan 209 pruebas backend, 18 frontend, tipos, lint y build institucional. Continúa el aviso de tamaño del bundle; no se afirma una auditoría de rendimiento/móvil.

El [manual de plantillas y mensajes naturales](WHATSAPP_TEMPLATE_OPERATOR_GUIDE.md) distingue solicitudes reales de mensajes generales de programas. Los ejemplos no cambian por sí solos la categoría que decide Meta. OTP, catálogos, carruseles, Flows y formatos exclusivos de Marketing Messages API quedan pendientes de integración/aceptación específicas; no se afirma paridad total con todos los productos de Meta ni se suman hitos nuevos al denominador original.

El cierre de esta sesión añade [el recorrido real Facebook y lectura Instagram](../../artifacts/live/p4-meta-recovery-20261117.json): comentario del propietario a las 20:34:33 Bogotá, Gemini confirmado, respuesta aceptada y observada de vuelta por webhook, un intento. La publicación de origen tiene vista previa real. Se dejó ese comentario en Humano y se rechazó sin proveedor una revisión con su versión vigente. Instagram recibió la prueba nueva manual y notificó `read` firmado/procesado, un intento. Esas pruebas eliminan sus pendientes individuales de la matriz, sin aceptar aún el criterio multicanal completo ni alterar sus pesos.


## Recuperación Meta: corte del 18 de noviembre

[Recibo externo](../../artifacts/live/p4-meta-external-recovery-20261117.json): WhatsApp, Messenger, Facebook e Instagram conservaron eventos firmados durante pausas y recuperaron una sola proyección de cada prueba. Facebook editó y eliminó comentarios propios con sus eventos reales. Las cuentas quedaron conectadas/verificadas y sin envíos pendientes. La mejora fc10635 identifica cada evento de recuperación y conserva permisos del texto; frontend y backend comprobados en Coolify, 140 pruebas backend y 15 frontend correctas.

El borrado externo de Instagram sigue abierto: propietario lo confirmó, Meta rechazó consultar ese objeto y el comentario de control sí fue accesible, pero no se recibió evento de eliminación y el CRM conserva Nuevo/Humano. No se fabricó un estado Eliminado. Próximo ajuste necesario: conciliación explícita de fuente no disponible/cambiada. También faltan el recorrido WhatsApp CBN y escenarios restantes de reintento/resultado incierto antes de aceptación formal. P4.4.m4 enlaza la evidencia parcial nueva y permanece pendiente; 94,23% general y 82,29% P4 se conservan con los mismos pesos.
