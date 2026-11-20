# P13 · Atención CBN, contexto institucional y entrega por ideas

Revisión: 19 de noviembre de2026. Mejora solicitada antes de aceptar el piloto P13. No modifica los porcentajes históricos ni acredita nuevas unidades aceptadas.

## Prompts y nombre de atención

El perfil general presenta CBN y orienta sobre sus programas con fuentes revisadas. Los especialistas mantienen un prompt por programa/jornada y las20skills existentes. La presentación repetitiva «asistente virtual» se sustituye por un nombre de atención configurable, inicialmente Juan para el perfil de voz actual. **Agentes → editar → Nombre de atención** permite ajustarlo al cambiar la voz. El nombre vacío hereda el del orientador; una elección explícita del especialista prevalece.

El nombre no representa la identidad de un empleado. El agente no afirma ser humano, no inventa experiencias personales y responde con transparencia si preguntan si es IA. Usa español colombiano profesional y cercano, normalmente40–100palabras para consultas rutinarias, ideas completas y cero a dos emojis pertinentes. Amplía cuando la consulta lo requiere. No saluda ni se presenta en cada turno, no dice «catálogo» al cliente ni afirma que ejecutó una gestión pendiente.

**Agentes → Especialistas por programa → Revisar actualización de prompts y tono CBN** prepara un cambio con versiones y digest. Actualiza el orientador y los prompts generados reconocidos de forma exacta. Los especialistas con instrucciones personalizadas se conservan para revisión individual, incluso si empezaron desde una plantilla anterior. El guardado utiliza el constructor y su historial, conservando modelos, voces, permisos, cuotas y presupuestos. Una revisión desactualizada se rechaza antes de escribir.

**Ajustes → Inteligencia artificial → Preparar prompt y cadencia CBN** sólo prepara el borrador del prompt general y los controles de conversación. Se revisan y publican con Guardar ajustes y la confirmación normal. No sustituye las reglas de comentarios ni las credenciales. Los nuevos modelos y nombres siguen siendo editables por los recorridos existentes.

## Revisión institucional

Se revisaron las páginas públicas oficiales de CBN:

