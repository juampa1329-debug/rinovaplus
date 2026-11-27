# Baja global y negociación con beneficios verificados — 27Nov2026

El titular pidió aplicar No contactar y cierre a toda persona que solicite no recibir más mensajes, en sus canales vinculados. También confirmó la homologación universitaria sujeta a los requisitos de cada universidad y pidió presentar becas, prácticas y calendario financiero como argumentos de valor. Los precios, cuotas, fechas, jornadas y demás condiciones académicas de las fichas se conservan.

## Baja entrante y exclusiones

backend/app/institutional/automatic_optout.py reconoce solicitudes expresas mediante backend/app/institutional/contact_intent.py y vuelve a comprobar el mensaje entrante, su ruta externa, integración, identidad, conversación y persona canónica. No depende de inferencia de un proveedor. WhatsApp, Instagram y Messenger aplican la baja después de persistir la ruta y antes de programar una respuesta. Una objeción de precio, rechazo de un programa, pregunta sobre la frase o preferencia por no recibir un formulario/audio no se convierte en baja global.

backend/app/institutional/contact_preference.py comparte el efecto de la baja manual y automática: eventos persistentes de exclusión en todas las identidades de la ficha canónica y sus alias verificados, cierre de sus conversaciones y cancelación de trabajo que no empezó. Se detienen seguimientos CRM y destinatarios de campañas pendientes; los envíos iniciados o de resultado incierto conservan su evidencia y no se reenvían. La etapa académica/comercial no se transforma automáticamente en Cerrado sin matrícula: una persona inscrita también puede pedir dejar de recibir mensajes.

Las solicitudes automáticas llevan prueba de origen y no inventan un operador. Consent.ActorId exige un actor real, por lo que la baja automática se apoya en los eventos opt_out autoritativos; no inserta una revocación fingida. La baja manual conserva su actor, revocación, permiso crm.write, confirmación y operación idempotente. backend/app/institutional/broadcasts.py utiliza la misma exclusión canónica para audiencia y envío, aun cuando quede una fila histórica de consentimiento concedido. backend/app/institutional/whatsapp_gemini.py revalida esa exclusión al generar una respuesta de cualquier canal soportado.

backend/app/institutional/voice_transcripts.py aplica la misma regla después de guardar una transcripción vinculada al mensaje y su audio. La transcripción conserva su autoridad automática, no verificada por una persona. No se generó ni envió un audio nuevo para este ensayo.

La recuperación histórica recorre sólo eventos opt_out de entrada autenticada atribuibles a un mensaje externo, uno por iteración. La búsqueda vacía o fallida queda limitada a una vez por minuto y usa lectura separada de la escritura revalidada. Respeta una autorización posterior y marca fuentes no atribuibles para revisión sin inventar bajas nuevas. backend/app/institutional/channel_workers.py aísla un fallo de esta recuperación para que campañas, despacho y mantenimiento continúen. No se creó otro servicio ni una tarea de IA supervisora.

Cuando no quedan esos eventos, la misma recuperación busca una conversación abierta de una persona que ya figura en la exclusión canónica autoritativa. Revalida esa preferencia bajo escritor antes de completar el cierre, con fuente recorded_no_contact_recovery; no inventa un mensaje entrante ni un operador. Así cubre bajas antiguas registradas por las vías anteriores aunque carezcan del evento de entrada recuperable. La consulta de exclusión es la misma utilizada por las audiencias. Un intento manual durante la revisión devolvió conflicto de revisión global y no se contabiliza como cierre guardado.

El alcance entre canales requiere identidades vinculadas a la misma ficha. No se unen perfiles independientes por nombre o teléfono supuesto. No puede retirarse un mensaje que el proveedor ya haya recibido. La selección histórica acotada no acredita por sí sola que todas las bajas anteriores ya se hayan cerrado.

## Becas y conversación comercial

Lectura nativa de siete ofertas pertinentes: Cocina nocturna, Repostería, Barismo/Bartender, Turismo, Aduanas, Logística y Ventas/Marketing. Las becas de Negocios del Sector Gastronómico y Gestión Ambiental ya constaban como opcionales y del100% de toda la formación complementaria donde aplican. Su diploma exige cursarla y completarla. Ventas/Marketing conserva dos programas obligatorios por una oferta; Barismo/Bartender conserva su oferta conjunta de dos títulos. El Gran Diploma corresponde sólo a Cocina al cursar ambas formaciones indicadas. No se modificó ninguna ficha académica en esta petición.

Se identificó otra omisión: la proyección de hechos para financiación/objeciones retiraba presentation, donde algunas fichas explican la beca. backend/app/modules/agents/skill_policy.py conserva ahora esa presentación cuando contiene beca/doble titulación/Gran Diploma, además de sus planes financieros completos. Las skills sales-enablement y deal-value-calc se actualizaron con su manifiesto de integridad, sin cambiar las37guías disponibles ni sus límites.

