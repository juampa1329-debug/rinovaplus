# P20 · Llamadas de WhatsApp, agentes de voz y supervisión humana

Corte: 19 de noviembre de 2026. **Planificada, 0/8 unidades aceptadas; implementación 0%.** El propietario separa todas las llamadas de P19. P19 conserva voces/notas de audio. No se añade peso al roadmap original ni se acredita una integración de llamadas por la integración de mensajería existente.

## Decisión de producto y número colombiano

Priorizar el número institucional colombiano existente de WhatsApp, entrantes y salientes dentro de WhatsApp, conservando el Inbox, las campañas y sus webhooks. No exigir comprar un número extranjero ni contratar Twilio. Evaluar primero si la cuenta CBN permite ese recorrido. No se compró, portó o importó un número ni se habilitaron llamadas durante esta planificación.

SIP es el protocolo que conecta una central o sistema de voz con otro por internet; no es un número ni obliga a usar Twilio. Para llamadas telefónicas normales, un operador colombiano con línea/SIP compatible puede conectar su numeración al agente. Una SIM por sí sola no proporciona esa conexión. Esa telefonía convencional queda como alternativa por evaluar si el propietario la solicita, fuera del piloto WhatsApp. [SIP de ElevenLabs](https://elevenlabs.io/docs/eleven-agents/phone-numbers/sip-trunking).

## Arquitectura candidata, pendiente de validar

WhatsApp del cliente → número CBN / Meta Calling → conexión de voz compatible → agente ElevenLabs con contexto de RinovaPlus. En paralelo, RinovaPlus conserva el procesamiento de mensajes. Dos candidatos: señalización Graph/Webhooks con un servicio de medios WebRTC, o ruteo SIP compatible. Comparar complejidad, compatibilidad y costes antes de elegir; no dar por compatible el SIP de Meta con ElevenLabs sin un ensayo.

Meta documenta mismo número para mensajes/llamadas y ruteo Graph o SIP. Para producción exige número Cloud API, permiso `whatsapp_business_messaging`, app suscrita a la cuenta, habilitación de llamadas y capacidad de mensajería mínima vigente (la guía consultada indica 2.000 destinatarios únicos diarios). El campo `calls` se suscribe si se utiliza señalización Graph. Confirmar elegibilidad y restricciones de país por cuenta; Colombia no figura entre las exclusiones de salientes de la guía consultada. [Meta Calling](https://developers.facebook.com/documentation/business-messaging/whatsapp/calling).

La conexión sólo llamadas de ElevenLabs con una app propia y su alternativa SIP requieren revisar la propiedad y ruteo de CBN. Su FAQ aún declara limitaciones de importación y handoff; Meta documenta además evolución del modelo de cuentas. Resolver esa diferencia con la cuenta real, sin retirar socios ni cambiar los webhooks actuales como supuesto previo. [ElevenLabs: compatibilidad](https://elevenlabs.io/docs/eleven-agents/whatsapp/troubleshooting), [Meta: separación de soluciones de chat/voz](https://developers.facebook.com/documentation/business-messaging/whatsapp/calling/faq).

## Atención y continuidad CRM

- Entrante: identificar cuenta/contacto, aplicar horarios America/Bogota y disponibilidad; atender con el agente asignado o derivar por el recorrido validado.
- Saliente: seguimiento → condiciones → agenda persistida → permiso vigente de llamada → llamada → agente al contestar. Reutilizar P8 donde proceda; no se exige n8n.
- Cargar contexto autorizado antes de hablar: ficha CRM, programa/escuela, etapa, WhatsApp previo, notas, tareas y compromisos. La voz se toma de P19. Consultar sólo información académica/financiera revisada.
- Guardar resultado, resumen y próximo seguimiento en el contacto correcto. Diferenciar no contestó, ocupado, cancelado, conectado y resultado incierto; no duplicar una llamada por perder el recibo.
- Definir el efecto separado de pasar el chat a Humano sobre llamadas programadas y activas. Una llamada activa sólo cambia de interlocutor después de confirmarse el traspaso; no colgar ni reanudar la IA por un cambio visual.

## Intervenir, transferir y escuchar: capacidades separadas

| Acción solicitada | Requisito de P20 y límite conocido |
|---|---|
| Tomar la llamada como humano | Control explícito con destino humano VoIP/WebRTC o extensión SIP compatible; apagar la voz IA sólo al confirmar la transición. Ensayar que ninguna parte quede sin audio. El handoff de chat no prueba transferencia de voz. |
| Desviar a otro destino | Validar destinos VoIP y ruteo soportado. No ofrecer como disponible transferencia de WhatsApp a una línea móvil/fija convencional: la documentación de WhatsApp Calling de Twilio rechaza conexión a PSTN. SIP no elimina esa restricción. |
| Escuchar audio en vivo | Requisito propio: servicio de medios/conferencia compatible y acceso de supervisor. El monitor de ElevenLabs no entrega audio; no sirve por sí solo para esta función. Evaluar esfuerzo/coste y probar ambos sentidos de audio antes de habilitar el botón. |
| Leer la conversación en vivo | ElevenLabs documenta monitor de eventos/transcripción sólo Enterprise. No equivale a escuchar ni a una grabación disponible después. Validar acceso del plan y retraso real. |
| Participar o cortar | Separar escuchar, tomar, transferir y finalizar; permisos por rol y registro de cada acción. Participación humana dentro del navegador es candidata, no capacidad implementada. |

[Restricción de llamadas WhatsApp/PSTN](https://www.twilio.com/docs/voice/whatsapp-business-calling). [Monitor de ElevenLabs: Enterprise, texto y metadatos, sin audio](https://elevenlabs.io/docs/eleven-agents/guides/realtime-monitoring). [Transferencias ElevenLabs: dependen del transporte](https://elevenlabs.io/docs/eleven-agents/customization/tools/system-tools/transfer-to-number).

Si el transporte/plan no soporta escucha o traspaso, registrar el bloqueo y mostrar la capacidad como no disponible. No declarar P20 al 100% sustituyendo escucha por transcripción o rebajando el requisito sin decisión del propietario.

## Requisitos para ejecutar

1. Inspeccionar de forma acotada WABA, Phone Number ID, app, capacidad y ajustes de llamadas de CBN; comprobar reversión y conservación de mensajes antes de cualquier cambio.
2. Proyecto/clave ElevenLabs con acceso a agentes y voces elegidas en P19. El acceso Enterprise sólo se exige si se elige su monitor; no contratarlo como requisito implícito del piloto.
3. Elegir señalización y servicio de audio. Si SIP: compatibilidad de autenticación, TLS/SRTP, codecs, red y transferencias. Si Graph/WebRTC: receptor de eventos y servicio de medios comprobados; no abrir puertos de SIP/medios en el backend HTTP por defecto.
4. Confirmar facturación habilitada cuando la exija Meta, consumo ElevenLabs/LLM, límites propios y presupuesto del piloto. Reutilizar un número evita exigir otro alquiler; no convierte el agente ni la infraestructura en gratuitos. Obtener permiso vigente del destinatario para salientes y respetar revocación y restricciones del canal.
5. Configurar disponibilidad, horarios, contacto/no contactar, máximo de intentos, destinos humanos y alternativa cuando no haya asesor. No se autoriza llamar a toda la base por crear el plan.
6. Endpoints autenticados de contexto y resultados, firma cuando corresponda, correlación e idempotencia. La clave del proveedor queda en servidor, no en el navegador del supervisor.
7. Control de acceso a escucha/grabación/transcripción, avisos y conservación definidos para el piloto; registro de supervisor y destino. No confundir capacidad de grabar con escucha durante la llamada.
8. Destinatario y guion acotados para probar entrante, saliente, rechazo/no respuesta, cancelación, paso a humano, transferencia, escucha, caída/recuperación y reversión. Validar costes antes del ensayo y pedir sólo la autorización necesaria para efectos concretos.

Propuesta de UI: Comunicaciones → Llamadas, con agenda e historial; ficha CRM → Programar llamada; sesión activa → estado, agente, contexto y controles habilitados según capacidades comprobadas. Reutilizar branding y modales de causa/solución. No mostrar un botón de Escuchar que únicamente abra texto.

## Unidades de aceptación

| Unidad | Entregable y evidencia requerida |
|---|---|
| P20.1 · Cuenta y ruteo | Elegibilidad CBN, número colombiano, transporte, señalización y reversión; mensajería conservada. |
| P20.2 · Entrantes | Cliente llama por WhatsApp y agente atiende; horarios, asignación y errores comprobados. |
| P20.3 · Salientes y seguimiento | Permiso, agenda persistida, agente al contestar, cancelación y ausencia de duplicados. |
| P20.4 · Contexto CRM | Continuidad de WhatsApp/notas/seguimientos y datos revisados del contacto correcto. |
| P20.5 · Atención humana | Tomar/transferir por destino compatible, exclusión de PSTN y prueba de transición de audio. |
| P20.6 · Escucha y supervisión | Audio en vivo de ambas partes, permisos y terminación; transcripción identificada por separado. |
| P20.7 · Resultados | Resumen, estado, tareas, historial y métricas reales; conservación configurada. |
| P20.8 · Operación y coste | Límites, costes, fallos/recuperación, reversión y aceptación del propietario. |

Todas siguen planificadas. Fuentes oficiales consultadas el 19-11-2026; volver a verificar al ejecutar, porque las capacidades, requisitos y planes cambian.
