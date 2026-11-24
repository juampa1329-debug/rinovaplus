# Seguimiento de Logística y Aduanas — 23/11/2026

El titular autoriza las dos campañas con sus plantillas Meta respectivas y confirma que las políticas de preinscripción incluían autorización de seguimiento WhatsApp. Esta declaración se registra como evidencia del titular; no se afirma haber inspeccionado el texto de las políticas ni que el Excel incluyera un opt-in.

## Preparación

Se revisaron 50 registros fuente: un teléfono inválido y tres registros anteriores que comparten número quedan fuera. Se conserva la preinscripción más reciente por número, sin fusionar personas. El contraste nativo de 46 seleccionados reconoció 35 importados e incorporó ocho fichas adicionales; tres posibles coincidencias con CRM quedan para revisión. Cohorte prevista: 32 Logística y 11 Aduanas, sujeta a las guardas de canal y consentimiento.

La nueva vinculación explícita trabaja en lotes de diez y exige permisos de campañas, CRM e Inbox, reautenticación, evidencia y vigencia máxima de dos días. Conserva la autorización nativa con CAS e idempotencia. Una revocación anterior, otro canal o una conversación real/intervención humana exigen revisión individual. No crea entradas recibidas ni verifica la existencia del destinatario en Meta. Reutiliza la conversación vacía de importación y habilita IA mediante el control nativo con nuevo epoch sólo si nunca hubo mensajes o intervención humana. Esta preparación no envía mensajes.

El titular amplía después la habilitación a todos los preinscritos del CRM, para completar la revisión de una vez. El botón nativo carga hasta 5.000 fichas con fuente de importación, teléfono válido y programa declarado, y procesa automáticamente grupos de diez con una sola evidencia. Conserva autorizaciones vigentes y pone revocaciones/conflictos de canal/historial en revisión sin detener las demás fichas. Esto no amplía el envío: sólo se activarán Logística y Aduanas. Las fichas originalmente dudosas que no fueron importadas siguen fuera del CRM.

## Etapa después del envío

La campaña permite elegir una etapa activa del CRM con permiso `crm.write`. La etapa se fija en la instantánea de destinatarios. Sólo un recibo auténtico Meta `sent`, `delivered` o `read` dispara la actualización; `accepted`, cola, preparación, fallo e incertidumbre no lo hacen. La operación usa el registro nativo de intentos, una clave idempotente por destinatario y auditoría compartida. Un CAS conserva cambios de etapa posteriores del asesor y no altera contactos fusionados. Si se revoca la autoridad de campaña, el recibo se conserva sin ejecutar el cambio CRM.

Para estas dos campañas se configurará **Seguimiento**. El valor predeterminado de las demás campañas conserva la etapa actual.

## Validación previa a publicar

154 pruebas backend seleccionadas y 25 frontend pasan; TypeScript, ESLint de archivos cambiados, Ruff de módulos/pruebas nuevos y workspace build pasan. Se conserva la advertencia histórica de bundle. Los archivos backend heredados contienen avisos previos de formato fuera del cambio. Sin DDL, seeds, servicios nuevos, escrituras SIIE ni cambios de modelos.

El primer despliegue `6cf1b0a` estuvo saludable, pero la vinculación fue rechazada por la restricción nativa de una conversación por contacto (`23505`); cero mensajes. Un diagnóstico transaccional se revirtió íntegramente. La corrección reutiliza la conversación vacía y agrega regresión para impedir una segunda inserción. Se conserva el intento fallido, sin atribuirle vinculación ni consentimiento completados.

Publicación, vinculación efectiva, activación y resultados reales pendientes en este corte. Los recibos nominales permanecen únicamente en `.local/preinscritos-import/logistica-aduanas/`.

## Habilitación general realizada

`66e885d` publicado en Coolify `4jprj8piliechjaho2pmyaap`, saludable/Running, 4m18s. La prueba transaccional corregida vinculó diez fichas reales y revirtió todo, sin envío. Después, el proceso nativo general completó 772 fichas: 771 habilitadas y una para revisión. Las evidencias son declaraciones del titular sobre políticas de preinscripción; éste añade posteriormente que la web informa tratamiento de datos y contacto por los medios institucionales. No se presenta como inspección independiente del texto web. Registro de este seguimiento hasta 24/11/2026 23:59, hora mostrada por el navegador. Sin activación automática de las otras campañas.