La política común obliga a conectar la beca pertinente con la meta, presentar el plazo real entre abono y siguiente cuota como organización financiera y tranquilidad durante las fiestas, y conservar el concepto y la fecha exacta. El8de marzo de2027 se usa sólo donde el plan lo establece; PRE-ICFES y otros planes mantienen sus propias fechas. No se promete ausencia de otros gastos ni se renombra un abono como gratuidad.

Las prácticas remuneradas confirmadas pueden ayudar a recuperar la inversión de la formación completa, sin garantizar importe, plazo o recuperación total ni calcular la carrera multiplicando una tarifa semestral. La política conserva el alcance de prácticas técnicas, sus requisitos, convenios y condiciones. No las atribuye a Inglés, PRE-ICFES o cursos.

backend/app/institutional/cbn_profile.py incorpora la aclaración expresa: sí es posible homologar y cada universidad define requisitos y alcance. Instituciones concretas, convenio vigente, destino, créditos y semestres reconocidos requieren información específica; no se promete homologación automática ni con todas las universidades. Esta regla y su fuente revisada son comunes al estilo y al prompt de Admisiones, sin sustituir las fichas.

## Memoria institucional y trabajo concurrente

Se guardó y publicó nativamente ADN institucional «CBN · Valor formativo, becas, prácticas y continuidad profesional», Publicadov2 y Compartida con asistentes. Contiene esas pautas y los límites de ROI/homologación. Su vigencia editorial predeterminada2027-02-25 exige revisión del contenido, no extiende ninguna promoción ni modifica fechas de pago. backend/app/institutional/knowledge.py filtra estos registros por publicación, vigencia, visibilidad y contexto autorizado.

Se integraron los avances remotos6d99039/6e9c40f y las mejoras de trazabilidad de seguimiento, sin sobrescribirlos. Los tres borradores CRM de beneficios del informe PROGRAM_VALUE_MESSAGING_20261127.md siguen separados de activación y envío. Esta petición no activó plantillas ni campañas ni envió mensajes a clientes. La aclaración posterior de homologación queda en este corte, sin reescribir la evidencia histórica del otro informe.

## Validación y publicación

312 pruebas backend focalizadas pasan: entrada de tres canales, origen vinculado, transcripción, idempotencia, bajas manuales, alias, audiencias, seguimientos, colas, memoria/skills, becas durante financiación, fechas intactas, homologación, guía de formulario, bajas ya registradas e aislamiento de fallos de recuperación. RuffE9/F pasa. Veintiuna pruebas frontend de campañas/edición/No contactar pasan; TypeScript y build pasan. Bundle745,27kB/219,77gzip conserva advertencia de tamaño y Node local22 difiere del rango declarado24.

La integración inicial dejó siete consultas de inscripción por encima del límite40000caracteres. Se condensaron reglas derivadas de beneficios y frases repetidas; todas las fuentes y condiciones permanecen y las pruebas pasan sin ampliar el límite. Diez fallos de fixtures en test_crm_followup_scope.py se reprodujeron idénticos con la revisión anteriorfaf7b6e: dos mocks de descubrimiento y ocho sin contexto de configuración SIIE. No se declara suite completa verde ni un motor PostgreSQL aislado ejecutado.

Commits1b328d9, integración0aa21d2, b226700,8d32eef yce90a43 publicados en deploy/coolify-rinovaplus, sin force ni cambios a main. Publicación y comprobación nativa final se registran en artifacts/live/global-optout-sales-value-20261127.json.

Backendce90a43: despliegueublgwmbyvviy6qu4zhvsfpds, Success4m23, healthy19:28:28UTC y rollout completado19:28:38UTC del27Nov. Frontendce90a43: lqdrcbmmbtkwga3q6nr5kpp2, Success28s. El grafo offline se recompiló con50fuentes documentales y38archivosAST, con hashes y cobertura hastaEOF; las cuatro regresiones de integridad de fuentes pasan.

Una solicitud anterior con último mensaje «No recibir mensajes» figuraba No contactar pero Abierta. Después de publicar ce90a43, una búsqueda nueva del Inbox mostró Cerrada y la ficha volvió a mostrar No contactar; su etapa Seguimiento se conservó. El intento manual anterior había sido rechazado, por lo que este cierre corresponde a la recuperación, no se contabiliza como guardado manual. No hubo mensajes nuevos. Esto verifica un caso previo real, no un evento entrante nuevo ni el cierre de todo el histórico.

Sin DDL, seeds, nuevos servicios, escrituras SIIE, cambios de modelos/respaldos/cupos, consumo de inferencia, nuevas aceptaciones de fases ni mensajes comerciales de prueba. Se conservan P13/P19/P21 iniciales, P22técnico3/5/comercial0/5, P23=0/9 y P24=0/6. El grafo offline incorpora este corte y mantiene el histórico; no contiene datos privados de contactos ni equivale a memoria CRM. No se repiten correo o apagado históricos.
