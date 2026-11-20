# P19 · Voces y notas de audio con ElevenLabs

Corte: 19 de noviembre de 2026. **Aceptada en su alcance técnico inicial, 5/5 unidades (100%).** Por decisión del propietario, todas las llamadas, agentes durante llamadas, seguimiento telefónico y supervisión de llamadas pasan a P20. Esta división reemplaza el primer borrador conjunto, aún sin aceptar. No cambia los 56 criterios ni los 279 hitos originales.

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

## Revisión de cierre P19 — 2026-11-19

El propietario solicitó cerrar asignaciones y operación. Se añade selección del perfil de voz al crear/editar un agente institucional, persistida en su configuración versionada; se elige entre perfiles activos, preparados con voces propias o predeterminadas del catálogo autenticado. Actualizar voces disponibles incorpora perfiles nuevos sin perder el borrador. Cambiar voz no activa IA ni amplia cupos. Selección directa del agente prevalece sobre asignación central del agente, escuela y predeterminada; voz/modelo fijados en el hilo tienen prioridad. Un perfil fijado pausado o cambiado conduce a texto, sin cambiar silenciosamente la voz. Escuelas elegidas del catálogo Académico, sin nombres manuales.

Comprobar voz y límites es un recorrido de lectura: usa las mismas funciones de selección/reglas, sin proveedor, archivos, reservas ni mensajes. Un chat real conserva su contexto y requiere inbox.read; no acepta agente/programa externos al hilo. La simulación sin chat no confirma control, alcance, catálogo ni credencial. Consumo distingue reservas, conteos reportados por ElevenLabs y ausencia de recibo, incertidumbre y operaciones en curso. Consulta de cuenta sólo GET user/subscription, sin facturas ni datos de pago en la respuesta, con autorización/clave revalidadas. La vista de cupo por chat conserva reservas y perfil fijado.

Pruebas locales cubren selección directa/escuela/predeterminada/fijada, pausa, máximos, saldo interno, duración y resultados inciertos; no se fuerzan fallos de Meta/ElevenLabs en producción. Las pruebas nativas históricas bajo rollback conservan sus límites. La aceptación adicional permanece pendiente del despliegue y las pruebas de UI/catálogo/asignación/consumo reales de este corte. No se declara 100% por completar código o contar tests.

## Cierre técnico aceptado — 2026-11-19

Se aceptan P19.2 y P19.5: **P19 queda5/5,100% en su alcance técnico inicial de notas de voz WhatsApp**. Backend0fd449c saludable, rolling update22:04:43UTC. Tres perfiles reales disponibles: Juampa propia, Sarah y George predeterminadas, todos seleccionados desde el catálogo de la clave. Se guardó una elección directa Juampa en el agente existente, se comprobó su prioridad sobre Salud→Sarah y se restauró Automática. Simulaciones de TIC→George y Salud→Sarah comprobadas; las asignaciones temporales se quitaron. El formulario de creación ofrece los tres perfiles. El hilo real conserva Juampa fijada y1de3reservas, incluso después de recargar.

Pausa/restauración de George sin tráfico verificadas en versiones14/15. La consulta real de cuenta ElevenLabs responde; dos muestras privadas v4 de68caracteres de texto,5segundos cada una, reservan131caracteres cada una incluyendo dirección oral. Reservas+262, sin conteo facturado por generación disponible. El contador inmediato de cuenta no cambió: no significa gratuidad ni coste cero; puede tener retraso e incluye otros proyectos. El reproductor privado se recuperó tras recarga sin sintetizar otra vez y cargó5,2065segundos de audio.

Comprobaciones publicadas sin consumo: Humano bloquea voz; tamaño excesivo y duración estimada120s sobre60s continúan íntegros por texto; entrada sin nota no cumple el modo elegido. Se conservan pruebas nativas PG con rollback y proveedores simulados para agotamiento de cupo, resultado incierto, deduplicación y cambio a Humano durante síntesis. No se provocaron fallos pagados ni caídas de proveedores en producción.242backend y56frontend seleccionadas, tipos/lint/build pasan; advertencia previa de bundle permanece. Evidencia de cierre: [p19-close-review](../../artifacts/live/p19-close-review-20261119.json).

Estado final: política15, predeterminadaJuampa/Tranquila, alcance global previamente guardado por el propietario, modo nota entrante, máximo3audios/60segundos y20000caracteres en24h. No se envió WhatsApp nuevo por este cierre. Calidad contextual y reproducción real ya confirmadas por el titular en P19.3/P19.4; las muestras de Sarah/George no sustituyen esa aceptación ni prometen eficacia comercial. P20 llamadas y las demás fases adicionales siguen pendientes. El historial superior de implementación conserva las condiciones de cada corte.

## Ampliación: ambiente y vista previa — 19 de noviembre de 2026

Oficina y tecleo originales sintéticos, control independiente de ambas pistas y
de la voz, reducción automática durante el habla y recuperación suave en pausas.
Cada perfil conserva ambiente apagado por defecto. La muestra retiene su original
privado para escuchar otras mezclas sin una segunda síntesis de ElevenLabs.
Escuchar no guarda: Usar esta mezcla crea borrador y Guardar configuración aplica
a los siguientes audios. El titular solicitó expresamente este ensayo previo.

Pasan66 pruebas backend,16 frontend, tipos, ESLint modificado, Ruff y build del
workspace (advertencia de bundle anterior conservada). FFmpeg real comprobó
ducking, duración y picos. Evidencia: `artifacts/live/p19-ambience-review-20261119.json`.
Publicación y preview real pendientes al corte; reproducción con el44 aplazada
por el titular. No se acredita su aceptación de la nueva calidad sonora.
El cierre inicial5/5 se conserva, sin cambiar denominadores. P13 queda para otra
petición; biblioteca v5 y cambios de esa fase se conservan fuera de este commit.

### Resultado publicado de la ampliación — 19-11-2026

Backend/frontend d09b969 publicados y saludables en Coolify. Vista previa real
Juampa/Tranquila de12,2465segundos; navegador readyState4 sin error de audio.
270caracteres reservados una vez. El remix local conservó6561caracteres diarios
y la configuración versión22 sin escrituras. Deslizador oficina12→13→12 y aviso
de vista previa desactualizada comprobados. Mantener distinguido este consumo
reservado del coste facturado, que el proveedor no devolvió individualmente.

El titular autorizó posteriormente una muestra al44: se envió el mismo archivo
de la vista previa (voz100%, oficina12%, teclado16%, reducción automática) y Meta
confirmó Entregado. Falta su escucha y elección de balance; no afirmar calidad
aceptada por el recibo. La política vigente conserva máximo5audios,60segundos,
20000caracteres diarios y Juampa/Tranquila. No se activó ambiente global.
P13 permanece fuera de esta entrega, pendiente para otra petición.