La consulta de consentimiento tenía un límite histórico de 500 identidades y falló al refrescar después de completar la habilitación. No fue un fallo de los registros ya confirmados y no se repitieron las escrituras. Por petición expresa se añade búsqueda por nombre/número y páginas de cien, con selección y autorización individual conservadas. La interfaz distingue la actualización fallida del listado de un lote pendiente de guardar. 155 pruebas backend y 26 frontend pasan; tipos, lint y build se verifican para este ajuste.

Revisión de Excel pendiente: 193 registros (201 iniciales menos ocho resueltos), separada del único caso ya importado que no se habilitó. Envíos y cambio efectivo de etapa todavía pendientes.

## Activación y bloqueo de reserva comprobado

Activadas únicamente Aduanas (11) y Logística (32), con sus plantillas Meta aprobadas y filtro exacto de referencias de importación. Vistas previas 11/11 y 32/32 elegibles; etapa tras envío confirmado Seguimiento. Cuenta CBN habilitada con límite 100/24h e intervalo 30 segundos; todas las demás campañas comerciales siguen Borrador. Se observaron cuatro entregas reales de Aduanas, incluida una lectura, antes de una espera prolongada. Los 43 destinatarios tienen trabajo nativo en cola; esto no acredita 43 POST a Meta. Un destinatario aún pendiente conserva Calificación en CRM.

Diagnóstico transaccional sin llamada a proveedor: `ready` pasa, pero `reserve` intenta insertar de nuevo la reserva ya liberada de una operación que volvió a cola por `broadcast_cadence_wait`; PostgreSQL rechaza `23505`. Esto bloquea el despacho de los trabajos siguientes. No se atribuye a saldo o rechazo de Meta. La prueba se revierte y no repite envíos aceptados.

La corrección reutiliza la reserva sólo si está liberada, corresponde a la misma integración/operación y el trabajo permanece en cola, sin ID externo ni lease; la operación del proveedor debe estar pendiente y confirmar exactamente una espera conocida previa a I/O (`broadcast_cadence_wait` o `campaign_quiet_or_not_due`). Reservas comprometidas, inciertas, activas o errores desconocidos requieren revisión. Se conservan presupuestos, contadores de cuota y día UTC; no se crea otra operación ni se relanza un resultado incierto. 310 pruebas backend seleccionadas y Ruff de módulo/pruebas nuevos pasan. Publicación y recuperación efectiva pendientes en este corte.

Se conservan los cambios concurrentes de `76b1f49` sobre agrupación de preguntas y respuestas citadas del Inbox; no se modifican sus asignaciones o modelos.

## Recuperación efectiva y revisión de bajas

`428852b` publicado saludable en `gpuovtst0oyuveqtzbhm0l69`, 4m19s. El diagnóstico de la corrección devolvió `RESERVE_OK` sobre la reserva real y revirtió toda la prueba, sin I/O al proveedor. El despachador continuó después por su recorrido normal, sin replay manual. Aduanas alcanzó 11 entregas; el CRM mostró un caso real Calificación antes del envío y Seguimiento después. Se observó recuperación posterior de Logística. El despliegue concurrente `08d0a5f` conserva la corrección y quedó saludable en `ulhl5wq7sdkikpk88ukn6zvs`.

La búsqueda por nombre y por fragmento del teléfono, además del caso sin coincidencias, quedó verificada en vivo. `b222f02` aclara en el informe que una espera de cadencia conserva el mensaje en cola y no necesita reintento; interfaz actualizada observada. Listados nominales de 193 pendientes de Excel y del único conflicto de vinculación guardados sólo en `.local/`.

Se añade reconocimiento nativo del texto exacto «No recibir mensajes» del botón de las plantillas, como evento autenticado `opt_out` de esa identidad/mensaje. Una habilitación en bloque no puede sustituir una baja previa, incluso si la autorización antigua expiró. La renovación individual con evidencia nueva conserva su recorrido nativo. 369 pruebas backend seleccionadas pasan; la baja real no se simula escribiendo como un prospecto ni enviando otro mensaje.

