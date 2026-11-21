# P22 · Comparación real de modelos

Corte inicial: 20-11-2026. Presupuesto autorizado: USD 10 para toda la comparación.
No se recargó saldo ni se cambió el modelo de los agentes activos.

## Qué se midió

Cinco casos idénticos por modelo: apertura con valor, objeción y financiación,
cambio Barismo→Software con memoria ficticia, seguimiento ante comparación y
solicitud de revisión humana. Cada caso conservó las mismas fuentes proyectadas
por intención y las guías consultadas completas, sin recortar condiciones de pago;
el hash del contexto se contrastó por caso. Especialista seleccionado manualmente,
no enrutamiento automático entre etapas. Tope común de salida: 700 tokens.

25 respuestas válidas de cinco modelos, más dos intentos inválidos de DeepSeek y
Qwen. Los cuatro intentos preliminares del contrato antiguo no se usan para
calificar la venta, pero su consumo sí cuenta. El simulador no envía ni escribe
memoria/CRM. Las muestras enviadas después al propietario son copias manuales.

Todos los candidatos, incluido Gemini, utilizaron OpenRouter para mantener la
misma pasarela y formato JSON. Esto no mide la latencia de la API directa de
Google usada actualmente en producción. La prueba manual tiene un contrato de
salida diferente al de los mensajes/comentarios automáticos: requiere piloto.

## Tiempo y costo de la matriz inicial

| Modelo | Mediana de tiempo | Costo medio por respuesta | Aproximación por 1.000 respuestas iguales | Palabras medias |
|---|---:|---:|---:|---:|
| Gemini 3.1 Flash Lite | 2,68 s | USD 0,002850 | USD 2,85 | 95 |
| Claude Sonnet 4.6 | 9,38 s | USD 0,042036 | USD 42,04 | 129 |
| Claude Haiku 4.5 | 4,43 s | USD 0,013970 | USD 13,97 | 123 |
| GPT-4.1 mini | 3,00 s | USD 0,004034 | USD 4,03 | 90 |
| Mistral Small 4 | 3,30 s | USD 0,001704 | USD 1,70 | 81 |

Tokens reportados por el proveedor × tarifas del catálogo autenticado de cada
modelo. No son factura ni promesa de precio; no se recibieron contadores de
caché. No incluyen WhatsApp, ElevenLabs, impuestos u otros cargos. La proyección
por mil sólo multiplica esta muestra de contexto; un historial más largo cambia
el costo. Una respuesta breve no elimina el costo de leer fichas y skills.

## Revisión comercial y de precisión

| Modelo | Lo mejor observado | Límites encontrados |
|---|---|---|
| Sonnet 4.6 | Mejor diagnóstico de la objeción; pregunta qué pesa más del pago. Explica el valor y conserva la memoria al cambiar de carrera. | Más lento, caro y extenso. Alguna formulación excesiva sobre autonomía profesional; dice conectar de inmediato sin comprobar la gestión. |
| GPT-4.1 mini | Mejor equilibrio de brevedad, fechas, alcance financiero y tiempo. Conserva nombre, ciudad, objetivo y cuatro semestres de Software. | Venta algo genérica y emoji de café arrastrado al hablar de Software. La derivación debe describir lo que realmente hará el sistema. |
| Gemini | Rápido y económico; explica el beneficio y el cambio de carrera. | En financiación omite la exclusión del uniforme. En el caso ambiguo de derivación retoma el programa del historial antiguo. |
| Haiku 4.5 | Buena continuidad y seguimiento; no confirma matrícula y activa handoff. | Más costoso que GPT sin ventaja clara en esta muestra; respuestas largas, cierre prematuro y condición de prácticas atribuida al desempeño sin prueba suficiente. |
| Mistral Small 4 | Menor costo, brevedad y velocidad razonable. | Omite ciudad solicitada y condiciones financieras. Afirma que las prácticas no son remuneradas, cuando esa condición debe confirmarse. No recomendarlo para atención autónoma con estos resultados. |

Los cinco activaron handoff ante la solicitud humana y ninguno confirmó matrícula
ni garantizó empleo en España. Eso no significa que cada detalle de su respuesta
sea correcto. La decisión de atender en Humano sigue siendo una guarda del
backend, no una promesa del modelo. La muestra no prueba mayor conversión.

