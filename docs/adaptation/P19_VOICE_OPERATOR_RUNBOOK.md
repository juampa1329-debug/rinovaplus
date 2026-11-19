# P19 · Voces y notas de audio

La implementación se valida por separado de su aceptación real. Las llamadas siguen en P20. No requiere tablas nuevas, seeds ni cambios en SIIE.

## Configuración

1. Ajustes → APIs y modelos → Credenciales → ElevenLabs: guardar la clave directamente. Debe permitir leer voces/modelos y generar texto a voz. La clave permanece cifrada y nunca se devuelve al navegador.
2. Ajustes → Voces y audios: cargar el catálogo y crear perfiles con una voz y un modelo disponibles, seleccionados por nombre. También se pueden consultar desde APIs y modelos; las selecciones de texto, visión, audio y respaldos siguen sus catálogos.
3. Elegir perfil predeterminado y, opcionalmente, agentes o escuelas. Agente tiene prioridad; escuela sólo procede del programa realmente asignado en CRM, nunca de inferirlo por una pregunta. El primer perfil reservado queda ligado a la conversación; cambiar o desactivar esa voz hace que el hilo continúe por texto.
4. Guardar perfiles antes de generar una muestra. La muestra consume caracteres, es privada del operador, vence a las 24 horas y no se envía a contactos. Repetir el mismo intento consulta el resultado sin repetir la petición de pago.
5. Activar la voz sólo después de revisar el perfil. El máximo de audios pertenece al hilo y no se reinicia por reinicios o IA/Humano. **0 audios por conversación significa sólo texto.**

## Cuándo usar voz y cuánto dura

- Modos: nota de voz del cliente; explicación larga; cualquiera de ambas; ambas a la vez. Longitud mínima configurable en caracteres.
- Duración máxima en segundos: **0 desactiva el límite de duración configurado**. El procesador compartido admite archivos de hasta cinco minutos; no representa duración infinita ni elimina los otros límites.
- Antes de sintetizar se estima la duración según palabras, caracteres y pausas. Es una estimación conservadora, no una garantía del proveedor. Si supera el máximo, se conserva íntegra la respuesta por texto, sin llamar a ElevenLabs.
- La duración real se verifica después de convertir. Si supera el máximo, el audio se descarta completo; nunca se recorta. Este intento puede haber consumido caracteres y un lugar del cupo.
- Hay un máximo de caracteres por audio y un tope para las últimas 24 horas; 0 en este último significa sin tope diario interno. El límite por conversación sigue vigente.
- Si falla ElevenLabs o falta saldo, Gemini continúa por texto. El control Humano cancela la generación/publicación pendiente y no permite nuevos envíos automáticos.

## Operación y límites

Las reservas durables usan ProviderOperation y el bloqueo de escritura de PostgreSQL. Reservar consume un lugar antes de cualquier síntesis; los intentos inciertos no se reintentan automáticamente. El sistema no debe liberar un lugar suponiendo que el proveedor no cobró. El historial muestra caracteres reservados; los recibos de ElevenLabs se conservan cuando devuelve conteo/request-id. No se inventa un coste en dólares: depende del plan y del modelo.

Las notas entrantes se descargan e inspeccionan antes de enviarlas como audio a Gemini. Se respetan vínculo de cuenta/conversación, huella del archivo, epoch IA/Humano, modelo/credencial y contexto revisado. La respuesta textual de Gemini es la única fuente del TTS. El MP3 se convierte mediante el inspector probado a OGG/Opus mono; WhatsApp recibe una nota de voz, no un archivo MP3 renombrado. El mensaje conserva el texto en CRM y los recibos reales del outbox.

Una caída tras reservar puede dejar una generación en curso o incierta y un archivo reservado sin mensaje. No reenviar ni restaurar su estado a pendiente: revisar el padre Gemini, el consumo y el archivo antes de conciliar. Los activos generados quedan vinculados a la cuenta y sujetos al cupo de almacenamiento compartido. Los fallos conocidos no borran evidencias de consumo. Las muestras antiguas se limpian al crear nuevas muestras; su historial permanece.

## Piloto autorizado

El propietario guardó la clave y autorizó usar su voz «Juampa» para pruebas al teléfono terminado en 44. Solicitó una explicación natural sobre estudiar marketing, oportunidades profesionales y trabajo remoto, sin promesas de empleo o salarios. Faltan registrar catálogo real, muestra, envío/reproducción, límite alcanzado, nota entrante y silencio en Humano antes de cerrar las cinco unidades.

Referencias: [catálogo de voces](https://elevenlabs.io/docs/api-reference/voices/search), [modelos](https://elevenlabs.io/docs/api-reference/models/list), [síntesis](https://elevenlabs.io/docs/api-reference/text-to-speech/convert).