- [La Institución](https://cbn.edu.co/institucion/): institución sin ánimo de lucro de Santa Marta, fundada en1995, formación para el trabajo y el desarrollo humano y técnicos laborales por competencias.
- [Oferta y escuelas](https://cbn.edu.co/): Salud, TIC, Gastronomía, Administración, Logística y Turismo, Centro de Idiomas y extensión. La oferta vigente se confirma en las fichas locales, sin convertir la navegación web en disponibilidad garantizada.
- [Calidad ICONTEC](https://cbn.edu.co/cbn-renueva-certificacion-icontec-16-anos-de-calidad/): publicación institucional de renovación y ampliación de certificaciones y mejora continua. No equivale a acreditar cada programa ni a acreditación universitaria de alta calidad.
- [Empresas y prácticas](https://cbn.edu.co/empresas/): prácticas y acompañamiento con condiciones de postulación y selección. Sin garantía automática de empresa, plaza, remuneración o empleo.

Las páginas publican cifras distintas de convenios, por lo que el contexto no promete un total ni la vigencia de un convenio particular. Tampoco incorpora normas laborales antiguas de esa página como asesoramiento vigente. Las fuentes identifican la institución; precios, cuotas, abonos y vigencias provienen de las fichas financieras revisadas. La información financiera anunciada por el propietario sigue pendiente de entrega y revisión.

Firecrawl CLI se intentó en modo público sin clave; el proveedor rechazó esta IP para el modo gratuito. Se continuó con las páginas oficiales mediante navegación web, sin extraer credenciales de Coolify. La copia editorial acotada está en `backend/app/institutional/cbn_profile.py`; no hay un crawl completo ni una certificación externa del contenido publicado.

## Entrega por partes

La propuesta de cadencia usa3s de espera para agrupar la entrada,1,5s de preparación y3s entre partes. Son valores editables, no una promesa de latencia total: se suman generación, síntesis opcional y respuesta de Meta.

La respuesta de Gemini se valida completa antes de preparar el grupo. Se divide por párrafos/frases como referencia de350caracteres, preservando palabras, enlaces, emojis, importes y condiciones. Hasta6partes; al superar ese número se combinan partes, nunca se descarta el final. Una frase que excede el límite de su canal pasa a revisión sin enviar una respuesta parcial. Una nota de voz permanece como una única nota; no se sintetiza cada fragmento ni se multiplica su cupo.

Cada parte tiene un MessageId, SendJob y recibos propios, ligados a la misma generación y a su entrada. El grupo y sus fechas viven en PostgreSQL y sobreviven al reinicio. La siguiente parte espera confirmación de aceptación de la anterior y el intervalo desde su aceptación real. Un fallo o resultado incierto detiene las posteriores. No se repite automáticamente un POST incierto. El mensaje completo y las partes se conservan para revisar qué llegó.

Antes de cada efecto se vuelve a comprobar cuenta, ventana, fuente, modelo/contexto y época IA/Humano. Pasar a Humano o recibir una entrada nueva invalida las partes pendientes del contexto anterior. El nuevo agente sólo toma como historial hablado las partes aceptadas; los fragmentos todavía en cola o cancelados no se presentan como respuestas ya enviadas. La evaluación comercial se registra una sola vez por entrada. El SLA conserva los tiempos/recibos reales existentes.

## Indicador de escritura

Se solicita la acción oficial al comenzar la generación y durante la pausa entre partes aceptadas. El indicador es opcional: su fallo no convierte una respuesta aceptada en fallo ni provoca reenvío. WhatsApp requiere un ID entrante real y `status=read` junto con `typing_indicator`; esto procesa la entrada, no fabrica un recibo de lectura de una respuesta saliente. Messenger e Instagram usan `sender_action=typing_on`. Meta controla su aparición y caducidad; no se manda un texto ficticio «escribiendo» ni se atribuye una identidad humana al indicador.

Fuentes técnicas: [WhatsApp Message API](https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/whatsapp-business-phone-number/message-api), [Page Messages](https://developers.facebook.com/docs/graph-api/reference/page/messages), [Instagram changelog: Sender Actions](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/changelog/).

Referencia leída: `C:/verane-whatsapp-ai/saas-version/backend/app_saas/ai_agent/service.py`, agrupación y `_maybe_send_typing_indicator`; `workers/dispatch.py`, indicador antes de envío. Se adapta a la institución y al outbox existentes de RinovaPlus; no se introducen tenant, billing ni tablas nuevas.

## Evidencia y cierre

327pruebas backend seleccionadas y44frontend seleccionadas; tipos, ESLint de archivos modificados y build workspace pasan. Ruff funcional de módulos nuevos pasa; no es una recertificación global de estilo Python. Advertencia histórica del bundle conservada. Las pruebas de orden, incertidumbre, límites y SQL traducido usan proveedores/dobles controlados; no acreditan una prueba productiva de todas las carreras ni una recuperación nativa adicional.

Despliegue, prompts realmente publicados y simulación/prueba posterior se registran en `artifacts/live/p13-conversation-style-20261119.json`. P13 continúa0/4unidades aceptadas hasta revisión de las fichas, financieros, continuidad entre programas, memoria y control Humano del piloto. La reproducción de una nota previa no cierra estos criterios.

## Publicación y prueba real

Backend c2dcd4a saludable en Coolify (rla42xbuh9g8mnb1serm4m6w); frontend ft8ovodkobf1asrebzdtlsga Success. Ajustes IA revisión18 guardada y consultada; orientador versión8 y25especialistas versión2,26prompts actualizados, nombre Juan. Cadencia3s/1500ms/3000ms/350caracteres confirmada.

Dos llamadas reales del orientador a Gemini verificaron información institucional y transparencia al preguntar por IA. La nueva simulación de Enfermería no se acepta: primero timeout y después HTTP503 del proveedor. Se añaden avisos específicos de causa/solución y modal compartido en Agentes; no se reintenta automáticamente ni se envían mensajes desde el simulador. La prueba de partes e indicador en teléfono y los financieros del propietario siguen pendientes. P13 conserva0/4unidades aceptadas.

Frontend de avisos7fe7a47 publicado: qih5zrmwcjggcjywqfxmwtcr Success en41s. La tercera simulación Enfermería volvió a503 y el modal mostró la causa/solución específica; se cerró correctamente sin repetir más. La prueba telefónica se solicitó al titular y aún no tiene confirmación en este corte. El backend permanece c2dcd4a saludable; esta actualización documental no cambia su imagen.

## Cita opcional y fallo de la primera prueba telefónica

El titular observó el indicador oficial pero no recibió respuesta. Coolify registró42703 y channel_gemini_worker_retry_required: DATEADD(millisecond,...) no estaba convertido por el adaptador PostgreSQL. La operación venció sin respuesta en cola; no se reenviará a ciegas. Se añade traducción a INTERVAL de milisegundos y rechazo de DATEADD sin convertir. La regresión comprueba ahora la conversión efectiva, además del parser.333backend y84frontend seleccionadas pasan; tipos/lint modificado y build con vite.workspace.config.ts pasan. Publicación y recuperación real pendientes al corte.

Ajustes → Inteligencia artificial → Mensajes y contexto incorpora «Citar el mensaje del cliente sólo en la primera parte de WhatsApp», apagado por defecto. La opción usa context.message_id oficial en la primera parte y no repite la cita en las demás. Funciona también con una única nota de voz. El remitente, conversación, origen interno/externo e índice deben coincidir con la generación confirmada; cambiar a Humano mantiene sus controles. El Inbox muestra el mensaje citado en un bloque acotado, sin consultas adicionales por cada burbuja. No activa citas ni suscripciones nuevas en Messenger/Instagram.

Se recibieron hojas financieras/requisitos del propietario para la oferta conjunta Barismo y Bartender (dos semestres) y dos programas de Salud. El propietario aclaró que la beca del100% es para el programa Negocios del Sector Gastronómico al matricularse en la oferta gastronómica, con posibilidad de tres títulos; no se interpreta como beca para el otro componente ni para empresas. Valores exactos en un borrador local privado, publicación en fichas pendiente. No se escribirá en SIIE ni se borrarán sus registros históricos por esa agrupación comercial.

## Corte de fichas y cita confirmada

691edf0 quedó saludable en Coolify. Se recuperó explícitamente la generación vencida que no tenía respuesta persistida: tres partes leídas; el propietario confirmó cita sólo en la primera y pausas correctas. Ajustes IA revisión19, orientador9,26especialistas/27agentes activos; Barismo y Bartender actualizado como oferta conjunta.

Las26fichas locales tienen requisitos y contenido académico revisado;24contienen planes del propietario. Inglés conserva sus dos fichas sin tarifa hasta confirmar el alcance por nivel/bloque. Se preservan las aclaraciones de becas de carrera completa y dobles titulaciones. No se publica información financiera privada en Git ni se escribe en SIIE. Las mallas antiguas por ciclos no se convierten en una distribución inventada de la oferta conjunta.

Una comparación extensa del simulador excedía el contexto disponible con perfiles completos repetidos. Se conserva íntegra la ficha seleccionada y se eliminan duplicaciones; perfiles adicionales caben completos o quedan expresamente como catálogo sin detalle comercial. No se cortan importes ni condiciones y el fingerprint conserva todas las fuentes. Pasan335backend/85frontend, tipos, lint modificado y build; publicación de este último ajuste y piloto de continuidad pendientes. P13 continúa0/4aceptadas.
