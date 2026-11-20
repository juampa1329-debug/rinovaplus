# P21 · Catálogos, pruebas y respaldo de lenguaje

Corte de implementación: 20 de noviembre de 2026. Fase nueva, con aceptación
independiente de P13 (calidad comercial) y P19 (voz). No modifica los pesos ni
denominadores del roadmap original.

## Referencia de Scentra

Se revisaron `H:/saas-version/backend/app_saas/ai_gateway/service.py`,
`ai_agent/service.py` y `frontend/src/AiAgentsPanel.jsx`: cadena ordenada de
proveedores, prioridad por agente y registro del modelo/proveedor que respondió.
RinovaPlus conserva esa idea y añade controles propios de incertidumbre,
credenciales, presupuesto, contexto y control IA/Humano. No se copian tenant,
billing, claves, datos privados ni un bucle que reintente cualquier excepción.

## Recorridos implementados

- **Simulador de agentes:** proveedor/modelo temporal desde catálogo autenticado
  de OpenRouter, con agrupación por empresa/familia. Conserva las skills, fuentes
  y límites. No publica el cambio, crea agentes ni envía mensajes al contacto.
  Las tarifas se obtienen del catálogo, incluidas tarifas cero; requiere JSON y
  temperatura compatibles. El contexto previo continúa disponible sin inferencia.
- **Mensajes de WhatsApp, Messenger e Instagram y comentarios automáticos:**
  Ajustes → Inteligencia artificial → Modelos de respaldo. Hasta tres alternativas
  ordenadas Gemini/OpenRouter. Se ejecutan sólo si están habilitadas y la ruta
  principal rechaza por modelo inexistente, límite, conexión no establecida o
  HTTP 503 explícito. No cambia el proveedor principal de los agentes.
- **Agentes y Asistente:** conservan sus rutas explícitas existentes; usan la
  misma clasificación segura de fallos. Los agentes tienen sus tarifas de
  respaldo propias. La lista institucional de mensajes/comentarios no sustituye
  silenciosamente esas rutas del simulador.

La compatibilidad es de tarea, no una promesa de igual calidad comercial:
catálogo disponible, entrada/salida de texto, JSON, temperatura, contexto
suficiente y salida completa. Sólo se eligen alternativas revisadas; no se usa
el primer modelo encontrado ni se asciende automáticamente a uno de pago.

## Consumo y seguridad

Cada alternativa consulta el catálogo actual y reserva tokens/USD antes de su
único POST. El principal mantiene su reserva conservadora. En OpenRouter, los
topes cero admiten sólo tarifas gratuitas; un incremento de precio, coste fijo
por solicitud o metadatos ausentes impide inferir. En Gemini los topes son los
máximos revisados por el operador. El formato, contexto y límites se comprueban
antes de reservar. El cambio de credencial, revisión, época, historial o modo
Humano cancela la operación. El guardado que activa una política nueva exige
confirmación reciente de identidad.

Los timeouts de lectura, respuesta truncada/incorrecta, fallo de protocolo,
HTTP 502/504 y resultados inciertos no provocan otra inferencia automática.
Las respuestas incompletas no se publican. Un rechazo de autenticación no se
oculta usando otra credencial. Si todas las alternativas fallan, se conserva el
error y su traza; no se genera una respuesta de bienvenida inventada.

La lista contiene hasta tres alternativas y tiene 35 segundos de presupuesto
adicional total. No hay un circuito distribuido ni monitor proactivo de salud:
la disponibilidad se conoce por catálogo y respuesta real, y puede cambiar.
La interpretación inicial de audio sigue siendo Gemini. Sólo después de su
transcripción se puede usar un respaldo de texto; no se envía audio a un modelo
que no lo admita. ElevenLabs no es un modelo de respaldo de lenguaje.

`ResultMetadata.language_execution` registra proveedor, modelo, intentos,
motivo, latencia y uso de respaldo, sin claves, prompt ni datos del cliente.
La reserva es conservadora y no equivale a una factura del proveedor.

