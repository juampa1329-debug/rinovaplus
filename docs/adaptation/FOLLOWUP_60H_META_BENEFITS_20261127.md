# Seguimiento con cierre a 60 horas y tres campañas de beneficios — 27Nov2026

El titular autorizó enviar los tres mensajes de beneficios a revisión de Meta y preparar sus campañas sin enviar mensajes a los contactos. Después sustituyó el cierre de siete días por un cierre a las 60 horas desde la salida original confirmada. La interrupción se retomó sin duplicar plantillas, campañas ni acciones de envío.

## Secuencia publicada y aplicada

La secuencia general activa es 8 horas → 36 horas → cierre a 60 horas. El activador conserva 480 minutos desde una salida confirmada; las esperas siguientes son 1680 y 1440 minutos. No son 60 horas adicionales después del mensaje de 36 horas. Se retiraron el mensaje de pausa de 60 horas y la espera posterior de siete días. El horario de silencio 21:00–08:00 Bogotá, la cola y la cadencia pueden aplazar el envío efectivo.

La acción nativa `close_at_60_hours` dejó el flujo `CRM · Seguimiento consultivo · 8h, 36h y cierre 60h · CBN` Activo v5/revisión8, con cinco pasos. El activador `CRM · Inactividad de conversación · 8 horas · CBN` quedó Activo v5/revisión9 y enlaza ese flujo v5. Los tres flujos por avance permanecieron Activos v3 y sus activadores v2: interés confirmado, formulario enviado y formulario completado por verificar.

`backend/app/institutional/campaign_closure.py` migra sólo las ejecuciones abiertas compatibles de la versión y época vigentes, conserva su paso, vencimiento, contexto e historial y no reinscribe a las personas. Un mensaje aún sin trabajo nativo puede conservarse; trabajo iniciado, encolado o incierto bloquea la operación. La cola histórica cuyo mensaje de pausa ya se completó queda pausada para revisión, evitando reutilizar un paso completado. No se afirma un recuento global de migración: la interfaz comprobó esperas v5 y un historial con «Cierre (horas): 60 · Versión actual: 5 · Versión anterior: 4 · Paso: 2».

Se conservan autorización reciente, permisos, revisión previa, CAS, operación idempotente y transacción institucional. El cierre del seguimiento no registra una baja. Una respuesta, No contactar, control Humano, avance comercial o autorización inválida detienen el seguimiento según las guardas existentes. La recuperación global de bajas publicada por el trabajo concurrente se conserva.

Estos seguimientos exigen una conversación real iniciada por el contacto. Los importados que nunca respondieron no entran automáticamente. La plantilla CRM de ocho horas requiere la ventana real de 24 horas; los mensajes posteriores usan Meta aprobado y autorización vigente. No se amplió ningún consentimiento ni el límite de 3000/24h con intervalo de 30 segundos.

## Textos de seguimiento comprobados

**8 horas — CRM activo v1, Orientación después de conversar.** «{{nombre}}, retomando lo que conversamos 😊 Elegir una formación que conecte con lo que quieres lograr merece hacerlo con tranquilidad y con información clara. ¿Qué te ayudaría más a decidir: conocer lo que aprenderías, revisar los horarios o mirar cómo empezar con el abono inicial?» La variable usa primer nombre.

**36 horas — Meta aprobado `cbn_crm_seguimiento_duda_v1`, es/Marketing.** «Hola, {{1}} 😊 Soy Juan Pablo, de CBN. A veces las ganas de estudiar están, pero queda una duda por resolver. Podemos revisar juntos la formación y las opciones de pago vigentes para que sepas cómo dar el primer paso, sin comprometerte antes de tener todo claro. ¿Qué te está frenando hoy?» Pie: «CBN · Puedes pedir que pausemos el seguimiento.»

**60 horas — cierre Meta aprobado `cbn_crm_cierre_21d_juan_pablo_v1`, es/Marketing.** «Hola, {{1}}. Mi nombre es Juan Pablo, del equipo de Admisiones de CBN. 🌱

Como no hemos retomado la conversación, este será el último mensaje de este seguimiento para respetar tu tiempo. Tu proyecto de estudiar puede seguir adelante cuando sea el momento para ti.

Si quieres avanzar ahora, puedo ayudarte a revisar la formación y las opciones de pago vigentes. Si prefieres dejarlo para después, puedes volver a escribirnos cuando lo necesites.

