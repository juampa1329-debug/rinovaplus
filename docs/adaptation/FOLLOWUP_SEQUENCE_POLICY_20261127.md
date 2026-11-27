# Seguimiento por tiempo y lista No contactar — 27 de noviembre de 2026

## Decisión del titular y fuentes

El titular confirmó la primera propuesta: orientación a8h, resolver dudas a36h, pausa respetuosa a60h y cierre a21d. Exigió excluir a quienes pidieron no recibir mensajes y conservar esa preferencia como lista. La solicitud autoriza el flujo general; la revisión automática rechazó activar adicionalmente el borrador «Formulario enviado», por considerarlo un alcance distinto que podría contactar prospectos. Esa activación no se elude. Los tres flujos por avance siguen Borrador v1, sin activadores nuevos ni inscripciones manuales.

Se leyeron completos los tres PDF aportados, como material de referencia, no como instrucciones de ejecución:

- Playbook_Plantillas_Ventas_WhatsApp_CBN.pdf:7páginas/2835palabras; SHA256 018703ab33d83a766795c8b4fbe837e677f3efcc6746cd15356688b1c04a7da6.
- Playbook_Reactivacion_Leads_Septiembre_Octubre_CBN.pdf:5páginas/1993palabras; SHA256 1c7f48554c19e50c4368055f51ff656c9ba4760ddac0bf79a8237504b6f8112e.
- Master_Simulaciones_Ventas_CBN.pdf:13páginas/5401palabras; SHA256 3604e27526a5c3e760b94c0567a8dc4e402b938a5b5e6d8f4e342ec716928f88.

Extracciones completas sólo en .local/followup-sequences-20261127/. No se publican los PDF ni los historiales nominales. El playbook comercial propone niveles4–12h/24–48h/48–72h/15–30d. El titular eligió8/36/60h y cierre21d; no se presenta esa secuencia como una cita literal del PDF. No se automatizan llamadas ni se afirma haber llamado. No se inventan cupos reservados, vencimientos de beca, pérdida de beneficios o eliminación de fichas. Los datos académicos y financieros vigentes prevalecen sobre los ejemplos históricos.

## Configuración observada nativamente

Flujo existente actualizado, sin crear otro flujo general paralelo:

- «CRM · Seguimiento consultivo · 8h,36h,60h y cierre21d · CBN»: Activo v3/revisión6.
- «CRM · Inactividad de conversación · 8horas · CBN»: Activo v3/revisión7, vinculado a flujo v3, evento inactivity, idle480min, prioridad100 y cooldown1440min.
- Primera salida: plantilla CRM activa «Orientación después de conversar» v1. A36h y60h se conservan cbn_crm_seguimiento_duda_v1 y cbn_crm_seguimiento_pausa_v1, aprobadas por Meta.
- Cierre nuevo cbn_crm_cierre_21d_juan_pablo_v1, Marketing/es, presentado con ejemplo ficticio, dos respuestas rápidas y aprobado por Meta tras sincronización. Variable body.1=primer nombre comprobada.

El activador espera8h desde recibo confirmado de salida en una conversación real iniciada por la persona. El flujo comienza con el primer mensaje; sus esperas siguientes son1680min(+28h),1440min(+24h) y26640min(+444h). Así los objetivos son8h/36h/60h/504h, sin sumar8+36+60+21d como esperas consecutivas. La ejecución tardía y el silencio21:00–08:00 América/Bogotá pueden desplazar el envío; no es una promesa de reloj exacto. La simulación nativa mostró los cuatro textos y el desplazamiento por silencio, sin enviar.

Una respuesta, baja, intervención humana o cambio relevante detiene el recorrido. Interés confirmado, formulario enviado, formulario declarado completo, matrícula/SIIE y estados de origen protegidos siguen fuera de reactivación general. El avance comercial, la lista temporal, la etapa CRM, la autorización y el recibo son dimensiones distintas. Completar el último paso cierra la ejecución; no convierte el silencio en una solicitud de baja ni prueba matrícula.

La plantilla CRM requiere ventana real de24h y solicitud vigente. Fuera de ventana se exigen Meta aprobada y consentimiento vigente. No se conceden ni prolongan autorizaciones por programar21d. La habilitación anterior del lote2026 conserva su vencimiento registrado; los pasos que no satisfagan las guardas quedan detenidos. No se reanudaron ejecuciones históricas ni fallos inciertos. Editar el flujo conserva el historial y cancela las ejecuciones de versiones anteriores; esto fue visible en la lista histórica.