DeepSeek v4.1 Flash y Qwen 3.6 Plus devolvieron una respuesta no utilizable por la
pasarela, sin uso reportado al CRM. Se conserva reserva de costo, sin repetir el
POST incierto. No se les asigna una nota de venta ni se presume gratuidad.
Sonnet/Haiku 5.5 estaban en catálogo pero no admitían la temperatura de esta ruta;
se rechazaron antes de generar. Eso es compatibilidad del adaptador, no prueba de
mala calidad del modelo. No se relajaron privacidad ni permisos para forzarlos.

## Propuesta por etapa, todavía sin activar

| Etapa CRM | Candidato para piloto | Criterio |
|---|---|---|
| Nuevo / Calificación | GPT-4.1 mini; Gemini como opción económica | Respuesta breve, datos declarados y una pregunta útil. |
| Programa definido | GPT-4.1 mini | Explicación y continuidad al cambiar de especialista. |
| Propuesta y financiación | GPT-4.1 mini, Sonnet para una objeción compleja | Conservar cada cuota, fecha, vigencia y exclusión; no vender sólo el abono. |
| Dudas y objeciones | Sonnet 4.6 con estilo breve | Mejor diagnóstico y argumentación consultiva observados. |
| Seguimiento | GPT para seguimiento rutinario; Sonnet si hay duda compleja | Próximo paso voluntario y respeto a la decisión. |
| Inscripción / Matriculado | GPT para orientar; confirmación institucional humana | El modelo no acredita pagos, matrícula o elegibilidad. |
| Cerrado sin matrícula | GPT con consentimiento de seguimiento | Sin insistencia automática ni urgencia inventada. |

Haiku queda como alternativa a revisar, no elección automática por su nombre o
familia. Ningún cambio se publicará en los agentes antes de revisar las muestras
y probar continuidad/reversión del enlace con el pipeline.

## Resumir sin perder contexto

El contexto de entrada y la memoria pueden permanecer intactos mientras se pide
una salida más breve. La instrucción se aplica antes de generar: una idea por
mensaje, hasta tres párrafos y una pregunta útil. Para financiación la precisión
de cuotas, fechas, vigencia, alcance y exclusiones prevalece sobre la longitud.
No recortar por caracteres una respuesta ya generada ni borrar su final.

Se compararon apertura original/breve y financiación original/breve de Sonnet y
Haiku sobre la misma versión `00c5a54`, sin mezclar con la matriz inicial.

| Modelo / caso | Palabras original → breve | Costo original → breve, USD |
|---|---:|---:|
| Sonnet / apertura | 122 → 66 | 0,047772 → 0,046233 |
| Sonnet / financiación | 176 → 129 | 0,048450 → 0,048000 |
| Haiku / apertura | 108 → 61 | 0,015828 → 0,015380 |
| Haiku / financiación | 116 → 108 | 0,015454 → 0,015769 |

Un menor número de palabras no garantiza igual reducción porcentual del costo:
domina la lectura del contexto y también cuentan las referencias del JSON.
Haiku incluso costó un poco más en el ensayo financiero breve. Sonnet conservó
condiciones pero superó el objetivo de 115 palabras; es una indicación de estilo,
no un recorte obligatorio de datos. El objetivo de apertura de 55–75 sí se cumplió.

## Ampliación comercial y muestras al teléfono

45 respuestas válidas capturadas en 52 intentos pagados, incluidos cuatro
preliminares. Sólo las 25 de la matriz inicial se agregan en su tabla de medias.
Las demás prueban futuras opciones, brevedad, calendario y dirección, con sus
versiones y hashes propios. No se usó un juez LLM pagado.

Costo estimado conocido de toda la comparación: **USD 0,7807282**. Reserva
conservadora de dos intentos sin uso confirmado: **USD 0,0528926**. Total conocido
más reserva: **USD 0,8336208**, dentro de USD10 autorizados. No se presenta como
factura final ni como consumo gratuito de los intentos fallidos.

Se enviaron 30 copias manuales al teléfono de prueba autorizado terminado en44;
los 30 recibos figuraron Leído. Incluyen explicación, financiación, comparación,
diplomas/prácticas/proyección internacional, calendario y versiones breves.
Se restauró el chat a IA y los modelos activos siguen intactos. Son muestras de
contenido identificadas; no prueban un cambio productivo del modelo ni la
cadencia automática de sus mensajes. La aceptación comercial del titular sigue
pendiente.

