# Motor de agentes por etapa y margen de salida

Publicado: backend 9178c8b saludable en Coolify, despliegue jtef0rendpxohoyacc404cgw (4m23s). Frontend inicial aflhhneruftyxzlhwth3mvky Success45s. Ajuste visual ee693ea, despliegue lbufwtcxjihekxuqlh9ogbu8 Success45s: general Admisiones CBN versión10 y especialista Barismo versión3 muestran principal heredado Sonnet4.6, salida4000 y tarifas efectivas3/15.

## Diagnóstico

La ficha general mostraba Gemini 3.1 Flash Lite, mientras el motor P21 global ya tenía OpenRouter Sonnet 4.6 como principal y Sonnet 5.5 de respaldo. Eso no demostraba una llamada a Flash Lite en cada turno. Sí existía una dependencia real: el trabajador exigía perfil y credencial Gemini antes de ejecutar el principal global. El simulador sin elección explícita tampoco heredaba ese motor. Los fallos PostgreSQL documentados anteriormente son otra causa y no se atribuyen a cuotas de Gemini.

## Cambio

- IA general y especialistas heredan el motor institucional. Sus instrucciones, skills, fuentes, memoria, asignación de voz y permisos siguen perteneciendo al agente.
- Una ruta de apertura opcional se aplica sólo en las etapas CRM activas seleccionadas por clave. La pregunta y el turno pendiente completo tienen prioridad: financiación, objeciones, comparación, decisión y seguimiento conservan el principal comercial incluso en Nuevo.
- Apertura fallida: principal comercial y después respaldos aprobados, sin regresar al modelo propio antiguo. Se conserva la revisión de catálogo/capacidades/precios y las reservas por intento. Cambiar modelo no permite enviar en Humano.
- El simulador sin modelo explícito hereda el motor; las pruebas explícitas P22 conservan su modelo exacto. Sin ficha CRM vinculada utiliza el principal comercial. El simulador de agente admite un alternativo; la cola automática conserva la lista completa de respaldos P21.
- El trabajador ya no exige una clave Gemini para texto/imágenes si el motor elegido usa OpenRouter. La interpretación de audio es una etapa aparte, con el modelo de audio seleccionado en APIs y modelos. La síntesis sigue siendo ElevenLabs.
- Máximo común de salida configurable entre 512 y 8000 tokens, independiente del presupuesto acumulado y del tamaño visual de cada parte. La propuesta operativa es 4000; las reglas siguen exigiendo mensajes breves y contratos completos. No implica cobrar ni generar siempre ese máximo. Las reservas son conservadoras, no facturas de consumo real.
- Se evita una segunda reserva inicial completa para la generación que ya reserva P21 tras validar el catálogo. Se mantienen reservas de ASR y de cada alternativa.
- Los perfiles muestran el modelo efectivo heredado; sus versiones históricas se conservan sin reescribir 28 perfiles. Desactivar el motor central haría reaparecer sus configuraciones propias: revisar antes de hacerlo.

## Comprobación local

334 pruebas backend focalizadas aprobadas, incluida selección por necesidad/etapa, ausencia de dependencia Gemini en texto, cambio de contexto, control Humano, ASR e imágenes. Selección solapada con rondas anteriores; no suite completa verde. Se actualizó un contador de biblioteca de 34 a las 37 guías existentes y se aisló el doble de ASR de consultas de cola ya cubiertas por otros tests.

21 pruebas frontend focalizadas, tipos, ESLint de archivos modificados y build institucional aprobados. ESLint global informa 8 errores y 4 advertencias en archivos ajenos a este cambio, incluidos ChannelSettings, AdmissionsPanel y vistas multimedia; no se declara lint global verde. Advertencia histórica de bundle grande conservada.

## Publicación y aceptación

Política guardada nativamente en revisión IA34; selección de audio en Modelos5 actualizó IA35, conservando el motor. Reconsulta nativa confirma apertura OpenRouter google/gemini-3.8-flash en Nuevo y Calificación; principal OpenRouter anthropic/claude-sonnet-4.6; respaldo anthropic/claude-sonnet-5.5; salida4000 y respaldo por timeout activos. Las tarifas de apertura se cargaron del catálogo: 0,75/3,75 USD por millón de entrada/salida. Sonnet4.6 conserva3/15 y Sonnet5.5 conserva2/10. Audio Gemini gemini-3.8-flash recargado desde la configuración guardada. Las cuotas del servicio de interpretación Gemini son independientes de los modelos de conversación en OpenRouter; no se acredita una nueva transcripción real.

Catálogo nativo: 28 agentes. Especialista Barismo versión3 muestra el motor heredado, salida4000 y presupuesto institucional ilimitado; sus versiones propias antiguas no se reescribieron. Un ensayo sin proveedor verificó la ruta comercial y max_tokens4000 antes de la llamada. Dos consultas generativas aisladas, sin CRM ni envíos a clientes:

| Caso | Modelo real | Entrada | Salida | Generación | Estimación USD |
|---|---|---:|---:|---:|---:|
| Objeción, abono menor y memoria ficticia | Sonnet4.6 heredado | 16873 | 263 | 8,892s | 0,054564 |
| Apertura para emprender una cafetería | Flash3.8, selección explícita del simulador | 11529 | 211 | 4,869s | 0,009438 |

Costo estimado conjunto: USD0,064002 con las tarifas de catálogo/topes observadas; no recibo de facturación. Los casos y tamaños de contexto son distintos: no es una comparación homogénea de calidad ni una nueva aceptación P22. Flash conservó el límite aislado700 de la prueba explícita; no modificó el máximo4000 de producción. Sonnet mantuvo nombre/objetivo, respondió al abono menor de770.000 y al calendario completo, sin cambiar de programa. Flash produjo una respuesta completa sobre la formación. La clasificación automática real de etapas en un chat aún no se acredita por estas simulaciones; los tests cubren su prioridad, memoria y guardias. La espera configurada60s es anterior a la inferencia y no se suma a estas latencias de generación.

La prueba específica de selección de audio añade un caso:19 pruebas del archivo de etapas pasan (18 ya incluidas en las334). Sin afirmar suite completa verde, transcripción nueva, entrega real de prueba, cero fallos universales ni aceptación comercial de P22.

Sin DDL, seeds, servicios nuevos ni escrituras SIIE. P23 sigue con 0/9 criterios aceptados; P22 conserva 3/5 técnico y 0/5 comercial. Otros pendientes del Inbox y el envío incierto de horarios no se reenvían con esta configuración.