¿Te acompaño con el siguiente paso o dejamos aquí el seguimiento?» Pie: «Juan Pablo · CBN | Puedes pedir no recibir mensajes.» Respuestas rápidas: Retomar mi formación / No recibir mensajes. El identificador histórico contiene 21d, pero su texto no promete un plazo; se conserva la aprobación al cambiar sólo el calendario.

Los PDF locales orientaron el tono y los intervalos generales; 8h/36h/cierre60h es la adaptación elegida por el titular, no una cita literal de su calendario.

## Tres mensajes de beneficios aprobados por Meta

Se conservaron íntegros los tres cuerpos revisados por el titular en `docs/adaptation/PROGRAM_VALUE_MESSAGING_20261127.md`, cambiando sólo las variables a formato Meta: nombre→{{1}} y programa→{{2}}. Ejemplos ficticios, cuenta WhatsApp · CBN, idioma es y categoría Marketing. No se añadieron promesas de rentabilidad ni universidades concretas.

Tras los tres envíos autorizados y una sincronización nativa, Meta mostró Aprobada por Meta para `cbn_beneficios_gastronomia_juan_pablo_v1`, `cbn_beneficios_logistica_aduanas_turismo_juan_pablo_v1` y `cbn_beneficios_carreras_tecnicas_juan_pablo_v1`. La confirmación reciente se completó con la credencial guardada, sin leerla ni exportarla y con el segundo campo vacío. No se enviaron pruebas a contactos.

Los tres son alternativas de presentación o reactivación por familia de programa; no son los tres pasos temporales del seguimiento. La gastronomía presenta la beca opcional del sector gastronómico; Logística/Aduanas/Turismo presenta Gestión Ambiental opcional; las demás carreras técnicas destacan formación, financiación, prácticas y continuidad educativa. La homologación posible sigue sujeta a los requisitos de cada universidad conforme a la aclaración vigente del titular.

## Campañas guardadas, sin activar

Se crearon y recargaron tres Borradores v1, con los nombres «Beneficios · Gastronomía · Juan Pablo · Revisión previa», «Beneficios · Logística, Aduanas y Turismo · Juan Pablo · Revisión previa» y «Beneficios · Carreras técnicas sin beca · Juan Pablo · Revisión previa». Cada una enlaza su nueva plantilla Meta, cuenta CBN, primer nombre y programa desde CRM; etapa tras recibo confirmado: Seguimiento. No tienen fecha programada.

Gastronomía selecciona Cocina, Repostería y Barismo/Bartender, incluyendo las dos entradas nativas distintas de Cocina. El segundo borrador selecciona Logística, Aduanas y Turismo. El tercero selecciona las once familias técnicas restantes, incluyendo entradas nativas repetidas con IDs distintos; excluye Inglés, PRE-ICFES, gastronomía y los tres programas ambientales. No se fusionaron IDs por etiqueta.

Los tres filtran Nuevo, Calificación, Programa definido, Dudas y objeciones y Seguimiento; no Inscripción, Matriculado ni Propuesta y financiación. Las exclusiones canónicas de No contactar, Humano, falta de consentimiento, duplicados y avance comercial se conservan. Los filtros representan candidatos: no se ejecutó un recuento exhaustivo ni se habilitaron destinatarios. La relectura comprobó los tres Borradores v1 y «Sin destinatarios preparados»; cero nuevas activaciones o preparaciones. Las campañas activas previas continúan su trabajo autorizado, por lo que no se afirma cero envíos globales durante este intervalo.

## Publicación, validación y límites

Implementación `67f3991`, integrada con producción concurrente hasta `fdd0017` en `54c97c5` y publicada en ambas ramas de trabajo/producción, main intacto. Backend Coolify `2ipgm7tpnnsydiycsgmjiuuh`: contenedor healthy y Rolling update completed, 4m22. Frontend `okgkbwyq19rlczfhbkom5czs`: Success, 44s. La aplicación recargada mostró el control nuevo y persistió flujo/activador v5.

Pasaron 187 pruebas backend focalizadas después de integrar producción y 20 frontend; TypeScript, ESLint de archivos cambiados, Ruff E9/F y build institucional pasaron. Bundle 1219,11kB/352,87gzip conserva aviso histórico. No se afirma suite completa verde, entrega de nuevos seguimientos ni resolución universal de contención. La prueba nativa acredita configuración e historial, no ejecución futura exacta de los tres plazos.

Sin DDL, seeds, servicios nuevos, cambios de modelos, escrituras SIIE ni nuevas aceptaciones P22/P23/P24. Evidencia agregada sin datos nominales: `artifacts/live/followup-60h-meta-benefits-20261127.json`. El grafo de continuidad incorpora este corte y conserva sus fuentes históricas.