Durante Logística caducó la verificación horaria de las plantillas (`broadcast_template_refresh_required`). Se renovó el catálogo mediante el botón nativo; ambas plantillas conservaron aprobación y texto y la cola continuó sin editar las campañas ni repetir envíos aceptados. La recuperación de cuota usa como prueba el resultado pendiente registrado por la operación del proveedor, de modo que una pausa posterior de validación de plantilla no borre la evidencia de espera anterior sin I/O. Se mantienen estado en cola, ausencia de ID externo/lease y reserva liberada; una operación incierta o comprometida no pasa. Regresión añadida: 370 backend y 26 frontend pasan; tipos/lint/build y Ruff nuevos comprobados. La interfaz explica la actualización de plantilla y la revisión de reserva con acciones concretas.

## Cierre operativo comprobado

El código `ca1793b` quedó saludable en Coolify `ob0mmmccse7nqmfzufqbkssm` (inicio 24/11/2026 00:56:04 UTC). Las dos campañas muestran **Completada**. Corte de gráficos y CSV nativos: 24/11/2026 01:21:59 UTC (23/11, 20:21:59 Bogotá). Logística: 32 destinatarios, 32 entregados, seis leídos, seis respuestas atribuidas y cero fallidos. Aduanas: 11 destinatarios, 11 entregados, cuatro leídos, dos respuestas atribuidas y cero fallidos. Los CSV confirman recibo de entrega para los 43, diez lecturas y ocho destinatarios con respuesta atribuida. No quedan destinatarios pendientes, enviándose o inciertos. Se conservaron las 18 campañas restantes en Borrador, sin ampliar el público ni repetir manualmente las salidas aceptadas.

Se verificaron siete conversaciones con respuesta real en el listado de Inbox, sin abrirlas ni marcar las entradas como leídas. El octavo destinatario con respuesta atribuida aparece en el corte posterior del informe/CSV; no se acredita una octava comprobación individual del Inbox ni una respuesta automática de IA. Una de las siete entradas comprobadas solicitó «No recibir mensajes»; se registró la revocación nativa con esa evidencia y se comprobó Estado: Revocado. El resultado inicial de habilitación sigue siendo 771 de 772; una baja posterior se conserva y no se cuenta como caso dudoso. La vigencia registrada de este seguimiento termina el 24/11/2026 a las 23:59 Bogotá (`2026-11-25T04:59:00Z`), sin prometer habilitación perpetua.

El cambio efectivo a Seguimiento se comprobó sobre una ficha real tras el recibo Meta. La búsqueda de consentimiento funciona por nombre y fragmento del número, con páginas de cien. La cuota de cuenta permanece en 100/24h con intervalo de 30 segundos. No se cambian modelos, voces ni agentes, y no se acredita conversión comercial.

Permanecen **193 registros fuente para revisión**, más **una ficha importada con conflicto de vinculación de número**. Son conjuntos separados. En los 193, 154 tienen teléfono o correo compartido entre nombres distintos; hay además teléfonos inválidos, múltiples datos de contacto, duplicados y etapas sin equivalencia segura. Los motivos se superponen; no deben sumarse como personas independientes. Los listados nominales y capturas permanecen exclusivamente en `.local/`; el artefacto publicado contiene sólo agregados. No se envió a estos casos por suponer que un número identifica una persona.

Lectura significa recibo Meta, sin una métrica adicional independiente de apertura/visualización. Las respuestas atribuidas requieren referencia al mensaje de campaña; no se presenta el clic externo como métrica medida. La entrega acredita que Meta permitió estos envíos, sin afirmar un saldo global ni un método de pago que no se haya inspeccionado.

Validación final: 370 pruebas backend seleccionadas y 26 frontend pasan; TypeScript, ESLint de archivos cambiados, Ruff de módulos/pruebas nuevos y workspace build comprobados. La restauración final de saltos de línea de InboxDelivery no cambia su código; frente al padre anterior a `ca1793b` conserva únicamente las diez líneas de orientación añadidas. Sin DDL, seeds, servicios nuevos ni escrituras SIIE. Las aceptaciones de otras fases y P22 permanecen intactas.