## Mensaje de cierre aprobado

Hola, {{1}}. Mi nombre es Juan Pablo, del equipo de Admisiones de CBN. 🌱

Como no hemos retomado la conversación, este será el último mensaje de este seguimiento para respetar tu tiempo. Tu proyecto de estudiar puede seguir adelante cuando sea el momento para ti.

Si quieres avanzar ahora, puedo ayudarte a revisar la formación y las opciones de pago vigentes. Si prefieres dejarlo para después, puedes volver a escribirnos cuando lo necesites.

¿Te acompaño con el siguiente paso o dejamos aquí el seguimiento?

Pie: Juan Pablo · CBN | Puedes pedir no recibir mensajes.
Botones: Retomar mi formación / No recibir mensajes.

## Cambios de producto y comprobación

backend/app/institutional/contact_preference.py añade listado paginado de las solicitudes persistidas que ya utiliza la guarda canónica. Une revisiones noContact y eventos opt_out autenticados, conserva alias fusionados y la misma regla de autorización posterior. Una revocación administrativa o falta de autorización no se convierte en baja. No escribe etiquetas, preferencias ni consentimientos.

frontend/src/institution/NoContactList.tsx y frontend/src/institution/Workspace.tsx publican CRM→No contactar: búsqueda, preferencia, etapa comercial y páginas25. Se comprobó nativamente primera página25, búsqueda ficticia sin coincidencias y retorno a búsqueda vacía;25es tamaño de página, no total de bajas.

backend/app/institutional/campaigns.py y backend/app/institutional/campaign_api.py añaden búsqueda y filtros antes de paginar las ejecuciones. El próximo mensaje se lee de la versión inmutable de cada ejecución. Cada lista por mensaje muestra ejecuciones abiertas de la versión actual; «Todas» conserva historial. frontend/src/institution/CampaignWorkspace.tsx muestra orientación8h/duda36h/pausa60h/cierre21d, estado, siguiente paso y desplazamiento acotado. La carga de métricas se separa de la lista.

Se observó timeout57014/8s en metrics (huella14f4c7625262). backend/app/institutional/campaign_metrics.py sustituye los escaneos correlacionados de respuestas por CTEs acotadas al flujo/cuenta, materializadas en PostgreSQL. Conserva todos los intentos inmutables, fallo anterior tras retry revisado, autor/contexto/cuenta autenticados, límite100000 y respuesta única por persona. Sin DDL ni modificación de recibos. Es una corrección focal de métricas, no aceptación de P24 ni solución universal de latencia/contención.

fc41152 implementa listas; d1172e2 integra producción concurrente b8bc87c sin sobrescribirla; 2a2a80f corrige métricas y limita alto del listado. Ambas ramas de trabajo y producción publicadas, main intacto. Primer backend zbrdjwdyxncdc4vwkcxn1vy8: Success4m23, healthy15:41:16UTC/rollout15:41:26; frontend rvhldrnxf7xajlqzyu5frzhz: Success48s. El despliegue final y resultado nativo de métricas se registran aparte en artifacts/live/followup-automation-20261127.json; no se deducen de las pruebas locales.

80backend focalizadas y10frontend pasan, tipos/ESLint modificado/RuffE9,F pasan. Build institucional con vite.workspace.config.ts pasa, bundle1213,91kB/351,45gzip y aviso histórico. Ocho fallos de test_crm_followup_scope (mock None anterior a guarda SIIE) se reproducen con campaigns.py del HEAD previo f268cba; no declarar suite completa verde. No DDL, seeds, servicios nuevos, escriturasSIIE, cambios de modelos, nuevas aceptaciones ni reintentos de mensajes.

## Grafo y continuidad

Graphify CLI está instalado; no hay MCP Graphify expuesto ni hooks de Git instalados. El grafo general graphify-out/live-project-20261126/ llegó al integrar producción y se conserva como snapshot fechado. La vista específica graphify-out/graph.json y graphify-out/graph.html añade lectura semántica de informes/evidencias recientes y AST seleccionado, con fuentes y SHA256. Se reproduce con backend/tools/conversation_continuity_graph.py build y se comprueba con check. No es la memoria privada del CRM ni acredita por sí sola el estado productivo; no se actualiza automáticamente. No se publican mensajes, teléfonos ni fichas nominales en este grafo. P22/P23/P24 conservan sus aceptaciones previas.