## Validación y aceptación

1. Catálogo autenticado, agrupación, variantes interactivas y prueba aislada de
   OpenRouter con modelo gratuito.
2. Recuperación y límites: rechazo conocido → respaldo; ninguna repetición de
   resultado incierto, ausencia de modelo, precio, capacidad, formato o contexto.
3. Integración de mensajes/comentarios, reserva por intento y guardas de
   credencial, revisión y control Humano.
4. Publicación saludable, revisión de configuración, prueba de respuesta y
   observabilidad operativa por el titular.

Las pruebas locales usan proveedores simulados; no acreditan un fallo inducido
de Gemini en producción. No provocar fallos pagados ni duplicar consultas cuyo
consumo esté por confirmar. La prueba gratuita real y la activación de respaldo
con contexto CRM se registran por separado en el artefacto de esta fase.

### Ensayo controlado solicitado por el titular

En Ajustes → Inteligencia artificial → Simular una caída se puede representar un
503 o 429 del principal sin efectuar su petición ni modificar su configuración.
El respaldo guardado sí se consulta mediante el mismo ejecutor de mensajes y
comentarios, con fuente e historial ficticios. Se comprueban programa, duración,
jornada y continuidad privada, o exclusión de memoria privada en público.
Los casos principal saludable y Humano no hacen consultas externas.

Cada ensayo se registra antes de ejecutar. Consultar resultado utiliza GET;
repetir el mismo identificador recupera el registro, sin generar de nuevo.
No se crea ninguna entrada de Inbox, comentario, SendJob ni ficha CRM. La prueba
es diagnóstico, no una caída real de Gemini. Por solicitud del titular, este
ensayo publicado y satisfactorio puede completar la aceptación técnica inicial
sin esperar una caída natural. Evidencia: `artifacts/live/p21-failover-rehearsal-20261120.json`.

Referencias oficiales: [catálogo de cuenta de OpenRouter](https://openrouter.ai/docs/api/api-reference/models/list-models-filtered-by-user-provider-preferences-privacy-settings-and-guardrails)
y [API Batch separada](https://openrouter.ai/docs/batch-quickstart).

### Respaldos de pago autorizados

El titular permite modelos de pago en OpenRouter. El ensayo requiere marcar su
autorización explícita y aplica un máximo acumulado de USD 0,05 por operación,
calculado con los tokens conservadores y los topes de tarifa guardados antes
de reservar el presupuesto diario o hacer cada POST. Una consulta de resultado
no vuelve a consumir. Los casos saludable/Humano no necesitan esa autorización
porque no consultan al proveedor. Una tarifa de catálogo superior al tope
guardado sigue bloqueada. La reserva no equivale al cargo final del proveedor.

GPT-4.1 mini se revisa como alternativa económica: USD 0,40/M de entrada y
USD 1,60/M de salida según el [catálogo oficial](https://openrouter.ai/openai/gpt-4.1-mini).
La disponibilidad y el precio se validan de nuevo en cada intento.

### Resultado operativo del 20 de noviembre

Gemini se conservó como principal y el titular autorizó GPT-4.1 mini de pago
como respaldo. El principal saludable y Humano pasaron con cero consultas
externas. La caída503 ficticia sí consultó una vez OpenRouter: rechazo402 por
crédito de cuenta/API key insuficiente, sin respuesta y sin reintento. La
reserva USD0,006314 no es cargo confirmado. El intento anterior gratuito429
se conserva como evidencia. P21 continúa en validación; no está al100%.

El titular debe revisar [Credits](https://openrouter.ai/settings/credits) y el
límite de su [API key](https://openrouter.ai/settings/keys). El adaptador no
lee ni expone el cuerpo de error del proveedor, no recarga saldo y no hace
reintentos automáticos por402. Tener tarjeta guardada no acredita saldo.
Referencia: [errores oficiales](https://github.com/OpenRouterTeam/docs/blob/main/api_reference/errors-and-debugging.mdx).
