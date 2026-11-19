# P19 · Voces y notas de audio con ElevenLabs

Corte: 19 de noviembre de 2026. **En implementación y validación, 2/5 unidades aceptadas.** Por decisión del propietario, todas las llamadas, agentes durante llamadas, seguimiento telefónico y supervisión de llamadas pasan a P20. Esta división reemplaza el primer borrador conjunto, aún sin aceptar. No cambia los 56 criterios ni los 279 hitos originales.

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

## Implementación del 19-11

El propietario autorizó iniciar P19 sin esperar el arreglo del productor SIIE y guardó la clave de ElevenLabs. Se implementaron catálogo, perfiles, cuota durable por conversación, cuatro modos de voz, duración estimada/real sin recorte y muestras privadas. Pruebas locales seleccionadas: 130 backend y 15 frontend; dos pruebas de multimedia omitidas por su entorno. Aceptación real pendiente: catálogo Juampa, envío al 44, reproducción, límite y Humano. Manual: [operación P19](P19_VOICE_OPERATOR_RUNBOOK.md).

## Primer piloto real

Catálogo autenticado: 22 voces y 9 modelos, incluidos Eleven v4/v4 Turbo. Juampa disponible. Una muestra de374caracteres,25segundos, convertida a OGG/Opus y enviada manualmente al44 desde WhatsApp institucional: recibo Entregado y reproducción completa confirmada por el propietario. Se aceptan proveedor/catálogo y compatibilidad/reproducción (P19.1 yP19.4). El propietario solicita mejorar la naturalidad: se prepara interpretación por perfil, instrucciones orales y controles compatibles por modelo, con nueva muestra v4. La voz automática sigue apagada hasta el piloto. No se declara P19al100%.

## Controles y cuatro saludos publicados

2fd5214 saludable en Coolify. Estabilidad, similitud e idioma elegidos del catálogo funcionan por perfil; Entonación del saludo ofrece Natural, Cálida, Tranquila y Animada para v4/v3. Se generaron cuatro muestras con idéntico texto y voz Juampa y las cuatro figuran entregadas al44 en ese orden. La reproducción desde historial y descarga privada se verificaron sin nuevas generaciones. El propietario aún debe elegir la entonación.

Piloto guardado en revisión8: sólo el hilo institucional del44, modo nota de voz entrante, máximo1audio automático y60segundos. Chat de vuelta en IA después de los envíos manuales. Pendiente nota entrante real, comprobar respuesta Gemini/Eleven, cupo y cierre de asignaciones/operación antes de aceptar P19al100%.143backend y20frontend pasan; dos pruebas locales omitidas por multimedia.

## Audio entrante real y configuración vigente

Se corrigió el webhook: registraba audio pero sólo programaba Gemini para texto. Tras11085da, dos notas entrantes reales generaron respuestas personalizadas con Juampa/v4, de18segundos cada una; recibos Leído y Entregado. No se repitieron los audios antiguos sin respuesta. Controles multimedia heredados de IA general se sustituyen por un enlace a Voces y audios.

La versión11 guardada desde el lado del propietario se observó con alcance todas las conversaciones, máximo3audios por hilo,60segundos, saludo Tranquila, estabilidad40% y similitud91%. Esta revisión no activó alcance global ni reemplazó esos ajustes. Se conserva el historial del piloto44 anterior. P19 mantiene2/5hasta terminar aceptación de asignaciones, cupo/Humano y operación; no confundir entrega de dos respuestas con cierre integral.

El titular confirmó que ambas respuestas automáticas se escuchan completas y responden a sus preguntas. Se acepta P19.3 en alcance técnico: contexto e instrucciones aplicados a notas reales, con guardas de Humano/cupo previamente comprobadas en PG con proveedores simulados y rollback. P19 queda3/5(60%). Pendientes P19.2, asignación de varias voces, yP19.5, aceptación operativa final de consumo/pausa/recuperación. No se declara eficacia comercial, finanzas SIIE completas ni llamadas.
