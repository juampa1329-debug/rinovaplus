# P19 · Voces y notas de audio con ElevenLabs

Corte: 19 de noviembre de 2026. **Planificada, 0/5 unidades aceptadas; implementación 0%.** Por decisión del propietario, todas las llamadas, agentes durante llamadas, seguimiento telefónico y supervisión de llamadas pasan a P20. Esta división reemplaza el primer borrador conjunto, aún sin aceptar. No cambia los 56 criterios ni los 279 hitos originales.

## Alcance

- Configurar ElevenLabs en IA/APIs, sin Hermes: credencial protegida, catálogo de modelos y voces disponibles según acceso, idioma, parámetros compatibles y consumo.
- Preparar dos o tres voces asignables por escuela y agente. La asignación del agente prevalece sobre la escuela y se conserva en la conversación para evitar cambios arbitrarios.
- Generar una respuesta de audio a partir del contexto y del system prompt del agente, con información revisada y las mismas reglas de IA/Humano del Inbox.
- Escuchar una muestra, revisar el contenido y enviar una nota de voz compatible con WhatsApp. La generación automática y sus límites se configuran explícitamente.
- Registrar generación, envío, fallos y consumo; explicar errores y permitir pausa. La clonación de una persona requiere un recorrido específico, no se presupone por pedir voces distintas.

## Unidades de aceptación

| Unidad | Entregable y prueba |
|---|---|
| P19.1 · Proveedor y catálogo | Credencial protegida, modelos/voces según acceso y errores explicativos. |
| P19.2 · Asignación de voces | Dos o tres perfiles por escuela/agente, prioridad y continuidad comprobadas. |
| P19.3 · Generación contextual | System prompt y hechos revisados; IA/Humano, autorización y cancelación coherentes. |
| P19.4 · Nota de voz | Vista previa, conversión compatible y reproducción real autorizada en WhatsApp. |
| P19.5 · Operación y consumo | Coste observado, límites configurables, pausa, fallos/recuperación y aceptación del piloto. |

Requisitos: proyecto/clave ElevenLabs guardada directamente en el producto, voces elegidas, alcance de generación autorizado y destinatario de prueba. Se prepara después de SIIE y la revisión de IA/APIs contra Scentra. No se generó audio por crear este plan.

Referencia oficial: [ElevenLabs, texto a voz](https://elevenlabs.io/docs/overview/capabilities/text-to-speech). Llamadas: [P20](P20_WHATSAPP_CALLS.md).