Skillsv6 agrega una prioridad explícita y el backend deriva `calendar_benefit`
del menor abono vigente sólo con fechas completas y ordenadas. Distingue la
siguiente cuota de otros cargos y calcula «año entrante» desde Bogotá, sin
copiar una frase fija del playbook. Las cinco respuestas nuevas aprovecharon el
calendario, con calidad desigual. Gemini añadió una reserva de cupo no respaldada;
esa muestra se rotuló como defecto, no como condición aprobada. GPT omitió la
vigencia en esa ejecución aunque la había conservado en la matriz inicial.
Por eso la recomendación no sustituye guardas y revisión de condiciones.

Sonnet fue el más completo al distinguir los dos títulos principales y el tercer
diploma opcional. Ningún modelo debe vender homologación, permiso laboral o
empleo internacional como automáticos. Las prácticas conservan requisitos,
disponibilidad y selección; no se generaliza gratuidad o remuneración.

## Ubicación y visita presencial

El propietario detectó en el Inbox una dirección no respaldada que Gemini repitió
desde su propio historial. Las fuentes recuperadas del especialista afectado no
la contenían. Se incorpora como dato revisado por el titular la oficina de
Admisiones: Avenida del Libertador #13-45, frente a la Registraduría, Santa Marta.
No se atribuye a una página web ni se confirma como sede académica.

El historial de la IA no prueba datos institucionales. Una corrección debe
reconocerse; no se inventan horarios ni la presencia física de un empleado.
La pregunta por atención presencial se resuelve ofreciendo conversar con el
equipo de Admisiones, sin presentación innecesaria de asistente virtual ni
prometer que pueden encontrar físicamente al nombre de atención de la IA.
Si preguntan expresamente si es IA, responde con transparencia.

Prueba publicada con historial que contenía la dirección incorrecta: Gemini y
GPT corrigieron la dirección. GPT invitó al equipo de Admisiones sin atribuir
presencia física al agente; Gemini añadió por iniciativa propia una explicación
de identidad IA en la pregunta sobre visita. La pregunta explícita de identidad
se contestó con transparencia. No se configura una identidad humana ficticia.

## Diagnóstico de Instagram/Messenger durante la revisión

El titular reportó un DM sin respuesta. La interfaz confirmó Instagram y
Messenger conectados, webhook habilitado/verificado y salud del token confirmada
por Meta. El hilo Instagram indicado está en IA, con el orientador activo.
Su operación persistida tiene `provider_response_timeout`: generación sin
respuesta comprometida, no una desconexión de Meta. El fallo se conserva para
revisión; no se repite automáticamente un resultado incierto.

Se preparó la recuperación nativa de ese último DM. La ejecución requiere
instrucción expresa para enviar una respuesta real a la persona; no se recuperan
en bloque operaciones antiguas. No se atribuye a Messenger la misma causa sin
localizar el mensaje afectado. La recepción reciente de un evento puede ser un
recibo, no necesariamente un DM nuevo. Este incidente no se usa como una llamada
de la comparación ni prueba que el cambio de modelo activo haya ocurrido.

## Estado de P22

Tres hitos técnicos trabajados de cinco: casos, catálogo/compatibilidad y
comparación aislada. Faltan la elección/revisión del titular, el enlace de modelos
con el pipeline y el piloto supervisado con reversión. Las muestras manuales al44
no sustituyen ese piloto. P13 y P21 conservan su aceptación del alcance inicial;
no se cambian los denominadores originales del roadmap.

173 pruebas backend seleccionadas pasan; 21 de frontend, tipos, lint y build del
simulador habían pasado, con advertencia histórica de bundle. Backend final
`00c5a54` publicado saludable en Coolify; fuentes/ubicación y política comercial
son cambios centrales, sin sustituir Gemini en agentes activos.

Evidencia agregada: `artifacts/live/p22-model-comparison-20261120.json`.
Respuestas e importes comerciales permanecen en el registro privado ignorado por
Git. Las ampliaciones no se mezclan con las estadísticas de la matriz inicial.
