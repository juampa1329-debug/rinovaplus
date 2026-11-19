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

## Naturalidad por perfil

Cada perfil incorpora estilo conversado, calmado, expresivo o neutro; instrucciones de cómo hablar para Gemini y reacciones opcionales sólo cuando el contexto es empático. Las guías de actuación no alteran las palabras ni añaden hechos al texto revisado. v4 recibe sólo estabilidad y semejanza; no se le envían estilo, velocidad, speaker boost ni SSML. v3 usa sus niveles compatibles de estabilidad; otros motores no reciben etiquetas de reacción. Los modelos disponibles se consultan al abrir el panel, incluidos v4/v4 Turbo si aparecen en el catálogo de la clave. La calidad se revisa con muestras, no se garantiza naturalidad perfecta por configurar parámetros.

## Controles de ElevenLabs en RinovaPlus

Cada perfil incorpora deslizadores Estabilidad (creativo→robusto) y Similitud (baja→alta), con valores0–100% y teclado nativo. El estilo propone valores iniciales; el operador puede ajustarlos. v3 adapta estabilidad a sus niveles0/0.5/1. Idioma ofrece Automático o los idiomas de la lista del modelo, sin escribir códigos. Multilingualv2 conserva automático porque su API no permite imponer idioma. Cambiar de modelo vuelve el idioma a automático. El backend valida la selección contra el catálogo antes de un POST de síntesis. No modifica permanentemente la voz en ElevenLabs: los controles se aplican a cada generación.

## Piloto delimitado y saludos

La voz automática usa por defecto Sólo conversaciones seleccionadas. Marca el hilo por cuenta y últimos cuatro dígitos: el servidor comprueba esta lista antes de generar y en la salida. Activarla para toda la institución cambia respuestas reales fuera del piloto y requiere autorización explícita del propietario. La revisión automática rechazó esa activación global durante el ensayo; no se ejecutó ni se sortea con comandos. El piloto autorizado se limita al44.

Entonación del saludo permite Natural, Cálida, Tranquila o Animada en v4/v3. Sólo dirige el primer saludo y conserva las palabras. Probar saludos genera cuatro muestras del mismo texto sin cambiar la voz guardada ni enviar mensajes. Cada muestra consume caracteres; repetir la comparación en la misma vista reutiliza sus intentos. Una respuesta incierta detiene el resto; navegar fuera impide iniciar las generaciones siguientes. El servidor vuelve a comprobar autoridad/control y clave después del catálogo, inmediatamente antes de la síntesis de pago.

La prueba integral nativa usa SQL real y ffmpeg, con Gemini/TTS simulados y rollback. Comprueba entrada de voz, respuesta contextual ligada a outbox, rechazo de archivo cambiado, respuesta por texto tras agotar cupo y cancelación por Humano durante síntesis. Fuente reproducible: artifacts/live/p19-native-worker-rollback-20261119.py. No acredita una conversación comercial real de Gemini por sustituir los proveedores.

## Recuperar una muestra

Actividad y consumo permite escuchar las muestras propias confirmadas de las últimas 24 horas y descargarlas como nota-de-voz.ogg, sin volver a generar ni consumir caracteres. El acceso sigue siendo privado y comprueba usuario, vigencia, archivo y huella. El reproductor se ajusta al ancho de su tarjeta. No se comparten muestras de otro operador mediante este historial.

## Asignar voces desde el constructor

1. En Voces y audios, carga el catálogo autenticado y prepara un perfil para cada voz que quieras ofrecer (propia o predeterminada de ElevenLabs). El modelo y la voz se eligen del catálogo, nunca se escriben IDs.
2. En Agentes, al crear o editar, elige Perfil de voz para WhatsApp y Guarda configuración. Automática usa las asignaciones centrales/escuela/predeterminada. Los perfiles nuevos aparecen con Actualizar voces disponibles.
3. Para escuelas, abre Asignar agentes y escuelas del perfil y elige las escuelas que existen en Académico; Actualizar agentes y escuelas trae las recién creadas.
4. Comprueba la voz y los límites sin generar audio. Sin chat es una simulación de asignación; con chat usa control/contexto/reservas reales. No confirma que el proveedor vaya a aceptar la siguiente generación.
5. Revisa consumo: reservados no equivalen a caracteres reportados ni a dólares. Sin recibo no significa gratis. Consultar uso de la cuenta informa toda la cuenta, incluidos otros proyectos, y no modifica plan/sobreconsumo.

Una voz fijada no se reemplaza por asignaciones nuevas; un perfil/modelo cambiado o pausado hace continuar el hilo por texto. Crea otro perfil para conservar los anteriores. Cambiar IA/Humano o redesplegar no reinicia el cupo. Ante resultado incierto, revisa el recibo del proveedor y el historial; no repitas la síntesis ni liberes la reserva suponiendo que no hubo consumo.
