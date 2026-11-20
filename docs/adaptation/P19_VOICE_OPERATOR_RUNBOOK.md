# P19 · Voces y notas de audio

Estado vigente: P19 aceptada5/5 en su alcance técnico inicial; evidencia en artifacts/live/p19-close-review-20261119.json. Los apartados de piloto inferiores conservan su historia. La implementación se valida por separado de su aceptación real. Las llamadas siguen en P20. No requiere tablas nuevas, seeds ni cambios en SIIE.

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

## Estado de entrega del cierre

Tres perfiles disponibles: Juampa predeterminada y dos alternativas Sarah/George, sin asignaciones permanentes de escuela decididas por el ensayo. El agente existente volvió a Automática. Política15 conserva el alcance guardado por el propietario y sus topes3audios/60segundos/20000caracteres diarios, modo nota entrante. Para otras voces, crea un perfil desde el catálogo y actualiza la lista en el constructor de agentes.

Cuenta ElevenLabs: la consulta de uso requiere que la clave permita la lectura de usuario/suscripción. Si falta ese permiso, la generación puede seguir funcionando; revisa el permiso de lectura de la clave sin exponerla. El contador puede retrasarse y no equivale a una factura por generación. Las dos muestras de cierre reservaron262caracteres; el proveedor no devolvió conteo facturado individual. No se interpreta un contador inmóvil como consumo gratuito. Las muestras privadas vencen en24h y no se envían automáticamente.

## Ambiente de oficina y tecleo — ampliación 19-11-2026

En Ajustes → Voces y audios, cada perfil tiene Ambiente y mezcla de audio.
Los perfiles anteriores conservan el ambiente apagado. Tres volúmenes separados:
voz 20–150%, oficina 0–100% y tecleo 0–100%; cero silencia una pista de fondo.
La reducción automática está activada por defecto: detecta la voz original,
reduce ambas pistas durante el habla y las recupera suavemente en las pausas.
Versión v2: oficina con teléfonos e impresora y tecleo de portátil grabado;
fuentes CC0 empaquetadas, sin diálogos ni conversaciones de clientes. Las fuentes
y su licencia están en backend/app/institutional/voice_assets/sources.json.
La v1 sintética fue rechazada por su sonido; se conserva esa evaluación histórica.
No se promete que sea una grabación del lugar real donde opera el asesor.

Prueba antes de guardar:
1. Selecciona Juampa en Escucha antes de activar y genera una muestra corta.
   Esta única generación usa caracteres de ElevenLabs y conserva sus reservas.
2. En Mezcla de la muestra activa el ambiente y ajusta los tres volúmenes.
3. Pulsa Escuchar mezcla. Se procesa la voz original sin otra llamada de síntesis,
   sin guardar configuración y sin enviar mensajes. Puedes repetir este paso.
4. Cuando te guste, pulsa Usar esta mezcla en el perfil. Esto crea un borrador.
5. Pulsa Guardar configuración de voz para aplicarlo a audios futuros.

La muestra y su original privado vencen en 24 horas y sólo puede escucharlos el
usuario que los generó, mientras mantenga permiso. La mezcla requiere FFmpeg;
dos trabajos simultáneos como máximo, 25 segundos por trabajo, duración hasta
300 segundos, inspección final OGG/Opus mono y límite de picos. No corta el texto
ni reinicia cupos, ni modifica voz/modelo, control Humano o credenciales.
Las muestras anteriores al despliegue no tienen original separado: genera una
muestra nueva para probar la mezcla. Las copias originales de envíos automáticos
se eliminan al terminar; sólo se conservan temporalmente en muestras privadas.

El titular aplazó la prueba al teléfono 44 hasta que continuemos. No se enviarán
nuevos audios de prueba ni se activará ambiente global sin ese recorrido. P13
Académico/agentes comerciales queda para otra petición; sus cambios locales no
forman parte del commit de esta ampliación.

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

### Revisión sonora v2 — 20-11-2026

El titular confirmó mezcla, faders y generador, pero rechazó la oficina y el
teclado sintéticos. Se sustituyen por fuentes CC0 de Fupicat y se2001, con
procedencia y SHA-256 verificables. No hay nuevas llamadas al proveedor para
crear el fondo, ni se modifica la política de audios. Publicación y escucha
comparada pendientes de esta revisión; no aceptar automáticamente su realismo.

### Recuperar una muestra para mezclar sin consumo

En Actividad y consumo, junto a una muestra privada vigente, pulsa
**Preparar mezcla sin generar**. Recupera el original y el mezclador durante
24horas para su mismo propietario; no llama a ElevenLabs, no modifica el perfil
ni envía mensajes. Ajusta los faders y pulsa Escuchar mezcla. Las muestras
anteriores a la ampliación no tienen original separado para esta operación.
