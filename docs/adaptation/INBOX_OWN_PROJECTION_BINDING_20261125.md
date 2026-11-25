# Inbox · Descarte tras guardar el interés del cliente

## Incidencia y atención

El 25 de noviembre, un turno de WhatsApp generó dos partes a las 11:44 de Bogotá. Ambas quedaron descartadas: primera `gemini_whatsapp_model_changed`, siguiente `gemini_whatsapp_previous_part_not_sent`, cero intentos de envío. La generación de OpenRouter/Sonnet había terminado correctamente. No fue un rechazo de WhatsApp, falta de saldo ni la espera de almacenamiento corregida antes.

La ficha confirmó que el interés declarado se guardó desde ese mismo mensaje. El cliente venía de una orientación de masterclass y eligió un programa con dos jornadas, aún por aclarar. El diagnóstico de generación mostraba actualización propia de la ficha dentro de la transacción.

Se envió una orientación nueva, sin relanzar la cola descartada. WhatsApp la confirmó Entregada y después Leída, a las 11:56 de Bogotá. Se restauró IA y se comprobó el control desactivado para Humano. El historial anterior se conserva.

## Causa y corrección

La selección del agente incluye un digest del contexto comercial, además de identidad de agente, modelo y credencial. Al guardar el interés declarado, deja de aplicar la sugerencia anterior de masterclass. El digest cambia aunque el agente y la configuración efectiva sean los mismos.

La transacción ya actualizaba `contextBinding` después de su propia proyección CRM, pero dejaba `modelBinding` con el digest previo. El guardián de la primera parte rechazaba esa diferencia como un cambio de modelo.

Después de guardar la memoria/ficha, y dentro de la misma transacción protegida, se vuelve a resolver la selección. Sólo se conserva el nuevo digest si siguen idénticos el agente, modelo, credencial y **toda** la configuración efectiva. Se guardan juntos ambos bindings y un indicador operativo sin datos personales. Un cambio posterior sigue invalidando la salida.

Se conservan las comprobaciones de cuenta, identidad, último mensaje, modo Humano, época, ventana del canal, texto exacto, referencia de cita y orden/aceptación de fragmentos. No se reproducen resultados inciertos ni colas históricas. El mismo código protege WhatsApp, Messenger e Instagram.

El diagnóstico ahora distingue un cambio de selección/configuración de un problema de canal o saldo, y muestra cuándo se actualizó el binding por una proyección propia.

## Pruebas

- Regresión antes del cambio: fallo reproducido en `dispatch_authorized` con el mismo `gemini_whatsapp_model_changed` después de una proyección propia.
- 180 pruebas backend focalizadas pasan: generación principal/respaldo, proyección y primer despacho; rechazo de cambio real de agente/modelo/credencial/configuración; texto/contexto alterados; Humano, orden de fragmentos y cobertura de turnos. Una prueba usa el enrutamiento comercial real para demostrar que retirar la orientación de masterclass cambia el digest, sin cambiar agente ni configuración.
- 15 pruebas frontend focalizadas, tipos, ESLint, Ruff y build institucional pasan. Permanece el aviso histórico de bundle grande. No se declara la suite completa verde.

## Publicación y límites

Corrección preparada para publicar; el cierre con referencia de imagen y comprobación operativa se registra en la evidencia `artifacts/live/inbox-own-projection-binding-20261125.json`.

Las pruebas locales no acreditan entrega perpetua ni todos los mensajes históricos atendidos. La orientación manual sí tiene recibo real. No se cambian modelos activos, claves, límites, consentimientos ni fases aceptadas. Sin DDL, seeds, servicios nuevos, escrituras SIIE ni nuevas pruebas pagadas de LLM.
